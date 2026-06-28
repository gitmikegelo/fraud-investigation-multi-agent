"""7-step investigation checklist for Car Insurance claims.

CHECKLIST is the single source of truth.  CHECKLIST_STEPS (the list of
(step_number, name) tuples consumed by api.py) is derived from it, so the
two can never drift.  run_full_checklist / run_checklist_step preserve the
existing public interface that api.py depends on.
"""

from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime

from core.engine import Step, ChecklistStepResult, run_checklist, run_checklist_step_spec


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_claim(context, claim_id):
    return next((c for c in context.get("claims", []) if c.claim_id == claim_id), None)


def _get_insured(context, insured_id):
    return next((i for i in context.get("insureds", []) if i.insured_id == insured_id), None)


def _get_policy(context, policy_id):
    return next((p for p in context.get("policies", []) if p.policy_id == policy_id), None)


def _get_vehicle(context, vehicle_id):
    return next((v for v in context.get("vehicles", []) if v.vehicle_id == vehicle_id), None)


def _get_shop(context, shop_id):
    return next((s for s in context.get("repair_shops", []) if s.shop_id == shop_id), None)


def _get_estimate(context, claim):
    by_id = next((e for e in context.get("estimates", []) if e.estimate_id == getattr(claim, "estimate_id", None)), None)
    if by_id:
        return by_id
    return next((e for e in context.get("estimates", []) if e.claim_id == claim.claim_id), None)


def _get_claim_tasks(context, claim_id):
    return [t for t in context.get("workflow_tasks", []) if t.claim_id == claim_id]


def _get_claim_rules(context, claim_id):
    return context.get("claim_rules", {}).get(claim_id, [])


def _get_claim_risk(context, claim_id):
    return context.get("claim_risk_scores", {}).get(claim_id, None)


def _get_claim_doc_results(context, claim_id):
    return context.get("claim_doc_results", {}).get(claim_id, [])


# ── Step check functions (irreducibly procedural logic) ───────────────────────

def _initial_review(claim, context) -> ChecklistStepResult:
    findings = []
    all_ok = True
    for attr, label in [("insured_id", "Insured ID"), ("policy_id", "Policy ID"),
                        ("claim_type", "Claim type"), ("date_of_incident", "Date of incident")]:
        if not getattr(claim, attr, None):
            findings.append(f"MISSING: {label}")
            all_ok = False
    if claim.claim_amount <= 0:
        findings.append("WARNING: Claim amount is zero or negative")
        all_ok = False
    tasks = _get_claim_tasks(context, claim.claim_id)
    if any(t.task_type == "INITIAL_REVIEW" for t in tasks):
        findings.append("INITIAL_REVIEW task assigned")
    else:
        findings.append("MISSING: No INITIAL_REVIEW task assigned")
        all_ok = False
    if all_ok:
        findings.insert(0, "All required fields present")
    return ChecklistStepResult(1, "Initial Review", "pass" if all_ok else "needs_review", all_ok, findings)


def _damage_documentation(claim, context) -> ChecklistStepResult:
    findings = []
    all_ok = True
    estimate = _get_estimate(context, claim)
    if claim.claim_type in ("collision", "comprehensive", "liability"):
        if estimate:
            findings.append(f"Repair estimate ${estimate.amount:,.2f} on file ({len(estimate.line_items)} line items)")
        else:
            findings.append("WARNING: No repair estimate on file for a damage claim")
            all_ok = False
    elif claim.claim_type == "theft":
        findings.append("Total-loss / theft claim — no repair estimate expected")
    doc_results = _get_claim_doc_results(context, claim.claim_id)
    if doc_results:
        failed = [d for d in doc_results if not d.passed]
        critical = [d for d in failed if d.severity == "CRITICAL"]
        warnings = [d for d in failed if d.severity == "WARNING"]
        assessment = next(
            (d.details.get("overall_assessment") for d in doc_results
             if isinstance(getattr(d, "details", None), dict) and d.details.get("overall_assessment")), "")
        if not failed:
            findings.append(f"Evidence image passed all {len(doc_results)} authenticity checks")
        else:
            for c in critical:
                findings.append(f"CRITICAL [{c.check_id}] {c.check_name}: {c.explanation}")
            for w in warnings:
                findings.append(f"WARNING [{w.check_id}] {w.check_name}: {w.explanation}")
            all_ok = False
        if assessment:
            findings.append(f"Vision assessment: {assessment}")
    rules = _get_claim_rules(context, claim.claim_id)
    r002 = next((r for r in rules if r.rule_id == "R-002"), None)
    if r002 and r002.triggered:
        findings.append(f"BLOCK R-002: {r002.explanation}")
        all_ok = False
    return ChecklistStepResult(2, "Damage Documentation", "pass" if all_ok else "needs_review", all_ok, findings)


