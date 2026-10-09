"""
Step 3: Video → Key Frames

FFmpeg extracts frames at 2fps, then:
1. Blur filter (sharpness far below its temporal neighbors → discard)
2. Duplicate filter (SSIM > 0.92 between consecutive → discard later)
3. Keep 3-12 most distinct frames
"""

import asyncio
import logging
import subprocess
import uuid
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from config import (
    SSIM_DUPLICATE_THRESHOLD,
    MIN_FRAMES,
    MAX_FRAMES,
    EXTRACT_FPS,
    FRAMES_DIR,
)

logger = logging.getLogger(__name__)


class VideoProcessingError(Exception):
    pass


# Blur filter. Variance of the Laplacian measures focus AND texture: a blank wall
# scores as low as a smeared frame. A fixed threshold therefore drops textureless
# frames, which still matter (a bare wall is evidence that a grab bar is absent).
# So a frame is judged against its neighbors in time, which show similar content.
SHARPNESS_LONG_SIDE = 960     # measure at a fixed size so scores don't depend on resolution
SHARPNESS_RATIO = 0.5         # blurry = under half the median of its neighbors
SHARPNESS_NEIGHBORS = 2       # frames on each side
TEXTURELESS_FLOOR = 15.0      # below this there is too little texture to judge; keep the frame
# Ratio and floor were set on one 14 s walkthrough (drops 3 motion-blurred frames of 28,
# keeps 4 blank-wall frames). Revisit when more recordings exist.


def sharpness(gray: np.ndarray) -> float:
    """Variance of the Laplacian on a copy resized to SHARPNESS_LONG_SIDE."""
    scale = SHARPNESS_LONG_SIDE / max(gray.shape)
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(small, cv2.CV_64F).var())


def blurry_mask(scores: List[float]) -> List[bool]:
    """True where a frame is much less sharp than its temporal neighbors."""
    out = []
    for i, s in enumerate(scores):
        nb = scores[max(0, i - SHARPNESS_NEIGHBORS):i] + scores[i + 1:i + 1 + SHARPNESS_NEIGHBORS]
        if not nb or s < TEXTURELESS_FLOOR:
            out.append(False)  # nothing to compare against, or too little texture to judge
        else:
            out.append(s < SHARPNESS_RATIO * float(np.median(nb)))
    return out


def _ssim(a: np.ndarray, b: np.ndarray) -> float:
    """Simplified SSIM using OpenCV."""
    # Resize to same dimensions if needed
    if a.shape != b.shape:
        b = cv2.resize(b, (a.shape[1], a.shape[0]))
    score, _ = cv2.quality.QualitySSIM_compute(a, b)  # type: ignore
    return float(score[0])


def _ssim_simple(a: np.ndarray, b: np.ndarray) -> float:
    """
    Fallback SSIM approximation using normalized cross-correlation.
    Used when cv2.quality is unavailable.
    """
    if a.shape != b.shape:
        b = cv2.resize(b, (a.shape[1], a.shape[0]))
    a_f = a.astype(np.float64)
    b_f = b.astype(np.float64)
    mu_a, mu_b = a_f.mean(), b_f.mean()
    sigma_a = a_f.std()
    sigma_b = b_f.std()
    if sigma_a == 0 or sigma_b == 0:
        return 1.0 if sigma_a == sigma_b else 0.0
    cov = ((a_f - mu_a) * (b_f - mu_b)).mean()
    c1, c2 = 6.5025, 58.5225  # (0.01*255)^2, (0.03*255)^2
    ssim = ((2 * mu_a * mu_b + c1) * (2 * cov + c2)) / (
        (mu_a**2 + mu_b**2 + c1) * (sigma_a**2 + sigma_b**2 + c2)
    )
    return float(ssim)


def compute_ssim(a: np.ndarray, b: np.ndarray) -> float:
    try:
        return _ssim(a, b)
    except Exception:
        return _ssim_simple(a, b)


