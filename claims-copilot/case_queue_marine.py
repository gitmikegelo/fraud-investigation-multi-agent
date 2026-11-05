"""Builds case queue from marine cargo claims + risk scores."""

from typing import List, Dict
from cases import Case, CaseType, ClaimType, CasePriority


MARINE_CLAIM_TYPE_MAP = {
    "breakage": ClaimType.BREAKAGE,
    "wet_damage": ClaimType.WET_DAMAGE,
    "contamination": ClaimType.CONTAMINATION,
    "shortage": ClaimType.SHORTAGE,
    "theft_pilferage": ClaimType.THEFT_PILFERAGE,
}


def build_marine_case_queue(
    claims: List,
    claim_risk_scores: Dict,
    claim_rules: Dict,
    data: Dict,
) -> List[Case]:
    """Build the case queue from marine cargo claims."""
    cases = []
    consignee_map = {p.party_id: p for p in data.get("consignees", [])}
    shipment_map = {s.shipment_id: s for s in data.get("shipments", [])}
    surveyor_map = {s.surveyor_id: s for s in data.get("surveyors", [])}
    policy_map = {p.policy_id: p for p in data.get("policies", [])}

    for claim in claims:
        risk = claim_risk_scores.get(claim.claim_id)
        rules = claim_rules.get(claim.claim_id, [])
        score = risk.total_score if risk else 0.0
        tier = risk.tier if risk else "LOW"

        if tier == "HIGH":
            priority = CasePriority.HIGH
        elif tier == "MEDIUM":
            priority = CasePriority.MEDIUM
        else:
            priority = CasePriority.LOW

        triggered = [r for r in rules if r.triggered]
        block_rules = [r for r in triggered if r.severity == "BLOCK"]
        flag_rules = [r for r in triggered if r.severity == "FLAG"]

        if block_rules:
            flag_reason = f"BLOCK: {block_rules[0].rule_name} — {block_rules[0].explanation[:80]}"
        elif flag_rules:
            flag_reason = f"FLAG: {flag_rules[0].rule_name} — {flag_rules[0].explanation[:80]}"
        elif risk and risk.top_factors:
            flag_reason = risk.top_factors[0][:80]
        else:
            flag_reason = "Standard review"

        consignee = consignee_map.get(claim.consignee_id)
        consignee_name = consignee.name if consignee else claim.consignee_id

        shipment = shipment_map.get(claim.shipment_id)
        shipment_desc = shipment.description if shipment else ""

        surveyor = surveyor_map.get(claim.surveyor_id) if claim.surveyor_id else None
        surveyor_name = surveyor.name if surveyor else ""

        policy = policy_map.get(claim.policy_id)
        coverage_start = policy.effective_date if policy else None
        coverage_end = policy.expiration_date if policy else None

        claim_tasks = [t for t in data.get("workflow_tasks", []) if t.claim_id == claim.claim_id]
        task_summaries = [{
            "task_id": t.task_id,
            "task_type": t.task_type,
            "status": t.status,
            "days_waiting": t.days_waiting,
            "due_date": t.due_date,
        } for t in claim_tasks]

        rule_summaries = [{
            "rule_id": r.rule_id,
            "rule_name": r.rule_name,
            "severity": r.severity,
            "explanation": r.explanation,
        } for r in triggered]

        cases.append(Case(
            case_id=claim.claim_id,
            case_type=CaseType.MARINE_CARGO,
            claim_type=MARINE_CLAIM_TYPE_MAP.get(claim.claim_type, ClaimType.BREAKAGE),
            subject_id=claim.consignee_id,
            subject_name=consignee_name,
            priority=priority,
            flag_reason=flag_reason,
            risk_score=round(score, 1),
            claim_source=claim.claim_source,
            date_filed=claim.date_filed if hasattr(claim, 'date_filed') else None,
            key_metrics={
                "risk_score": round(score, 1),
                "risk_tier": tier,
                "claim_amount": claim.claim_amount,
                "rules_triggered": len(triggered),
                "block_rules": len(block_rules),
                "flag_rules": len(flag_rules),
                "shipment": shipment_desc,
                "bl_number": shipment.bl_number if shipment else "",
                "claim_type": claim.claim_type,
            },
            rules_triggered=rule_summaries,
            workflow_tasks=task_summaries,
            employer_name=shipment_desc,  # Repurposed field: shipment summary
            member_id=claim.consignee_id,
            provider_name=surveyor_name,  # Repurposed field: surveyor
            claim_amount=claim.claim_amount,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
        ))

    order = {CasePriority.HIGH: 0, CasePriority.MEDIUM: 1, CasePriority.LOW: 2}
    cases.sort(key=lambda c: (order[c.priority], -c.risk_score))
    return cases
