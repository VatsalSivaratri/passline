"""
Depth backends: the same Depth Anything V2 metric model run two ways.

  TorchDepth  - PyTorch, FP32 (the original path)
  OnnxDepth   - ONNX Runtime, FP32 or INT8 file

Both share preprocess() so any difference in output comes from the runtime
and quantization, not from different input handling.
"""

import sys
from pathlib import Path

import cv2
import numpy as np

INPUT_SIZE = 518
MAX_DEPTH_M = 20.0
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

VITS_CFG = {"encoder": "vits", "features": 64, "out_channels": [48, 96, 192, 384]}


def preprocess(image_bgr: np.ndarray) -> np.ndarray:
    """BGR uint8 HxWx3 -> float32 1x3x518x518, ImageNet-normalized."""
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_CUBIC)
    x = (rgb.astype(np.float32) / 255.0 - _MEAN) / _STD
    return x.transpose(2, 0, 1)[None]


def postprocess(depth: np.ndarray, out_hw) -> np.ndarray:
    """1x518x518 model output -> HxW metric depth in meters."""
    d = np.asarray(depth, dtype=np.float32).squeeze()
    return cv2.resize(d, (out_hw[1], out_hw[0]), interpolation=cv2.INTER_LINEAR)


def build_torch_model(checkpoint: str, da2_root: str):
    """Load the metric model. da2_root = path to a Depth-Anything-V2 clone."""
    import torch

    metric_dir = str(Path(da2_root) / "metric_depth")
    if metric_dir not in sys.path:
        sys.path.insert(0, metric_dir)
    from depth_anything_v2.dpt import DepthAnythingV2

    model = DepthAnythingV2(**VITS_CFG, max_depth=MAX_DEPTH_M)
    if checkpoint:
        model.load_state_dict(torch.load(checkpoint, map_location="cpu"))
    return model.eval()


class TorchDepth:
    def __init__(self, checkpoint: str, da2_root: str):
        import torch

        self._torch = torch
        self.model = build_torch_model(checkpoint, da2_root)

    def raw(self, x: np.ndarray) -> np.ndarray:
        with self._torch.no_grad():
            return self.model(self._torch.from_numpy(x)).numpy()

    def predict(self, image_bgr: np.ndarray) -> np.ndarray:
        return postprocess(self.raw(preprocess(image_bgr)), image_bgr.shape[:2])


class OnnxDepth:
    def __init__(self, onnx_path: str, threads: int = 0):
        import onnxruntime as ort

        opts = ort.SessionOptions()
        if threads:
            opts.intra_op_num_threads = threads
        self.sess = ort.InferenceSession(onnx_path, opts, providers=["CPUExecutionProvider"])

    def raw(self, x: np.ndarray) -> np.ndarray:
        return self.sess.run(["depth"], {"image": x})[0]

    def predict(self, image_bgr: np.ndarray) -> np.ndarray:
        return postprocess(self.raw(preprocess(image_bgr)), image_bgr.shape[:2])
