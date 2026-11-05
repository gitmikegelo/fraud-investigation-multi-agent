"""7-step claims checklist for Marine Cargo claims."""

from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime

from data.generate_marine import COMMODITIES


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
    (2, "Shipping Documents"),
    (3, "Transit & Coverage Period"),
    (4, "Document AI Review"),
    (5, "Survey & Surveyor"),
    (6, "ICC Coverage & Exclusions"),
    (7, "Final Determination"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find(ctx, key, attr, value):
    return next((x for x in ctx.get(key, []) if getattr(x, attr) == value), None) if value else None


def _get_claim(ctx, claim_id):
    return _find(ctx, "claims", "claim_id", claim_id)


def _rules(ctx, claim_id):
    return ctx.get("claim_rules", {}).get(claim_id, [])


def _rule(ctx, claim_id, rule_id):
    return next((r for r in _rules(ctx, claim_id) if r.rule_id == rule_id), None)


def _rule_line(r) -> str:
    return f"{r.severity} {r.rule_id}: {r.explanation}"


def _days(a: str, b: str) -> int:
    return (datetime.strptime(b, "%Y-%m-%d") - datetime.strptime(a, "%Y-%m-%d")).days


def _money(x: float) -> str:
    return f"${x:,.2f}"


def _status(ok: bool, blocked: bool = False) -> str:
    if blocked:
        return "fail"
    return "pass" if ok else "needs_review"


# ── Step Implementations ──────────────────────────────────────────────────────

def _step_initial_review(claim, ctx) -> ChecklistStepResult:
    """Step 1: Required fields present; claim notified promptly."""
    findings = []
    ok = True
    for attr, label in (("consignee_id", "Claimant"), ("shipment_id", "Shipment / B/L"),
                        ("policy_id", "Insurance certificate"), ("date_of_loss", "Date loss discovered")):
        if not getattr(claim, attr, None):
            findings.append(f"MISSING: {label}")
            ok = False
    if claim.claim_amount <= 0:
        findings.append("WARNING: Claim amount is zero or negative")
        ok = False

    cne = _find(ctx, "consignees", "party_id", claim.consignee_id)
    if cne:
        findings.append(f"Claimant: {cne.name} ({cne.city}) — ~{cne.shipments_per_year} shipments/yr")
    if claim.date_of_loss and claim.notice_to_insurer_date:
        lag = _days(claim.date_of_loss, claim.notice_to_insurer_date)
        if lag > 3:
            findings.append(f"WARNING: Insurer notified {lag} days after discovery — ICC 'Important' clause requires immediate notice")
            ok = False
        else:
            findings.append(f"Insurer notified {lag} day(s) after discovery")

    r007 = _rule(ctx, claim.claim_id, "R-007")
    if r007:
        findings.append(_rule_line(r007) if r007.triggered else f"Claim frequency: {r007.explanation}")
        if r007.triggered:
            ok = False
    r012 = _rule(ctx, claim.claim_id, "R-012")
    if r012 and r012.triggered:
        findings.append(_rule_line(r012))

    if ok:
        findings.insert(0, "All required fields present")
    return ChecklistStepResult(1, "Initial Review", _status(ok), ok, findings)


def _step_shipping_documents(claim, ctx) -> ChecklistStepResult:
    """Step 2: Cross-check B/L, commercial invoice, packing list and VGM."""
    findings = []
    shp = _find(ctx, "shipments", "shipment_id", claim.shipment_id)
    if not shp:
        return ChecklistStepResult(2, "Shipping Documents", "fail", False, ["Shipment record not found"])

    unit = shp.unit.replace("m2", "m²")
    findings.append(f"B/L {shp.bl_number} — {shp.carrier}, {shp.vessel} voy. {shp.voyage}, "
                    f"{shp.port_of_loading} → {shp.port_of_discharge}, shipped on board {shp.shipped_on_board}")
    findings.append(f"B/L clause: {shp.bl_clause}")
    findings.append(f"Invoice {shp.invoice_no}: {shp.quantity:,.0f} {unit} × ${shp.unit_price:,.2f} = "
                    f"{_money(shp.invoice_value)} ({shp.incoterm})")
    boxes = ", ".join(f"{c.container_no} seal {c.seal_no_loading}" for c in shp.containers[:3])
    more = f" (+{len(shp.containers) - 3} more)" if len(shp.containers) > 3 else ""
    findings.append(f"{len(shp.containers)} container(s): {boxes}{more}")

    blocked = False
    ok = True
    for rid in ("R-003", "R-002"):
        r = _rule(ctx, claim.claim_id, rid)
        if not r:
            continue
        if r.triggered:
            findings.append(_rule_line(r))
            ok = False
            blocked = blocked or r.severity == "BLOCK"
        else:
            findings.append(r.explanation)

    details = {
        "bl_weight_kg": shp.gross_weight_bl_kg,
        "vgm_gross_kg": shp.total_vgm_kg,
        "vgm_cargo_kg": shp.vgm_cargo_kg,
        "tare_kg": shp.total_tare_kg,
    }
    com = next((c for c in COMMODITIES.values() if c["name"] == shp.commodity), None)
    if com and com["unit"] != "t":
        implied_qty = shp.vgm_cargo_kg / com["kg_per_unit"]
        details["vgm_implied_quantity"] = round(implied_qty)
        r003 = _rule(ctx, claim.claim_id, "R-003")
        if r003 and r003.triggered:
            findings.append(f"VGM weight supports at most ~{implied_qty:,.0f} {unit} loaded vs "
                            f"{shp.quantity:,.0f} {unit} invoiced")
    return ChecklistStepResult(2, "Shipping Documents", _status(ok, blocked), ok, findings, details)


def _step_transit_period(claim, ctx) -> ChecklistStepResult:
    """Step 3: Loss within the insured transit (ICC cl. 8) and the open cover period."""
    findings = []
    ok = True
    shp = _find(ctx, "shipments", "shipment_id", claim.shipment_id)
    pol = _find(ctx, "policies", "policy_id", claim.policy_id)
    if not shp or not pol:
        return ChecklistStepResult(3, "Transit & Coverage Period", "fail", False, ["Shipment or certificate not found"])

    findings.append(f"Certificate {pol.policy_id} under open cover {pol.open_cover_no} "
                    f"({pol.effective_date} → {pol.expiration_date})")
    findings.append(f"Shipped on board {shp.shipped_on_board} · discharged {shp.discharge_date} · "
                    f"gate-out {shp.gate_out_date} · loss discovered {claim.date_of_loss}")
    r001 = _rule(ctx, claim.claim_id, "R-001")
    blocked = bool(r001 and r001.triggered)
    if r001:
        findings.append(_rule_line(r001) if blocked else r001.explanation)
    if pol.effective_date <= shp.shipped_on_board <= pol.expiration_date:
        findings.append("Shipment declared within the open cover period")
    else:
        findings.append("FAIL: Shipment date outside the open cover period")
        ok = False
    return ChecklistStepResult(3, "Transit & Coverage Period", _status(ok and not blocked, blocked),
                               ok and not blocked, findings)


def _step_document_ai(claim, ctx) -> ChecklistStepResult:
    """Step 4: Vision forensics on evidence images + reused-photo check + rules summary."""
    findings = []
    doc_results = ctx.get("claim_doc_results", {}).get(claim.claim_id, [])
    has_images = ctx.get("has_claim_images", False)
    details = {}
    if has_images:
        details = {"has_document_image": True, "image_url": f"/api/claims/{claim.claim_id}/document-image"}

    vision_ok = True
    if doc_results:
        failed = [d for d in doc_results if not d.passed]
        if not failed:
            findings.append(f"Evidence images passed all {len(doc_results)} forensic checks")
        for d in sorted(failed, key=lambda d: d.severity != "CRITICAL"):
            findings.append(f"{d.severity} [{d.check_id}] {d.check_name}: {d.explanation}")
            vision_ok = False
        assessment = next((d.details.get("overall_assessment") for d in doc_results
                           if isinstance(getattr(d, "details", None), dict) and d.details.get("overall_assessment")), "")
        if assessment:
            findings.append(f"Vision assessment: {assessment}")
    elif has_images:
        findings.append("Evidence images on file — vision analysis unavailable, manual review required")
        vision_ok = False
    else:
        findings.append("No evidence images on file")

    r009 = _rule(ctx, claim.claim_id, "R-009")
    blocked = bool(r009 and r009.triggered)
    if blocked:
        findings.insert(0, _rule_line(r009))

    risk = ctx.get("claim_risk_scores", {}).get(claim.claim_id)
    score = risk.total_score if risk else 0
    findings.append(f"Risk score: {score:.1f} ({risk.tier if risk else 'UNKNOWN'})")
    details["risk_score"] = score

    if score < 30 and vision_ok and not blocked:
        return ChecklistStepResult(4, "Document AI Review", "pass", True, findings, {**details, "auto_passed": True})
    return ChecklistStepResult(4, "Document AI Review", "fail" if blocked else "needs_review", False, findings, details)


def _step_survey(claim, ctx) -> ChecklistStepResult:
    """Step 5: Survey independence, timing and surveyor relationships."""
    findings = []
    svr = _find(ctx, "surveys", "survey_id", claim.survey_id)
    svy = _find(ctx, "surveyors", "surveyor_id", claim.surveyor_id)
    if not svr or not svy:
        return ChecklistStepResult(5, "Survey & Surveyor", "needs_review", False, ["WARNING: No survey report on file"])

    findings.append(f"Survey {svr.report_no} by {svy.name} ({'insurer panel' if svy.insurer_panel else 'not on insurer panel'}), "
                    f"appointed by {svr.appointed_by}, {svr.survey_date} at {svr.survey_location}")
    findings.append(f"Surveyed cause: {svr.cause_of_loss} · damage {svr.damage_pct:.0f}% · "
                    f"{'joint survey with carrier' if svr.joint_with_carrier else 'no joint survey with carrier'}")

    ok, blocked = True, False
    for rid in ("R-004", "R-005"):
        r = _rule(ctx, claim.claim_id, rid)
        if r and r.triggered:
            findings.append(_rule_line(r))
            ok = False
            blocked = blocked or r.severity == "BLOCK"

    priors = [p for p in ctx.get("prior_claims", []) if p.surveyor_id == svy.surveyor_id]
    if priors and not svy.insurer_panel:
        consignees = {p.consignee_id for p in priors}
        total = sum(p.amount_paid for p in priors)
        findings.append(f"Surveyor history: {len(priors)} prior paid claims across {len(consignees)} "
                        f"consignee(s), {_money(total)} total")
    return ChecklistStepResult(5, "Survey & Surveyor", _status(ok, blocked), ok, findings)


def _step_icc_coverage(claim, ctx) -> ChecklistStepResult:
    """Step 6: Peril covered by the ICC clause; exclusions; sum insured; recovery rights."""
    findings = []
    ok, blocked = True, False
    pol = _find(ctx, "policies", "policy_id", claim.policy_id)
    shp = _find(ctx, "shipments", "shipment_id", claim.shipment_id)
    if not pol:
        return ChecklistStepResult(6, "ICC Coverage & Exclusions", "fail", False, ["Certificate not found"])

    findings.append(f"{pol.clause}, insured value {_money(pol.insured_value)} ({pol.basis_of_valuation}), "
                    f"excess {_money(pol.excess)}")
    if "(C)" in pol.clause and claim.claim_type in ("breakage", "wet_damage", "contamination", "theft_pilferage"):
        findings.append(f"FAIL: {claim.claim_type.replace('_', ' ')} is not a named peril under {pol.clause} "
                        "(major casualties only) — cover requires ICC (A)")
        ok = False
    else:
        findings.append(f"Loss type '{claim.claim_type.replace('_', ' ')}' is within the scope of {pol.clause} (all risks, subject to exclusions)")

    if claim.claim_amount > pol.insured_value:
        findings.append(f"EXCEED: Claim {_money(claim.claim_amount)} exceeds insured value {_money(pol.insured_value)}")
        ok = False

    for rid in ("R-010", "R-008", "R-006"):
        r = _rule(ctx, claim.claim_id, rid)
        if r and r.triggered:
            findings.append(_rule_line(r))
            ok = False
            blocked = blocked or r.severity == "BLOCK"
    r011 = _rule(ctx, claim.claim_id, "R-011")
    if r011 and r011.triggered:
        findings.append(f"RECOVERY: {r011.explanation}")
    if shp and not shp.eir_remarks_discharge.lower().startswith("clean"):
        findings.append(f"EIR at discharge: {shp.eir_remarks_discharge}")
    return ChecklistStepResult(6, "ICC Coverage & Exclusions", _status(ok, blocked), ok, findings)


def _step_final_determination(claim, ctx) -> ChecklistStepResult:
    """Step 7: Always manual — handler approves / declines / refers."""
    return ChecklistStepResult(
        7, "Final Determination", "needs_review", False,
        ["Awaiting claims handler determination: APPROVE / DECLINE / REFER FOR INVESTIGATION"],
        {"requires_manual_review": True},
    )


# ── Public API ────────────────────────────────────────────────────────────────

_DISPATCH = {
    1: _step_initial_review,
    2: _step_shipping_documents,
    3: _step_transit_period,
    4: _step_document_ai,
    5: _step_survey,
    6: _step_icc_coverage,
    7: _step_final_determination,
}


def run_checklist_step(step_number: int, claim_id: str, context: Dict) -> ChecklistStepResult:
    """Run a single checklist step for a marine cargo claim."""
    claim = _get_claim(context, claim_id)
    if not claim:
        return ChecklistStepResult(step_number, CHECKLIST_STEPS[step_number - 1][1],
                                   "error", False, ["Claim not found"])
    fn = _DISPATCH.get(step_number)
    if not fn:
        return ChecklistStepResult(step_number, "Unknown", "error", False, ["Invalid step number"])
    return fn(claim, context)


def run_full_checklist(claim_id: str, context: Dict) -> List[ChecklistStepResult]:
    """Run all 7 checklist steps for a marine cargo claim."""
    return [run_checklist_step(i, claim_id, context) for i in range(1, 8)]
