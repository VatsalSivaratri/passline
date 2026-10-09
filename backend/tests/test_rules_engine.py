"""
data/rules.yaml + services/rules_engine.py must behave exactly like the original
Python lambdas (tests/legacy_feature_rules.py), and every rule must be reachable.
"""

import random
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import legacy_feature_rules as legacy  # noqa: E402
from services.rules_engine import Condition, RULES_PATH, Rule, evaluate, load_rules  # noqa: E402

RULES = load_rules()
LEGACY = {r["rule_id"]: (ftype, r) for ftype, rs in legacy.FEATURE_RULES.items() for r in rs}


def legacy_hits(features):
    return sorted((f["feature_type"], r["rule_id"], r["finding"](f.get("properties", {})))
                  for f in features
                  for r in legacy.FEATURE_RULES.get(f["feature_type"], [])
                  if r["condition"](f.get("properties", {})))


def engine_hits(features):
    return sorted((v.module_type, v.rule_id, v.finding) for v in evaluate(features, "m", False))


# ---- structure ----

def test_same_rule_set_as_legacy():
    assert {r.id for r in RULES} == set(LEGACY)


def test_sections_and_metadata_carried_over():
    for r in RULES:
        ftype, old = LEGACY[r.id]
        assert r.feature_type == ftype
        assert f"ADA §{r.section}" == old["code"]
        assert (r.severity, r.element) == (old["severity"], old["element"])


def test_provision_count():
    # The resume number comes from here, not from memory.
    assert len({r.section for r in RULES}) == 40
    assert len(RULES) == 45


# ---- per-rule: each rule fires on an input built from its own condition ----

def triggering_props(rule: Rule) -> dict:
    clauses = rule.when.all or rule.when.any[:1]
    props = {}
    for c in clauses:
        if c.op == "in":
            props[c.field] = c.value[0]
        elif c.op == "gt":
            props[c.field] = c.value + 1
        elif c.op == "is_not":
            props[c.field] = not c.value
        else:  # eq, is
            props[c.field] = c.value
    return props


@pytest.mark.parametrize("rule", RULES, ids=lambda r: r.id)
def test_rule_fires_and_matches_legacy(rule):
    feature = {"feature_type": rule.feature_type, "properties": triggering_props(rule)}
    assert rule.id in {v.rule_id for v in evaluate([feature], "m", False)}
    assert engine_hits([feature]) == legacy_hits([feature])


# ---- randomized equivalence ----

def value_pool():
    pool = {None, True, False, 0, 1, 2, "x"}
    for r in RULES:
        for c in (r.when.all or []) + (r.when.any or []):
            for v in (c.value if isinstance(c.value, list) else [c.value]):
                pool.add(v)
    return sorted(pool, key=repr)


def test_random_inputs_match_legacy():
    rng = random.Random(0)
    fields = sorted({c.field for r in RULES for c in (r.when.all or []) + (r.when.any or [])})
    types = sorted({r.feature_type for r in RULES})
    pool = value_pool()
    for _ in range(20_000):
        props = {f: rng.choice(pool) for f in rng.sample(fields, rng.randint(0, 4))}
        feature = {"feature_type": rng.choice(types), "properties": props}
        try:
            expected = legacy_hits([feature])
        except TypeError:  # legacy crashes on e.g. "x" > 0; engine logs and skips that rule
            continue
        assert engine_hits([feature]) == expected, feature


# ---- engine semantics and validation ----

def test_is_means_identity_not_truthiness():
    c = Condition.model_validate({"all": [{"field": "present", "op": "is", "value": False}]})
    assert c.test({"present": False})
    assert not c.test({"present": 0}) and not c.test({"present": None}) and not c.test({})


def test_condition_needs_exactly_one_of_all_any():
    with pytest.raises(ValueError):
        Condition.model_validate({"all": [], "any": []})


def test_duplicate_ids_rejected(tmp_path):
    raw = yaml.safe_load(RULES_PATH.read_text())
    p = tmp_path / "dupe.yaml"
    p.write_text(yaml.safe_dump(raw + raw[:1]))
    with pytest.raises(ValueError, match="duplicate"):
        load_rules(p)


def test_bad_model_value_does_not_crash():
    feature = {"feature_type": "parking_space", "properties": {"count": "several", "van_accessible": False}}
    evaluate([feature], "m", False)  # 'gt' on a string is logged and skipped
