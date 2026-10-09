"""
Step 5A: Gemini Feature Detection

Sends key frames to Gemini 2.5 Flash with a universal feature-detection prompt.
Returns every ADA-relevant feature visible in the frames, with per-feature properties.
"""

import hashlib
import json
import logging
import time
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from google import genai  # type: ignore
from google.genai import types as genai_types  # type: ignore

from config import GEMINI_API_KEY, GEMINI_MODEL, FRAMES_DIR, MODULE_TYPES

logger = logging.getLogger(__name__)

_genai_client = None


class AnalysisError(Exception):
    """Gemini could not produce a usable answer. Callers must handle this
    explicitly; there is no default result that pretends to be a prediction."""

FEATURE_TYPES = [
    "door", "door_hardware", "door_threshold", "door_closer",
    "toilet", "toilet_grab_bar", "sink", "sink_faucet", "sink_clearance",
    "mirror", "paper_dispenser", "soap_dispenser", "coat_hook",
    "grab_bar", "handrail", "stair", "stair_nosing", "tactile_warning_strip",
    "ramp", "curb_cut",
    "hallway", "floor_surface",
    "parking_space", "parking_sign", "parking_access_aisle", "curb_ramp",
    "counter", "service_window", "checkout_lane",
    "signage", "braille_signage", "exit_sign",
    "elevator_door", "elevator_button", "elevator_interior",
    "drinking_fountain",
    "seating", "bench",
    "pool_lift",
]


# ---------------------------------------------------------------------------
# Response schema. Passed to Gemini as response_schema so the model can only
# return known feature types and known property values, instead of free-form
# JSON that varies run to run. Property names and values match data/rules.yaml.
# ---------------------------------------------------------------------------

FeatureType = Enum("FeatureType", {t: t for t in FEATURE_TYPES}, type=str)


class Relative(str, Enum):
    narrow = "narrow"
    adequate = "adequate"
    wide = "wide"


class Height(str, Enum):
    low = "low"
    ok = "ok"
    high = "high"


class Slope(str, Enum):
    flat = "flat"
    gentle = "gentle"
    steep = "steep"


class Clearance(str, Enum):
    tight = "tight"
    adequate = "adequate"


class Hardware(str, Enum):
    lever = "lever"
    round_knob = "round_knob"
    knob = "knob"
    push_bar = "push_bar"
    pull_handle = "pull_handle"
    automatic = "automatic"


class Surface(str, Enum):
    firm = "firm"
    loose = "loose"
    uneven = "uneven"
    cracked = "cracked"
    slippery = "slippery"
    thick_carpet = "thick_carpet"


class FeatureProps(BaseModel):
    present: Optional[bool] = None
    width_relative: Optional[Relative] = None
    height_relative: Optional[Height] = None
    handle_type: Optional[Hardware] = None
    faucet_type: Optional[Hardware] = None
    appears_raised: Optional[bool] = None
    swing_direction: Optional[str] = None
    both_sides: Optional[bool] = None
    extension_present: Optional[bool] = None
    handrail: Optional[bool] = None
    handrails_present: Optional[bool] = None
    slope_apparent: Optional[Slope] = None
    surface_condition: Optional[Surface] = None
    clearance_relative: Optional[Clearance] = None
    knee_clearance_present: Optional[bool] = None
    hi_lo_present: Optional[bool] = None
    isa_present: Optional[bool] = None
    braille_present: Optional[bool] = None
    access_aisle_present: Optional[bool] = None
    van_accessible: Optional[bool] = None
    accessible_section_present: Optional[bool] = None
    accessible_lane_present: Optional[bool] = None
    count: Optional[int] = None


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class DetectedFeature(BaseModel):
    feature_type: FeatureType
    properties: FeatureProps
    confidence: float
    frame_index: int
    bounding_box: Optional[BoundingBox] = None


class FeaturesResponse(BaseModel):
    features: List[DetectedFeature]


def _get_client():
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
    return _genai_client


def _load_frame_as_part(frame_path: str):
    """Load a frame from disk and return a Gemini-compatible image part."""
    full_path = FRAMES_DIR / frame_path
    with open(str(full_path), "rb") as f:
        data = f.read()
    return genai_types.Part.from_bytes(data=data, mime_type="image/jpeg")


