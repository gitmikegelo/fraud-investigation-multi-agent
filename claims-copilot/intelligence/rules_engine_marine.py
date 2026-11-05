"""Deterministic rules (R-001 to R-012) for Marine Cargo claims."""

from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime

from data.generate_marine import COMMODITIES


@dataclass
class RuleResult:
    rule_id: str
    rule_name: str
    severity: str  # BLOCK, FLAG, INFO
    triggered: bool
    explanation: str
    details: Dict = field(default_factory=dict)


# ICC 2009 transit clause 8.1.4: cover ends 60 days after completion of discharge
# (if not delivered to the final warehouse earlier).
ICC_POST_DISCHARGE_DAYS = 60
# Hague-Visby Art. III r.6: notice of loss to the carrier within 3 days where damage is not apparent.
CARRIER_NOTICE_DAYS = 3
SURVEY_LATE_DAYS = 7
OVERVALUATION_RATIO = 1.4
WEIGHT_TOLERANCE = 0.15
MAJOR_LOSS_PCT = 0.40
REPEAT_CLAIM_RATE = 0.05
SETTLING_AUTHORITY_USD = 50_000
EXCLUDED_CAUSE_KEYWORDS = ("insufficient packing", "inherent vice", "delay", "ordinary leakage",
                           "wear and tear", "prolonged open-air storage")


# ── Context accessors ─────────────────────────────────────────────────────────

def _find(items, attr, value):
    return next((x for x in items if getattr(x, attr) == value), None)


def _get_consignee(ctx, cid):
    return _find(ctx.get("consignees", []), "party_id", cid)


def _get_shipment(ctx, sid):
    return _find(ctx.get("shipments", []), "shipment_id", sid)


def _get_policy(ctx, pid):
    return _find(ctx.get("policies", []), "policy_id", pid)


def _get_survey(ctx, claim):
    return _find(ctx.get("surveys", []), "survey_id", claim.survey_id) if claim.survey_id else None


def _get_surveyor(ctx, sid):
    return _find(ctx.get("surveyors", []), "surveyor_id", sid) if sid else None


def _get_forwarder(ctx, fid):
    return _find(ctx.get("forwarders", []), "forwarder_id", fid) if fid else None


def _commodity_for(shipment):
    return next((c for c in COMMODITIES.values() if c["name"] == shipment.commodity), None)


def _days(a: str, b: str) -> int:
    return (datetime.strptime(b, "%Y-%m-%d") - datetime.strptime(a, "%Y-%m-%d")).days


def _not_found(rid, name, sev, what):
    return RuleResult(rid, name, sev, False, f"{what} not found")


# ── Rule Definitions ──────────────────────────────────────────────────────────

def r001_loss_outside_transit(claim, ctx) -> RuleResult:
    """R-001: Loss discovered outside the insured transit (ICC cl. 8) → BLOCK"""
    shp = _get_shipment(ctx, claim.shipment_id)
    if not shp or not shp.discharge_date or not claim.date_of_loss:
        return _not_found("R-001", "Loss Outside Transit Period", "BLOCK", "Shipment")
    days_after = _days(shp.discharge_date, claim.date_of_loss)
    before_sob = _days(shp.shipped_on_board, claim.date_of_loss) < -30
    triggered = days_after > ICC_POST_DISCHARGE_DAYS or before_sob
    return RuleResult(
        "R-001", "Loss Outside Transit Period", "BLOCK", triggered,
        (f"Loss discovered {days_after} days after discharge — beyond the ICC cl. 8.1.4 "
         f"{ICC_POST_DISCHARGE_DAYS}-day limit" if triggered
         else f"Loss discovered {days_after} days after discharge — within transit cover"),
        {"days_after_discharge": days_after, "limit_days": ICC_POST_DISCHARGE_DAYS},
    )


