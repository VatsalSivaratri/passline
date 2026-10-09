"""
Reference-object calibration on synthetic 4K frames with a known scale.

The original detector ran Canny on full-resolution frames. With any motion
blur or sensor noise, the object's outline came back as short open segments
(largest contour ~5 px^2 against a ~83,000 px^2 threshold), so calibration
failed on every real recording. The fix searches downscaled copies and closes
edge gaps morphologically. test_noisy_4k_paper is the case the old code failed.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.calibration import detect_reference_object  # noqa: E402

W, H = 3840, 2160
PPI = 60.0  # true scale of the synthetic scene, pixels per inch


def countertop(seed=0):
    """Gray surface with low-frequency streaks, like wood grain or laminate."""
    rng = np.random.default_rng(seed)
    g = rng.normal(0, 18, (H // 8, W // 8)).astype(np.float32)
    g = cv2.resize(cv2.GaussianBlur(g, (0, 0), 3), (W, H))
    return np.clip(120 + g[..., None], 0, 255).repeat(3, axis=2).astype(np.uint8)


def degrade(img, blur, noise, seed=1):
    """Horizontal motion blur plus Gaussian sensor noise."""
    if blur:
        k = np.zeros((2 * blur + 1, 2 * blur + 1), np.float32)
        k[blur, :] = 1 / (2 * blur + 1)
        img = cv2.filter2D(img, -1, k)
    rng = np.random.default_rng(seed)
    return np.clip(img + rng.normal(0, noise, img.shape), 0, 255).astype(np.uint8)


def with_object(long_in, short_in, color, angle=12, blur=0, noise=0, ppi=PPI):
    img = countertop()
    box = cv2.boxPoints(((W * 0.5, H * 0.5), (long_in * ppi, short_in * ppi), angle))
    cv2.fillConvexPoly(img, box.astype(np.int32), color)
    return degrade(img, blur, noise)


def paper(**kw):
    return with_object(11.0, 8.5, (235, 235, 230), **kw)


def card(color=(30, 30, 30), **kw):
    return with_object(3.375, 2.125, color, **kw)


def assert_scale(result, ref_type, ppi=PPI, tol=0.03):
    got_ppi, got_type, _ = result
    assert got_type == ref_type
    assert got_ppi == pytest.approx(ppi, rel=tol)


@pytest.mark.parametrize("blur,noise", [(0, 0), (3, 6), (6, 10), (10, 14)])
@pytest.mark.parametrize("angle", [0, 12, 35])
def test_noisy_4k_paper(blur, noise, angle):
    assert_scale(detect_reference_object(paper(blur=blur, noise=noise, angle=angle)), "letter_paper")


@pytest.mark.parametrize("blur,noise", [(0, 0), (6, 10), (10, 14)])
def test_dark_credit_card(blur, noise):
    # A card covers ~0.3% of a 4K frame; the old 1% area minimum rejected it outright.
    assert_scale(detect_reference_object(card(blur=blur, noise=noise)), "credit_card", tol=0.05)


def test_scale_reported_at_full_resolution():
    # Detection runs on a downscaled copy; px/in must be mapped back to the input size.
    half = cv2.resize(paper(blur=3, noise=6), (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    assert_scale(detect_reference_object(half), "letter_paper", ppi=PPI / 2)


def test_no_object_returns_none():
    assert detect_reference_object(degrade(countertop(), 6, 10)) == (None, None, 0.0)


@pytest.mark.xfail(strict=True, reason="known limit: low-contrast card (red on gray) is missed; "
                   "thresholds are kept high to avoid false scales from vents and switch plates")
def test_low_contrast_card():
    assert_scale(detect_reference_object(card(color=(40, 40, 200))), "credit_card", tol=0.05)