def _parse_json(text: str) -> dict:
    """Parse model output as JSON, tolerating a ```json fence around it."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def _call_gemini(parts: list, prompt: str, retries: int = 2,
                 temperature: float = 0.0, schema=None) -> dict:
    """Call Gemini with image parts and return parsed JSON.

    temperature 0 and a response schema are the defaults because the same
    frames should give the same answer; see tools/gemini_determinism.py.
    """
    contents = [prompt] + parts
    config = genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=temperature,
        response_schema=schema,
    )
    for attempt in range(retries + 1):
        try:
            response = _get_client().models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )
            return _parse_json(response.text)
        except json.JSONDecodeError as e:
            if attempt == retries:
                raise AnalysisError(f"invalid JSON after {retries + 1} attempts: {e}") from e
            logger.warning(f"Gemini JSON parse error (attempt {attempt+1}), retrying...")
        except Exception as e:
            if attempt == retries:
                raise AnalysisError(f"API call failed after {retries + 1} attempts: {e}") from e
            logger.warning(f"Gemini API error (attempt {attempt+1}): {e}")
            time.sleep(2 * 2 ** attempt)  # back off instead of hammering a rate-limited API
    raise AnalysisError("unreachable")


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:12]


def features_prompt() -> str:
    types_str = ", ".join(FEATURE_TYPES)
    return (
        "You are analyzing building images for ADA (Americans with Disabilities Act) "
        "accessibility compliance.\n"
        "Identify every ADA-relevant feature visible across all provided images.\n\n"
        "For each detected feature return:\n"
        "  - feature_type: MUST be exactly one of: [" + types_str + "]\n"
        "  - properties: object with key-value pairs describing what you observe.\n"
        "      Include relevant keys such as: handle_type, width_relative, height_relative,\n"
        "      present, appears_raised, faucet_type, isa_present, clearance_relative,\n"
        "      count, surface_type, swing_direction, braille_present, both_sides,\n"
        "      extension_present, slope_apparent, knee_clearance_present, hi_lo_present,\n"
        "      access_aisle_present, van_accessible, surface_condition\n"
        "  - confidence: float 0.0-1.0\n"
        "  - frame_index: integer index (0-based) of the frame where this feature is most visible\n"
        "  - bounding_box: normalized coordinates {x1, y1, x2, y2} (0.0-1.0) of the feature\n"
        "      in the frame at frame_index. Omit or set to null if you cannot localize it.\n\n"
        "Only include features you can actually see. Do not hallucinate features.\n"
        'Return ONLY: {"features": [ ... ]}'
    )


async def analyze_features(frame_paths: List[str], temperature: float = 0.0,
                           structured: bool = True) -> dict:
    """
    Universal ADA feature detection.
    Sends up to 8 frames and returns all detected ADA-relevant features.
    Returns: {"features": [{"feature_type": str, "properties": dict,
                             "confidence": float, "frame_index": int}, ...]}
    Raises AnalysisError if detection fails. An empty feature list means
    Gemini looked and found nothing, never that the call failed.
    """
    selected_paths = frame_paths[:16]
    image_parts = []
    for p in selected_paths:
        try:
            image_parts.append(_load_frame_as_part(p))
        except Exception as e:
            logger.warning(f"Could not load frame {p}: {e}")

    if not image_parts:
        raise AnalysisError("no frames could be loaded for feature detection")

    prompt = features_prompt()
    result = _call_gemini(image_parts, prompt, temperature=temperature,
                          schema=FeaturesResponse if structured else None)
    if not isinstance(result.get("features"), list):
        raise AnalysisError(f"response has no 'features' list: {str(result)[:200]}")
    for f in result["features"]:
        # A schema'd response spells every unset property as null. Drop those so
        # rules see "absent" exactly as before (p.get(key, default) needs absence).
        props = f.get("properties") or {}
        f["properties"] = {k: v for k, v in props.items() if v is not None}
    valid = [f for f in result["features"] if f.get("feature_type") in FEATURE_TYPES]
    if len(valid) < len(result["features"]):
        logger.warning(f"Dropped {len(result['features']) - len(valid)} features with unknown type")
    result["features"] = valid
    logger.info(f"analyze_features: detected {len(valid)} feature(s)")
    return result


async def classify_room(frame_paths: List[str]) -> str:
    """
    Use Gemini to identify the room/space type from extracted frames.
    Returns one of MODULE_TYPES. Raises AnalysisError on failure; the old
    behavior of returning 'entrance' made failures look like real predictions.
    """
    image_parts = []
    for p in frame_paths[:5]:
        try:
            image_parts.append(_load_frame_as_part(p))
        except Exception as e:
            logger.warning(f"Could not load frame {p} for classification: {e}")
    if not image_parts:
        raise AnalysisError("no frames could be loaded for room classification")

    types_list = ", ".join(MODULE_TYPES)
    prompt = (
        "You are analyzing frames from a building space for ADA compliance auditing.\n"
        "Identify what type of space or room is shown in these images.\n\n"
        f"You MUST return exactly one value from this list:\n{types_list}\n\n"
        'Return ONLY a JSON object with this exact structure: {"room_type": "<value>"}\n'
        "No explanation, no markdown, just the JSON."
    )
    result = _call_gemini(image_parts, prompt)
    detected = str(result.get("room_type", "")).strip()
    if detected not in MODULE_TYPES:
        raise AnalysisError(f"unrecognized room type {detected!r}")
    logger.info(f"Room classified as: {detected}")
    return detected
