"""
Benchmark depth backends: PyTorch FP32 vs ONNX FP32 vs ONNX INT8.

  python tools/bench_depth.py --checkpoint backend/checkpoints/depth_anything_v2_metric_hypersim_vits.pth \
      --da2-root backend/Depth-Anything-V2

Method:
- Every backend runs in a fresh subprocess, so model load time and peak memory
  are measured per backend and nothing is shared between them.
- --repeats full passes; the backend order rotates each pass so slow drift
  (thermal throttling, background load) does not always hit the same backend.
- All backends use the same fixed thread count.
- Accuracy uses standard monocular-depth metrics with FP32 as the reference.
- results.json records versions, git commit, and SHA-256 of every model file
  and the frame set, so a number can be traced back to exactly what produced it.
"""

import argparse
import hashlib
import json
import os
import platform
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from services.depth_backends import OnnxDepth, TorchDepth, preprocess 

WARMUP = 5
BACKENDS = ["torch", "onnx_fp32", "onnx_int8"]


# ---------- environment ----------

def sh(cmd):
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, cwd=ROOT).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def cpu_name() -> str:
    if sys.platform == "darwin":  # Apple Silicon: platform.processor() just says "arm"
        name = sh(["sysctl", "-n", "machdep.cpu.brand_string"])
        if name:
            return name
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def default_threads() -> int:
    # On Apple Silicon, use only performance cores. Letting work spill onto the
    # slower efficiency cores makes timings noisier and less comparable.
    if sys.platform == "darwin":
        n = sh(["sysctl", "-n", "hw.perflevel0.physicalcpu"])
        if n and n.isdigit():
            return int(n)
    return os.cpu_count() or 1


