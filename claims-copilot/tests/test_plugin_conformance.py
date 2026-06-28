"""Plugin conformance tests.

For every plugin registered in DOMAIN_REGISTRY assert:
- All DomainPlugin fields are present and correctly typed
- generate_fn() returns the declared context_keys
- rules_fn() returns valid RuleResult objects on a minimal claim
- score_fn() returns a RiskBreakdown with total_score in [0, 100]
- build_queue_fn() returns a non-empty list of Cases with no phantom fields
- Case objects carry no legacy field names (member_id, employer_name, provider_name)

Run:
    pytest tests/test_plugin_conformance.py
"""

import os
import sys
import types
import inspect
from dataclasses import fields as dc_fields

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import domains  # noqa: F401 — registers all plugins
from core.registry import DOMAIN_REGISTRY
from core.contracts import DomainPlugin, DomainConfig


# ── Helpers ───────────────────────────────────────────────────────────────────

def _minimal_claim(plugin):
    """Return the first claim from a freshly generated data set (no cache)."""
    data = plugin.generate_fn()
    return data["claims"][0], data


PHANTOM_FIELDS = {"member_id", "employer_name", "provider_name"}


# ── Parametrize over all registered plugins ───────────────────────────────────

@pytest.fixture(scope="module", params=list(DOMAIN_REGISTRY.keys()))
def plugin(request):
    return DOMAIN_REGISTRY[request.param]


# ── 1. Type structure ─────────────────────────────────────────────────────────

def test_plugin_is_domainplugin(plugin):
    assert isinstance(plugin, DomainPlugin)


def test_plugin_name_is_string(plugin):
    assert isinstance(plugin.name, str) and plugin.name


def test_plugin_config_is_domaincofig(plugin):
    # DomainConfig may be imported from domain_config or core.contracts — check by class name.
    assert type(plugin.config).__name__ == "DomainConfig"


def test_plugin_display_name(plugin):
    assert isinstance(plugin.config.display_name, str) and plugin.config.display_name


def test_plugin_claim_types_nonempty(plugin):
    assert isinstance(plugin.config.claim_types, list) and len(plugin.config.claim_types) > 0


def test_plugin_risk_tiers_nonempty(plugin):
    assert isinstance(plugin.config.risk_tiers, dict) and len(plugin.config.risk_tiers) > 0


def test_plugin_callables(plugin):
    for attr in ("generate_fn", "rules_fn", "score_fn", "build_queue_fn",
                 "build_checklist_ctx", "dossier_context_fn"):
        assert callable(getattr(plugin, attr)), f"{attr} must be callable"


def test_plugin_set_tool_context_fns(plugin):
    assert isinstance(plugin.set_tool_context_fns, list)
    for fn in plugin.set_tool_context_fns:
        assert callable(fn)


def test_plugin_copilot_prompt_nonempty(plugin):
    assert isinstance(plugin.copilot_prompt, str) and plugin.copilot_prompt


def test_plugin_investigation_prompts_keys(plugin):
    prompts = plugin.investigation_prompts
    assert isinstance(prompts, dict)
    for key in ("ORCHESTRATOR", "INVESTIGATION", "DOSSIER"):
        assert key in prompts and prompts[key], f"investigation_prompts missing key: {key}"


def test_plugin_tools_lists(plugin):
    assert isinstance(plugin.copilot_tools, list) and len(plugin.copilot_tools) > 0
    assert isinstance(plugin.investigation_tools, list) and len(plugin.investigation_tools) > 0
    assert isinstance(plugin.dossier_tools, list) and len(plugin.dossier_tools) > 0


def test_plugin_checklist_module(plugin):
    mod = plugin.checklist_module
    assert hasattr(mod, "run_full_checklist"), "checklist_module must expose run_full_checklist"
    assert hasattr(mod, "run_checklist_step"), "checklist_module must expose run_checklist_step"
    assert hasattr(mod, "CHECKLIST_STEPS"), "checklist_module must expose CHECKLIST_STEPS"


def test_plugin_checklist_descriptions(plugin):
    desc = plugin.checklist_descriptions
    assert isinstance(desc, dict) and len(desc) > 0
    steps = plugin.checklist_module.CHECKLIST_STEPS
    for step_num, _ in steps:
        assert step_num in desc, f"checklist_descriptions missing step {step_num}"


