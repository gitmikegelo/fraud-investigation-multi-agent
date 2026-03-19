"""7-step investigation checklist framework for supplemental health claims."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ChecklistStepResult:
    step_number: int
    step_name: str
    status: str  # pass, fail, needs_review, not_run, error
    auto_passed: bool
    findings: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


CHECKLIST_STEPS = [
    (1, "Initial Review"),
    (2, "Eligibility Verification"),
    (3, "Fraud Screening"),
    (4, "Family & Network Check"),
    (5, "Medical Documentation Review"),
    (6, "Policy & Coverage Determination"),
    (7, "Final Determination"),
]


def _get_claim(context, claim_id):
    return next((c for c in context.get("claims", []) if c.claim_id == claim_id), None)


def _get_member(context, member_id):
    return next((m for m in context.get("members", []) if m.member_id == member_id), None)


def _get_policy(context, policy_id):
    return next((p for p in context.get("policies", []) if p.policy_id == policy_id), None)


def _get_claim_tasks(context, claim_id):
    return [t for t in context.get("workflow_tasks", []) if t.claim_id == claim_id]


def _get_claim_rules(context, claim_id):
    return context.get("claim_rules", {}).get(claim_id, [])


def _get_claim_doc_results(context, claim_id):
    return context.get("claim_doc_results", {}).get(claim_id, [])


def _get_claim_risk(context, claim_id):
    return context.get("claim_risk_scores", {}).get(claim_id, None)


def run_checklist_step(step_number: int, claim_id: str, context: Dict) -> ChecklistStepResult:
    """Run a single checklist step for a claim."""
    claim = _get_claim(context, claim_id)
    if not claim:
        return ChecklistStepResult(step_number, CHECKLIST_STEPS[step_number - 1][1],
                                   "error", False, ["Claim not found"])

    step_name = CHECKLIST_STEPS[step_number - 1][1]

    if step_number == 1:
        return _step_initial_review(claim, context)
    elif step_number == 2:
        return _step_eligibility(claim, context)
    elif step_number == 3:
        return _step_fraud_screening(claim, context)
    elif step_number == 4:
        return _step_family_network(claim, context)
    elif step_number == 5:
        return _step_medical_docs(claim, context)
    elif step_number == 6:
        return _step_policy_coverage(claim, context)
    elif step_number == 7:
        return _step_final_determination(claim, context)
    else:
        return ChecklistStepResult(step_number, "Unknown", "error", False, ["Invalid step number"])


def _step_initial_review(claim, context) -> ChecklistStepResult:
    """Step 1: Check claim exists, basic data complete, INITIAL_REVIEW task exists."""
    findings = []
    all_ok = True

    # Basic data completeness
    if not claim.member_id:
        findings.append("MISSING: Member ID")
        all_ok = False
    if not claim.provider_id:
        findings.append("MISSING: Provider ID")
        all_ok = False
    if not claim.policy_id:
        findings.append("MISSING: Policy ID")
        all_ok = False
    if not claim.date_of_service:
        findings.append("MISSING: Date of service")
        all_ok = False
    if claim.claim_amount <= 0:
        findings.append("WARNING: Claim amount is zero or negative")
        all_ok = False

    # Check INITIAL_REVIEW task
    tasks = _get_claim_tasks(context, claim.claim_id)
    has_ir = any(t.task_type == "INITIAL_REVIEW" for t in tasks)
    if not has_ir:
        findings.append("MISSING: No INITIAL_REVIEW task assigned")
        all_ok = False
    else:
        findings.append("INITIAL_REVIEW task assigned")

    if all_ok:
        findings.insert(0, "All required fields present")

    return ChecklistStepResult(1, "Initial Review", "pass" if all_ok else "needs_review",
                               all_ok, findings)


def _step_eligibility(claim, context) -> ChecklistStepResult:
    """Step 2: Policy active, coverage matches claim type."""
    findings = []
    all_ok = True

    policy = _get_policy(context, claim.policy_id)
    if not policy:
        return ChecklistStepResult(2, "Eligibility Verification", "fail", False,
                                   ["Policy not found"])

    if policy.status != "active":
        findings.append(f"FAIL: Policy status is {policy.status}")
        all_ok = False
    else:
        findings.append("Policy is active")

    if policy.plan_type != claim.claim_type:
        findings.append(f"WARNING: Policy type ({policy.plan_type}) doesn't match claim type ({claim.claim_type})")
        all_ok = False
    else:
        findings.append(f"Coverage type matches: {policy.plan_type}")

    member = _get_member(context, claim.member_id)
    if member and member.termination_date:
        findings.append(f"NOTE: Member has termination date: {member.termination_date}")

    return ChecklistStepResult(2, "Eligibility Verification", "pass" if all_ok else "needs_review",
                               all_ok, findings)


def _step_fraud_screening(claim, context) -> ChecklistStepResult:
    """Step 3: Fraud screening — branches on suspicious banner."""
    findings = []
    member = _get_member(context, claim.member_id)
    rules = _get_claim_rules(context, claim.claim_id)
    risk = _get_claim_risk(context, claim.claim_id)

    has_banner = member.suspicious_banner if member else False

    if has_banner:
        findings.append("⚠️ SUSPICIOUS BANNER ACTIVE — Full fraud review required regardless of risk score")
        findings.append("Routing to senior examiner review path")

        # Run all fraud checks even if score is low
        block_rules = [r for r in rules if r.triggered and r.severity == "BLOCK"]
        flag_rules = [r for r in rules if r.triggered and r.severity == "FLAG"]
        if block_rules:
            findings.append(f"BLOCK rules triggered: {', '.join(r.rule_id for r in block_rules)}")
        if flag_rules:
            findings.append(f"FLAG rules triggered: {', '.join(r.rule_id for r in flag_rules)}")

        return ChecklistStepResult(3, "Fraud Screening", "needs_review", False, findings,
                                   {"banner": True, "requires_senior_review": True})
    else:
        # Standard scoring path
        risk_score = risk.total_score if risk else 0
        block_rules = [r for r in rules if r.triggered and r.severity == "BLOCK"]

        if risk_score < 30 and not block_rules:
            findings.append(f"Risk score: {risk_score:.1f} (LOW) — auto-pass")
            findings.append("No BLOCK rules triggered")
            return ChecklistStepResult(3, "Fraud Screening", "pass", True, findings,
                                       {"risk_score": risk_score, "auto_passed": True})
        else:
            if block_rules:
                findings.append(f"BLOCK rules: {', '.join(r.rule_id for r in block_rules)}")
            flag_rules = [r for r in rules if r.triggered and r.severity == "FLAG"]
            if flag_rules:
                findings.append(f"FLAG rules: {', '.join(r.rule_id for r in flag_rules)}")
            findings.append(f"Risk score: {risk_score:.1f} ({risk.tier if risk else 'UNKNOWN'})")

            status = "fail" if block_rules else "needs_review"
            return ChecklistStepResult(3, "Fraud Screening", status, False, findings,
                                       {"risk_score": risk_score})


def _step_family_network(claim, context) -> ChecklistStepResult:
    """Step 4: No dependent anomalies, no network flags, R-015 not triggered."""
    findings = []
    all_ok = True

    rules = _get_claim_rules(context, claim.claim_id)
    r015 = next((r for r in rules if r.rule_id == "R-015"), None)
    r001 = next((r for r in rules if r.rule_id == "R-001"), None)
    r010 = next((r for r in rules if r.rule_id == "R-010"), None)

    if r015 and r015.triggered:
        findings.append(f"FLAG: {r015.explanation}")
        all_ok = False
    else:
        findings.append("Family claim cluster: Normal")

    if r001 and r001.triggered:
        findings.append(f"BLOCK: {r001.explanation}")
        all_ok = False
    else:
        findings.append("Dependent count: Normal")

    if r010 and r010.triggered:
        findings.append(f"FLAG: {r010.explanation}")
        all_ok = False
    else:
        findings.append("Shared address: Normal")

    return ChecklistStepResult(4, "Family & Network Check", "pass" if all_ok else "needs_review",
                               all_ok, findings)


def _step_medical_docs(claim, context) -> ChecklistStepResult:
    """Step 5: All DOC checks pass, medical records received."""
    findings = []
    details = {}
    all_ok = True

    doc_results = _get_claim_doc_results(context, claim.claim_id)
    if not doc_results:
        findings.append("No document analysis results available")
        return ChecklistStepResult(5, "Medical Documentation Review", "needs_review", False, findings)

    # Check if vision was used (details contain 'source': 'vision_ai')
    is_vision = any(
        getattr(d, 'details', {}).get('source') == 'vision_ai' for d in doc_results
    )
    if is_vision:
        details["has_document_image"] = True
        details["image_url"] = f"/api/claims/{claim.claim_id}/document-image"

    failed_docs = [d for d in doc_results if not d.passed]
    critical_docs = [d for d in failed_docs if d.severity == "CRITICAL"]

    if critical_docs:
        for cd in critical_docs:
            findings.append(f"CRITICAL: {cd.check_name} — {cd.explanation}")
        all_ok = False
    elif failed_docs:
        for fd in failed_docs:
            findings.append(f"WARNING: {fd.check_name} — {fd.explanation}")
        all_ok = False
    else:
        findings.append(f"All {len(doc_results)} document checks passed")

    # Check medical record request status
    tasks = _get_claim_tasks(context, claim.claim_id)
    mr_tasks = [t for t in tasks if t.task_type == "MEDICAL_RECORD_REQUEST"]
    for mrt in mr_tasks:
        if mrt.status == "pending":
            findings.append(f"⏳ Medical records pending — waiting {mrt.days_waiting} days")
            all_ok = False
        elif mrt.status == "completed":
            findings.append("Medical records received")

    return ChecklistStepResult(5, "Medical Documentation Review",
                               "pass" if all_ok else "needs_review", all_ok, findings, details)


def _step_policy_coverage(claim, context) -> ChecklistStepResult:
    """Step 6: Coverage matches, no state conflicts."""
    findings = []
    all_ok = True

    policy = _get_policy(context, claim.policy_id)
    if not policy:
        return ChecklistStepResult(6, "Policy & Coverage Determination", "fail", False,
                                   ["Policy not found"])

    # Coverage match
    if policy.plan_type == claim.claim_type:
        findings.append(f"Coverage matches: {policy.plan_type}")
    else:
        findings.append(f"MISMATCH: Policy covers {policy.plan_type}, claim is {claim.claim_type}")
        all_ok = False

    # Amount within coverage
    if claim.claim_amount <= policy.coverage_amount or policy.plan_type == "hospital_indemnity":
        findings.append(f"Amount ${claim.claim_amount:,.2f} within coverage limits")
    else:
        findings.append(f"Amount ${claim.claim_amount:,.2f} may exceed coverage ${policy.coverage_amount:,.2f}")

    return ChecklistStepResult(6, "Policy & Coverage Determination",
                               "pass" if all_ok else "needs_review", all_ok, findings)


def _step_final_determination(claim, context) -> ChecklistStepResult:
    """Step 7: Always manual — approve/deny/escalate."""
    return ChecklistStepResult(
        7, "Final Determination", "needs_review", False,
        ["Awaiting examiner determination: APPROVE / DENY / ESCALATE"],
        {"requires_manual": True},
    )


def run_full_checklist(claim_id: str, context: Dict) -> List[ChecklistStepResult]:
    """Run all 7 checklist steps for a claim."""
    results = []
    for step_num, step_name in CHECKLIST_STEPS:
        result = run_checklist_step(step_num, claim_id, context)
        results.append(result)
    return results
