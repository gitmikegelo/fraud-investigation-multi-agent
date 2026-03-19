"""Builds case queue from supplemental health claims + risk scores."""

from typing import List, Dict
from cases import Case, CaseType, ClaimType, CasePriority, CaseStatus


CLAIM_TYPE_MAP = {
    "wellness": ClaimType.WELLNESS,
    "accident": ClaimType.ACCIDENT,
    "hospital_indemnity": ClaimType.HOSPITAL_INDEMNITY,
    "critical_illness": ClaimType.CRITICAL_ILLNESS,
}


def build_case_queue(
    claims: List,
    claim_risk_scores: Dict,
    claim_rules: Dict,
    data: Dict,
) -> List[Case]:
    """Build the case queue from supplemental health claims."""
    cases = []
    member_map = {m.member_id: m for m in data.get("members", [])}
    employer_map = {e.employer_id: e for e in data.get("employers", [])}
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

        # Member / employer info
        member = member_map.get(claim.member_id)
        member_name = member.full_name if member else claim.member_id
        employer_id = member.employer_id if member else ""
        employer = employer_map.get(employer_id)
        employer_name = employer.name if employer else ""

        provider = provider_map.get(claim.provider_id)
        provider_name = provider.name if provider else ""

        policy = policy_map.get(claim.policy_id)
        coverage_start = policy.effective_date if policy else None
        coverage_end = policy.termination_date if policy else None

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
            case_type=CaseType.SUPPLEMENTAL_HEALTH,
            claim_type=CLAIM_TYPE_MAP.get(claim.claim_type, ClaimType.WELLNESS),
            subject_id=claim.member_id,
            subject_name=member_name,
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
            },
            rules_triggered=rule_summaries,
            workflow_tasks=task_summaries,
            employer_name=employer_name,
            member_id=claim.member_id,
            provider_name=provider_name,
            claim_amount=claim.claim_amount,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
        ))

    # Sort: HIGH first, then risk_score descending
    order = {CasePriority.HIGH: 0, CasePriority.MEDIUM: 1, CasePriority.LOW: 2}
    cases.sort(key=lambda c: (order[c.priority], -c.risk_score))
    return cases