def test_plugin_vision_prompt_nonempty(plugin):
    assert isinstance(plugin.vision_prompt, str) and plugin.vision_prompt


def test_plugin_context_keys_nonempty(plugin):
    assert isinstance(plugin.context_keys, list) and len(plugin.context_keys) > 0


# ── 2. generate_fn returns declared context_keys ─────────────────────────────

@pytest.fixture(scope="module")
def generated_data(plugin):
    return plugin.generate_fn()


def test_generate_fn_returns_claims(plugin, generated_data):
    assert "claims" in generated_data
    assert len(generated_data["claims"]) > 0


def test_generate_fn_returns_context_keys(plugin, generated_data):
    for key in plugin.context_keys:
        assert key in generated_data, f"generate_fn missing declared context_key: {key}"


# ── 3. rules_fn returns valid RuleResult list ────────────────────────────────

def test_rules_fn_returns_nonempty_list(plugin, generated_data):
    claim = generated_data["claims"][0]
    ctx = {k: generated_data[k] for k in plugin.context_keys if k in generated_data}
    results = plugin.rules_fn(claim, ctx)
    assert isinstance(results, list) and len(results) > 0


def test_rules_fn_result_shape(plugin, generated_data):
    claim = generated_data["claims"][0]
    ctx = {k: generated_data[k] for k in plugin.context_keys if k in generated_data}
    results = plugin.rules_fn(claim, ctx)
    for r in results:
        assert hasattr(r, "rule_id"), "RuleResult missing rule_id"
        assert hasattr(r, "triggered"), "RuleResult missing triggered"
        assert hasattr(r, "severity"), "RuleResult missing severity"
        assert isinstance(r.triggered, bool)


# ── 4. score_fn returns RiskBreakdown in [0, 100] ────────────────────────────

def test_score_fn_range(plugin, generated_data):
    claim = generated_data["claims"][0]
    ctx = {k: generated_data[k] for k in plugin.context_keys if k in generated_data}
    rules = plugin.rules_fn(claim, ctx)
    breakdown = plugin.score_fn(claim, ctx, rules)
    assert hasattr(breakdown, "total_score"), "RiskBreakdown missing total_score"
    assert hasattr(breakdown, "tier"), "RiskBreakdown missing tier"
    assert 0.0 <= breakdown.total_score <= 100.0, f"total_score out of range: {breakdown.total_score}"


def test_score_fn_tier_is_valid(plugin, generated_data):
    claim = generated_data["claims"][0]
    ctx = {k: generated_data[k] for k in plugin.context_keys if k in generated_data}
    rules = plugin.rules_fn(claim, ctx)
    breakdown = plugin.score_fn(claim, ctx, rules)
    valid_tiers = set(plugin.config.risk_tiers.keys())
    assert breakdown.tier in valid_tiers, f"tier {breakdown.tier!r} not in {valid_tiers}"


# ── 5. build_queue_fn returns Cases with no phantom fields ───────────────────

@pytest.fixture(scope="module")
def case_queue(plugin, generated_data):
    ctx = {k: generated_data[k] for k in plugin.context_keys if k in generated_data}
    claims = generated_data["claims"]
    claim_rules = {c.claim_id: plugin.rules_fn(c, ctx) for c in claims}
    claim_scores = {c.claim_id: plugin.score_fn(c, ctx, claim_rules[c.claim_id]) for c in claims}
    return plugin.build_queue_fn(claims, claim_scores, claim_rules, generated_data)


def test_queue_nonempty(plugin, case_queue):
    assert len(case_queue) > 0


def test_queue_cases_have_neutral_fields(plugin, case_queue):
    case = case_queue[0]
    assert hasattr(case, "case_id"), "Case missing case_id"
    assert hasattr(case, "subject_name"), "Case missing subject_name"
    assert hasattr(case, "risk_score"), "Case missing risk_score"
    assert hasattr(case, "asset_description"), "Case missing asset_description"
    assert hasattr(case, "counterparty_name"), "Case missing counterparty_name"


def test_queue_cases_no_phantom_fields(plugin, case_queue):
    for case in case_queue[:5]:
        for phantom in PHANTOM_FIELDS:
            assert not hasattr(case, phantom), \
                f"Case has phantom field '{phantom}' — domain leak in plugin '{plugin.name}'"
