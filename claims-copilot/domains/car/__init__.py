"""Car Insurance domain plugin.

This is the single assembly point for the car domain.  All core files will
read PLUGIN after WS5 rewires their imports; until then this module is only
loaded when explicitly imported (e.g. from the registry or tests).
"""

from core.contracts import DomainPlugin, DomainConfig
from core.registry import register_plugin

# ── Domain config ─────────────────────────────────────────────────────────────

from domain_config import CAR_INSURANCE as _CAR_CFG

# ── Data generation ───────────────────────────────────────────────────────────

from data.generate_car import generate_car_data

# ── Rules, scoring, checklist ─────────────────────────────────────────────────

from intelligence.rules_engine_car import run_car_rules_engine
from intelligence.risk_scoring_car import score_car_claim
import intelligence.checklist_car as _checklist_mod

# ── Case queue ────────────────────────────────────────────────────────────────

from case_queue_car import build_car_case_queue

# ── Agent prompts ─────────────────────────────────────────────────────────────

from agents.prompts_car import CAR_COPILOT_PROMPT
from agents.prompts_investigation_car import (
    ORCHESTRATOR_PROMPT,
    INVESTIGATION_PROMPT,
    DOSSIER_PROMPT,
)

# ── Agent tools ───────────────────────────────────────────────────────────────

from agents.tools_car import ALL_CAR_TOOLS, set_context as _set_car_ctx
from agents.tools_investigation_car import INVESTIGATION_TOOLS, set_context as _set_inv_ctx
from agents.tools_dossier_car import DOSSIER_TOOLS, set_context as _set_dos_ctx

# ── Vision prompt ─────────────────────────────────────────────────────────────

from intelligence.document_vision import _CAR_VISION_PROMPT

# ── Checklist descriptions (derived from CHECKLIST, never hardcoded) ──────────

from intelligence.checklist_car import CHECKLIST, CHECKLIST_STEPS

_CHECKLIST_DESCRIPTIONS = {
    i + 1: f"Step {i + 1}: {step.name}"
    for i, step in enumerate(CHECKLIST)
}

# Override with the richer descriptions that api.py currently hard-codes.
# Keeping them here makes them part of the plugin, not scattered in api.py.
_CHECKLIST_DESCRIPTIONS.update({
    1: "Validating required fields and claim completeness",
    2: "Verifying repair estimate and damage evidence",
    3: "Confirming incident within the policy coverage period",
    4: "AI document analysis, fraud scoring and rule-based screening",
    5: "Checking repair-shop watchlist and valuation",
    6: "Verifying coverage type and policy limits",
    7: "Compiling final determination for examiner review",
})


# ── Entity wiring ─────────────────────────────────────────────────────────────

def _build_checklist_ctx(data_ctx, claim_id: str) -> dict:
    """Build the context dict that checklist_car functions expect."""
    from intelligence.document_vision import run_vision_document_checks, find_claim_images
    live_doc_results = dict(data_ctx.claim_doc_results)
    images = find_claim_images(claim_id)
    has_images = len(images) > 0
    if images:
        try:
            vision_results = run_vision_document_checks(claim_id)
            if vision_results:
                live_doc_results[claim_id] = vision_results
        except Exception as e:
            print(f"  Vision analysis failed for {claim_id}: {e} — using cached metadata")
    return {
        "claims": data_ctx.claims,
        "insureds": data_ctx.entities.get("insureds", []),
        "vehicles": data_ctx.entities.get("vehicles", []),
        "repair_shops": data_ctx.entities.get("repair_shops", []),
        "policies": data_ctx.entities.get("policies", []),
        "estimates": data_ctx.entities.get("estimates", []),
        "police_reports": data_ctx.entities.get("police_reports", []),
        "workflow_tasks": data_ctx.entities.get("workflow_tasks", []),
        "claim_rules": data_ctx.claim_rules,
        "claim_risk_scores": data_ctx.claim_risk_scores,
        "claim_doc_results": live_doc_results,
        "has_claim_images": has_images,
    }


def _dossier_context_fn(data_ctx, claim_id: str) -> dict:
    """Build the context dict for the dossier builder in api.py."""
    claim = data_ctx.get_claim(claim_id)
    subject_id = getattr(claim, "insured_id", "") if claim else ""
    return {
        "claim": claim,
        "subject_id": subject_id,
        "insured": data_ctx.get_insured(subject_id) if subject_id else None,
        "vehicle": data_ctx.get_vehicle(claim.vehicle_id)
            if claim and getattr(claim, "vehicle_id", None) else None,
        "shop": data_ctx.get_shop(claim.shop_id)
            if claim and getattr(claim, "shop_id", None) else None,
        "policy": data_ctx.get_policy(claim.policy_id) if claim else None,
        "risk": data_ctx.claim_risk_scores.get(claim_id),
        "rules": data_ctx.claim_rules.get(claim_id, []),
        "doc_results": data_ctx.claim_doc_results.get(claim_id, []),
        "tasks": data_ctx.get_claim_tasks(claim_id),
        "all_claims": data_ctx.claims,
    }


# ── PLUGIN assembly ───────────────────────────────────────────────────────────

PLUGIN = DomainPlugin(
    name="car_insurance",
    config=_CAR_CFG,

    generate_fn=generate_car_data,
    rules_fn=run_car_rules_engine,
    score_fn=score_car_claim,
    build_queue_fn=build_car_case_queue,
    checklist_module=_checklist_mod,

    copilot_prompt=CAR_COPILOT_PROMPT,
    copilot_tools=ALL_CAR_TOOLS,

    investigation_prompts={
        "ORCHESTRATOR": ORCHESTRATOR_PROMPT,
        "INVESTIGATION": INVESTIGATION_PROMPT,
        "DOSSIER": DOSSIER_PROMPT,
    },
    investigation_tools=INVESTIGATION_TOOLS,
    dossier_tools=DOSSIER_TOOLS,

    vision_prompt=_CAR_VISION_PROMPT,
    checklist_descriptions=_CHECKLIST_DESCRIPTIONS,

    context_keys=[
        "claims", "insureds", "vehicles", "repair_shops",
        "policies", "estimates", "police_reports", "workflow_tasks", "documents",
    ],
    build_checklist_ctx=_build_checklist_ctx,
    dossier_context_fn=_dossier_context_fn,
    set_tool_context_fns=[_set_car_ctx, _set_inv_ctx, _set_dos_ctx],

    entity_types=_CAR_CFG.entity_types,
)

# Auto-register when this module is imported.
register_plugin(PLUGIN)