def r002_overvaluation(claim, ctx) -> RuleResult:
    """R-002: Invoiced unit price far above the commodity market benchmark → FLAG"""
    shp = _get_shipment(ctx, claim.shipment_id)
    com = _commodity_for(shp) if shp else None
    if not com:
        return _not_found("R-002", "Declared Value vs Market Benchmark", "FLAG", "Commodity benchmark")
    lo, hi = com["price"]
    mid = (lo + hi) / 2
    ratio = shp.unit_price / mid if mid else 0
    triggered = ratio > OVERVALUATION_RATIO
    unit = com["unit"].replace("m2", "m²")
    return RuleResult(
        "R-002", "Declared Value vs Market Benchmark", "FLAG", triggered,
        (f"Invoiced ${shp.unit_price:,.2f}/{unit} is {ratio:.2f}x the market benchmark "
         f"(${lo:,.0f}–${hi:,.0f}/{unit})" if triggered
         else f"Invoiced ${shp.unit_price:,.2f}/{unit} within market range (${lo:,.0f}–${hi:,.0f})"),
        {"unit_price": shp.unit_price, "benchmark_low": lo, "benchmark_high": hi, "ratio": round(ratio, 2)},
    )


def r003_weight_discrepancy(claim, ctx) -> RuleResult:
    """R-003: VGM cargo weight contradicts the invoiced/B/L weight → BLOCK"""
    shp = _get_shipment(ctx, claim.shipment_id)
    if not shp or not shp.gross_weight_bl_kg:
        return _not_found("R-003", "VGM vs Declared Weight", "BLOCK", "Shipment weights")
    declared = shp.gross_weight_bl_kg
    vgm_cargo = shp.vgm_cargo_kg
    gap = (declared - vgm_cargo) / declared
    triggered = abs(gap) > WEIGHT_TOLERANCE
    return RuleResult(
        "R-003", "VGM vs Declared Weight", "BLOCK", triggered,
        (f"VGM shows {vgm_cargo:,} kg of cargo vs {declared:,} kg declared on B/L and packing list "
         f"({gap:.0%} short) — invoiced quantity cannot have been loaded" if triggered
         else f"VGM cargo weight {vgm_cargo:,} kg consistent with B/L {declared:,} kg"),
        {"bl_weight_kg": declared, "vgm_cargo_kg": vgm_cargo, "gap_pct": round(gap * 100, 1)},
    )


def r004_surveyor_conflict(claim, ctx) -> RuleResult:
    """R-004: Surveyor on watchlist or sharing directors/address with the claimant → BLOCK"""
    svy = _get_surveyor(ctx, claim.surveyor_id)
    cne = _get_consignee(ctx, claim.consignee_id)
    if not svy or not cne:
        return _not_found("R-004", "Surveyor Independence", "BLOCK", "Surveyor")
    shared_dirs = set(svy.director_ids) & set(cne.director_ids)
    shared_addr = bool(svy.registered_address) and svy.registered_address == cne.registered_address
    triggered = svy.on_watchlist or bool(shared_dirs) or shared_addr
    reasons = []
    if svy.on_watchlist:
        reasons.append("on the surveyor watchlist")
    if shared_dirs:
        reasons.append("shares a director with the claimant")
    if shared_addr:
        reasons.append("shares the claimant's registered address")
    return RuleResult(
        "R-004", "Surveyor Independence", "BLOCK", triggered,
        (f"Surveyor '{svy.name}' " + ", ".join(reasons) if triggered
         else f"Surveyor '{svy.name}' — independent{', insurer panel' if svy.insurer_panel else ''}"),
        {"surveyor": svy.name, "watchlist": svy.on_watchlist, "shared_directors": sorted(shared_dirs),
         "shared_address": shared_addr},
    )


def r005_survey_quality(claim, ctx) -> RuleResult:
    """R-005: Survey late, appointed by the assured, or not joint with the carrier → FLAG"""
    svr = _get_survey(ctx, claim)
    shp = _get_shipment(ctx, claim.shipment_id)
    if not svr or not shp:
        return _not_found("R-005", "Survey Timing & Appointment", "FLAG", "Survey report")
    days_after = _days(shp.discharge_date, svr.survey_date)
    issues = []
    if days_after > SURVEY_LATE_DAYS:
        issues.append(f"survey {days_after} days after discharge")
    if svr.appointed_by != "insurer":
        issues.append("surveyor appointed by the assured, not the insurer")
    if not svr.joint_with_carrier and claim.claim_type in ("breakage", "shortage", "theft_pilferage"):
        issues.append("no joint survey with the carrier")
    triggered = len(issues) >= 2
    return RuleResult(
        "R-005", "Survey Timing & Appointment", "FLAG", triggered,
        ("Survey not independent or timely: " + "; ".join(issues) if triggered
         else f"Survey {days_after} days after discharge by {svr.appointed_by}-appointed surveyor"),
        {"days_after_discharge": days_after, "appointed_by": svr.appointed_by,
         "joint_with_carrier": svr.joint_with_carrier},
    )