async def extract_key_frames(video_path: str, audit_id: str, module_id: str) -> List[str]:
    """
    Extract key frames from video. Returns list of frame file paths (relative to FRAMES_DIR).
    Raises VideoProcessingError on failure.
    """
    out_dir = FRAMES_DIR / audit_id / module_id
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_pattern = str(out_dir / "raw_%04d.jpg")

    # Step 1: Extract frames with FFmpeg at EXTRACT_FPS
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"fps={EXTRACT_FPS}",
        "-q:v", "2",
        raw_pattern,
    ]
    logger.info(f"Running FFmpeg: {' '.join(cmd)}")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise VideoProcessingError(f"FFmpeg failed: {stderr.decode()[-500:]}")

    # Load extracted frames
    raw_paths = sorted(out_dir.glob("raw_*.jpg"))
    if not raw_paths:
        raise VideoProcessingError("FFmpeg produced no frames. Video may be corrupted or too short.")

    frames = []
    for p in raw_paths:
        img = cv2.imread(str(p))
        if img is not None:
            frames.append((p, img))

    # Step 2: Drop motion-blurred frames
    grays = [cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) for _, img in frames]
    blurry = blurry_mask([sharpness(g) for g in grays])
    sharp_frames = [(p, img, g) for (p, img), g, b in zip(frames, grays, blurry) if not b]
    logger.info(f"Blur filter dropped {sum(blurry)} of {len(frames)} frames")

    if len(sharp_frames) < MIN_FRAMES:
        raise VideoProcessingError(
            f"Only {len(sharp_frames)} frames extracted (need {MIN_FRAMES}). "
            "Video may be too short."
        )

    # Step 3: Drop near-duplicate consecutive frames (SSIM > threshold)
    distinct_frames = [sharp_frames[0]]
    for i in range(1, len(sharp_frames)):
        prev_gray = distinct_frames[-1][2]
        curr_gray = sharp_frames[i][2]
        ssim_score = compute_ssim(prev_gray, curr_gray)
        if ssim_score <= SSIM_DUPLICATE_THRESHOLD:
            distinct_frames.append(sharp_frames[i])
        else:
            logger.debug(f"Discarding near-duplicate frame {sharp_frames[i][0].name} (SSIM={ssim_score:.3f})")

    if len(distinct_frames) < MIN_FRAMES:
        raise VideoProcessingError(
            f"Only {len(distinct_frames)} distinct frames after deduplication (need {MIN_FRAMES}). "
            "Please re-record with more movement between positions."
        )

    # Step 4: Keep up to MAX_FRAMES most distinct frames
    selected = _select_most_distinct(distinct_frames, MAX_FRAMES)

    # Save final frames with clean naming
    saved_paths = []
    for idx, (_, img, _) in enumerate(selected):
        out_name = f"frame_{idx + 1:03d}.jpg"
        out_path = out_dir / out_name
        cv2.imwrite(str(out_path), img)
        # Return path relative to FRAMES_DIR for URL construction
        saved_paths.append(f"{audit_id}/{module_id}/{out_name}")

    # Clean up raw frames
    for p in raw_paths:
        p.unlink(missing_ok=True)

    logger.info(f"Extracted {len(saved_paths)} key frames for module {module_id}")
    return saved_paths


def _select_most_distinct(frames: list, max_count: int) -> list:
    """Greedy selection: keep frames with lowest average SSIM to already-selected set."""
    if len(frames) <= max_count:
        return frames

    # Always keep first and last
    selected = [frames[0], frames[-1]]
    remaining = frames[1:-1]

    while len(selected) < max_count and remaining:
        # Find the frame in remaining with lowest avg SSIM to selected set
        best_idx = 0
        best_score = float("inf")
        for i, (_, _, gray_r) in enumerate(remaining):
            avg_ssim = np.mean([
                compute_ssim(gray_r, gray_s)
                for _, _, gray_s in selected
            ])
            if avg_ssim < best_score:
                best_score = avg_ssim
                best_idx = i
        selected.append(remaining.pop(best_idx))

    # Sort by original index (approximate — use filename ordering)
    return selected
