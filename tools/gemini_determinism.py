"""
How stable is Gemini feature detection on identical input?

Extracts key frames from one video once (the real pipeline: FFmpeg, blur filter,
SSIM dedup), then calls detection N times per configuration on those same frames:

  legacy      temperature 0.1, free-form JSON   (the hackathon setting)
  structured  temperature 0.0, response schema  (current default)

Configs are interleaved (L, S, L, S, ...) so time-of-day drift hits both equally.
For each run the detected features also go through the rule engine, because the
number that matters is whether the *findings* change, not just the raw output.

  python tools/gemini_determinism.py --video IMG_6053.mov --runs 10

Writes bench/determinism.json with model ID, prompt hash, frame hashes and git commit.
Needs GEMINI_API_KEY in backend/.env. 2 x runs API calls.
"""

import argparse
import asyncio
import re
import hashlib
import itertools
import json
import os
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START_DIR = Path.cwd()  # resolve user-given paths against where the command was run
os.chdir(ROOT / "backend")  # config.py resolves .env and output dirs relative to backend/
sys.path.insert(0, str(ROOT / "backend"))

from config import FRAMES_DIR, GEMINI_MODEL  # noqa: E402
from services.gemini_analysis import AnalysisError, analyze_features, features_prompt, prompt_hash  # noqa: E402
from services.rules_engine import evaluate  # noqa: E402
from services.video_processing import extract_key_frames  # noqa: E402

CONFIGS = {
    "legacy": {"temperature": 0.1, "structured": False},
    "structured": {"temperature": 0.0, "structured": True},
}


TRANSIENT = ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")


async def call_with_backoff(frames, cfg, max_tries=6):
    """Rate limits and overload are not results: wait them out and retry.
    Any other error is returned as an error run."""
    for attempt in range(max_tries):
        try:
            return await analyze_features(frames, **cfg), attempt
        except AnalysisError as e:
            msg = str(e)
            if not any(t in msg for t in TRANSIENT) or attempt == max_tries - 1:
                raise
            hint = re.search(r"retry in ([0-9.]+)s", msg)
            wait = float(hint.group(1)) + 1 if hint else min(60, 10 * 2 ** attempt)
            print(f"   transient ({'429' if '429' in msg else '503'}), waiting {wait:.0f}s")
            time.sleep(wait)


def jaccard(a: set, b: set) -> float:
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def summarize(all_runs: list) -> dict:
    # Error runs are reported in the count but excluded from stability metrics.
    runs = [r for r in all_runs if not r.get("error")] or [{"features": [], "types": [], "violations": []}]
    counts = [len(r["features"]) for r in runs]
    type_sets = [frozenset(Counter(r["types"]).items()) for r in runs]   # multiset of feature types
    viol_sets = [frozenset(r["violations"]) for r in runs]
    pairs = list(itertools.combinations(range(len(runs)), 2))

    def modal_share(sets):
        top, n = Counter(sets).most_common(1)[0]
        return n / len(sets), sorted(top)

    type_share, _ = modal_share(type_sets)
    viol_share, modal_viol = modal_share(viol_sets)
    return {
        "runs": len(runs),
        "feature_count": {"min": min(counts), "max": max(counts),
                          "mean": round(statistics.mean(counts), 2),
                          "stdev": round(statistics.pstdev(counts), 2)},
        # share of runs that returned exactly the most common output
        "identical_feature_types_share": round(type_share, 2),
        "identical_violations_share": round(viol_share, 2),
        # average overlap between every pair of runs (1.0 = always the same)
        "mean_pairwise_jaccard_violations": round(
            statistics.mean(jaccard(set(viol_sets[i]), set(viol_sets[j])) for i, j in pairs), 3) if pairs else None,
        "violations_ever_reported": sorted(set().union(*viol_sets)),
        "violations_always_reported": sorted(set.intersection(*map(set, viol_sets))),
        "modal_violations": modal_viol,
        "errors": sum(1 for r in all_runs if r.get("error")),
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--sleep", type=float, default=13.0,
                    help="seconds between calls; 13 keeps under the free tier's 5 requests/minute")
    ap.add_argument("--out", default=str(ROOT / "bench" / "determinism.json"))
    a = ap.parse_args()

    video = (START_DIR / a.video).resolve()
    frames = await extract_key_frames(str(video), "determinism", "run")
    frame_hash = hashlib.sha256(b"".join((FRAMES_DIR / f).read_bytes() for f in frames)).hexdigest()[:16]
    print(f"{len(frames)} key frames, sha {frame_hash}; model {GEMINI_MODEL}")

    results = {name: [] for name in CONFIGS}
    for i in range(a.runs):
        for name, cfg in CONFIGS.items():
            t = time.perf_counter()
            try:
                out, retries = await call_with_backoff(frames, cfg)
                feats = out["features"]
                run = {"features": feats, "transient_retries": retries,
                       "types": [f["feature_type"] for f in feats],
                       "violations": [v.rule_id for v in evaluate(feats, "m", False)]}
            except Exception as e:  # recorded, not hidden: an error is a result too
                run = {"features": [], "types": [], "violations": [], "error": str(e)[:200]}
            run["seconds"] = round(time.perf_counter() - t, 1)
            results[name].append(run)
            print(f"run {i + 1}/{a.runs} {name:<10} features={len(run['features']):>2} "
                  f"violations={sorted(run['violations'])}{'  ERROR ' + run['error'] if 'error' in run else ''}")
            time.sleep(a.sleep)

    report = {
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git_commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                         capture_output=True, text=True).stdout.strip(),
            "model": GEMINI_MODEL,
            "prompt_sha": prompt_hash(features_prompt()),
            "video": video.name,
            "frames": len(frames),
            "frames_sha256": frame_hash,
            "configs": CONFIGS,
        },
        "summary": {name: summarize(runs) for name, runs in results.items()},
        "raw": results,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=2, default=str))

    print(f"\n{'config':<11}{'features min-max':>17}{'stdev':>7}{'same types':>12}{'same findings':>15}{'jaccard':>9}{'errors':>8}")
    for name, s in report["summary"].items():
        fc = s["feature_count"]
        print(f"{name:<11}{fc['min']:>8}-{fc['max']:<8}{fc['stdev']:>7}{s['identical_feature_types_share']:>11.0%}"
              f"{s['identical_violations_share']:>14.0%}{str(s['mean_pairwise_jaccard_violations']):>10}{s['errors']:>7}")
    print(f"\nsaved {a.out}")


if __name__ == "__main__":
    asyncio.run(main())
