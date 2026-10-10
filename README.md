# Passline

[![CI](https://github.com/VatsalSivaratri/passline/actions/workflows/ci.yml/badge.svg)](https://github.com/VatsalSivaratri/passline/actions/workflows/ci.yml)

Passline turns a phone walkthrough video of a building into an ADA accessibility pre-screening report: which elements were found, which rules from the 2010 ADA Standards for Accessible Design they may not meet, and the evidence frames behind each finding.

First place overall at HackIndy 2026, built by Vatsal Sivaratri, Shrey Sharma, Sneha Chavan and Adwaiy Ranjith. Developed further since by Vatsal Sivaratri.

> **Pre-screening only.** Passline points out likely barriers so an owner knows where to look first. It is not a certified inspection, a compliance determination, or legal advice.

## Why

Many buildings that predate the ADA Standards still lack accessible features, and a professional audit is expensive enough that most small properties never get one. Passline is meant to be the cheap first pass: record each space on a phone, get a prioritized list of what to check.

## How it works

```
Phone video (per space)
  │
  ├─ FFmpeg ............... extract frames at 2 fps
  ├─ Blur filter .......... drop frames much less sharp than their neighbors in time
  ├─ SSIM ................. drop near-duplicates, keep up to 20 distinct key frames
  ├─ Calibration .......... find a credit card or letter paper; pixels per inch
  ├─ Gemini ............... classify the space; detect ADA-relevant features
  │                         (schema-constrained JSON, temperature 0)
  ├─ Depth Anything V2 .... metric depth map per frame (PyTorch or ONNX INT8)
  ├─ Rule engine .......... evaluate features against data/rules.yaml
  └─ Report ............... LLM-written descriptions per finding, PDF via ReportLab
```

Results are stored in MongoDB; the Next.js frontend polls processing status and shows findings with annotated frames and depth maps.

### Current state

| Stage | Status |
| --- | --- |
| Frame extraction, blur filter, SSIM dedup | Working, tested |
| Reference-object calibration | Working on synthetic 4K tests; not yet validated on real footage with a reference object |
| Metric depth (PyTorch and ONNX INT8) | Working, benchmarked; ONNX parity tested |
| Feature detection and room classification (Gemini) | Working; failures raise errors instead of returning defaults |
| Rule engine | 45 rules citing 40 sections of the 2010 Standards; rules evaluate model-observed properties |
| Depth-based measurements feeding rules | **Not yet.** Depth maps are computed but no measured value reaches a rule |
| Required-element checks per space type, confidence tiers | Designed, not built |

## Results

All numbers come from scripts in this repo; the output files are committed.

**Depth model export** (`tools/bench_depth.py`, results in `bench/results.json`). Depth Anything V2 metric ViT-S (Hypersim), 518 x 518 input, 50 frames from one walkthrough, Apple M1 Pro, 6 threads, 3 passes with rotated order; run-to-run spread under 1%.

| Backend | Size | Median latency | Peak memory | Load time |
| --- | --- | --- | --- | --- |
| PyTorch FP32 | 99.2 MB | 221 ms | 1510 MB | 1.9 s |
| ONNX FP32 | 98.9 MB | 350 ms | 666 MB | 0.14 s |
| ONNX INT8 (dynamic) | 35.4 MB | 251 ms | 614 MB | 0.09 s |

INT8 versus PyTorch FP32 depth: AbsRel 2.47%, MAE 3.8 cm, worst frame 10.6% (median scene depth 1.8 m). ONNX FP32 matches PyTorch exactly. INT8 is faster than ONNX FP32 but not faster than PyTorch on this CPU; see `DECISIONS.md`.

**Calibration** (`backend/tests/test_calibration.py`). On synthetic 4K frames with motion blur and sensor noise, the original detector found nothing (the outline broke into open contours of about 5 px² against an 83,000 px² threshold). The multi-scale detector finds the reference in all 15 degraded cases, with scale error at most 1.2% for letter paper and 3.5% for a dark card, and reported no false positives on 14 real frames. Known miss: a low-contrast card, kept as an expected failure.

**Rules** (`backend/tests/test_rules_engine.py`). The 45 original Python rules were converted to YAML by an AST script and checked identical to the originals on every rule and on 20,000 random inputs.

**Blur filter** (`backend/tests/test_blur_filter.py`). Judges each frame against its neighbors because a fixed threshold also drops blank walls, which still count as coverage. On the test walkthrough it drops the 3 motion-blurred frames of 28 and keeps all 4 wall frames.

## Quickstart

**Prerequisites:** Python 3.12, Node 18+, FFmpeg (`brew install ffmpeg` or `sudo apt install ffmpeg`), and MongoDB (local `mongod` or an Atlas cluster).

### Backend

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt onnx onnxruntime onnxscript pytest

# Depth model code and metric checkpoint (~99 MB)
git clone https://github.com/DepthAnything/Depth-Anything-V2 backend/Depth-Anything-V2
mkdir -p backend/checkpoints
curl -L -o backend/checkpoints/depth_anything_v2_metric_hypersim_vits.pth \
  https://huggingface.co/depth-anything/Depth-Anything-V2-Metric-Hypersim-Small/resolve/main/depth_anything_v2_metric_hypersim_vits.pth

cp backend/.env.example backend/.env   # then fill in keys (see Configuration)
cd backend && uvicorn main:app --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000, expects the API at NEXT_PUBLIC_API_URL (default http://localhost:8000)
```

### Optional: ONNX depth backend

```bash
python tools/export_depth_onnx.py \
  --checkpoint backend/checkpoints/depth_anything_v2_metric_hypersim_vits.pth \
  --da2-root backend/Depth-Anything-V2
# writes models/dav2_fp32.onnx and models/dav2_int8.onnx; then set DEPTH_BACKEND=onnx in backend/.env
```

## Configuration

Set in `backend/.env` (template in `backend/.env.example`). Never commit `.env`.

| Variable | Purpose |
| --- | --- |
| `MONGODB_URI`, `MONGODB_DB` | Database; `mongodb://localhost:27017` for local |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Feature detection and room classification |
| `ANVILGPT_API_KEY`, `ANVILGPT_BASE_URL`, `ANVILGPT_MODEL` | OpenAI-compatible endpoint for report text |
| `DEPTH_BACKEND` | `torch` (default) or `onnx` |
| `DEPTH_MODEL_PATH`, `DA2_ROOT`, `DEPTH_ONNX_PATH` | Depth checkpoint, Depth-Anything-V2 clone, exported ONNX file |
| `UPLOAD_DIR`, `FRAMES_DIR`, `REPORTS_DIR` | Local storage for videos, frames, PDFs |

## Tests and tools

```bash
cd backend && pytest tests -q
```

87 tests. CI runs everything except the 3 depth parity tests, which need model weights.

| Tool | What it does |
| --- | --- |
| `tools/export_depth_onnx.py` | Export the depth model to ONNX FP32 and INT8 |
| `tools/bench_depth.py` | Size, latency, memory and depth agreement across backends, with provenance |
| `tools/gemini_determinism.py` | Run detection repeatedly on the same frames; compare settings and resulting findings |

## Repository layout

```
backend/
  main.py                FastAPI app
  routers/               audits, modules (upload + processing pipeline), reports
  services/              video_processing, calibration, depth_backends, depth_estimation,
                         gemini_analysis, rules_engine, report_generator
  data/rules.yaml        rule set, one entry per check with its ADA section
  tests/                 pytest suite
frontend/                Next.js app: questionnaire, capture, processing, report
tools/                   export, benchmark and experiment scripts
bench/                   committed benchmark results
DECISIONS.md             why each design decision was made, with evidence
SPEC.md                  API, data model, pipeline stages and rule format
RUNNING.md               running locally, troubleshooting, running experiments
```

## Limitations

- Rules read properties the vision model reports ("door appears narrow"), not measured dimensions. Depth is computed but not yet turned into measurements.
- Calibration has been tested on synthetic frames only. Shape alone cannot tell a card from other card-shaped rectangles.
- Gemini output can vary between runs on identical input; temperature 0 and a response schema reduce this, and `tools/gemini_determinism.py` measures it.
- Rule section numbers come from the original implementation and still need checking against the official 2010 Standards text.
- Elements such as door opening force, surface slip resistance and braille correctness cannot be judged from video.
- Frames are sent to Google's Gemini API. Video metadata (including location) is not yet stripped.

## Next

Measured dimensions from depth and camera intrinsics, with uncertainty and a guard band around each threshold; required-element checks per space type with coverage; per-instance findings in place of a single score; a validation study against tape-measured dimensions.
