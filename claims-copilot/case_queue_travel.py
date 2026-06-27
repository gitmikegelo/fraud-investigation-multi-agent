"""Builds case queue from travel insurance claims + risk scores."""

from typing import List, Dict
from cases import Case, CaseType, ClaimType, CasePriority, CaseStatus


TRAVEL_CLAIM_TYPE_MAP = {
    "trip_cancellation": ClaimType.TRIP_CANCELLATION,
    "trip_interruption": ClaimType.TRIP_INTERRUPTION,
    "medical_emergency": ClaimType.MEDICAL_EMERGENCY,
    "baggage_loss": ClaimType.BAGGAGE_LOSS,
    "travel_delay": ClaimType.TRAVEL_DELAY,
}


def build_travel_case_queue(
    claims: List,
    claim_risk_scores: Dict,
    claim_rules: Dict,
    data: Dict,
) -> List[Case]:
    """Build the case queue from travel insurance claims."""
    cases = []
    traveler_map = {t.traveler_id: t for t in data.get("travelers", [])}
    destination_map = {d.destination_id: d for d in data.get("destinations", [])}
    provider_map = {p.provider_id: p for p in data.get("providers", [])}
    policy_map = {p.policy_id: p for p in data.get("policies", [])}

    for claim in claims:
        risk = claim_risk_scores.get(claim.claim_id)
        rules = claim_rules.get(claim.claim_id, [])
        score = risk.total_score if risk else 0.0
        tier = risk.tier if risk else "LOW"

        # Priority from tier
        if tier == "HIGH":
            priority = CasePriority.HIGH
        elif tier == "MEDIUM":
            priority = CasePriority.MEDIUM
        else:
            priority = CasePriority.LOW

        # Flag reason from top rule or risk
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

        # Traveler / destination info
        traveler = traveler_map.get(claim.traveler_id)
        traveler_name = traveler.full_name if traveler else claim.traveler_id

        dest = destination_map.get(claim.destination_id)
        dest_name = f"{dest.city}, {dest.country}" if dest else ""

        provider = provider_map.get(claim.provider_id) if claim.provider_id else None
        provider_name = provider.name if provider else ""

        policy = policy_map.get(claim.policy_id)
        coverage_start = policy.trip_start_date if policy else None
        coverage_end = policy.trip_end_date if policy else None

        # Workflow tasks for this claim
        claim_tasks = [t for t in data.get("workflow_tasks", []) if t.claim_id == claim.claim_id]
        task_summaries = []
        for t in claim_tasks:
            task_summaries.append({
                "task_id": t.task_id,
                "task_type": t.task_type,
                "status": t.status,
                "days_waiting": t.days_waiting,
                "due_date": t.due_date,
            })

        # Rules triggered summaries
        rule_summaries = []
        for r in triggered:
            rule_summaries.append({
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "severity": r.severity,
                "explanation": r.explanation,
            })

        cases.append(Case(
            case_id=claim.claim_id,
            case_type=CaseType.TRAVEL_GUARD,
            claim_type=TRAVEL_CLAIM_TYPE_MAP.get(claim.claim_type, ClaimType.TRIP_CANCELLATION),
            subject_id=claim.traveler_id,
            subject_name=traveler_name,
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
                "destination": dest_name,
                "claim_type": claim.claim_type,
            },
            rules_triggered=rule_summaries,
            workflow_tasks=task_summaries,
            employer_name=dest_name,  # Repurpose field for destination display
            member_id=claim.traveler_id,
            provider_name=provider_name,
            claim_amount=claim.claim_amount,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
        ))

    # Sort: HIGH first, then risk_score descending
    order = {CasePriority.HIGH: 0, CasePriority.MEDIUM: 1, CasePriority.LOW: 2}
    cases.sort(key=lambda c: (order[c.priority], -c.risk_score))

    return cases
