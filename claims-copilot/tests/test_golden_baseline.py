"""Regression gate: hero-case snapshots must stay byte-identical after each refactor.

Run:
    pytest tests/test_golden_baseline.py

The fixture is generated once by tests/create_baseline.py and committed. Every
workstream (WS2, WS3, WS4, WS5) must leave these numbers unchanged — if they
drift, the refactor changed behavior, not just structure.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import initialize_car_data

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "golden_baseline.json")
HERO_CLAIM_IDS = ["COL-107", "THEFT-009", "LIAB-021"]


@pytest.fixture(scope="module")
def baseline():
    if not os.path.exists(FIXTURE_PATH):
        pytest.skip(
            "Golden baseline fixture not found. "
            "Run `python tests/create_baseline.py` first."
        )
    with open(FIXTURE_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ctx():
    return initialize_car_data(force_regenerate=True)


@pytest.mark.parametrize("claim_id", HERO_CLAIM_IDS)
def test_hero_risk_score(claim_id, ctx, baseline):
    expected = baseline["hero_cases"][claim_id]
    risk = ctx.claim_risk_scores.get(claim_id)
    assert risk is not None, f"No risk score for {claim_id}"
    assert risk.total_score == expected["risk_score"], (
        f"{claim_id}: score {risk.total_score} != baseline {expected['risk_score']}"
    )


@pytest.mark.parametrize("claim_id", HERO_CLAIM_IDS)
def test_hero_risk_tier(claim_id, ctx, baseline):
    expected = baseline["hero_cases"][claim_id]
    risk = ctx.claim_risk_scores.get(claim_id)
    assert risk is not None
    assert risk.tier == expected["risk_tier"], (
        f"{claim_id}: tier '{risk.tier}' != baseline '{expected['risk_tier']}'"
    )


@pytest.mark.parametrize("claim_id", HERO_CLAIM_IDS)
def test_hero_triggered_rules(claim_id, ctx, baseline):
    expected = baseline["hero_cases"][claim_id]
    rules = ctx.claim_rules.get(claim_id, [])
    triggered = sorted(r.rule_id for r in rules if r.triggered)
    assert triggered == expected["triggered_rule_ids"], (
        f"{claim_id}: triggered rules {triggered} != baseline {expected['triggered_rule_ids']}"
    )


@pytest.mark.parametrize("claim_id", HERO_CLAIM_IDS)
def test_hero_queue_position(claim_id, ctx, baseline):
    expected = baseline["hero_cases"][claim_id]
    queue_pos = next(
        (i for i, c in enumerate(ctx.case_queue) if c.case_id == claim_id), None
    )
    assert queue_pos == expected["queue_position"], (
        f"{claim_id}: queue position {queue_pos} != baseline {expected['queue_position']}"
    )


def test_queue_length(ctx, baseline):
    assert len(ctx.case_queue) == baseline["meta"]["total_cases"], (
        f"Queue length {len(ctx.case_queue)} != baseline {baseline['meta']['total_cases']}"
    )


def test_top10_queue_order(ctx, baseline):
    top10 = [c.case_id for c in ctx.case_queue[:10]]
    assert top10 == baseline["meta"]["top10_queue_ids"], (
        f"Top-10 order changed.\n  Got:      {top10}\n  Baseline: {baseline['meta']['top10_queue_ids']}"
    )
