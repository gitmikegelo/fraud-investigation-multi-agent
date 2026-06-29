"""13 deterministic rules (R-001 to R-013) for Zurich Travel Guard claims."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta


@dataclass
class RuleResult:
    rule_id: str
    rule_name: str
    severity: str  # BLOCK, FLAG, INFO
    triggered: bool
    explanation: str
    details: Dict = field(default_factory=dict)


def _days_between(d1: str, d2: str) -> int:
    try:
        dt1 = datetime.strptime(d1, "%Y-%m-%d")
        dt2 = datetime.strptime(d2, "%Y-%m-%d")
        return abs((dt2 - dt1).days)
    except (ValueError, TypeError):
        return 9999


def _get_traveler(context: Dict, traveler_id: str):
    return next((t for t in context.get("travelers", []) if t.traveler_id == traveler_id), None)


def _get_policy(context: Dict, policy_id: str):
    return next((p for p in context.get("policies", []) if p.policy_id == policy_id), None)


def _get_destination(context: Dict, destination_id: str):
    return next((d for d in context.get("destinations", []) if d.destination_id == destination_id), None)


def _get_provider(context: Dict, provider_id: str):
    return next((p for p in context.get("providers", []) if p.provider_id == provider_id), None)


def _get_traveler_claims(context: Dict, traveler_id: str) -> List:
    return [c for c in context.get("claims", []) if c.traveler_id == traveler_id]


def _get_booking_for_policy(context: Dict, policy_id: str) -> List:
    return [b for b in context.get("bookings", []) if b.policy_id == policy_id]


def _get_flight(context: Dict, flight_id: str):
    return next((f for f in context.get("flights", []) if f.flight_id == flight_id), None)


# ── Rule Definitions ─────────────────────────────────────────────────────────

def r001_pre_existing_condition(claim, context) -> RuleResult:
    """R-001: Medical claim filed within 30 days of policy purchase -> FLAG"""
    if claim.claim_type != "medical_emergency":
        return RuleResult("R-001", "Pre-Existing Condition Window", "FLAG", False, "Not a medical claim")
    policy = _get_policy(context, claim.policy_id)
    if not policy:
        return RuleResult("R-001", "Pre-Existing Condition Window", "FLAG", False, "Policy not found")
    days = _days_between(policy.purchase_date, claim.date_of_incident)
    triggered = days <= 30
    return RuleResult(
        rule_id="R-001", rule_name="Pre-Existing Condition Window",
        severity="FLAG", triggered=triggered,
        explanation=f"Medical incident {days} days after policy purchase (threshold: 30)" if triggered else f"Incident {days} days after purchase (outside window)",
        details={"days_after_purchase": days, "threshold": 30},
    )


def r002_no_booking_confirmation(claim, context) -> RuleResult:
    """R-002: Trip cancellation/interruption with no confirmed booking -> BLOCK"""
    if claim.claim_type not in ("trip_cancellation", "trip_interruption"):
        return RuleResult("R-002", "No Booking Confirmation", "BLOCK", False, "Not applicable")
    bookings = _get_booking_for_policy(context, claim.policy_id)
    confirmed = [b for b in bookings if b.confirmed]
    triggered = len(confirmed) == 0
    return RuleResult(
        rule_id="R-002", rule_name="No Booking Confirmation",
        severity="BLOCK", triggered=triggered,
        explanation="No confirmed bookings found for this policy" if triggered else f"{len(confirmed)} confirmed booking(s) on file",
        details={"confirmed_bookings": len(confirmed)},
    )


def r003_duplicate_claim(claim, context) -> RuleResult:
    """R-003: Duplicate/resubmission of an existing claim -> BLOCK"""
    triggered = claim.is_resubmission
    return RuleResult(
        rule_id="R-003", rule_name="Duplicate/Resubmission",
        severity="BLOCK", triggered=triggered,
        explanation=f"Resubmission of {claim.original_claim_id}" if triggered else "No duplicate detected",
        details={"is_resubmission": triggered, "original": claim.original_claim_id},
    )


def r004_baggage_amount_outlier(claim, context) -> RuleResult:
    """R-004: Baggage claim >3x average for the type -> FLAG"""
    if claim.claim_type != "baggage_loss":
        return RuleResult("R-004", "Baggage Amount Outlier", "FLAG", False, "Not a baggage claim")
    baggage_claims = [c for c in context.get("claims", []) if c.claim_type == "baggage_loss"]
    if not baggage_claims:
        return RuleResult("R-004", "Baggage Amount Outlier", "FLAG", False, "No comparison data")
    avg = sum(c.claim_amount for c in baggage_claims) / len(baggage_claims)
    ratio = claim.claim_amount / avg if avg > 0 else 0
    triggered = ratio > 3.0
    return RuleResult(
        rule_id="R-004", rule_name="Baggage Amount Outlier",
        severity="FLAG", triggered=triggered,
        explanation=f"Claim ${claim.claim_amount:,.2f} is {ratio:.1f}x average ${avg:,.2f}" if triggered else f"Amount ${claim.claim_amount:,.2f} within range (avg ${avg:,.2f})",
        details={"claim_amount": claim.claim_amount, "avg_amount": round(avg, 2), "ratio": round(ratio, 2)},
    )


def r005_destination_fraud_ring(claim, context) -> RuleResult:
    """R-005: Claim destination + provider on known fraud watchlist -> BLOCK"""
    if claim.claim_type != "medical_emergency":
        return RuleResult("R-005", "Destination Fraud Ring", "BLOCK", False, "Not a medical claim")
    dest = _get_destination(context, claim.destination_id)
    provider = _get_provider(context, claim.provider_id) if claim.provider_id else None
    dest_flagged = dest.known_fraud_ring if dest else False
    provider_flagged = (provider.on_watchlist if provider else False)
    triggered = dest_flagged and provider_flagged
    return RuleResult(
        rule_id="R-005", rule_name="Destination Fraud Ring",
        severity="BLOCK", triggered=triggered,
        explanation=f"Destination '{dest.city if dest else 'unknown'}' has known fraud ring AND provider is on watchlist" if triggered else "No destination/provider fraud ring match",
        details={"destination_flagged": dest_flagged, "provider_on_watchlist": provider_flagged,
                 "destination": dest.city if dest else None, "provider": provider.name if provider else None},
    )


def r006_policy_after_event(claim, context) -> RuleResult:
    """R-006: Policy purchased after the claimed incident date -> BLOCK"""
    policy = _get_policy(context, claim.policy_id)
    if not policy:
        return RuleResult("R-006", "Policy Purchased After Event", "BLOCK", False, "Policy not found")
    try:
        purchase = datetime.strptime(policy.purchase_date, "%Y-%m-%d")
        incident = datetime.strptime(claim.date_of_incident, "%Y-%m-%d")
        triggered = purchase > incident
    except (ValueError, TypeError):
        triggered = False
    return RuleResult(
        rule_id="R-006", rule_name="Policy Purchased After Event",
        severity="BLOCK", triggered=triggered,
        explanation=f"Policy purchased on {policy.purchase_date} AFTER incident on {claim.date_of_incident}" if triggered else "Policy purchased before incident",
        details={"purchase_date": policy.purchase_date, "incident_date": claim.date_of_incident},
    )


def r007_serial_claimer(claim, context) -> RuleResult:
    """R-007: Traveler has 3+ claims in 12 months -> FLAG"""
    traveler_claims = _get_traveler_claims(context, claim.traveler_id)
    count = len(traveler_claims)
    traveler = _get_traveler(context, claim.traveler_id)
    # Also check stored claim history
    history_count = traveler.claim_history_count if traveler else 0
    total = max(count, history_count)
    triggered = total >= 3
    return RuleResult(
        rule_id="R-007", rule_name="Serial Claimer",
        severity="FLAG", triggered=triggered,
        explanation=f"Traveler has {total} claims (threshold: 3)" if triggered else f"Traveler has {total} claims (normal)",
        details={"claim_count": total, "threshold": 3},
    )


def r008_airline_refund_double_dip(claim, context) -> RuleResult:
    """R-008: Trip cancellation where airline has already issued refund -> FLAG"""
    if claim.claim_type not in ("trip_cancellation", "trip_interruption"):
        return RuleResult("R-008", "Airline Refund Double-Dip", "FLAG", False, "Not applicable")
    # In real system, check refund API; here check booking status
    bookings = _get_booking_for_policy(context, claim.policy_id)
    flight_bookings = [b for b in bookings if b.booking_type == "flight"]
    # Simulated: if booking is NOT confirmed, airline may have already refunded
    unconfirmed_flights = [b for b in flight_bookings if not b.confirmed]
    triggered = len(unconfirmed_flights) > 0 and claim.claim_type == "trip_cancellation"
    return RuleResult(
        rule_id="R-008", rule_name="Airline Refund Double-Dip",
        severity="FLAG", triggered=triggered,
        explanation="Flight booking cancelled/refunded by airline — possible double recovery" if triggered else "No refund conflict detected",
        details={"unconfirmed_bookings": len(unconfirmed_flights)},
    )


def r009_flight_on_time(claim, context) -> RuleResult:
    """R-009: Delay claim but flight tracking shows on-time -> FLAG"""
    if claim.claim_type != "travel_delay":
        return RuleResult("R-009", "Flight On-Time (Tracking)", "FLAG", False, "Not a delay claim")
    if not claim.flight_id:
        return RuleResult("R-009", "Flight On-Time (Tracking)", "FLAG", False, "No flight record linked")
    flight = _get_flight(context, claim.flight_id)
    if not flight:
        return RuleResult("R-009", "Flight On-Time (Tracking)", "FLAG", False, "Flight record not found")
    # Compare claimed delay vs actual
    actual_delay_hours = flight.delay_minutes / 60.0
    claimed_delay = claim.delay_hours
    triggered = claimed_delay > 4 and actual_delay_hours < 1  # Claims big delay, flight was on time
    return RuleResult(
        rule_id="R-009", rule_name="Flight On-Time (Tracking)",
        severity="FLAG", triggered=triggered,
        explanation=f"Traveler claims {claimed_delay}h delay but FlightStats shows {flight.delay_minutes} min actual delay" if triggered else f"Claimed delay consistent with tracking ({flight.delay_minutes} min actual)",
        details={"claimed_delay_hours": claimed_delay, "actual_delay_minutes": flight.delay_minutes},
    )


def r011_baggage_photo_evidence_review(claim, context) -> RuleResult:
    """R-011: High-value baggage claim with submitted photo evidence requiring forensic review -> BLOCK.

    Damaged/lost-baggage claims supported by a photo are the prime vector for staged-damage
    and value-padding fraud. Any baggage claim that carries an evidence image (flagged via
    photo_evidence on the claim) is held for forensic photo review before payout.
    """
    if claim.claim_type != "baggage_loss":
        return RuleResult("R-011", "Baggage Photo Evidence Review", "BLOCK", False, "Not a baggage claim")
    has_photo = bool(getattr(claim, "photo_evidence", False))
    triggered = has_photo
    return RuleResult(
        rule_id="R-011", rule_name="Baggage Photo Evidence Review",
        severity="BLOCK", triggered=triggered,
        explanation="Photo evidence submitted — held for forensic image review (staged-damage / value-padding risk)" if triggered else "No photo evidence on file",
        details={"photo_evidence": has_photo},
    )


def r010_unverified_provider(claim, context) -> RuleResult:
    """R-010: Medical claim from provider not in verified network -> BLOCK"""
    if claim.claim_type != "medical_emergency":
        return RuleResult("R-010", "Unverified Medical Provider", "BLOCK", False, "Not a medical claim")
    if not claim.provider_id:
        return RuleResult("R-010", "Unverified Medical Provider", "BLOCK", True,
                          "No provider ID on medical claim",
                          details={"provider_id": None, "verified": False})
    provider = _get_provider(context, claim.provider_id)
    if not provider:
        return RuleResult("R-010", "Unverified Medical Provider", "BLOCK", True,
                          "Provider ID not found in database",
                          details={"provider_id": claim.provider_id, "verified": False})
    triggered = not provider.verified
    return RuleResult(
        rule_id="R-010", rule_name="Unverified Medical Provider",
        severity="BLOCK", triggered=triggered,
        explanation=f"Provider '{provider.name}' is NOT in verified network" if triggered else f"Provider '{provider.name}' is verified",
        details={"provider_id": claim.provider_id, "provider_name": provider.name, "verified": provider.verified},
    )


_COMPLEXITY_THRESHOLDS = {
    "medical_emergency": 5_000,
    "trip_cancellation": 25_000,
    "trip_interruption": 25_000,
    "baggage_loss":       5_000,
    "travel_delay":       1_000,
}


def r012_claim_amount_threshold(claim, context) -> RuleResult:
    """R-012: Claim amount exceeds section-specific threshold -> COMPLEX"""
    threshold = _COMPLEXITY_THRESHOLDS.get(claim.claim_type)
    if threshold is None:
        return RuleResult("R-012", "Claimed amount is over threshold", "COMPLEX", False, "No threshold defined for this claim type")
    triggered = claim.claim_amount > threshold
    return RuleResult(
        rule_id="R-012",
        rule_name="Claimed amount is over threshold",
        severity="COMPLEX",
        triggered=triggered,
        explanation=f"Claimed ${claim.claim_amount:,.2f} exceeds complexity threshold ${threshold:,}" if triggered else f"Claimed ${claim.claim_amount:,.2f} is within threshold ${threshold:,}",
        details={"claim_amount": claim.claim_amount, "threshold": threshold, "claim_type": claim.claim_type},
    )


_MEDEVAC_SUBTYPES = {
    "emergency_medical_evacuation", "medical_evacuation", "evacuation_and_repatriation",
    "repatriation_of_remains", "security_evacuation", "political_evacuation",
    "natural_disaster_evacuation", "emergency_reunification", "return_of_minor_children",
}


def r013_medical_evacuation(claim, context) -> RuleResult:
    """R-013: Claim involves medical evacuation -> COMPLEX"""
    is_medevac = bool(getattr(claim, "is_medical_evacuation", False))
    if not is_medevac:
        subtype = str(getattr(claim, "claim_subtype", "") or "").lower().replace(" ", "_")
        is_medevac = subtype in _MEDEVAC_SUBTYPES or "evacuation" in subtype
    return RuleResult(
        rule_id="R-013",
        rule_name="Claim is a Medical Evacuation",
        severity="COMPLEX",
        triggered=is_medevac,
        explanation="Claim involves medical evacuation — automatically complex" if is_medevac else "Not a medical evacuation claim",
        details={"is_medical_evacuation": is_medevac},
    )


# ── Rules Engine Runner ──────────────────────────────────────────────────────

ALL_TRAVEL_RULES = [
    r001_pre_existing_condition,
    r002_no_booking_confirmation,
    r003_duplicate_claim,
    r004_baggage_amount_outlier,
    r005_destination_fraud_ring,
    r006_policy_after_event,
    r007_serial_claimer,
    r008_airline_refund_double_dip,
    r009_flight_on_time,
    r010_unverified_provider,
    r011_baggage_photo_evidence_review,
    r012_claim_amount_threshold,
    r013_medical_evacuation,
]


def run_travel_rules_engine(claim, context: Dict) -> List[RuleResult]:
    """Run all 13 travel rules against a single claim."""
    results = []
    for rule_fn in ALL_TRAVEL_RULES:
        try:
            result = rule_fn(claim, context)
            results.append(result)
        except Exception as e:
            results.append(RuleResult(
                rule_id="ERR", rule_name=rule_fn.__name__,
                severity="INFO", triggered=False,
                explanation=f"Rule error: {str(e)[:100]}",
            ))
    return results