def _coverage_timeline(claim, context) -> ChecklistStepResult:
    findings = []
    all_ok = True
    policy = _get_policy(context, getattr(claim, "policy_id", ""))
    if not policy:
        return ChecklistStepResult(3, "Coverage Timeline", "fail", False, ["Policy not found"])
    incident_date = getattr(claim, "date_of_incident", "")
    effective = getattr(policy, "effective_date", "")
    expiration = getattr(policy, "expiration_date", "")
    if incident_date and effective and expiration:
        try:
            inc = datetime.strptime(incident_date, "%Y-%m-%d")
            eff = datetime.strptime(effective, "%Y-%m-%d")
            exp = datetime.strptime(expiration, "%Y-%m-%d")
            if eff <= inc <= exp:
                findings.append(f"Incident {incident_date} within coverage period ({effective} → {expiration})")
            elif inc < eff:
                findings.append(f"BLOCK: Incident {incident_date} BEFORE policy effective {effective}")
                all_ok = False
            else:
                findings.append(f"FAIL: Incident {incident_date} AFTER policy expiration {expiration}")
                all_ok = False
        except ValueError:
            findings.append("WARNING: Could not parse coverage dates")
    rules = _get_claim_rules(context, claim.claim_id)
    r001 = next((r for r in rules if r.rule_id == "R-001"), None)
    if r001 and r001.triggered:
        findings.append(f"BLOCK R-001: {r001.explanation}")
        all_ok = False
    return ChecklistStepResult(3, "Coverage Timeline", "pass" if all_ok else "needs_review", all_ok, findings)


def _fraud_screening(claim, context) -> ChecklistStepResult:
    findings = []
    rules = _get_claim_rules(context, claim.claim_id)
    risk = _get_claim_risk(context, claim.claim_id)
    doc_results = _get_claim_doc_results(context, claim.claim_id)
    is_vision = any(getattr(d, "details", {}).get("source") == "vision_ai" for d in doc_results)
    has_images = context.get("has_claim_images", False)
    image_details = {}
    if is_vision or has_images:
        image_details = {"has_document_image": True,
                         "image_url": f"/api/claims/{claim.claim_id}/document-image"}
    insured = _get_insured(context, getattr(claim, "insured_id", ""))
    is_serial = getattr(insured, "claim_history_count", 0) >= 3 if insured else False
    is_flagged = getattr(insured, "flagged", False) if insured else False
    if is_flagged or is_serial:
        findings.append(f"⚠️ INSURED FLAGGED — claim_history_count: {getattr(insured, 'claim_history_count', 0)}")
        findings.append("Routing to senior examiner review path")
    risk_score = risk.total_score if risk else 0
    block_rules = [r for r in rules if r.triggered and r.severity == "BLOCK"]
    flag_rules = [r for r in rules if r.triggered and r.severity == "FLAG"]
    for br in block_rules:
        findings.append(f"BLOCK {br.rule_id}: {br.explanation}")
    for fr in flag_rules:
        findings.append(f"FLAG {fr.rule_id}: {fr.explanation}")
    if not block_rules and not flag_rules:
        findings.append("No BLOCK or FLAG rules triggered")
    findings.append(f"Risk score: {risk_score:.1f} ({risk.tier if risk else 'UNKNOWN'})")
    if risk_score < 30 and not block_rules and not is_flagged:
        return ChecklistStepResult(4, "Document AI Review", "pass", True, findings,
                                   {"risk_score": risk_score, "auto_passed": True, **image_details})
    status = "fail" if block_rules else "needs_review"
    return ChecklistStepResult(4, "Document AI Review", status, False, findings,
                               {"risk_score": risk_score, **image_details})


def _shop_verification(claim, context) -> ChecklistStepResult:
    findings = []
    all_ok = True
    shop_id = getattr(claim, "shop_id", None)
    if shop_id:
        shop = _get_shop(context, shop_id)
        if shop:
            if shop.on_watchlist:
                findings.append(f"BLOCK: Repair shop {shop.name} is on the fraud watchlist")
                all_ok = False
            elif not shop.verified or not shop.in_network:
                findings.append(f"WARNING: Repair shop {shop.name} is out-of-network / unverified")
                all_ok = False
            else:
                findings.append(f"Repair shop {shop.name} — verified, in-network")
        else:
            findings.append(f"WARNING: Repair shop {shop_id} not found in system")
    else:
        if claim.claim_type == "theft":
            findings.append("Theft claim — no repair shop required")
        else:
            findings.append("WARNING: Damage claim has no repair shop on record")
            all_ok = False
    vehicle = _get_vehicle(context, getattr(claim, "vehicle_id", ""))
    if vehicle and vehicle.acv:
        ratio = claim.claim_amount / vehicle.acv if vehicle.acv > 0 else 0
        if ratio > 1.1:
            findings.append(f"FLAG: Claim ${claim.claim_amount:,.2f} is {ratio:.1f}x the vehicle ACV ${vehicle.acv:,.2f}")
            all_ok = False
        else:
            findings.append(f"Claim amount consistent with vehicle ACV ${vehicle.acv:,.2f}")
    rules = _get_claim_rules(context, claim.claim_id)
    for rid in ("R-004", "R-005"):
        r = next((x for x in rules if x.rule_id == rid), None)
        if r and r.triggered:
            findings.append(f"{r.severity} {r.rule_id}: {r.explanation}")
            all_ok = False
    return ChecklistStepResult(5, "Repair Shop Verification", "pass" if all_ok else "needs_review", all_ok, findings)


