"""Deterministic rules (R-001 to R-006) for Car Insurance claims."""

from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime


@dataclass
class RuleResult:
    rule_id: str
    rule_name: str
    severity: str  # BLOCK, FLAG, INFO
    triggered: bool
    explanation: str
    details: Dict = field(default_factory=dict)


# ── Context accessors ─────────────────────────────────────────────────────────

def _get_insured(context: Dict, insured_id: str):
    return next((i for i in context.get("insureds", []) if i.insured_id == insured_id), None)


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


def _get_insured_claims(context: Dict, insured_id: str) -> List:
    return [c for c in context.get("claims", []) if c.insured_id == insured_id]


# ── Rule Definitions ──────────────────────────────────────────────────────────

def r001_policy_after_incident(claim, context) -> RuleResult:
    """R-001: Policy effective date is AFTER the incident date -> BLOCK"""
    policy = _get_policy(context, claim.policy_id)
    if not policy:
        return RuleResult("R-001", "Policy Effective After Incident", "BLOCK", False, "Policy not found")
    try:
        effective = datetime.strptime(policy.effective_date, "%Y-%m-%d")
        incident = datetime.strptime(claim.date_of_incident, "%Y-%m-%d")
        triggered = effective > incident
    except (ValueError, TypeError):
        triggered = False
    return RuleResult(
        rule_id="R-001", rule_name="Policy Effective After Incident",
        severity="BLOCK", triggered=triggered,
        explanation=(f"Policy effective {policy.effective_date} AFTER incident {claim.date_of_incident}"
                     if triggered else "Policy effective before incident"),
        details={"effective_date": policy.effective_date, "incident_date": claim.date_of_incident},
    )


def r002_no_repair_estimate(claim, context) -> RuleResult:
    """R-002: Collision/comprehensive/liability claim with no repair estimate on file -> BLOCK"""
    if claim.claim_type not in ("collision", "comprehensive", "liability"):
        return RuleResult("R-002", "No Repair Estimate", "BLOCK", False, "Not applicable to this claim type")
    estimate = _get_estimate(context, claim)
    triggered = estimate is None
    return RuleResult(
        rule_id="R-002", rule_name="No Repair Estimate",
        severity="BLOCK", triggered=triggered,
        explanation=("No repair estimate on file for a damage claim" if triggered
                     else f"Estimate ${estimate.amount:,.2f} on file"),
        details={"has_estimate": not triggered},
    )


def r003_duplicate_claim(claim, context) -> RuleResult:
    """R-003: Duplicate/resubmission of an existing claim -> BLOCK"""
    triggered = claim.is_resubmission
    return RuleResult(
        rule_id="R-003", rule_name="Duplicate/Resubmission",
        severity="BLOCK", triggered=triggered,
        explanation=(f"Resubmission of {claim.original_claim_id}" if triggered else "No duplicate detected"),
        details={"is_resubmission": triggered, "original": claim.original_claim_id},
    )


def r004_shop_on_watchlist(claim, context) -> RuleResult:
    """R-004: Repair shop on the fraud watchlist (or unverified) -> BLOCK"""
    if not claim.shop_id:
        return RuleResult("R-004", "Repair Shop Watchlist", "BLOCK", False, "No repair shop on claim")
    shop = _get_shop(context, claim.shop_id)
    if not shop:
        return RuleResult("R-004", "Repair Shop Watchlist", "BLOCK", False, "Shop not found")
    triggered = bool(shop.on_watchlist)
    return RuleResult(
        rule_id="R-004", rule_name="Repair Shop Watchlist",
        severity="BLOCK", triggered=triggered,
        explanation=(f"Repair shop '{shop.name}' is on the fraud watchlist" if triggered
                     else f"Shop '{shop.name}' — not on watchlist"),
        details={"shop_name": shop.name, "on_watchlist": shop.on_watchlist, "verified": shop.verified},
    )


def r005_amount_exceeds_acv(claim, context) -> RuleResult:
    """R-005: Claim/estimate amount far exceeds the vehicle ACV (total-loss padding) -> FLAG"""
    vehicle = _get_vehicle(context, claim.vehicle_id)
    if not vehicle or not vehicle.acv:
        return RuleResult("R-005", "Amount Exceeds Vehicle Value", "FLAG", False, "No vehicle ACV on file")
    ratio = claim.claim_amount / vehicle.acv if vehicle.acv > 0 else 0
    triggered = ratio > 1.1
    return RuleResult(
        rule_id="R-005", rule_name="Amount Exceeds Vehicle Value",
        severity="FLAG", triggered=triggered,
        explanation=(f"Claim ${claim.claim_amount:,.2f} is {ratio:.1f}x the vehicle ACV ${vehicle.acv:,.2f}"
                     if triggered else f"Amount ${claim.claim_amount:,.2f} within vehicle value (ACV ${vehicle.acv:,.2f})"),
        details={"claim_amount": claim.claim_amount, "vehicle_acv": vehicle.acv, "ratio": round(ratio, 2)},
    )


def r006_serial_claimer(claim, context) -> RuleResult:
    """R-006: Insured has 3+ claims in the tracking period -> FLAG"""
    insured_claims = _get_insured_claims(context, claim.insured_id)
    insured = _get_insured(context, claim.insured_id)
    history_count = insured.claim_history_count if insured else 0
    total = max(len(insured_claims), history_count)
    triggered = total >= 3
    return RuleResult(
        rule_id="R-006", rule_name="Serial Claimer",
        severity="FLAG", triggered=triggered,
        explanation=(f"Insured has {total} claims (threshold: 3)" if triggered
                     else f"Insured has {total} claims (normal)"),
        details={"claim_count": total, "threshold": 3},
    )


# ── Rules Engine Runner ───────────────────────────────────────────────────────

ALL_CAR_RULES = [
    r001_policy_after_incident,
    r002_no_repair_estimate,
    r003_duplicate_claim,
    r004_shop_on_watchlist,
    r005_amount_exceeds_acv,
    r006_serial_claimer,
]


def run_car_rules_engine(claim, context: Dict) -> List[RuleResult]:
    """Run all car insurance rules against a single claim."""
    results = []
    for rule_fn in ALL_CAR_RULES:
        try:
            results.append(rule_fn(claim, context))
        except Exception as e:
            results.append(RuleResult(
                rule_id="ERR", rule_name=rule_fn.__name__,
                severity="INFO", triggered=False,
                explanation=f"Rule error: {str(e)[:100]}",
            ))
    return results
