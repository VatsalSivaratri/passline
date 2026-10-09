# Frozen copy of the hackathon rules, kept only so tests/test_rules_engine.py can prove
# data/rules.yaml + services/rules_engine.py behave identically. Do not edit.
"""
Feature-based ADA compliance rules.

FEATURE_RULES maps each feature_type to a list of rule dicts.
check_feature_compliance() evaluates detected features against these rules
and returns a list of Violation objects.
"""

import logging
from typing import List

from models.audit import Violation, RemediationCost  # noqa: F401  (kept as the original)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rule table
# Each rule: rule_id, condition(props)->bool, severity, element,
#            finding(props)->str, code, remediation_cost=(low, high)
# ---------------------------------------------------------------------------

FEATURE_RULES = {
    "door": [
        {
            "rule_id": "door_width_narrow",
            "condition": lambda p: p.get("width_relative") == "narrow",
            "severity": "critical",
            "element": "Door",
            "finding": lambda p: "Door appears too narrow for wheelchair passage (minimum 32\" clear width required).",
            "code": "ADA §404.2.3",
            "remediation_cost": (700, 2500),
        },
    ],
    "door_hardware": [
        {
            "rule_id": "door_hardware_knob",
            "condition": lambda p: p.get("handle_type") in ("round_knob", "knob"),
            "severity": "high",
            "element": "Door Hardware",
            "finding": lambda p: "Round knob hardware requires tight grasp; lever-style hardware required.",
            "code": "ADA §404.2.7",
            "remediation_cost": (75, 200),
        },
    ],
    "door_threshold": [
        {
            "rule_id": "door_threshold_raised",
            "condition": lambda p: p.get("appears_raised") is True,
            "severity": "medium",
            "element": "Door Threshold",
            "finding": lambda p: "Threshold appears raised above ½\" maximum; may impede wheelchair travel.",
            "code": "ADA §404.2.5",
            "remediation_cost": (200, 600),
        },
    ],
    "door_closer": [
        {
            "rule_id": "door_closer_inward",
            "condition": lambda p: p.get("present") is True and p.get("swing_direction") == "inward",
            "severity": "low",
            "element": "Door Closer",
            "finding": lambda p: "Inward-swinging door with closer may be difficult for wheelchair users; check closing speed.",
            "code": "ADA §404.2.8",
            "remediation_cost": (150, 400),
        },
    ],
    "toilet": [
        {
            "rule_id": "toilet_height",
            "condition": lambda p: p.get("height_relative") in ("high", "low"),
            "severity": "medium",
            "element": "Toilet",
            "finding": lambda p: f"Toilet seat height appears {p.get('height_relative')}; accessible range is 17\"–19\" from floor.",
            "code": "ADA §604.4",
            "remediation_cost": (500, 2000),
        },
    ],
    "toilet_grab_bar": [
        {
            "rule_id": "toilet_grab_bar_missing",
            "condition": lambda p: p.get("present") is False,
            "severity": "critical",
            "element": "Toilet Grab Bar",
            "finding": lambda p: "No grab bars detected at toilet; grab bars are required on side and rear walls.",
            "code": "ADA §604.5",
            "remediation_cost": (300, 900),
        },
        {
            "rule_id": "toilet_grab_bar_one_side",
            "condition": lambda p: p.get("present") is not False and p.get("both_sides") is False,
            "severity": "high",
            "element": "Toilet Grab Bar",
            "finding": lambda p: "Grab bar detected on only one side; both side and rear grab bars are required.",
            "code": "ADA §604.5.1",
            "remediation_cost": (200, 600),
        },
    ],
    "sink": [
        {
            "rule_id": "sink_height_high",
            "condition": lambda p: p.get("height_relative") == "high",
            "severity": "high",
            "element": "Sink",
            "finding": lambda p: "Sink rim appears too high; maximum 34\" height required for accessibility.",
            "code": "ADA §606.3",
            "remediation_cost": (400, 1500),
        },
    ],
    "sink_faucet": [
        {
            "rule_id": "sink_faucet_knob",
            "condition": lambda p: p.get("faucet_type") in ("knob", "round_knob"),
            "severity": "high",
            "element": "Sink Faucet",
            "finding": lambda p: "Round knob faucet requires tight grasp; lever or sensor faucet required.",
            "code": "ADA §606.4",
            "remediation_cost": (100, 350),
        },
    ],
    "sink_clearance": [
        {
            "rule_id": "sink_knee_clearance",
            "condition": lambda p: p.get("knee_clearance_present") is False,
            "severity": "high",
            "element": "Sink Clearance",
            "finding": lambda p: "Knee and toe clearance not visible below sink; 27\" knee clearance required.",
            "code": "ADA §606.2",
            "remediation_cost": (500, 2000),
        },
    ],
    "mirror": [
        {
            "rule_id": "mirror_height_high",
            "condition": lambda p: p.get("height_relative") == "high",
            "severity": "low",
            "element": "Mirror",
            "finding": lambda p: "Mirror bottom edge appears too high; maximum 40\" height required over accessible sinks.",
            "code": "ADA §603.3",
            "remediation_cost": (50, 150),
        },
    ],
    "grab_bar": [
        {
            "rule_id": "grab_bar_missing",
            "condition": lambda p: p.get("present") is False,
            "severity": "medium",
            "element": "Grab Bar",
            "finding": lambda p: "Grab bar absent in area where one is required.",
            "code": "ADA §604.5",
            "remediation_cost": (200, 600),
        },
    ],
    "handrail": [
        {
            "rule_id": "handrail_missing",
            "condition": lambda p: p.get("present") is False,
            "severity": "critical",
            "element": "Handrail",
            "finding": lambda p: "No handrail detected; handrails are required on both sides of stairs and ramps.",
            "code": "ADA §505.2",
            "remediation_cost": (400, 1200),
        },
        {
            "rule_id": "handrail_one_side",
            "condition": lambda p: p.get("present") is not False and p.get("both_sides") is False,
            "severity": "high",
            "element": "Handrail",
            "finding": lambda p: "Handrail visible on one side only; handrails required on both sides.",
            "code": "ADA §505.3",
            "remediation_cost": (300, 800),
        },
        {
            "rule_id": "handrail_no_extension",
            "condition": lambda p: p.get("present") is not False and p.get("extension_present") is False,
            "severity": "medium",
            "element": "Handrail",
            "finding": lambda p: "Handrail extension beyond top/bottom of stair not visible; 12\" extension required.",
            "code": "ADA §505.10",
            "remediation_cost": (300, 900),
        },
    ],
    "stair": [
        {
            "rule_id": "stair_no_handrail",
            "condition": lambda p: p.get("handrail") is False or p.get("handrails_present") is False,
            "severity": "critical",
            "element": "Stair",
            "finding": lambda p: "Stair without handrails detected; handrails required on both sides.",
            "code": "ADA §504.6",
            "remediation_cost": (400, 1200),
        },
    ],
    "stair_nosing": [
        {
            "rule_id": "stair_nosing_missing",
            "condition": lambda p: p.get("present") is False,
            "severity": "medium",
            "element": "Stair Nosing",
            "finding": lambda p: "Stair nosing not detected; nosings must be non-projecting and contrast with tread.",
            "code": "ADA §504.5",
            "remediation_cost": (200, 800),
        },
    ],
    "tactile_warning_strip": [
        {
            "rule_id": "tactile_strip_missing",
            "condition": lambda p: p.get("present") is False,
            "severity": "high",
            "element": "Tactile Warning Strip",
            "finding": lambda p: "Tactile detectable warning surface not visible at top of stairs or ramp.",
            "code": "ADA §705",
            "remediation_cost": (300, 1000),
        },
    ],
    "ramp": [
        {
            "rule_id": "ramp_no_handrails",
            "condition": lambda p: p.get("handrails_present") is False,
            "severity": "critical",
            "element": "Ramp",
            "finding": lambda p: "Ramp detected without handrails; handrails required when rise exceeds 6\".",
            "code": "ADA §405.8",
            "remediation_cost": (400, 1200),
        },
        {
            "rule_id": "ramp_steep_slope",
            "condition": lambda p: p.get("slope_apparent") == "steep",
            "severity": "critical",
            "element": "Ramp",
            "finding": lambda p: "Ramp slope appears to exceed the 1:12 maximum ratio.",
            "code": "ADA §405.2",
            "remediation_cost": (2000, 8000),
        },
        {
            "rule_id": "ramp_poor_surface",
            "condition": lambda p: p.get("surface_condition") in ("loose", "uneven", "cracked"),
            "severity": "high",
            "element": "Ramp",
            "finding": lambda p: f"Ramp surface appears {p.get('surface_condition')}; stable, firm, and slip-resistant surface required.",
            "code": "ADA §402.1",
            "remediation_cost": (500, 3000),
        },
    ],
    "curb_cut": [
        {
            "rule_id": "curb_cut_missing",
            "condition": lambda p: p.get("present") is False,
            "severity": "critical",
            "element": "Curb Cut",
            "finding": lambda p: "No curb cut detected; curb ramps required at all pedestrian crossings.",
            "code": "ADA §406",
            "remediation_cost": (800, 3000),
        },
    ],
    "hallway": [
        {
            "rule_id": "hallway_width_narrow",
            "condition": lambda p: p.get("width_relative") == "narrow",
            "severity": "critical",
            "element": "Corridor",
            "finding": lambda p: "Corridor appears narrower than the 36\" minimum clear width.",
            "code": "ADA §403.5.1",
            "remediation_cost": (1500, 8000),
        },
        {
            "rule_id": "hallway_poor_surface",
            "condition": lambda p: p.get("surface_condition") in ("uneven", "cracked", "slippery"),
            "severity": "high",
            "element": "Corridor",
            "finding": lambda p: f"Corridor floor surface appears {p.get('surface_condition')}; stable, firm surface required.",
            "code": "ADA §402.1",
            "remediation_cost": (500, 2000),
        },
    ],
    "floor_surface": [
        {
            "rule_id": "floor_surface_condition",
            "condition": lambda p: p.get("surface_condition") in ("loose", "uneven", "cracked", "thick_carpet"),
            "severity": "medium",
            "element": "Floor Surface",
            "finding": lambda p: f"Floor surface appears {p.get('surface_condition')}; accessible routes require firm, stable, slip-resistant surfaces.",
            "code": "ADA §402.1",
            "remediation_cost": (300, 2000),
        },
    ],
    "parking_space": [
        {
            "rule_id": "parking_no_accessible_spaces",
            "condition": lambda p: p.get("count") == 0,
            "severity": "critical",
            "element": "Parking Space",
            "finding": lambda p: "No accessible parking spaces detected; at least one accessible space required.",
            "code": "ADA §208.2",
            "remediation_cost": (500, 1500),
        },
        {
            "rule_id": "parking_no_van_accessible",
            "condition": lambda p: p.get("count", 1) > 0 and p.get("van_accessible") is False,
            "severity": "high",
            "element": "Parking Space",
            "finding": lambda p: "Van-accessible space not detected; one van-accessible space required per accessible lot.",
            "code": "ADA §208.2.4",
            "remediation_cost": (300, 1000),
        },
    ],
    "parking_sign": [
        {
            "rule_id": "parking_sign_no_isa",
            "condition": lambda p: p.get("isa_present") is False,
            "severity": "critical",
            "element": "Parking Sign",
            "finding": lambda p: "Accessible parking sign without ISA symbol detected; sign must display International Symbol of Accessibility.",
            "code": "ADA §502.6",
            "remediation_cost": (100, 400),
        },
    ],
    "parking_access_aisle": [
        {
            "rule_id": "parking_aisle_missing",
            "condition": lambda p: p.get("present") is False,
            "severity": "critical",
            "element": "Parking Access Aisle",
            "finding": lambda p: "Access aisle not detected adjacent to accessible parking space.",
            "code": "ADA §502.3",
            "remediation_cost": (300, 1000),
        },
        {
            "rule_id": "parking_aisle_narrow",
            "condition": lambda p: p.get("present") is not False and p.get("width_relative") == "narrow",
            "severity": "high",
            "element": "Parking Access Aisle",
            "finding": lambda p: "Access aisle appears too narrow; 60\" minimum (96\" for van) required.",
            "code": "ADA §502.3",
            "remediation_cost": (300, 800),
        },
    ],
    "curb_ramp": [
        {
            "rule_id": "curb_ramp_missing",
            "condition": lambda p: p.get("present") is False,
            "severity": "critical",
            "element": "Curb Ramp",
            "finding": lambda p: "Curb ramp absent; required at transitions between sidewalk and road.",
            "code": "ADA §406",
            "remediation_cost": (800, 3000),
        },
        {
            "rule_id": "curb_ramp_steep",
            "condition": lambda p: p.get("present") is not False and p.get("slope_apparent") == "steep",
            "severity": "high",
            "element": "Curb Ramp",
            "finding": lambda p: "Curb ramp slope appears to exceed the 1:12 maximum ratio.",
            "code": "ADA §406.1",
            "remediation_cost": (500, 2000),
        },
    ],
    "counter": [
        {
            "rule_id": "counter_no_accessible_section",
            "condition": lambda p: p.get("height_relative") == "high" and p.get("accessible_section_present") is False,
            "severity": "high",
            "element": "Service Counter",
            "finding": lambda p: "Counter is high with no accessible lowered section; a portion at 28\"–34\" height is required.",
            "code": "ADA §904.4",
            "remediation_cost": (1200, 4000),
        },
    ],
    "service_window": [
        {
            "rule_id": "service_window_high",
            "condition": lambda p: p.get("height_relative") == "high",
            "severity": "high",
            "element": "Service Window",
            "finding": lambda p: "Service window appears too high for seated users; maximum 48\" reach height required.",
            "code": "ADA §904.4.1",
            "remediation_cost": (500, 2000),
        },
    ],
    "checkout_lane": [
        {
            "rule_id": "checkout_no_accessible_lane",
            "condition": lambda p: p.get("accessible_lane_present") is False,
            "severity": "high",
            "element": "Checkout Counter",
            "finding": lambda p: "No accessible checkout lane detected; at least one accessible lane required.",
            "code": "ADA §904.3",
            "remediation_cost": (1000, 4000),
        },
    ],
    "signage": [
        {
            "rule_id": "signage_height",
            "condition": lambda p: p.get("height_relative") in ("low", "high"),
            "severity": "medium",
            "element": "Signage",
            "finding": lambda p: f"Sign appears mounted {p.get('height_relative')}; signs must be 48\"–60\" to center line.",
            "code": "ADA §703.4.1",
            "remediation_cost": (50, 200),
        },
    ],
    "braille_signage": [
        {
            "rule_id": "braille_missing",
            "condition": lambda p: p.get("present") is False,
            "severity": "high",
            "element": "Braille Signage",
            "finding": lambda p: "Braille not detected on room identification sign; Grade 2 Braille required on tactile signs.",
            "code": "ADA §703.3",
            "remediation_cost": (100, 400),
        },
    ],
    "exit_sign": [
        {
            "rule_id": "exit_sign_high",
            "condition": lambda p: p.get("height_relative") == "high",
            "severity": "low",
            "element": "Exit Sign",
            "finding": lambda p: "Exit sign may be mounted outside the 80\" maximum head-clearance zone.",
            "code": "ADA §703.4",
            "remediation_cost": (50, 150),
        },
    ],
    "elevator_door": [
        {
            "rule_id": "elevator_door_narrow",
            "condition": lambda p: p.get("width_relative") == "narrow",
            "severity": "critical",
            "element": "Elevator Door",
            "finding": lambda p: "Elevator door appears too narrow; minimum 36\" clear opening required.",
            "code": "ADA §407.3.3",
            "remediation_cost": (2000, 8000),
        },
    ],
    "elevator_button": [
        {
            "rule_id": "elevator_button_high",
            "condition": lambda p: p.get("height_relative") == "high",
            "severity": "high",
            "element": "Elevator Button",
            "finding": lambda p: "Elevator call button appears above the 48\" maximum reach height.",
            "code": "ADA §407.4.6",
            "remediation_cost": (500, 2000),
        },
    ],
    "elevator_interior": [
        {
            "rule_id": "elevator_interior_tight",
            "condition": lambda p: p.get("clearance_relative") == "tight",
            "severity": "critical",
            "element": "Elevator Interior",
            "finding": lambda p: "Elevator interior appears too small; minimum 51\"×68\" floor area required.",
            "code": "ADA §407.4.1",
            "remediation_cost": (5000, 20000),
        },
    ],
    "drinking_fountain": [
        {
            "rule_id": "drinking_fountain_no_hi_lo",
            "condition": lambda p: p.get("hi_lo_present") is False,
            "severity": "high",
            "element": "Drinking Fountain",
            "finding": lambda p: "High-low drinking fountain pair not detected; a hi-lo configuration is required to serve both standing and wheelchair users.",
            "code": "ADA §211.2",
            "remediation_cost": (800, 3000),
        },
        {
            "rule_id": "drinking_fountain_knee_clearance",
            "condition": lambda p: p.get("knee_clearance_present") is False,
            "severity": "medium",
            "element": "Drinking Fountain",
            "finding": lambda p: "Knee clearance not visible beneath wheelchair-accessible fountain spout.",
            "code": "ADA §602.2",
            "remediation_cost": (300, 1000),
        },
    ],
    "bench": [
        {
            "rule_id": "bench_missing",
            "condition": lambda p: p.get("present") is False,
            "severity": "medium",
            "element": "Bench",
            "finding": lambda p: "No bench detected in changing or waiting area; a bench with back support is required.",
            "code": "ADA §903",
            "remediation_cost": (200, 800),
        },
    ],
    "pool_lift": [
        {
            "rule_id": "pool_lift_missing",
            "condition": lambda p: p.get("present") is False,
            "severity": "critical",
            "element": "Pool Lift",
            "finding": lambda p: "No pool lift detected; a means of accessible entry/exit is required for swimming pools.",
            "code": "ADA §242.2",
            "remediation_cost": (3000, 10000),
        },
    ],
    # Feature types with no rules (present for completeness)
    "paper_dispenser": [],
    "soap_dispenser": [],
    "coat_hook": [],
    "seating": [],
}