def r006_no_carrier_notice(claim, ctx) -> RuleResult:
    """R-006: No timely notice of claim to the carrier — recovery rights prejudiced (ICC cl. 16) → FLAG"""
    if claim.notice_to_carrier_date is None:
        return RuleResult(
            "R-006", "Notice of Claim to Carrier", "FLAG", True,
            "No notice of claim served on the carrier — recovery rights not preserved (ICC cl. 16 duty of assured)",
            {"notice_to_carrier": None})
    late = _days(claim.date_of_loss, claim.notice_to_carrier_date)
    triggered = late > CARRIER_NOTICE_DAYS
    return RuleResult(
        "R-006", "Notice of Claim to Carrier", "FLAG", triggered,
        (f"Carrier notified {late} days after discovery (Hague-Visby: 3 days)" if triggered
         else f"Carrier notified {late} day(s) after discovery — recovery preserved"),
        {"days_to_notice": late})


def r007_repeat_claimant(claim, ctx) -> RuleResult:
    """R-007: Claimant has 3+ claims in 24 months AND a claim rate above 5% of shipments → FLAG"""
    cne = _get_consignee(ctx, claim.consignee_id)
    if not cne:
        return _not_found("R-007", "Repeat Claimant", "FLAG", "Consignee")
    current = sum(1 for c in ctx.get("claims", []) if c.consignee_id == claim.consignee_id)
    total = cne.claim_history_count + current     # prior closed claims + open claims in the queue
    shipments_24m = max(1, cne.shipments_per_year * 2)
    rate = total / shipments_24m
    triggered = total >= 3 and rate >= REPEAT_CLAIM_RATE
    return RuleResult(
        "R-007", "Repeat Claimant", "FLAG", triggered,
        (f"{total} claims in 24 months on ~{shipments_24m} shipments ({rate:.1%} claim rate)" if triggered
         else f"{total} claim(s) in 24 months on ~{shipments_24m} shipments ({rate:.1%} — normal for volume)"),
        {"claims_24m": total, "shipments_24m": shipments_24m, "claim_rate": round(rate, 4)})


def r008_clean_delivery(claim, ctx) -> RuleResult:
    """R-008: Clean EIR and intact seals at discharge, yet a major physical loss is claimed → FLAG"""
    shp = _get_shipment(ctx, claim.shipment_id)
    pol = _get_policy(ctx, claim.policy_id)
    if not shp or not pol:
        return _not_found("R-008", "Clean Delivery vs Claimed Loss", "FLAG", "Shipment")
    clean = shp.eir_remarks_discharge.lower().startswith("clean") and shp.seals_match
    loss_pct = claim.claim_amount / pol.insured_value if pol.insured_value else 0
    triggered = clean and loss_pct >= 0.5 and claim.claim_type in ("breakage", "shortage", "theft_pilferage")
    return RuleResult(
        "R-008", "Clean Delivery vs Claimed Loss", "FLAG", triggered,
        (f"EIR clean and seals intact at gate-out, yet {loss_pct:.0%} of insured value claimed" if triggered
         else "Delivery condition consistent with the claimed loss"),
        {"eir": shp.eir_remarks_discharge, "seals_match": shp.seals_match, "loss_pct": round(loss_pct * 100, 1)})


