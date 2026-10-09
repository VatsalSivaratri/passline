"""
Step 5B: Depth Estimation

Wraps Depth Anything V2 ViT-S metric (Hypersim, indoor). Backend is PyTorch
or ONNX Runtime, chosen by DEPTH_BACKEND. See services/depth_backends.py.
"""

import logging
from typing import Optional

import cv2
import numpy as np

from config import DA2_ROOT, DEPTH_BACKEND, DEPTH_MODEL_PATH, DEPTH_ONNX_PATH, FRAMES_DIR
from services.depth_backends import OnnxDepth, TorchDepth

logger = logging.getLogger(__name__)


class DepthEstimator:
    """Picks the depth backend from config (DEPTH_BACKEND = torch | onnx)."""

    def __init__(self, backend: str = DEPTH_BACKEND):
        self.backend_name = backend
        self.model = None
        try:
            if backend == "onnx":
                self.model = OnnxDepth(str(DEPTH_ONNX_PATH))
            else:
                self.model = TorchDepth(str(DEPTH_MODEL_PATH), str(DA2_ROOT))
            logger.info(f"Depth Anything V2 metric ViT-S loaded ({backend}).")
        except Exception as e:
            logger.warning(f"Could not load depth model ({backend}): {e}. Depth estimation unavailable.")

    def predict(self, image_bgr: np.ndarray) -> Optional[np.ndarray]:
        """Returns HxW metric depth in meters (float32), or None."""
        if self.model is None:
            return None
        try:
            return self.model.predict(image_bgr)
        except Exception as e:
            logger.error(f"Depth inference error: {e}")
            return None


def colorize_depth_map(depth: np.ndarray) -> np.ndarray:
    """Convert metric depth map to a colorized BGR image for visualization."""
    norm = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX)
    norm_uint8 = norm.astype(np.uint8)
    colored = cv2.applyColorMap(norm_uint8, cv2.COLORMAP_INFERNO)
    return colored


def measure_width_from_bbox(
    depth_map: np.ndarray,
    image: np.ndarray,
    bbox_norm: dict,
    pixels_per_inch: Optional[float],
) -> Optional[float]:
    """
    Estimate horizontal width of a bounding box in inches.

    bbox_norm: {"x1": 0-1, "y1": 0-1, "x2": 0-1, "y2": 0-1}
    Returns width in inches, or None.
    """
    h, w = image.shape[:2]
    try:
        x1 = int(float(bbox_norm["x1"]) * w)
        x2 = int(float(bbox_norm["x2"]) * w)
        y_mid = int(((float(bbox_norm["y1"]) + float(bbox_norm["y2"])) / 2) * h)
    except (TypeError, ValueError):
        return None

    pixel_width = abs(x2 - x1)
    if pixel_width == 0:
        return None

    if pixels_per_inch is not None:
        return pixel_width / pixels_per_inch

    # Metric fallback: use depth at midpoint to estimate angular size
    # (approximate, ±3-4 inches, better than nothing)
    if depth_map is not None:
        x_mid = (x1 + x2) // 2
        depth_m = float(depth_map[y_mid, x_mid]) if depth_map[y_mid, x_mid] > 0 else None
        if depth_m and depth_m > 0.1:
            # Assume ~60° horizontal FOV for a typical phone camera
            import math
            fov_rad = math.radians(60)
            px_per_meter = w / (2 * depth_m * math.tan(fov_rad / 2))
            width_m = pixel_width / px_per_meter
            return width_m * 39.3701  # meters → inches

    return None


def process_frames_depth(
    frame_paths: list,
    audit_id: str,
    module_id: str,
    estimator: "DepthEstimator",
    gemini_result: dict,
    calibration: dict,
) -> dict:
    """
    Run depth estimation on all frames and extract measurements.
    Returns dict with measurements and saved depth map frame paths.
    """
    depth_map_frames = []
    measurements = {}
    pixels_per_inch = calibration.get("pixels_per_inch")

    out_dir = FRAMES_DIR / audit_id / module_id
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, rel_path in enumerate(frame_paths):
        full_path = FRAMES_DIR / rel_path
        img = cv2.imread(str(full_path))
        if img is None:
            continue

        depth = estimator.predict(img)

        if depth is not None:
            colored = colorize_depth_map(depth)
            depth_name = f"depth_{i + 1:03d}.jpg"
            depth_out = out_dir / depth_name
            cv2.imwrite(str(depth_out), colored)
            depth_map_frames.append(f"{audit_id}/{module_id}/{depth_name}")

            # Extract door width if bounding box is available
            if "door_bounding_box" in gemini_result and "door_clear_width_inches" not in measurements:
                bbox = gemini_result["door_bounding_box"]
                width_in = measure_width_from_bbox(depth, img, bbox, pixels_per_inch)
                if width_in is not None:
                    measurements["door_clear_width_inches"] = round(width_in, 1)

            # Extract clearance for restroom
            if "clearance_bounding_box" in gemini_result and "clearance_inches" not in measurements:
                bbox = gemini_result["clearance_bounding_box"]
                width_in = measure_width_from_bbox(depth, img, bbox, pixels_per_inch)
                if width_in is not None:
                    measurements["clearance_inches"] = round(width_in, 1)
    # When the model is missing, return no depth maps rather than a fake one.
    return {
        "measurements": measurements,
        "depth_map_frames": depth_map_frames,
        "depth_available": estimator.model is not None,
    }
