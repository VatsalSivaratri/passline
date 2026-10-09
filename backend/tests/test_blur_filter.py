"""
Blur filter: drop motion-blurred frames, keep sharp ones, and keep textureless
frames (blank walls) that a fixed sharpness threshold would wrongly drop.
"""

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.video_processing import TEXTURELESS_FLOOR, blurry_mask, sharpness  # noqa: E402


def textured(seed, size=(1080, 1920)):
    rng = np.random.default_rng(seed)
    img = cv2.resize(rng.integers(0, 255, (size[0] // 12, size[1] // 12), dtype=np.uint8), size[::-1],
                     interpolation=cv2.INTER_NEAREST)
    return cv2.GaussianBlur(img, (3, 3), 0)


def motion_blur(gray, k=31):
    kernel = np.zeros((k, k), np.float32)
    kernel[k // 2, :] = 1 / k
    return cv2.filter2D(gray, -1, kernel)


def blank_wall(seed, size=(1080, 1920)):
    rng = np.random.default_rng(seed)
    return np.clip(200 + rng.normal(0, 1.0, size), 0, 255).astype(np.uint8)


def test_motion_blurred_frame_is_dropped():
    frames = [textured(i) for i in range(5)]
    frames[2] = motion_blur(frames[2])
    assert blurry_mask([sharpness(f) for f in frames]) == [False, False, True, False, False]


def test_sharp_sequence_keeps_everything():
    assert not any(blurry_mask([sharpness(textured(i)) for i in range(6)]))


def test_blank_wall_after_textured_frames_is_kept():
    # A fixed threshold would drop these; the walls are real coverage of the room.
    frames = [textured(0), textured(1), blank_wall(2), blank_wall(3), textured(4)]
    scores = [sharpness(f) for f in frames]
    assert scores[2] < TEXTURELESS_FLOOR
    assert blurry_mask(scores)[2:4] == [False, False]


def test_sharpness_independent_of_resolution():
    full = textured(7, size=(2160, 3840))
    half = cv2.resize(full, (1920, 1080), interpolation=cv2.INTER_AREA)
    assert abs(sharpness(full) - sharpness(half)) / sharpness(full) < 0.1


def test_single_frame_kept():
    assert blurry_mask([5.0]) == [False]
