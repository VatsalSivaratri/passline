# Running Passline

Setup is in the README Quickstart. This file covers day-to-day running, common failures and the experiment scripts.

## Start everything

Three terminals, from the repo root:

```bash
# 1. MongoDB (skip if using Atlas)
mongod --dbpath ~/data/db

# 2. API
source .venv/bin/activate && cd backend && uvicorn main:app --port 8000 --reload

# 3. Frontend
cd frontend && npm run dev
```

Open http://localhost:3000. Check the API with `curl localhost:8000/health`.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| API exits at startup on `ping` | MongoDB unreachable | Start `mongod`, or check `MONGODB_URI`. Local URIs must start with `mongodb://` |
| TLS error connecting to Atlas | CA bundle | `mongodb+srv://` URIs use `certifi` automatically; update it with `pip install -U certifi` |
| `FFmpeg failed` / `No such file or directory` | FFmpeg missing, or a relative video path | `brew install ffmpeg`; pass paths from the directory the command runs in |
| Log says "Could not load depth model" | Checkpoint or Depth-Anything-V2 clone missing | Check `DEPTH_MODEL_PATH` and `DA2_ROOT`; for `onnx`, run the export first |
| Module status `error`: "Feature detection failed" | Gemini call failed (key, quota, outage) | Check `GEMINI_API_KEY` and `GEMINI_MODEL`; the message includes the API error |
| `429 RESOURCE_EXHAUSTED` | Gemini free tier: 5 requests/minute and 20/day per model | Wait for the reset or enable billing |
| `503 UNAVAILABLE` | Gemini overloaded | Retry later |
| Module error: "Only N frames extracted" or "Only N distinct frames" | Fewer than 3 usable frames after the blur filter or dedup | Re-record more slowly with more movement between positions |
| `pytest` not found | venv not active | `source .venv/bin/activate` from the repo root |
| Depth tests skipped | Weights, ONNX files or `bench/frames` missing | Expected in CI; run the export and frame extraction locally |

## Tests

```bash
source .venv/bin/activate
cd backend && pytest tests -q          # 87 tests locally, 1 expected failure
```

## Depth benchmark

```bash
# 50 frames from a walkthrough
mkdir -p bench/frames
ffmpeg -i walkthrough.mov -vf "fps=50/<duration_seconds>,scale=1920:-2" -q:v 2 bench/frames/f_%03d.jpg

python tools/export_depth_onnx.py \
  --checkpoint backend/checkpoints/depth_anything_v2_metric_hypersim_vits.pth \
  --da2-root backend/Depth-Anything-V2

rm -rf bench/_tmp
python tools/bench_depth.py \
  --checkpoint backend/checkpoints/depth_anything_v2_metric_hypersim_vits.pth \
  --da2-root backend/Depth-Anything-V2
```

For numbers you intend to report: commit first so the result is not marked `(dirty)`, plug in, quit other apps, and rerun if the script warns about run-to-run spread above 5%. Results go to `bench/results.json`.

## Gemini determinism experiment

```bash
python tools/gemini_determinism.py --video walkthrough.mov --runs 9
```

Makes 2 calls per run, spaced 13 seconds apart. On the free tier keep `--runs` at 9 or fewer (18 calls under the 20-per-day limit) and make sure nothing else used the key that day. Results go to `bench/determinism.json`.
