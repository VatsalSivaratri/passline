"""
Rule engine: evaluates detected features against data/rules.yaml.

Rules are data, one entry per check, each citing its 2010 ADA Standards
section. This module only knows how to evaluate a condition; it holds no
ADA knowledge itself. Adding or fixing a rule means editing the YAML file.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Literal, Optional, Union

import yaml
from pydantic import BaseModel, Field, model_validator

from models.audit import RemediationCost, Violation

logger = logging.getLogger(__name__)

RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "rules.yaml"


class Clause(BaseModel):
    field: str
    op: Literal["eq", "in", "is", "is_not", "gt"]
    value: Any
    default: Any = None  # used when the property is absent, like dict.get(field, default)

    def test(self, props: dict) -> bool:
        x = props.get(self.field, self.default)
        if self.op == "eq":
            return x == self.value
        if self.op == "in":
            return x in self.value
        if self.op == "is":
            return x is self.value  # identity: only a real True/False matches, not "yes" or 1
        if self.op == "is_not":
            return x is not self.value
        if self.op == "gt":
            return x is not None and x > self.value
        raise AssertionError(self.op)


class Condition(BaseModel):
    all: Optional[List[Clause]] = None
    any: Optional[List[Clause]] = None

    @model_validator(mode="after")
    def exactly_one(self):
        if (self.all is None) == (self.any is None):
            raise ValueError("a condition needs exactly one of 'all' or 'any'")
        return self

    def test(self, props: dict) -> bool:
        if self.all is not None:
            return all(c.test(props) for c in self.all)
        return any(c.test(props) for c in self.any)


class Rule(BaseModel):
    id: str
    feature_type: str
    section: str
    element: str
    severity: Literal["critical", "high", "medium", "low"]
    when: Condition
    finding: str  # may contain {property} placeholders
    remediation_cost_usd: List[float] = Field(min_length=2, max_length=2)

    def render_finding(self, props: dict) -> str:
        return self.finding.format_map(_Missing(props))


class _Missing(dict):
    """format_map helper: an absent property renders as 'None', matching the old f-strings."""

    def __missing__(self, key):
        return "None"


@lru_cache(maxsize=None)
def load_rules(path: Union[str, Path] = RULES_PATH) -> tuple:
    raw = yaml.safe_load(Path(path).read_text())
    rules = tuple(Rule.model_validate(r) for r in raw)
    ids = [r.id for r in rules]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate rule ids in {path}: {sorted(dupes)}")
    return rules


def evaluate(features: list, module_id: str, calibrated: bool, rules=None) -> List[Violation]:
    """Return a Violation for every (feature, rule) pair whose condition holds."""
    rules = load_rules() if rules is None else rules
    by_type: dict = {}
    for r in rules:
        by_type.setdefault(r.feature_type, []).append(r)

    out = []
    for feature in features:
        ftype = feature.get("feature_type")
        props = feature.get("properties") or {}
        for rule in by_type.get(ftype, []):
            try:
                hit = rule.when.test(props)
            except TypeError as e:  # e.g. gt on a string the model returned
                logger.warning(f"Rule {rule.id} could not evaluate {props}: {e}")
                continue
            if hit:
                lo, hi = rule.remediation_cost_usd
                out.append(Violation(
                    module_id=module_id,
                    module_type=ftype,
                    rule_id=rule.id,
                    code=f"ADA §{rule.section}",
                    element=rule.element,
                    finding=rule.render_finding(props),
                    severity=rule.severity,
                    calibrated=calibrated,
                    confidence=float(feature.get("confidence", 0.5)),
                    remediation_cost=RemediationCost(low=lo, high=hi),
                ))
    logger.info(f"rules: {len(out)} violation(s) from {len(features)} feature(s)")
    return out
