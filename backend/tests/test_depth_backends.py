"""
The ONNX depth path must reproduce the PyTorch path.

Skips if the checkpoint or ONNX files aren't present (CI without model weights).
Run from backend/:  pytest tests/test_depth_backends.py
"""

import os
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

CKPT = Path(os.getenv("DEPTH_MODEL_PATH", BACKEND / "checkpoints/depth_anything_v2_metric_hypersim_vits.pth"))
DA2 = Path(os.getenv("DA2_ROOT", BACKEND / "Depth-Anything-V2"))
MODELS = BACKEND.parent / "models"
FRAMES = sorted((BACKEND.parent / "bench/frames").glob("*.jpg"))[::10]  # 5 real frames

needs_models = pytest.mark.skipif(
    not (CKPT.exists() and DA2.exists() and (MODELS / "dav2_int8.onnx").exists() and FRAMES),
    reason="model weights, ONNX files or bench frames not present",
)


@pytest.fixture(scope="module")
def outputs():
    from services.depth_backends import OnnxDepth, TorchDepth

    imgs = [cv2.imread(str(f)) for f in FRAMES]
    runs = {
        "torch": TorchDepth(str(CKPT), str(DA2)),
        "fp32": OnnxDepth(str(MODELS / "dav2_fp32.onnx")),
        "int8": OnnxDepth(str(MODELS / "dav2_int8.onnx")),
    }
    return {k: np.stack([m.predict(i) for i in imgs]) for k, m in runs.items()}


@needs_models
def test_onnx_fp32_matches_torch(outputs):
    # Same weights, same math: only float op-ordering differences are allowed.
    assert np.abs(outputs["fp32"] - outputs["torch"]).max() < 1e-2  # meters


@needs_models
def test_int8_close_to_fp32(outputs):
    rel = np.abs(outputs["int8"] - outputs["fp32"]) / np.maximum(outputs["fp32"], 1e-3)
    assert rel.mean() < 0.05  # mean depth within 5%


@needs_models
def test_output_is_metric(outputs):
    # Indoor metric depth: meters in a sane range, not 0-1 relative disparity.
    d = outputs["torch"]
    assert 0.1 < np.median(d) < 20.0
