"""Car insurance rules: R-001 to R-006 expressed as RuleSpec data.

CAR_RULE_SPECS is the single source of truth. run_car_rules_engine() is a
backwards-compatible shim used by main.py / tests until WS4 wires the plugin.
"""

from typing import Dict, List
from datetime import datetime

from core.engine import RuleSpec, RuleResult, run_rules


# ── Context accessors (shared by predicates and explain fns) ──────────────────

def _get_policy(context: Dict, policy_id: str):
    return next((p for p in context.get("policies", []) if p.policy_id == policy_id), None)


def _get_vehicle(context: Dict, vehicle_id: str):
    return next((v for v in context.get("vehicles", []) if v.vehicle_id == vehicle_id), None)


def _get_shop(context: Dict, shop_id: str):
    return next((s for s in context.get("repair_shops", []) if s.shop_id == shop_id), None)


def _get_estimate(context: Dict, claim):
    by_id = next((e for e in context.get("estimates", []) if e.estimate_id == claim.estimate_id), None)
    if by_id:
        return by_id
    return next((e for e in context.get("estimates", []) if e.claim_id == claim.claim_id), None)


def _get_insured(context: Dict, insured_id: str):
    return next((i for i in context.get("insureds", []) if i.insured_id == insured_id), None)


def _get_insured_claims(context: Dict, insured_id: str) -> List:
    return [c for c in context.get("claims", []) if c.insured_id == insured_id]


# ── R-001 ─────────────────────────────────────────────────────────────────────

def _r001_pred(claim, ctx) -> bool:
    policy = _get_policy(ctx, claim.policy_id)
    if not policy:
        return False
    try:
        return datetime.strptime(policy.effective_date, "%Y-%m-%d") > \
               datetime.strptime(claim.date_of_incident, "%Y-%m-%d")
    except (ValueError, TypeError):
        return False


def _r001_explain(claim, ctx, triggered: bool) -> str:
    policy = _get_policy(ctx, claim.policy_id)
    if not policy:
        return "Policy not found"
    if triggered:
        return f"Policy effective {policy.effective_date} AFTER incident {claim.date_of_incident}"
    return "Policy effective before incident"


def _r001_details(claim, ctx) -> Dict:
    policy = _get_policy(ctx, claim.policy_id)
    return {
        "effective_date": policy.effective_date if policy else None,
        "incident_date": claim.date_of_incident,
    }


# ── R-002 ─────────────────────────────────────────────────────────────────────

def _r002_pred(claim, ctx) -> bool:
    if claim.claim_type not in ("collision", "comprehensive", "liability"):
        return False
    return _get_estimate(ctx, claim) is None


def _r002_explain(claim, ctx, triggered: bool) -> str:
    if claim.claim_type not in ("collision", "comprehensive", "liability"):
        return "Not applicable to this claim type"
    if triggered:
        return "No repair estimate on file for a damage claim"
    estimate = _get_estimate(ctx, claim)
    return f"Estimate ${estimate.amount:,.2f} on file"


def _r002_details(claim, ctx) -> Dict:
    return {"has_estimate": _get_estimate(ctx, claim) is not None}


# ── R-003 ─────────────────────────────────────────────────────────────────────

def _r003_pred(claim, ctx) -> bool:
    return bool(claim.is_resubmission)


def _r003_explain(claim, ctx, triggered: bool) -> str:
    if triggered:
        return f"Resubmission of {claim.original_claim_id}"
    return "No duplicate detected"


def _r003_details(claim, ctx) -> Dict:
    return {"is_resubmission": claim.is_resubmission, "original": claim.original_claim_id}


# ── R-004 ─────────────────────────────────────────────────────────────────────

def _r004_pred(claim, ctx) -> bool:
    if not claim.shop_id:
        return False
    shop = _get_shop(ctx, claim.shop_id)
    return bool(shop and shop.on_watchlist)


def _r004_explain(claim, ctx, triggered: bool) -> str:
    if not claim.shop_id:
        return "No repair shop on claim"
    shop = _get_shop(ctx, claim.shop_id)
    if not shop:
        return "Shop not found"
    if triggered:
        return f"Repair shop '{shop.name}' is on the fraud watchlist"
    return f"Shop '{shop.name}' — not on watchlist"


