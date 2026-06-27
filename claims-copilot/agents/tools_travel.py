"""Travel insurance claim tools for the Zurich Travel Guard examiner copilot."""

import json
from typing import Dict, List, Annotated, Optional
from datetime import datetime

_context = None  # DataContext injected at startup


def set_context(ctx):
    global _context
    _context = ctx


def _tool_log(name: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"    [{ts}]   tool:{name} -> {msg}", flush=True)


def _get_claim(claim_id: str):
    """Find a travel claim by ID."""
    return next((c for c in _context.supplemental_claims if c.claim_id == claim_id), None)


def _get_traveler(traveler_id: str):
    return next((t for t in _context.supplemental_data.get("travelers", []) if t.traveler_id == traveler_id), None)


def _get_policy(policy_id: str):
    return next((p for p in _context.supplemental_data.get("policies", []) if p.policy_id == policy_id), None)


def _get_destination(destination_id: str):
    return next((d for d in _context.supplemental_data.get("destinations", []) if d.destination_id == destination_id), None)


def _get_provider(provider_id: str):
    return next((p for p in _context.supplemental_data.get("providers", []) if p.provider_id == provider_id), None)


def _get_flight(flight_id: str):
    return next((f for f in _context.supplemental_data.get("flights", []) if f.flight_id == flight_id), None)


def _get_booking_for_policy(policy_id: str) -> List:
    return [b for b in _context.supplemental_data.get("bookings", []) if b.policy_id == policy_id]


# ── Fraud Tools ──────────────────────────────────────────────────────────────

