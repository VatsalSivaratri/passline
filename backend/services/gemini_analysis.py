"""
Step 5A: Gemini Feature Detection

Sends key frames to Gemini 2.5 Flash with a universal feature-detection prompt.
Returns every ADA-relevant feature visible in the frames, with per-feature properties.
"""

import json
import logging
from pathlib import Path
from typing import List

from google import genai  # type: ignore
from google.genai import types as genai_types  # type: ignore

from config import GEMINI_API_KEY, GEMINI_MODEL, FRAMES_DIR, MODULE_TYPES

logger = logging.getLogger(__name__)

_genai_client = None

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


def _call_gemini(parts: list, prompt: str, retries: int = 2) -> dict:
    """Call Gemini 2.5 Flash with image parts and return parsed JSON."""
    contents = [prompt] + parts
    config = genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.1,
    )
    for attempt in range(retries + 1):
        try:
            response = _get_client().models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )
            text = response.text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except json.JSONDecodeError as e:
            if attempt == retries:
                logger.error(f"Gemini returned invalid JSON after {retries+1} attempts: {e}")
                raise
            logger.warning(f"Gemini JSON parse error (attempt {attempt+1}), retrying...")
        except Exception as e:
            if attempt == retries:
                raise
            logger.warning(f"Gemini API error (attempt {attempt+1}): {e}")
    return {}


async def analyze_features(frame_paths: List[str]) -> dict:
    """
    Universal ADA feature detection.
    Sends up to 8 frames and returns all detected ADA-relevant features.
    Returns: {"features": [{"feature_type": str, "properties": dict,
                             "confidence": float, "frame_index": int}, ...]}
    """
    selected_paths = frame_paths[:16]
    image_parts = []
    for p in selected_paths:
        try:
            image_parts.append(_load_frame_as_part(p))
        except Exception as e:
            logger.warning(f"Could not load frame {p}: {e}")

    if not image_parts:
        logger.warning("No frames available for feature analysis")
        return {"features": []}

    types_str = ", ".join(FEATURE_TYPES)
    prompt = (
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

    try:
        result = _call_gemini(image_parts, prompt)
        if "features" not in result:
            logger.warning("Gemini response missing 'features' key — wrapping")
            result = {"features": []}
        # Filter to only known feature types
        valid = [
            f for f in result["features"]
            if f.get("feature_type") in FEATURE_TYPES
        ]
        if len(valid) < len(result["features"]):
            logger.warning(
                f"Dropped {len(result['features']) - len(valid)} features with unknown type"
            )
        result["features"] = valid
        logger.info(f"analyze_features: detected {len(valid)} feature(s)")
        return result
    except Exception as e:
        logger.error(f"analyze_features failed: {e}")
        return {"features": []}


async def classify_room(frame_paths: List[str]) -> str:
    """
    Use Gemini to identify the room/space type from extracted frames.
    Returns one of the MODULE_TYPES strings. Falls back to 'entrance' on failure.
    """
    selected_paths = frame_paths[:5]
    image_parts = []
    for p in selected_paths:
        try:
            image_parts.append(_load_frame_as_part(p))
        except Exception as e:
            logger.warning(f"Could not load frame {p} for classification: {e}")

    if not image_parts:
        logger.warning("No frames available for room classification — defaulting to 'entrance'")
        return "entrance"

    types_list = ", ".join(MODULE_TYPES)
    prompt = (
        "You are analyzing frames from a building space for ADA compliance auditing.\n"
        "Identify what type of space or room is shown in these images.\n\n"
        f"You MUST return exactly one value from this list:\n{types_list}\n\n"
        'Return ONLY a JSON object with this exact structure: {"room_type": "<value>"}\n'
        "No explanation, no markdown, just the JSON."
    )

    try:
        config = genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
        )
        response = _get_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt] + image_parts,
            config=config,
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        detected = result.get("room_type", "").strip()
        if detected in MODULE_TYPES:
            logger.info(f"Room classified as: {detected}")
            return detected
        logger.warning(f"Gemini returned unrecognized room type '{detected}' — defaulting to 'entrance'")
    except Exception as e:
        logger.error(f"Room classification failed: {e} — defaulting to 'entrance'")

    return "entrance"


def get_default_result() -> dict:
    """Return a safe default result when Gemini is unavailable."""
    return {"features": []}
