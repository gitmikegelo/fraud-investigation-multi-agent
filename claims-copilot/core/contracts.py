"""Core contracts: DomainConfig, DomainPlugin, and shared result types.

All domain-neutral. No domain literals live here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# ── Domain configuration (data only) ─────────────────────────────────────────

@dataclass
class DomainConfig:
    name: str
    display_name: str
    claim_types: List[str]
    claim_id_prefixes: Dict[str, str]
    claim_sources: List[str]
    claim_source_weights: Dict[str, float]
    risk_tiers: Dict[str, Tuple[int, int]]   # tier_name -> (min_score, max_score)
    workflow_task_types: List[str]
    checklist_steps: List[str]
    system_references: Dict[str, str]
    rules_prefix: str
    doc_checks_prefix: str
    entity_types: List[str]


# ── DomainPlugin contract ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class DomainPlugin:
    """Everything a domain must supply.  Core files read this; they never branch on domain name."""

    name: str           # matches DOMAIN_MODE env var, e.g. "car_insurance"
    config: DomainConfig

    # ── data + intelligence ───────────────────────────────────────────────────
    generate_fn: Callable[[], Dict]
    # generate_fn() -> dict with context_keys as top-level keys

    rules_fn: Callable
    # rules_fn(claim, context_dict) -> List[RuleResult]

    score_fn: Callable
    # score_fn(claim, context_dict, rules_results) -> RiskBreakdown

    build_queue_fn: Callable
    # build_queue_fn(claims, risk_scores, rules, data_dict) -> List[Case]

    checklist_module: Any
    # must expose: run_full_checklist, run_checklist_step, CHECKLIST_STEPS

    # ── presentation / agent ─────────────────────────────────────────────────
    copilot_prompt: str
    copilot_tools: List

    investigation_prompts: Dict[str, str]   # keys: ORCHESTRATOR, INVESTIGATION, DOSSIER
    investigation_tools: List
    dossier_tools: List

    vision_prompt: str
    checklist_descriptions: Dict[int, str]

    # ── entity wiring (what api.py currently hard-codes) ─────────────────────
    context_keys: List[str]
    # ordered list of keys generate_fn returns, e.g. ["insureds", "vehicles", ...]

    build_checklist_ctx: Callable
    # build_checklist_ctx(data_ctx, claim_id) -> dict  (fed to checklist module)

    dossier_context_fn: Callable
    # dossier_context_fn(data_ctx, claim_id) -> dict  (fed to dossier builder)

    set_tool_context_fns: List[Callable]
    # called at startup: [tools_car.set_context, tools_investigation_car.set_context, ...]

    entity_types: List[str] = field(default_factory=list)
    # mirrors config.entity_types; kept here for convenience in conformance tests
