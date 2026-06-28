"""Domain swap smoke test.

Initialises data for the active DOMAIN_MODE, builds the case queue, and
asserts the result is usable — no AttributeError, non-empty queue, no
phantom Case fields.  This is the test the old copy-rename flow never had.

Run:
    $env:DOMAIN_MODE="car_insurance"; pytest tests/test_domain_swap.py
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import domains  # noqa: F401
from core.registry import get_active_plugin
from main import initialize_data

PHANTOM_FIELDS = {"member_id", "employer_name", "provider_name"}


@pytest.fixture(scope="module")
def ctx():
    return initialize_data(force_regenerate=True)


@pytest.fixture(scope="module")
def plugin():
    return get_active_plugin()


def test_active_plugin_loads(plugin):
    """get_active_plugin() must not raise and must return a plugin with a name."""
    assert plugin.name, "plugin.name must be a non-empty string"


def test_initialize_data_returns_context(ctx):
    assert ctx is not None


def test_case_queue_nonempty(ctx):
    assert len(ctx.case_queue) > 0, "case_queue must have at least one case"


def test_no_attribute_error_on_common_accessors(ctx):
    for case in ctx.case_queue[:5]:
        _ = case.case_id
        _ = case.subject_name
        _ = case.risk_score
        _ = case.asset_description
        _ = case.counterparty_name


def test_no_phantom_fields_on_cases(ctx):
    for case in ctx.case_queue[:10]:
        for phantom in PHANTOM_FIELDS:
            assert not hasattr(case, phantom), \
                f"Case has phantom field '{phantom}' — domain data contract leak"


def test_claim_rules_populated(ctx):
    assert len(ctx.claim_rules) > 0
    sample_rules = next(iter(ctx.claim_rules.values()))
    assert isinstance(sample_rules, list)


def test_claim_risk_scores_populated(ctx):
    assert len(ctx.claim_risk_scores) > 0
    sample_score = next(iter(ctx.claim_risk_scores.values()))
    assert hasattr(sample_score, "total_score")
    assert 0.0 <= sample_score.total_score <= 100.0


def test_entities_dict_has_claims(ctx):
    assert "claims" in ctx.entities or len(ctx.claims) > 0


def test_graph_has_nodes(ctx):
    assert ctx.graph.number_of_nodes() > 0


def test_domain_config_matches_active_plugin(ctx, plugin):
    assert ctx.domain_config.name == plugin.name