def check_eligibility(
    claim_id: Annotated[str, "Claim ID (e.g. ME-101, TC-202)"],
) -> Dict:
    """Check claim eligibility: policy active, coverage matches claim type, traveler enrolled, dates valid."""
    _tool_log("check_eligibility", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    traveler = _get_traveler(claim.traveler_id)
    policy = _get_policy(claim.policy_id)
    dest = _get_destination(claim.destination_id)

    issues = []
    if not policy:
        issues.append("No matching policy found")
    elif policy.status != "active":
        issues.append(f"Policy status is {policy.status}")

    # Check claim within trip dates
    if policy:
        try:
            incident = datetime.strptime(claim.date_of_incident, "%Y-%m-%d")
            trip_start = datetime.strptime(policy.trip_start_date, "%Y-%m-%d")
            trip_end = datetime.strptime(policy.trip_end_date, "%Y-%m-%d")
            if incident < trip_start or incident > trip_end:
                issues.append(f"Incident date {claim.date_of_incident} outside trip window ({policy.trip_start_date} to {policy.trip_end_date})")
        except (ValueError, TypeError):
            pass

    # Check policy purchased before incident
    if policy and claim.date_of_incident:
        try:
            purchase = datetime.strptime(policy.purchase_date, "%Y-%m-%d")
            incident = datetime.strptime(claim.date_of_incident, "%Y-%m-%d")
            if purchase > incident:
                issues.append(f"⚠ Policy purchased AFTER incident (purchased {policy.purchase_date}, incident {claim.date_of_incident})")
        except (ValueError, TypeError):
            pass

    if traveler and traveler.flagged:
        issues.append("⚠ TRAVELER FLAGGED for prior fraud referrals")

    # Coverage limit check
    coverage_map = {
        "trip_cancellation": policy.coverage_trip_cancel if policy else 0,
        "trip_interruption": policy.coverage_trip_cancel if policy else 0,
        "medical_emergency": policy.coverage_medical if policy else 0,
        "baggage_loss": policy.coverage_baggage if policy else 0,
        "travel_delay": policy.coverage_delay if policy else 0,
    }
    coverage_limit = coverage_map.get(claim.claim_type, 0)
    if claim.claim_amount > coverage_limit:
        issues.append(f"Claim ${claim.claim_amount:,.2f} exceeds coverage limit ${coverage_limit:,.2f}")

    return {
        "claim_id": claim_id,
        "eligible": len(issues) == 0,
        "issues": issues,
        "traveler_name": traveler.full_name if traveler else "Unknown",
        "traveler_id": claim.traveler_id,
        "destination": f"{dest.city}, {dest.country}" if dest else "Unknown",
        "policy_id": claim.policy_id,
        "policy_status": policy.status if policy else "N/A",
        "plan_type": policy.plan_type if policy else "N/A",
        "coverage_limit": coverage_limit,
        "claim_type": claim.claim_type,
        "claim_amount": claim.claim_amount,
        "traveler_flagged": traveler.flagged if traveler else False,
    }


def check_travel_history(
    claim_id: Annotated[str, "Claim ID to check traveler history for"],
) -> Dict:
    """Analyze traveler's claim history: frequency, patterns, serial claimer indicators."""
    _tool_log("check_travel_history", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    traveler = _get_traveler(claim.traveler_id)
    all_traveler_claims = [c for c in _context.supplemental_claims if c.traveler_id == claim.traveler_id]

    # Claim type distribution
    type_counts = {}
    for c in all_traveler_claims:
        type_counts[c.claim_type] = type_counts.get(c.claim_type, 0) + 1

    # Total claimed
    total_claimed = sum(c.claim_amount for c in all_traveler_claims)

    # Check for serial pattern (multiple similar claims)
    flags = []
    history_count = traveler.claim_history_count if traveler else 0
    effective_count = max(len(all_traveler_claims), history_count)

    if effective_count >= 3:
        flags.append(f"Serial claimer: {effective_count} claims in tracking period")
    if type_counts.get("medical_emergency", 0) >= 2:
        flags.append(f"Repeat medical claims: {type_counts['medical_emergency']}x medical emergency")
    if total_claimed > 20000:
        flags.append(f"High total claimed: ${total_claimed:,.2f}")

    return {
        "claim_id": claim_id,
        "traveler_id": claim.traveler_id,
        "traveler_name": traveler.full_name if traveler else "Unknown",
        "total_claims": effective_count,
        "claims_in_dataset": len(all_traveler_claims),
        "claim_history_count": history_count,
        "total_amount_claimed": round(total_claimed, 2),
        "type_distribution": type_counts,
        "flags": flags,
        "claims": [
            {"claim_id": c.claim_id, "type": c.claim_type, "amount": c.claim_amount,
             "date": c.date_filed, "destination": c.destination_id}
            for c in all_traveler_claims[:10]
        ],
    }


def verify_booking(
    claim_id: Annotated[str, "Claim ID to verify booking for"],
) -> Dict:
    """Verify booking confirmation exists and matches the claimed trip. Critical for cancellation/interruption claims."""
    _tool_log("verify_booking", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    bookings = _get_booking_for_policy(claim.policy_id)
    confirmed_bookings = [b for b in bookings if b.confirmed]
    flight_bookings = [b for b in bookings if b.booking_type == "flight"]
    hotel_bookings = [b for b in bookings if b.booking_type == "hotel"]

    flags = []
    if not bookings:
        flags.append("NO BOOKINGS FOUND for this policy — phantom booking risk")
    elif not confirmed_bookings:
        flags.append("All bookings are UNCONFIRMED — possible airline refund already issued")
    if claim.claim_type in ("trip_cancellation", "trip_interruption") and not flight_bookings:
        flags.append("No flight booking on file for cancellation/interruption claim")

    total_booking_value = sum(b.amount for b in bookings)

    return {
        "claim_id": claim_id,
        "policy_id": claim.policy_id,
        "total_bookings": len(bookings),
        "confirmed_bookings": len(confirmed_bookings),
        "flight_bookings": [{"ref": b.booking_reference, "airline": b.provider_name, "amount": b.amount, "confirmed": b.confirmed} for b in flight_bookings],
        "hotel_bookings": [{"ref": b.booking_reference, "hotel": b.provider_name, "amount": b.amount, "confirmed": b.confirmed} for b in hotel_bookings],
        "total_booking_value": round(total_booking_value, 2),
        "claim_amount": claim.claim_amount,
        "flags": flags,
    }


def check_destination_risk(
    claim_id: Annotated[str, "Claim ID to check destination risk for"],
) -> Dict:
    """Check destination fraud ring status and provider watchlist. Key for medical emergency claims in high-risk locations."""
    _tool_log("check_destination_risk", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    dest = _get_destination(claim.destination_id)
    provider = _get_provider(claim.provider_id) if claim.provider_id else None

    flags = []
    if dest and dest.known_fraud_ring:
        flags.append(f"⚠ DESTINATION FRAUD RING: {dest.city}, {dest.country} is on watchlist")
    if dest and dest.risk_level == "high":
        flags.append(f"High-risk destination (risk_level={dest.risk_level})")
    if provider and provider.on_watchlist:
        flags.append(f"⚠ PROVIDER ON WATCHLIST: {provider.name}")
    if provider and not provider.verified:
        flags.append(f"Provider NOT in verified network: {provider.name}")

    # Count other claims at same destination
    dest_claims = [c for c in _context.supplemental_claims
                   if c.destination_id == claim.destination_id and c.claim_id != claim_id]

    return {
        "claim_id": claim_id,
        "destination": f"{dest.city}, {dest.country}" if dest else "Unknown",
        "destination_id": claim.destination_id,
        "risk_level": dest.risk_level if dest else "unknown",
        "known_fraud_ring": dest.known_fraud_ring if dest else False,
        "avg_medical_cost_per_day": dest.avg_medical_cost_per_day if dest else 0,
        "provider_name": provider.name if provider else "N/A",
        "provider_on_watchlist": provider.on_watchlist if provider else False,
        "provider_verified": provider.verified if provider else False,
        "other_claims_at_destination": len(dest_claims),
        "flags": flags,
    }


def verify_flight_delay(
    claim_id: Annotated[str, "Claim ID to verify delay for"],
) -> Dict:
    """Cross-check claimed delay against IATA FlightStats tracking data. Use for travel delay claims."""
    _tool_log("verify_flight_delay", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    if claim.claim_type != "travel_delay":
        return {"claim_id": claim_id, "note": "Not a travel delay claim", "applicable": False}

    flight = _get_flight(claim.flight_id) if claim.flight_id else None

    flags = []
    if not flight:
        flags.append("No flight record linked to this claim — cannot verify delay")
        return {
            "claim_id": claim_id,
            "claimed_delay_hours": claim.delay_hours,
            "flight_found": False,
            "flags": flags,
        }

    actual_delay_hours = flight.delay_minutes / 60.0
    discrepancy = claim.delay_hours - actual_delay_hours

    if discrepancy > 3:
        flags.append(f"⚠ MAJOR DISCREPANCY: Traveler claims {claim.delay_hours}h delay, FlightStats shows {flight.delay_minutes} min ({actual_delay_hours:.1f}h)")
    if claim.delay_hours > 4 and flight.delay_minutes == 0:
        flags.append(f"⚠ FABRICATED DELAY: Flight was ON-TIME per FlightStats but traveler claims {claim.delay_hours}h delay")

    # Get airline info
    airline = next((a for a in _context.supplemental_data.get("airlines", []) if a.airline_id == flight.airline_id), None)

    return {
        "claim_id": claim_id,
        "claimed_delay_hours": claim.delay_hours,
        "actual_delay_minutes": flight.delay_minutes,
        "actual_delay_hours": round(actual_delay_hours, 1),
        "discrepancy_hours": round(discrepancy, 1),
        "flight_number": flight.flight_number,
        "airline": airline.name if airline else "Unknown",
        "flight_cancelled": flight.cancelled,
        "flight_found": True,
        "flags": flags,
    }


def analyze_documents(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Review documents submitted: receipts, boarding passes, medical reports, booking confirmations."""
    _tool_log("analyze_documents", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    docs = [d for d in _context.supplemental_data.get("documents", []) if d.claim_id == claim_id]

    flags = []
    if not docs:
        flags.append("No documents on file for this claim")

    doc_summary = []
    for doc in docs:
        d = {
            "doc_id": doc.doc_id,
            "type": doc.doc_type,
            "provider": doc.provider_name,
            "date": doc.date_created,
            "format": doc.format_type,
            "has_header": doc.has_header,
            "has_signature": doc.has_signature,
            "amount": doc.amount_on_doc,
        }
        if doc.tampering_indicators:
            d["tampering_indicators"] = doc.tampering_indicators
            flags.append(f"Document {doc.doc_id}: tampering detected — {', '.join(doc.tampering_indicators)}")
        if not doc.has_signature:
            flags.append(f"Document {doc.doc_id}: missing signature")
        doc_summary.append(d)

    # Check for expected documents by claim type
    expected = {
        "trip_cancellation": ["booking_confirmation"],
        "trip_interruption": ["booking_confirmation"],
        "medical_emergency": ["medical_report"],
        "baggage_loss": ["police_report"],
        "travel_delay": ["boarding_pass"],
    }
    required = expected.get(claim.claim_type, [])
    doc_types_present = [d.doc_type for d in docs]
    for req in required:
        if req not in doc_types_present:
            flags.append(f"MISSING: Required {req} not submitted")

    return {
        "claim_id": claim_id,
        "total_documents": len(docs),
        "documents": doc_summary,
        "flags": flags,
        "flag_count": len(flags),
    }


def find_related_claims(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Find related claims: same traveler, same destination, same provider."""
    _tool_log("find_related_claims", f"Finding related for {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    same_traveler = [c for c in _context.supplemental_claims
                     if c.traveler_id == claim.traveler_id and c.claim_id != claim_id]
    same_dest = [c for c in _context.supplemental_claims
                 if c.destination_id == claim.destination_id and c.claim_id != claim_id]
    same_provider = []
    if claim.provider_id:
        same_provider = [c for c in _context.supplemental_claims
                         if c.provider_id == claim.provider_id and c.claim_id != claim_id]

    def _brief(c):
        return {"claim_id": c.claim_id, "type": c.claim_type, "amount": c.claim_amount,
                "date_filed": c.date_filed, "destination": c.destination_id}

    return {
        "claim_id": claim_id,
        "same_traveler": [_brief(c) for c in same_traveler[:10]],
        "same_destination": [_brief(c) for c in same_dest[:10]],
        "same_provider": [_brief(c) for c in same_provider[:10]],
        "total_related": len(same_traveler) + len(same_dest) + len(same_provider),
    }


# ── Workflow Tools ───────────────────────────────────────────────────────────

def check_workflow_tasks(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Check workflow task status: INITIAL_REVIEW, DOCUMENT_REQUEST, BOOKING_VERIFICATION, MEDICAL_REVIEW."""
    _tool_log("check_workflow_tasks", f"Checking {claim_id}")
    tasks = [t for t in _context.supplemental_data.get("workflow_tasks", []) if t.claim_id == claim_id]

    task_list = []
    for t in tasks:
        task_list.append({
            "task_id": t.task_id, "type": t.task_type, "status": t.status,
            "assigned_date": t.assigned_date, "due_date": t.due_date,
            "days_waiting": t.days_waiting,
        })

    overdue = [t for t in tasks if t.status == "overdue"]
    return {
        "claim_id": claim_id,
        "total_tasks": len(tasks),
        "tasks": task_list,
        "overdue_count": len(overdue),
    }


# ── Policy Tools ─────────────────────────────────────────────────────────────

def get_policy_details(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Get full policy from TravelGuard Portal: coverage limits, trip dates, premium, plan type."""
    _tool_log("get_policy_details", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    policy = _get_policy(claim.policy_id)
    if not policy:
        return {"claim_id": claim_id, "error": "No policy found"}

    dest = _get_destination(policy.destination_id)

    return {
        "claim_id": claim_id,
        "policy_id": policy.policy_id,
        "traveler_id": policy.traveler_id,
        "plan_type": policy.plan_type,
        "purchase_date": policy.purchase_date,
        "trip_start_date": policy.trip_start_date,
        "trip_end_date": policy.trip_end_date,
        "destination": f"{dest.city}, {dest.country}" if dest else policy.destination_id,
        "coverage_trip_cancel": policy.coverage_trip_cancel,
        "coverage_medical": policy.coverage_medical,
        "coverage_baggage": policy.coverage_baggage,
        "coverage_delay": policy.coverage_delay,
        "premium": policy.premium,
        "status": policy.status,
    }


def match_claim_to_coverage(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Verify claim type matches policy, amounts within limits, incident within trip dates."""
    _tool_log("match_claim_to_coverage", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    policy = _get_policy(claim.policy_id)
    if not policy:
        return {"claim_id": claim_id, "error": "Policy not found"}

    issues = []

    # Coverage limit check
    coverage_map = {
        "trip_cancellation": ("Trip Cancellation", policy.coverage_trip_cancel),
        "trip_interruption": ("Trip Interruption", policy.coverage_trip_cancel),
        "medical_emergency": ("Medical Emergency", policy.coverage_medical),
        "baggage_loss": ("Baggage Loss", policy.coverage_baggage),
        "travel_delay": ("Travel Delay", policy.coverage_delay),
    }
    coverage_name, coverage_limit = coverage_map.get(claim.claim_type, ("Unknown", 0))

    if claim.claim_amount > coverage_limit:
        issues.append(f"Claim ${claim.claim_amount:,.2f} EXCEEDS {coverage_name} limit ${coverage_limit:,.2f}")

    # Date check
    try:
        incident = datetime.strptime(claim.date_of_incident, "%Y-%m-%d")
        trip_start = datetime.strptime(policy.trip_start_date, "%Y-%m-%d")
        trip_end = datetime.strptime(policy.trip_end_date, "%Y-%m-%d")
        if incident < trip_start:
            issues.append(f"Incident {claim.date_of_incident} is BEFORE trip start {policy.trip_start_date}")
        if incident > trip_end:
            issues.append(f"Incident {claim.date_of_incident} is AFTER trip end {policy.trip_end_date}")
    except (ValueError, TypeError):
        pass

    return {
        "claim_id": claim_id,
        "coverage_type": coverage_name,
        "coverage_limit": coverage_limit,
        "claim_amount": claim.claim_amount,
        "within_limits": claim.claim_amount <= coverage_limit,
        "issues": issues,
        "policy_status": policy.status,
    }


# ── Universal Tools ──────────────────────────────────────────────────────────

def explain_risk_score(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Full risk score breakdown with top factors and innocent explanations."""
    _tool_log("explain_risk_score", f"Explaining {claim_id}")
    risk = _context.claim_risk_scores.get(claim_id)
    if not risk:
        return {"claim_id": claim_id, "error": "No risk score found"}

    # Also get rules
    rules = _context.claim_rules.get(claim_id, [])
    triggered = [r for r in rules if r.triggered]

    return {
        "claim_id": claim_id,
        "total_score": risk.total_score,
        "tier": risk.tier,
        "top_factors": risk.top_factors,
        "rules_boost": risk.rules_boost,
        "feature_contributions": [
            {"category": fc.category, "feature": fc.feature_name,
             "raw_value": fc.raw_value, "contribution": round(fc.contribution * 100, 1)}
            for fc in risk.feature_contributions
        ],
        "rules_triggered": [
            {"rule_id": r.rule_id, "name": r.rule_name, "severity": r.severity, "explanation": r.explanation}
            for r in triggered
        ],
    }


def run_fraud_checklist(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Execute the full 7-step travel claims adjuster checklist."""
    _tool_log("run_fraud_checklist", f"Running for {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    steps = []

    # Step 1: Initial Claim Review
    step1_issues = []
    if not claim.traveler_id:
        step1_issues.append("Missing traveler ID")
    if not claim.policy_id:
        step1_issues.append("Missing policy ID")
    if not claim.date_of_incident:
        step1_issues.append("Missing incident date")
    steps.append({"step": 1, "name": "Initial Claim Review", "status": "fail" if step1_issues else "pass", "issues": step1_issues})

    # Step 2: Policy Coverage Verification
    policy = _get_policy(claim.policy_id)
    step2_issues = []
    if not policy:
        step2_issues.append("Policy not found")
    elif policy.status != "active":
        step2_issues.append(f"Policy status: {policy.status}")
    steps.append({"step": 2, "name": "Policy Coverage Verification", "status": "fail" if step2_issues else "pass", "issues": step2_issues})

    # Step 3: Trip Documentation Check
    bookings = _get_booking_for_policy(claim.policy_id) if claim.policy_id else []
    confirmed = [b for b in bookings if b.confirmed]
    step3_issues = []
    if claim.claim_type in ("trip_cancellation", "trip_interruption") and not confirmed:
        step3_issues.append("No confirmed bookings found")
    steps.append({"step": 3, "name": "Trip Documentation Check", "status": "fail" if step3_issues else "pass", "issues": step3_issues})

    # Step 4: Provider/Vendor Verification
    step4_issues = []
    if claim.provider_id:
        provider = _get_provider(claim.provider_id)
        if provider and provider.on_watchlist:
            step4_issues.append(f"Provider {provider.name} is on WATCHLIST")
        elif provider and not provider.verified:
            step4_issues.append(f"Provider {provider.name} not in verified network")
    steps.append({"step": 4, "name": "Provider/Vendor Verification", "status": "fail" if step4_issues else "pass", "issues": step4_issues})

    # Step 5: Fraud Screening
    rules = _context.claim_rules.get(claim_id, [])
    triggered = [r for r in rules if r.triggered]
    blocks = [r for r in triggered if r.severity == "BLOCK"]
    step5_issues = [f"{r.rule_id}: {r.rule_name}" for r in blocks]
    steps.append({"step": 5, "name": "Fraud Screening", "status": "fail" if blocks else ("needs_review" if triggered else "pass"), "issues": step5_issues})

    # Step 6: Medical Records Review (only for medical claims)
    step6_issues = []
    if claim.claim_type == "medical_emergency":
        dest = _get_destination(claim.destination_id)
        if dest and dest.known_fraud_ring:
            step6_issues.append(f"Medical claim at fraud-ring destination: {dest.city}")
    steps.append({"step": 6, "name": "Medical Records Review", "status": "fail" if step6_issues else "pass", "issues": step6_issues})

    # Step 7: Final Determination
    total_fails = sum(1 for s in steps if s["status"] == "fail")
    if total_fails >= 2:
        determination = "DENY — Multiple checklist failures"
    elif total_fails == 1:
        determination = "ESCALATE — Requires senior review"
    else:
        determination = "APPROVE — All checks passed"
    steps.append({"step": 7, "name": "Final Determination", "status": "pass" if total_fails == 0 else "needs_review", "issues": [determination]})

    return {
        "claim_id": claim_id,
        "total_steps": 7,
        "passed": sum(1 for s in steps if s["status"] == "pass"),
        "failed": total_fails,
        "needs_review": sum(1 for s in steps if s["status"] == "needs_review"),
        "steps": steps,
        "recommendation": determination,
    }


def compile_dossier(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Generate escalation dossier with all travel claim intelligence."""
    _tool_log("compile_dossier", f"Compiling for {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    traveler = _get_traveler(claim.traveler_id)
    policy = _get_policy(claim.policy_id)
    dest = _get_destination(claim.destination_id)
    provider = _get_provider(claim.provider_id) if claim.provider_id else None
    rules = _context.claim_rules.get(claim_id, [])
    risk = _context.claim_risk_scores.get(claim_id)
    triggered = [r for r in rules if r.triggered]

    dossier = f"""# Travel Claim Investigation Dossier

## Claim: {claim_id}
- **Type**: {claim.claim_type.replace('_', ' ').title()}
- **Amount**: ${claim.claim_amount:,.2f}
- **Date Filed**: {claim.date_filed}
- **Incident Date**: {claim.date_of_incident}
- **Status**: {claim.status}

## Traveler
- **Name**: {traveler.full_name if traveler else 'Unknown'}
- **ID**: {claim.traveler_id}
- **Flagged**: {'YES ⚠' if (traveler and traveler.flagged) else 'No'}
- **Prior Claims**: {traveler.claim_history_count if traveler else 0}

## Destination
- **Location**: {f'{dest.city}, {dest.country}' if dest else 'Unknown'}
- **Risk Level**: {dest.risk_level.upper() if dest else 'Unknown'}
- **Fraud Ring**: {'YES ⚠' if (dest and dest.known_fraud_ring) else 'No'}

## Policy
- **Policy ID**: {policy.policy_id if policy else 'N/A'}
- **Purchase Date**: {policy.purchase_date if policy else 'N/A'}
- **Trip**: {policy.trip_start_date if policy else '?'} to {policy.trip_end_date if policy else '?'}
- **Coverage ({claim.claim_type})**: ${_get_coverage_for_type(policy, claim.claim_type):,.2f}

## Risk Assessment
- **Score**: {risk.total_score if risk else 0}/100 ({risk.tier if risk else 'N/A'})
- **Top Factors**: {', '.join(risk.top_factors) if risk else 'None'}

## Rules Triggered ({len(triggered)})
"""
    for r in triggered:
        dossier += f"- **{r.rule_id}** [{r.severity}]: {r.rule_name} — {r.explanation}\n"

    if claim.notes:
        dossier += f"\n## Investigation Notes\n{claim.notes}\n"

    dossier += f"\n---\n*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · Zurich Travel Guard SIU*\n"

    return {
        "claim_id": claim_id,
        "dossier": dossier,
        "risk_score": risk.total_score if risk else 0,
        "rules_triggered": len(triggered),
    }


def _get_coverage_for_type(policy, claim_type: str) -> float:
    """Helper to get coverage limit for a claim type."""
    if not policy:
        return 0
    coverage_map = {
        "trip_cancellation": policy.coverage_trip_cancel,
        "trip_interruption": policy.coverage_trip_cancel,
        "medical_emergency": policy.coverage_medical,
        "baggage_loss": policy.coverage_baggage,
        "travel_delay": policy.coverage_delay,
    }
    return coverage_map.get(claim_type, 0)


# ── Tool Registry ────────────────────────────────────────────────────────────

ALL_TRAVEL_TOOLS = [
    # Fraud tools
    check_eligibility,
    check_travel_history,
    verify_booking,
    check_destination_risk,
    verify_flight_delay,
    analyze_documents,
    find_related_claims,
    # Workflow tools
    check_workflow_tasks,
    # Policy tools
    get_policy_details,
    match_claim_to_coverage,
    # Universal tools
    explain_risk_score,
    run_fraud_checklist,
    compile_dossier,
]
