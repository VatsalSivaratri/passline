"""
Step 4: Reference Object Calibration

Detects credit card or US letter paper in key frames: multi-scale Canny +
morphological closing + quadrilateral contour search.
Returns pixels_per_inch scale factor or None.
"""

import logging
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Known reference object dimensions (inches)
REFERENCE_OBJECTS = {
    "credit_card": {"long": 3.375, "short": 2.125},
    "letter_paper": {"long": 11.0, "short": 8.5},
}
ASPECT_RATIO_TOLERANCE = 0.10  # ±10%
MIN_CONTOUR_AREA_FRACTION = 0.002  # >0.2% of frame: a credit card at arm's length in 4K is ~0.3%


# Working resolutions for the edge search, long side in pixels. Several scales
# because the right one depends on how big the object is in frame: small
# objects need resolution, large ones need noise averaged away.
SEARCH_LONG_SIDES = (960, 1440, 640)
MIN_RECT_FILL = 0.85  # contour area / bounding-rect area
CLOSE_KERNEL = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))


def _find_quads(gray_small: np.ndarray) -> list:
    """
    Canny + morphological closing at one scale. Returns candidate
    (rect, aspect) tuples in the small image's pixel coordinates.

    Why closing: on noisy or motion-blurred frames Canny returns the object's
    outline as many short open segments. An open curve encloses ~0 area, so
    every piece fails the area threshold. Closing (dilate then erode) bridges
    the gaps so the outline becomes one closed contour again.
    """
    h, w = gray_small.shape
    blurred = cv2.GaussianBlur(gray_small, (5, 5), 0)
    # Thresholds from the image's median brightness instead of fixed 50/150,
    # so the same code works in dim and bright rooms. Deliberately conservative:
    # lower thresholds also catch low-contrast cards, but they pick up other
    # card-shaped rectangles (a ceiling vent grille in testing). A wrong scale is
    # worse than no scale, because no scale falls back to depth at a lower tier.
    med = float(np.median(blurred))
    edges = cv2.Canny(blurred, int(max(0, 0.66 * med)), int(min(255, 1.33 * med)))
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, CLOSE_KERNEL, iterations=2)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    quads = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < h * w * MIN_CONTOUR_AREA_FRACTION:
            continue
        approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        rect = cv2.minAreaRect(approx)
        rw, rh = rect[1]
        if min(rw, rh) == 0:
            continue
        if area / (rw * rh) < MIN_RECT_FILL:  # four corners but not actually rectangular
            continue
        quads.append((rect, max(rw, rh) / min(rw, rh)))
    return quads


def detect_reference_object(
    frame: np.ndarray,
) -> Tuple[Optional[float], Optional[str], float]:
    """
    Returns (pixels_per_inch, reference_type, confidence) or (None, None, 0.0).
    pixels_per_inch is in the ORIGINAL frame's resolution.

    Multi-scale: the frame is downscaled to each size in SEARCH_LONG_SIDES and
    searched there. Downscaling averages sensor noise and shrinks gaps in the
    edges, which is what full-resolution 4K Canny was missing. The first scale
    that finds a match wins; results are mapped back to full resolution.
    """
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    best: Optional[Tuple[float, str, float]] = None
    for long_side in SEARCH_LONG_SIDES:
        scale = min(1.0, long_side / max(h, w))
        small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        for rect, aspect in _find_quads(small):
            long_px = max(rect[1]) / scale  # back to full-resolution pixels
            for ref_name, dims in REFERENCE_OBJECTS.items():
                known = dims["long"] / dims["short"]
                err = abs(aspect - known) / known
                if err <= ASPECT_RATIO_TOLERANCE:
                    conf = 1.0 - err
                    if best is None or conf > best[2]:
                        best = (long_px / dims["long"], ref_name, conf)
        if best:
            break

    if best:
        ppi, ref_name, conf = best
        logger.info(f"Reference object detected: {ref_name} at {ppi:.1f} px/in (confidence={conf:.2f})")
        return ppi, ref_name, conf
    return None, None, 0.0


def calibrate_frames(frames_bgr: list) -> dict:
    """
    Try to find a reference object in any of the provided frames.
    Returns calibration result dict.
    """
    best_ppi = None
    best_type = None
    best_conf = 0.0

    for img in frames_bgr:
        ppi, ref_type, conf = detect_reference_object(img)
        if ppi is not None and conf > best_conf:
            best_ppi = ppi
            best_type = ref_type
            best_conf = conf

    return {
        "pixels_per_inch": best_ppi,
        "reference_type": best_type,
        "confidence": best_conf,
        "calibrated": best_ppi is not None,
    }


def pixels_to_inches(pixels: float, pixels_per_inch: float) -> float:
    return pixels / pixels_per_inch