def _r004_details(claim, ctx) -> Dict:
    shop = _get_shop(ctx, claim.shop_id) if claim.shop_id else None
    return {
        "shop_name": shop.name if shop else None,
        "on_watchlist": shop.on_watchlist if shop else False,
        "verified": shop.verified if shop else None,
    }


# ── R-005 ─────────────────────────────────────────────────────────────────────

# Threshold is now a module-level constant — tunable without touching predicate code.
R005_ACV_RATIO_THRESHOLD = 1.1


def _r005_pred(claim, ctx) -> bool:
    vehicle = _get_vehicle(ctx, claim.vehicle_id)
    if not vehicle or not vehicle.acv:
        return False
    ratio = claim.claim_amount / vehicle.acv if vehicle.acv > 0 else 0
    return ratio > R005_ACV_RATIO_THRESHOLD


def _r005_explain(claim, ctx, triggered: bool) -> str:
    vehicle = _get_vehicle(ctx, claim.vehicle_id)
    if not vehicle or not vehicle.acv:
        return "No vehicle ACV on file"
    ratio = claim.claim_amount / vehicle.acv if vehicle.acv > 0 else 0
    if triggered:
        return f"Claim ${claim.claim_amount:,.2f} is {ratio:.1f}x the vehicle ACV ${vehicle.acv:,.2f}"
    return f"Amount ${claim.claim_amount:,.2f} within vehicle value (ACV ${vehicle.acv:,.2f})"


def _r005_details(claim, ctx) -> Dict:
    vehicle = _get_vehicle(ctx, claim.vehicle_id)
    acv = vehicle.acv if vehicle else 0
    ratio = claim.claim_amount / acv if acv > 0 else 0
    return {"claim_amount": claim.claim_amount, "vehicle_acv": acv, "ratio": round(ratio, 2)}


# ── R-006 ─────────────────────────────────────────────────────────────────────

R006_SERIAL_CLAIM_THRESHOLD = 3


def _r006_pred(claim, ctx) -> bool:
    insured = _get_insured(ctx, claim.insured_id)
    history_count = insured.claim_history_count if insured else 0
    total = max(len(_get_insured_claims(ctx, claim.insured_id)), history_count)
    return total >= R006_SERIAL_CLAIM_THRESHOLD


def _r006_explain(claim, ctx, triggered: bool) -> str:
    insured = _get_insured(ctx, claim.insured_id)
    history_count = insured.claim_history_count if insured else 0
    total = max(len(_get_insured_claims(ctx, claim.insured_id)), history_count)
    if triggered:
        return f"Insured has {total} claims (threshold: {R006_SERIAL_CLAIM_THRESHOLD})"
    return f"Insured has {total} claims (normal)"


def _r006_details(claim, ctx) -> Dict:
    insured = _get_insured(ctx, claim.insured_id)
    history_count = insured.claim_history_count if insured else 0
    total = max(len(_get_insured_claims(ctx, claim.insured_id)), history_count)
    return {"claim_count": total, "threshold": R006_SERIAL_CLAIM_THRESHOLD}


# ── Rule spec list (the single source of truth for car rules) ─────────────────

CAR_RULE_SPECS: List[RuleSpec] = [
    RuleSpec("R-001", "Policy Effective After Incident", "BLOCK",
             _r001_pred, _r001_explain, _r001_details),
    RuleSpec("R-002", "No Repair Estimate",             "BLOCK",
             _r002_pred, _r002_explain, _r002_details),
    RuleSpec("R-003", "Duplicate/Resubmission",         "BLOCK",
             _r003_pred, _r003_explain, _r003_details),
    RuleSpec("R-004", "Repair Shop Watchlist",          "BLOCK",
             _r004_pred, _r004_explain, _r004_details),
    RuleSpec("R-005", "Amount Exceeds Vehicle Value",   "FLAG",
             _r005_pred, _r005_explain, _r005_details),
    RuleSpec("R-006", "Serial Claimer",                 "FLAG",
             _r006_pred, _r006_explain, _r006_details),
]


# ── Backwards-compatible shim ─────────────────────────────────────────────────

def run_car_rules_engine(claim, context: Dict) -> List[RuleResult]:
    """Run all car rules against a single claim. Shim over core.engine.run_rules."""
    return run_rules(claim, context, CAR_RULE_SPECS)