def r009_duplicate_photo(claim, ctx) -> RuleResult:
    """R-009: Survey photo is a near-duplicate of an image filed on another claim → BLOCK"""
    matches = ctx.get("duplicate_images", {}).get(claim.claim_id, [])
    triggered = bool(matches)
    other = matches[0]["other_claim_id"] if matches else None
    return RuleResult(
        "R-009", "Reused Evidence Photo", "BLOCK", triggered,
        (f"Survey photo {matches[0]['image']} matches {matches[0]['other_image']} filed on {other} "
         f"(perceptual-hash distance {matches[0]['distance']}/64)" if triggered
         else "No evidence images reused from other claims"),
        {"matches": matches})


def r010_excluded_cause(claim, ctx) -> RuleResult:
    """R-010: Surveyed cause of loss falls under an ICC exclusion (cl. 4) → BLOCK (hold for coverage decision)"""
    svr = _get_survey(ctx, claim)
    cause = (svr.cause_of_loss if svr else "").lower()
    hit = next((k for k in EXCLUDED_CAUSE_KEYWORDS if k in cause), None)
    return RuleResult(
        "R-010", "ICC Exclusion Indicated", "BLOCK", bool(hit),
        (f"Surveyed cause '{svr.cause_of_loss}' indicates an ICC cl. 4 exclusion" if hit
         else "Surveyed cause is an insured peril"),
        {"cause_of_loss": svr.cause_of_loss if svr else None})


def r011_recovery_opportunity(claim, ctx) -> RuleResult:
    """R-011: Carrier exception at discharge + timely notice → recovery (subrogation) opportunity → INFO"""
    shp = _get_shipment(ctx, claim.shipment_id)
    if not shp:
        return _not_found("R-011", "Recovery Opportunity", "INFO", "Shipment")
    exception = shp.eir_remarks_discharge.upper().startswith("EXCEPTION") or not shp.seals_match
    notified = claim.notice_to_carrier_date is not None and _days(claim.date_of_loss, claim.notice_to_carrier_date) <= CARRIER_NOTICE_DAYS
    triggered = exception and notified
    return RuleResult(
        "R-011", "Recovery Opportunity", "INFO", triggered,
        (f"Carrier exception recorded at discharge and notice served in time — pursue recovery from {shp.carrier}"
         if triggered else "No carrier exception recorded at discharge"),
        {"eir": shp.eir_remarks_discharge, "carrier": shp.carrier})


def r012_major_loss(claim, ctx) -> RuleResult:
    """R-012: Major loss — large share of insured value and above local settling authority → FLAG"""
    pol = _get_policy(ctx, claim.policy_id)
    if not pol or not pol.insured_value:
        return _not_found("R-012", "Major Loss Referral", "FLAG", "Policy")
    loss_pct = claim.claim_amount / pol.insured_value
    triggered = loss_pct >= MAJOR_LOSS_PCT and claim.claim_amount >= SETTLING_AUTHORITY_USD
    return RuleResult(
        "R-012", "Major Loss Referral", "FLAG", triggered,
        (f"${claim.claim_amount:,.0f} ({loss_pct:.0%} of insured value) exceeds the "
         f"${SETTLING_AUTHORITY_USD:,.0f} local settling authority — refer to marine claims" if triggered
         else f"Within local settling authority (${SETTLING_AUTHORITY_USD:,.0f})"),
        {"loss_pct": round(loss_pct * 100, 1), "authority": SETTLING_AUTHORITY_USD})


# ── Rules Engine Runner ───────────────────────────────────────────────────────

ALL_MARINE_RULES = [
    r001_loss_outside_transit,
    r002_overvaluation,
    r003_weight_discrepancy,
    r004_surveyor_conflict,
    r005_survey_quality,
    r006_no_carrier_notice,
    r007_repeat_claimant,
    r008_clean_delivery,
    r009_duplicate_photo,
    r010_excluded_cause,
    r011_recovery_opportunity,
    r012_major_loss,
]


def run_marine_rules_engine(claim, context: Dict) -> List[RuleResult]:
    """Run all marine cargo rules against a single claim."""
    results = []
    for rule_fn in ALL_MARINE_RULES:
        try:
            results.append(rule_fn(claim, context))
        except Exception as e:
            results.append(RuleResult(
                rule_id="ERR", rule_name=rule_fn.__name__,
                severity="INFO", triggered=False,
                explanation=f"Rule error: {str(e)[:100]}",
            ))
    return results