def pkg(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def sha256(paths) -> str:
    h = hashlib.sha256()
    for p in paths:
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()[:16]


def model_file(a, backend) -> Path:
    if backend == "torch":
        return Path(a.checkpoint)
    return Path(a.models) / f"dav2_{backend.split('_')[1]}.onnx"



def worker(a):
    frames = sorted(Path(a.frames).glob("*.jpg"))
    inputs = [preprocess(cv2.imread(str(f))) for f in frames]

    t = time.perf_counter()
    if a.backend == "torch":
        import torch
        torch.set_num_threads(a.threads)
        est = TorchDepth(a.checkpoint, a.da2_root)
    else:
        est = OnnxDepth(str(model_file(a, a.backend)), a.threads)
    load_ms = (time.perf_counter() - t) * 1000

    for x in inputs[:WARMUP]: 
        est.raw(x)

    times, outs = [], []
    for x in inputs:
        t = time.perf_counter()
        outs.append(est.raw(x).squeeze())
        times.append((time.perf_counter() - t) * 1000)

    if a.save:  # outputs are deterministic, so one run's outputs are enough
        np.save(Path(a.tmp) / f"{a.backend}.npy", np.stack(outs))

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mb = rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024  # macOS: bytes, Linux: KB
    out = {"ms": times, "load_ms": load_ms, "peak_rss_mb": peak_mb}
    json.dump(out, open(Path(a.tmp) / f"{a.backend}_r{a.run}.json", "w"))


# ---------- accuracy ----------

def depth_metrics(ref: np.ndarray, test: np.ndarray) -> dict:
    """Standard monocular-depth metrics, with `ref` as ground truth."""
    valid = ref > 0.1  # ignore near-zero reference depth, where relative error blows up
    r, t = ref[valid], test[valid]
    rel = np.abs(t - r) / r
    ratio = np.maximum(t / r, r / t)
    per_frame = [float((np.abs(tf - rf) / rf)[rf > 0.1].mean()) for rf, tf in zip(ref, test)]
    return {
        "abs_rel_pct": float(rel.mean() * 100),     # mean |t-r|/r
        "rmse_m": float(np.sqrt(np.mean((t - r) ** 2))),
        "mae_m": float(np.abs(t - r).mean()),
        "delta1_pct": float((ratio < 1.25).mean() * 100),  # share of pixels within 25%
        "p95_rel_pct": float(np.percentile(rel, 95) * 100),
        "worst_frame_abs_rel_pct": float(max(per_frame) * 100),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--da2-root", required=True)
    ap.add_argument("--frames", default="bench/frames")
    ap.add_argument("--models", default="models")
    ap.add_argument("--threads", type=int, default=default_threads())
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--out", default="bench/results.json")
    ap.add_argument("--tmp", default="bench/_tmp")
    ap.add_argument("--backend")  # internal: worker mode
    ap.add_argument("--run", type=int, default=0)  # internal
    ap.add_argument("--save", action="store_true")  # internal
    a = ap.parse_args()

    if a.backend:
        return worker(a)

    frames = sorted(Path(a.frames).glob("*.jpg"))
    if not frames:
        sys.exit(f"no frames in {a.frames}")
    Path(a.tmp).mkdir(parents=True, exist_ok=True)

    for r in range(a.repeats):
        order = BACKENDS[r % 3:] + BACKENDS[:r % 3]  # rotate order each pass
        for b in order:
            print(f"pass {r + 1}/{a.repeats}: {b}", flush=True)
            cmd = [sys.executable, __file__, "--checkpoint", a.checkpoint, "--da2-root", a.da2_root,
                   "--frames", a.frames, "--models", a.models, "--threads", str(a.threads),
                   "--tmp", a.tmp, "--backend", b, "--run", str(r)]
            subprocess.run(cmd + (["--save"] if r == 0 else []), check=True)

    res = {
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git_commit": sh(["git", "rev-parse", "--short", "HEAD"]),
            "git_dirty": bool(sh(["git", "status", "--porcelain"])),
            "cpu": cpu_name(),
            "os": platform.platform(),
            "threads": a.threads,
            "python": platform.python_version(),
            "torch": pkg("torch"),
            "onnxruntime": pkg("onnxruntime"),
            "numpy": pkg("numpy"),
            "opencv": pkg("opencv-python-headless") or pkg("opencv-python"),
            "frames": len(frames),
            "frames_sha256": sha256(frames),
            "input": "518x518",
            "warmup": WARMUP,
            "repeats": a.repeats,
        },
        "backends": {},
    }

    for b in BACKENDS:
        runs = [json.load(open(Path(a.tmp) / f"{b}_r{r}.json")) for r in range(a.repeats)]
        all_ms = np.concatenate([run["ms"] for run in runs])
        run_medians = [float(np.median(run["ms"])) for run in runs]
        q1, q3 = np.percentile(all_ms, [25, 75])
        res["backends"][b] = {
            "file_sha256": sha256([model_file(a, b)]),
            "size_mb": round(model_file(a, b).stat().st_size / 1e6, 1),
            "load_ms": round(float(np.median([run["load_ms"] for run in runs])), 0),
            "median_ms": round(float(np.median(all_ms)), 1),
            "iqr_ms": [round(float(q1), 1), round(float(q3), 1)],
            "p95_ms": round(float(np.percentile(all_ms, 95)), 1),
            "run_medians_ms": [round(m, 1) for m in run_medians],
            # how much the median moved between passes; above ~5% the machine was noisy
            "run_spread_pct": round((max(run_medians) - min(run_medians)) / np.median(run_medians) * 100, 1),
            "peak_rss_mb": round(max(run["peak_rss_mb"] for run in runs), 0),
        }

    outs = {b: np.load(Path(a.tmp) / f"{b}.npy") for b in BACKENDS}
    res["accuracy"] = {
        "onnx_fp32_vs_torch": depth_metrics(outs["torch"], outs["onnx_fp32"]),
        "onnx_int8_vs_torch": depth_metrics(outs["torch"], outs["onnx_int8"]),
    }
    res["depth_range_m"] = [round(float(np.percentile(outs["torch"], q)), 2) for q in (5, 50, 95)]

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=2)

    m = res["meta"]
    print(f"\n{m['cpu']} | {m['threads']} threads | {m['frames']} frames x {m['repeats']} passes"
          f" | commit {m['git_commit']}{' (dirty)' if m['git_dirty'] else ''}\n")
    print(f"{'backend':<11}{'size MB':>8}{'load ms':>9}{'median':>8}{'IQR':>16}{'p95':>8}{'spread':>8}{'peak MB':>9}")
    for b, v in res["backends"].items():
        iqr = f"{v['iqr_ms'][0]}-{v['iqr_ms'][1]}"
        print(f"{b:<11}{v['size_mb']:>8}{v['load_ms']:>9.0f}{v['median_ms']:>8}{iqr:>16}"
              f"{v['p95_ms']:>8}{v['run_spread_pct']:>7}%{v['peak_rss_mb']:>9.0f}")
    print(f"\ndepth p5/p50/p95: {res['depth_range_m']} m (reference: torch FP32)")
    for k, v in res["accuracy"].items():
        print(f"{k}: AbsRel {v['abs_rel_pct']:.2f}%  RMSE {v['rmse_m']:.3f} m  MAE {v['mae_m']:.3f} m  "
              f"d1 {v['delta1_pct']:.1f}%  p95 rel {v['p95_rel_pct']:.1f}%  "
              f"worst frame {v['worst_frame_abs_rel_pct']:.1f}%")
    if any(v["run_spread_pct"] > 5 for v in res["backends"].values()):
        print("\nwarning: run-to-run spread above 5%; close other apps, plug in, and rerun")


if __name__ == "__main__":
    main()