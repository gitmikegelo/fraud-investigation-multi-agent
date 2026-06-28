"""Builds case queue from car insurance claims + risk scores."""

from typing import List, Dict
from cases import Case, CaseType, ClaimType, CasePriority


CAR_CLAIM_TYPE_MAP = {
    "collision": ClaimType.COLLISION,
    "comprehensive": ClaimType.COMPREHENSIVE,
    "theft": ClaimType.THEFT,
    "liability": ClaimType.LIABILITY,
    "medical_payments": ClaimType.MEDICAL_PAYMENTS,
}


def build_car_case_queue(
    claims: List,
    claim_risk_scores: Dict,
    claim_rules: Dict,
    data: Dict,
) -> List[Case]:
    """Build the case queue from car insurance claims."""
    cases = []
    insured_map = {i.insured_id: i for i in data.get("insureds", [])}
    vehicle_map = {v.vehicle_id: v for v in data.get("vehicles", [])}
    shop_map = {s.shop_id: s for s in data.get("repair_shops", [])}
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

        insured = insured_map.get(claim.insured_id)
        insured_name = insured.full_name if insured else claim.insured_id

        vehicle = vehicle_map.get(claim.vehicle_id)
        vehicle_desc = f"{vehicle.year} {vehicle.make} {vehicle.model}" if vehicle else ""

        shop = shop_map.get(claim.shop_id) if claim.shop_id else None
        shop_name = shop.name if shop else ""

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
            case_type=CaseType.CAR_INSURANCE,
            claim_type=CAR_CLAIM_TYPE_MAP.get(claim.claim_type, ClaimType.COLLISION),
            subject_id=claim.insured_id,
            subject_name=insured_name,
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
                "vehicle": vehicle_desc,
                "claim_type": claim.claim_type,
            },
            rules_triggered=rule_summaries,
            workflow_tasks=task_summaries,
            employer_name=vehicle_desc,   # Repurpose field for vehicle display
            member_id=claim.insured_id,
            provider_name=shop_name,
            claim_amount=claim.claim_amount,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
        ))

    order = {CasePriority.HIGH: 0, CasePriority.MEDIUM: 1, CasePriority.LOW: 2}
    cases.sort(key=lambda c: (order[c.priority], -c.risk_score))
    return cases