def _make_violation(rule: dict, feature: dict, module_id: str, calibrated: bool) -> Violation:
    props = feature.get("properties", {})
    return Violation(
        module_id=module_id,
        module_type=feature["feature_type"],  # repurpose field for feature type
        rule_id=rule["rule_id"],
        code=rule["code"],
        element=rule["element"],
        finding=rule["finding"](props),
        severity=rule["severity"],
        calibrated=calibrated,
        confidence=float(feature.get("confidence", 0.5)),
        remediation_cost=RemediationCost(
            low=rule["remediation_cost"][0],
            high=rule["remediation_cost"][1],
        ),
    )


def check_feature_compliance(
    features: list,
    module_id: str,
    depth_measurements: dict,
    calibrated: bool,
) -> List[Violation]:
    """
    Evaluate detected features against FEATURE_RULES and return violations.
    """
    violations = []
    for feature in features:
        ftype = feature.get("feature_type")
        rules = FEATURE_RULES.get(ftype, [])
        props = feature.get("properties", {})
        for rule in rules:
            try:
                if rule["condition"](props):
                    v = _make_violation(rule, feature, module_id, calibrated)
                    violations.append(v)
                    logger.debug(f"Violation: {rule['rule_id']} on {ftype}")
            except Exception as e:
                logger.warning(f"Rule {rule['rule_id']} evaluation error: {e}")
    logger.info(f"check_feature_compliance: {len(violations)} violation(s) from {len(features)} feature(s)")
    return violations