def _policy_coverage(claim, context) -> ChecklistStepResult:
    findings = []
    all_ok = True
    policy = _get_policy(context, getattr(claim, "policy_id", ""))
    if not policy:
        return ChecklistStepResult(6, "Policy & Coverage", "fail", False, ["Policy not found"])
    if policy.status != "active":
        findings.append(f"FAIL: Policy status is {policy.status}")
        all_ok = False
    else:
        findings.append("Policy is active")
    coverage_map = {
        "collision": getattr(policy, "coverage_collision", 0),
        "comprehensive": getattr(policy, "coverage_comprehensive", 0),
        "theft": getattr(policy, "coverage_comprehensive", 0),
        "liability": getattr(policy, "coverage_liability", 0),
        "medical_payments": getattr(policy, "coverage_medical_payments", 0),
    }
    coverage_limit = coverage_map.get(claim.claim_type, 0)
    if coverage_limit > 0:
        if claim.claim_amount <= coverage_limit:
            findings.append(f"Amount ${claim.claim_amount:,.2f} within {claim.claim_type} coverage limit (${coverage_limit:,.2f})")
        else:
            findings.append(f"EXCEED: Amount ${claim.claim_amount:,.2f} exceeds coverage limit ${coverage_limit:,.2f}")
            all_ok = False
    else:
        findings.append(f"Coverage limit not defined for {claim.claim_type}")
    return ChecklistStepResult(6, "Policy & Coverage", "pass" if all_ok else "needs_review", all_ok, findings)


def _final_determination(claim, context) -> ChecklistStepResult:
    return ChecklistStepResult(
        7, "Final Determination", "needs_review", False,
        ["Awaiting examiner determination: APPROVE / DENY / ESCALATE TO SIU"],
        {"requires_manual_review": True},
    )


# ── CHECKLIST — single source of truth ───────────────────────────────────────

CHECKLIST: List[Step] = [
    Step(id="initial_review",       name="Initial Review",           check=_initial_review),
    Step(id="damage_documentation", name="Damage Documentation",     check=_damage_documentation),
    Step(id="coverage_timeline",    name="Coverage Timeline",        check=_coverage_timeline,
         config={"acv_ratio_threshold": 1.1}),
    Step(id="fraud_screening",      name="Document AI Review",       check=_fraud_screening),
    Step(id="shop_verification",    name="Repair Shop Verification", check=_shop_verification),
    Step(id="policy_coverage",      name="Policy & Coverage",        check=_policy_coverage),
    Step(id="final_determination",  name="Final Determination",      check=_final_determination),
]

# Derived — api.py reads this; it can never drift from CHECKLIST names.
CHECKLIST_STEPS = [(i + 1, step.name) for i, step in enumerate(CHECKLIST)]


# ── Public API (unchanged interface for api.py) ───────────────────────────────

def run_checklist_step(step_number: int, claim_id: str, context: Dict) -> ChecklistStepResult:
    """Run a single checklist step (1-indexed)."""
    claim = _get_claim(context, claim_id)
    if not claim:
        name = CHECKLIST[step_number - 1].name if 0 < step_number <= len(CHECKLIST) else "Unknown"
        return ChecklistStepResult(step_number, name, "error", False, ["Claim not found"])
    if not (1 <= step_number <= len(CHECKLIST)):
        return ChecklistStepResult(step_number, "Unknown", "error", False, ["Invalid step number"])
    result = run_checklist_step_spec(CHECKLIST[step_number - 1], claim, context)
    result.step_number = step_number   # ensure number matches position
    return result


def run_full_checklist(claim_id: str, context: Dict) -> List[ChecklistStepResult]:
    """Run all checklist steps for a car claim."""
    results = run_checklist(CHECKLIST, claim_id, context)
    for i, r in enumerate(results):
        r.step_number = i + 1
    return results
