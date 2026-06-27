"""7-step investigation checklist for Zurich Travel Guard claims."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


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
    (2, "Trip Documentation"),
    (3, "Travel Timeline"),
    (4, "Document AI Review"),
    (5, "Provider & Booking Verification"),
    (6, "Policy & Coverage"),
    (7, "Final Determination"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_claim(context, claim_id):
    return next((c for c in context.get("claims", []) if c.claim_id == claim_id), None)


def _get_traveler(context, traveler_id):
    return next((t for t in context.get("travelers", []) if t.traveler_id == traveler_id), None)


def _get_policy(context, policy_id):
    return next((p for p in context.get("policies", []) if p.policy_id == policy_id), None)


def _get_destination(context, destination_id):
    return next((d for d in context.get("destinations", []) if d.destination_id == destination_id), None)


def _get_provider(context, provider_id):
    return next((p for p in context.get("providers", []) if p.provider_id == provider_id), None)


def _get_bookings_for_policy(context, policy_id):
    return [b for b in context.get("bookings", []) if b.policy_id == policy_id]


def _get_flight(context, flight_id):
    return next((f for f in context.get("flights", []) if f.flight_id == flight_id), None)


def _get_claim_tasks(context, claim_id):
    return [t for t in context.get("workflow_tasks", []) if t.claim_id == claim_id]


def _get_claim_rules(context, claim_id):
    return context.get("claim_rules", {}).get(claim_id, [])


def _get_claim_risk(context, claim_id):
    return context.get("claim_risk_scores", {}).get(claim_id, None)


def _get_claim_doc_results(context, claim_id):
    return context.get("claim_doc_results", {}).get(claim_id, [])


def _days_between(d1: str, d2: str) -> Optional[int]:
    try:
        dt1 = datetime.strptime(d1, "%Y-%m-%d")
        dt2 = datetime.strptime(d2, "%Y-%m-%d")
        return abs((dt2 - dt1).days)
    except (ValueError, TypeError):
        return None


# ── Step Implementations ──────────────────────────────────────────────────────

def _step_initial_review(claim, context) -> ChecklistStepResult:
    """Step 1: Claim has required fields — traveler, policy, claim type, amount, incident date."""
    findings = []
    all_ok = True

    if not getattr(claim, 'traveler_id', None):
        findings.append("MISSING: Traveler ID")
        all_ok = False
    if not getattr(claim, 'policy_id', None):
        findings.append("MISSING: Policy ID")
        all_ok = False
    if not getattr(claim, 'claim_type', None):
        findings.append("MISSING: Claim type")
        all_ok = False
    if not getattr(claim, 'date_of_incident', None):
        findings.append("MISSING: Date of incident")
        all_ok = False
    if claim.claim_amount <= 0:
        findings.append("WARNING: Claim amount is zero or negative")
        all_ok = False

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


def _step_trip_documentation(claim, context) -> ChecklistStepResult:
    """Step 2: Booking records confirmed for the policy."""
    findings = []
    all_ok = True

    policy_id = getattr(claim, 'policy_id', '')
    bookings = _get_bookings_for_policy(context, policy_id)

    if not bookings:
        findings.append("WARNING: No booking records found for this policy")
        all_ok = False
    else:
        confirmed = [b for b in bookings if b.confirmed]
        unconfirmed = [b for b in bookings if not b.confirmed]
        findings.append(f"{len(confirmed)} confirmed booking(s): "
                        f"{', '.join(b.booking_type for b in confirmed[:3])}")
        if unconfirmed:
            findings.append(f"WARNING: {len(unconfirmed)} unconfirmed booking(s) on file")
            all_ok = False

    # Evidence-image vision analysis (e.g. damaged-baggage photo, receipt, police report)
    doc_results = _get_claim_doc_results(context, claim.claim_id)
    if doc_results:
        failed = [d for d in doc_results if not d.passed]
        critical = [d for d in failed if d.severity == "CRITICAL"]
        warnings = [d for d in failed if d.severity == "WARNING"]
        assessment = next(
            (d.details.get("overall_assessment") for d in doc_results
             if isinstance(getattr(d, "details", None), dict) and d.details.get("overall_assessment")),
            "",
        )
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

    # Check for document request tasks
    tasks = _get_claim_tasks(context, claim.claim_id)
    doc_tasks = [t for t in tasks if t.task_type == "DOCUMENT_REQUEST"]
    for dt in doc_tasks:
        if dt.status == "pending":
            findings.append(f"⏳ Document request pending — {dt.days_waiting}d waiting")

    # Cancellation/interruption requires confirmed booking per R-002
    if claim.claim_type in ("trip_cancellation", "trip_interruption"):
        rules = _get_claim_rules(context, claim.claim_id)
        r002 = next((r for r in rules if r.rule_id == "R-002"), None)
        if r002 and r002.triggered:
            findings.append(f"BLOCK R-002: {r002.explanation}")
            all_ok = False

    return ChecklistStepResult(2, "Trip Documentation", "pass" if all_ok else "needs_review",
                               all_ok, findings)


def _step_travel_timeline(claim, context) -> ChecklistStepResult:
    """Step 3: Incident date falls within the trip window; policy not purchased after event."""
    findings = []
    all_ok = True

    policy = _get_policy(context, getattr(claim, 'policy_id', ''))
    if not policy:
        return ChecklistStepResult(3, "Travel Timeline", "fail", False, ["Policy not found"])

    incident_date = getattr(claim, 'date_of_incident', '')
    trip_start = getattr(policy, 'trip_start_date', '')
    trip_end = getattr(policy, 'trip_end_date', '')
    purchase_date = getattr(policy, 'purchase_date', '')

    if incident_date and trip_start and trip_end:
        try:
            incident_dt = datetime.strptime(incident_date, "%Y-%m-%d")
            start_dt = datetime.strptime(trip_start, "%Y-%m-%d")
            end_dt = datetime.strptime(trip_end, "%Y-%m-%d")
            if start_dt <= incident_dt <= end_dt:
                findings.append(f"Incident date {incident_date} within trip window ({trip_start} → {trip_end})")
            else:
                findings.append(f"FAIL: Incident {incident_date} outside trip window ({trip_start} → {trip_end})")
                all_ok = False
        except ValueError:
            findings.append("WARNING: Could not parse trip dates")

    # Policy purchased after incident (R-007)
    if purchase_date and incident_date:
        days = _days_between(purchase_date, incident_date)
        if days is not None and purchase_date > incident_date:
            findings.append(f"BLOCK: Policy purchased {days}d AFTER incident date — {purchase_date} vs {incident_date}")
            all_ok = False
        else:
            findings.append(f"Policy purchased {days}d before incident — within normal range")

    # Pre-existing condition window (R-001)
    rules = _get_claim_rules(context, claim.claim_id)
    r001 = next((r for r in rules if r.rule_id == "R-001"), None)
    if r001 and r001.triggered:
        findings.append(f"FLAG R-001: {r001.explanation}")
        all_ok = False

    return ChecklistStepResult(3, "Travel Timeline", "pass" if all_ok else "needs_review",
                               all_ok, findings)


def _step_fraud_screening(claim, context) -> ChecklistStepResult:
    """Step 4: Document AI review + rules triggered, risk score, serial claimer flag."""
    findings = []
    rules = _get_claim_rules(context, claim.claim_id)
    risk = _get_claim_risk(context, claim.claim_id)

    # Build image details for the "View Source Document" button
    doc_results = _get_claim_doc_results(context, claim.claim_id)
    is_vision = any(getattr(d, 'details', {}).get('source') == 'vision_ai' for d in doc_results)
    has_images = context.get("has_claim_images", False)
    image_details = {}
    if is_vision or has_images:
        image_details = {
            "has_document_image": True,
            "image_url": f"/api/claims/{claim.claim_id}/document-image",
        }

    traveler = _get_traveler(context, getattr(claim, 'traveler_id', ''))
    is_serial = getattr(traveler, 'claim_history_count', 0) >= 3 if traveler else False
    is_flagged = getattr(traveler, 'flagged', False) if traveler else False

    if is_flagged or is_serial:
        findings.append(f"⚠️ TRAVELER FLAGGED — claim_history_count: {getattr(traveler, 'claim_history_count', 0)}")
        findings.append("Routing to senior examiner review path")

    risk_score = risk.total_score if risk else 0
    block_rules = [r for r in rules if r.triggered and r.severity == "BLOCK"]
    flag_rules = [r for r in rules if r.triggered and r.severity == "FLAG"]

    if block_rules:
        for br in block_rules:
            findings.append(f"BLOCK {br.rule_id}: {br.explanation}")
    if flag_rules:
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


def _step_provider_booking_verification(claim, context) -> ChecklistStepResult:
    """Step 5: Provider not on watchlist; bookings match claimed travel."""
    findings = []
    all_ok = True

    provider_id = getattr(claim, 'provider_id', None)
    if provider_id:
        provider = _get_provider(context, provider_id)
        if provider:
            on_watchlist = getattr(provider, 'on_watchlist', False)
            verified = getattr(provider, 'verified', True)
            if on_watchlist:
                findings.append(f"BLOCK: Provider {provider.name} is on the fraud watchlist")
                all_ok = False
            elif not verified:
                findings.append(f"WARNING: Provider {provider.name} is unverified")
                all_ok = False
            else:
                findings.append(f"Provider {provider.name} — verified, not on watchlist")
        else:
            findings.append(f"WARNING: Provider {provider_id} not found in system")
    else:
        if claim.claim_type == "medical_emergency":
            findings.append("WARNING: Medical claim has no provider on record")
            all_ok = False
        else:
            findings.append("No provider required for this claim type")

    # Flight verification for delay claims
    flight_id = getattr(claim, 'flight_id', None)
    if claim.claim_type == "travel_delay" and flight_id:
        flight = _get_flight(context, flight_id)
        if flight:
            delay_hrs = getattr(flight, 'delay_minutes', 0) / 60
            claim_delay = getattr(claim, 'delay_hours', 0)
            if abs(delay_hrs - claim_delay) > 2:
                findings.append(f"FLAG: Claimed delay ({claim_delay:.1f}h) vs flight record ({delay_hrs:.1f}h)")
                all_ok = False
            else:
                findings.append(f"Delay claim consistent with flight record ({delay_hrs:.1f}h delay)")
        else:
            findings.append("WARNING: Flight record not found for delay claim")
            all_ok = False

    # R-005: Destination fraud ring
    rules = _get_claim_rules(context, claim.claim_id)
    r005 = next((r for r in rules if r.rule_id == "R-005"), None)
    if r005 and r005.triggered:
        findings.append(f"FLAG R-005: {r005.explanation}")
        all_ok = False

    # R-009: Booking verification
    r009 = next((r for r in rules if r.rule_id == "R-009"), None)
    if r009 and r009.triggered:
        findings.append(f"FLAG R-009: {r009.explanation}")
        all_ok = False

    return ChecklistStepResult(5, "Provider & Booking Verification",
                               "pass" if all_ok else "needs_review", all_ok, findings)


def _step_policy_coverage(claim, context) -> ChecklistStepResult:
    """Step 6: Coverage type matches claim type; amount within limits."""
    findings = []
    all_ok = True

    policy = _get_policy(context, getattr(claim, 'policy_id', ''))
    if not policy:
        return ChecklistStepResult(6, "Policy & Coverage", "fail", False, ["Policy not found"])

    if policy.status != "active":
        findings.append(f"FAIL: Policy status is {policy.status}")
        all_ok = False
    else:
        findings.append("Policy is active")

    # Check coverage limit for this claim type
    coverage_map = {
        "trip_cancellation": getattr(policy, 'coverage_trip_cancel', 0),
        "trip_interruption": getattr(policy, 'coverage_trip_cancel', 0),
        "medical_emergency": getattr(policy, 'coverage_medical', 0),
        "baggage_loss": getattr(policy, 'coverage_baggage', 0),
        "travel_delay": getattr(policy, 'coverage_delay', 0),
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

    return ChecklistStepResult(6, "Policy & Coverage",
                               "pass" if all_ok else "needs_review", all_ok, findings)


def _step_final_determination(claim, context) -> ChecklistStepResult:
    """Step 7: Always manual — examiner approves/denies/escalates."""
    return ChecklistStepResult(
        7, "Final Determination", "needs_review", False,
        ["Awaiting examiner determination: APPROVE / DENY / ESCALATE TO SIU"],
        {"requires_manual_review": True},
    )


# ── Public API ────────────────────────────────────────────────────────────────

def run_checklist_step(step_number: int, claim_id: str, context: Dict) -> ChecklistStepResult:
    """Run a single checklist step for a travel claim."""
    claim = _get_claim(context, claim_id)
    if not claim:
        return ChecklistStepResult(step_number, CHECKLIST_STEPS[step_number - 1][1],
                                   "error", False, ["Claim not found"])

    if step_number == 1:
        return _step_initial_review(claim, context)
    elif step_number == 2:
        return _step_trip_documentation(claim, context)
    elif step_number == 3:
        return _step_travel_timeline(claim, context)
    elif step_number == 4:
        return _step_fraud_screening(claim, context)
    elif step_number == 5:
        return _step_provider_booking_verification(claim, context)
    elif step_number == 6:
        return _step_policy_coverage(claim, context)
    elif step_number == 7:
        return _step_final_determination(claim, context)
    else:
        return ChecklistStepResult(step_number, "Unknown", "error", False, ["Invalid step number"])


def run_full_checklist(claim_id: str, context: Dict) -> List[ChecklistStepResult]:
    """Run all 7 checklist steps for a travel claim."""
    return [run_checklist_step(i, claim_id, context) for i in range(1, 8)]
