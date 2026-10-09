# Decisions

One entry per real decision: what was decided, why, and the evidence. Newest last.

## ONNX with INT8 dynamic quantization for the depth model

Exported Depth Anything V2 metric (ViT-S, Hypersim) to ONNX and quantized the MatMul weights to INT8 with dynamic quantization. Dynamic needs no calibration set, which mattered with one walkthrough of data, and it suits transformers, whose cost is mostly MatMuls. On an M1 Pro (6 performance cores, 3 passes, 50 frames): size 99 to 35 MB, peak memory 1.5 to 0.6 GB, depth AbsRel 2.5% versus FP32, worst frame 10.6%. INT8 is 1.4x faster than ONNX FP32 but about 14% slower than PyTorch on this CPU: dynamic quantization computes activation scales at runtime before each MatMul, and PyTorch's arm64 kernels are well tuned. The benchmark rotates backend order, pins thread count, and records commit, versions and file hashes. Results: `bench/results.json`.

## Fail loudly instead of falling back

A batch run showed rooms classified as "entrance" when the API had failed: the except block returned a default that looked identical to a real prediction, and a failed detection returned an empty feature list that read as "no violations." Every default was replaced with an explicit `AnalysisError`, handled by what it breaks: an unknown room type continues with a warning (rules don't depend on it); failed detection stops the module (nothing to evaluate). The fake luminance "depth map" shown when the model was missing was removed too. Tests mock the Gemini client: `tests/test_fail_loudly.py`.

## Calibration: multi-scale search with morphological closing

Reproduced on synthetic 4K frames: with any blur or noise, Canny returned the reference object's outline as open fragments; the largest contour was about 5 px^2 against an 83,000 px^2 threshold, so nothing ever passed. A second bug: the 1% minimum area rejected a credit card outright (about 0.3% of a 4K frame). Fix: search downscaled copies at three sizes, close edge gaps morphologically, set Canny thresholds from image brightness, require rectangularity, map scale back to full resolution. Result: all 15 degraded synthetic cases detected, scale error at most 3.5% (paper at most 1.2%), no false positives on 14 real frames. Lower thresholds also caught a low-contrast red card but matched a ceiling vent grille with a card's aspect ratio, so thresholds stay conservative: a wrong scale is worse than none. That miss is an expected failure in `tests/test_calibration.py`.

## Rules as data

The 45 hackathon rules were Python lambdas. They were converted mechanically (an AST pass, so nothing was retyped) into `backend/data/rules.yaml`, one entry per check citing its 2010 Standards section (40 distinct sections), evaluated by a generic engine in `services/rules_engine.py`. Equivalence with the original lambdas is tested on every rule and on 20,000 random inputs; the original is frozen in `tests/legacy_feature_rules.py` for that test. The engine uses identity for booleans (`is: false` matches only a real false), like the originals, so a model answering "no" or 0 does not trigger a rule.

## Blur filter relative to temporal neighbors

Variance of the Laplacian measures focus and texture together: on the test walkthrough, blank walls scored as low as 1 while motion-blurred frames scored 20 to 66. A fixed threshold drops the walls, and walls matter (a bare wall is evidence a grab bar is missing). So a frame is dropped only when it is under half the median sharpness of its two neighbors on each side, and frames below a texture floor are never judged. On the walkthrough it drops the 3 motion-blurred frames of 28 and keeps all 4 wall frames. Ratio and floor were set on that one clip and should be revisited with more recordings.

## Gemini: temperature 0 and a response schema

Detection returned different feature lists on identical frames. The call now uses temperature 0 and a response schema: feature types are an enum of the 39 known types, and each property has a fixed type and, where rules read it, a fixed set of values matching `rules.yaml`. `tools/gemini_determinism.py` measures the effect by running both settings on the same frames and comparing raw output and resulting findings. Results: `bench/determinism.json`.
