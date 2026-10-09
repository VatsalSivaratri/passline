"""
Feature-based ADA compliance checks. The rules live in data/rules.yaml and are
evaluated by services/rules_engine.py; this module keeps the old entry point.
"""

from typing import List

from models.audit import Violation
from services.rules_engine import evaluate


def check_feature_compliance(
    features: list,
    module_id: str,
    depth_measurements: dict,
    calibrated: bool,
) -> List[Violation]:
    # depth_measurements is not used yet: every current rule reads model-observed
    # properties. Measured rules arrive with the geometry core (design review, phase 1).
    return evaluate(features, module_id, calibrated)
