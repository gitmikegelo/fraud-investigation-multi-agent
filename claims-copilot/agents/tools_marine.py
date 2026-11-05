"""Marine cargo claim tools for the Marine Cargo claims handler copilot.

Every tool is a LangChain @tool that returns a dict and never raises — failures come back
as {"error": ...} so a live chat session cannot crash on a bad lookup.
"""

import functools
from typing import Dict, List, Annotated, Optional
from datetime import datetime, timedelta

from langchain_core.tools import tool

try:
    from data.generate_marine import COMMODITIES
except Exception:  # pragma: no cover — keeps the module importable in isolation
    COMMODITIES = {}

_context = None  # DataContext injected at startup


def set_context(ctx):
    global _context
    _context = ctx


def _tool_log(name: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"    [{ts}]   tool:{name} -> {msg}", flush=True)


def _safe(fn):
    """Guarantee a dict result: no context → error dict; any exception → error dict."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if _context is None:
            return {"error": "Claims data not loaded (context not initialised)"}
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            try:
                _tool_log(fn.__name__, f"ERROR: {str(e)[:150]}")
            except Exception:
                pass
            return {"error": f"{fn.__name__} failed: {str(e)[:200]}"}
    return wrapper


# ── Constants ────────────────────────────────────────────────────────────────

ICC_POST_DISCHARGE_DAYS = 60          # ICC 2009 cl. 8.1.4 long-stop after discharge
CARRIER_NOTICE_DAYS = 3               # Hague-Visby Art. III r.6 (damage not apparent)
SURVEY_LATE_DAYS = 7                  # internal guideline MC-GL-01
VALUE_FLAG_RATIO = 1.4                # internal guideline MC-GL-02
WEIGHT_TOLERANCE = 0.15
# Hague-Visby Art. IV r.5 limitation: 666.67 SDR per package or 2 SDR per kg, whichever is higher.
HVR_SDR_PER_PACKAGE = 666.67
HVR_SDR_PER_KG = 2.0
SDR_USD_INDICATIVE = 1.35             # indicative conversion only — confirm on the day

REQUIRED_DOCS = ["bill_of_lading", "commercial_invoice", "packing_list", "survey_report", "eir"]
DOC_LABELS = {
    "bill_of_lading": "Bill of lading", "commercial_invoice": "Commercial invoice",
    "packing_list": "Packing list", "survey_report": "Survey report",
    "eir": "Equipment Interchange Receipt (EIR)", "survey_photo": "Survey photographs",
}

# Plausible innocent explanation for each rule — always shown next to the indicator.
INNOCENT_EXPLANATIONS = {
    "R-001": "The loss may be genuine but found late (cargo kept in original packing). This is a coverage "
             "question under the transit clause, not a fraud indicator.",
    "R-002": "A special specification (e.g. coated, laminated or tempered product), a small-lot premium or "
             "pricing on a delivered basis can put the unit price above the market benchmark.",
    "R-003": "A VGM obtained by calculation (SOLAS Method 2) can contain errors, and packaging or rack weights "
             "are sometimes omitted. The terminal weighbridge record will confirm or clear this.",
    "R-004": "Shared serviced-office addresses and family-run companies are common in smaller markets. "
             "Company registry records will confirm whether the relationship is real.",
    "R-005": "Customs clearance or surveyor availability can delay a survey, and the assured may have appointed "
             "a local surveyor in good faith if the insurer's claims agent was not notified.",
    "R-006": "The consignee may not have known the notice requirement, or the broker did not advise it. "
             "This affects recovery from the carrier rather than the validity of the claim.",
    "R-007": "Fragile or moisture-sensitive commodities have a higher claim frequency. Compare with importers "
             "of the same commodity before drawing conclusions.",
    "R-008": "Some damage (e.g. breakage inside intact racks or crates) is not visible at gate-out and is only "
             "found on unstuffing.",
    "R-009": "A surveyor may reuse a reference image, or a filing error may attach the wrong photo. Request the "
             "original image files with metadata.",
    "R-010": "The physical loss is probably genuine; an exclusion is a coverage decision. Confirm who packed or "
             "stowed the goods and whether the surveyed cause is the proximate cause.",
    "R-011": "Positive indicator: evidence supports a recovery against the carrier.",
    "R-012": "Large losses are frequently genuine. Referral is about settling authority, not suspicion.",
}


# ── Accessors ────────────────────────────────────────────────────────────────

def _get_claim(claim_id: str):
    return _context.get_claim(claim_id)


def _parse(d: Optional[str]) -> Optional[datetime]:
    try:
        return datetime.strptime(d, "%Y-%m-%d") if d else None
    except (TypeError, ValueError):
        return None


def _days(a: Optional[str], b: Optional[str]) -> Optional[int]:
    da, db = _parse(a), _parse(b)
    return (db - da).days if da and db else None


def _money(x) -> str:
    try:
        return f"${float(x):,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def _unit(u: str) -> str:
    return (u or "").replace("m2", "m²")


def _commodity_for(shipment):
    if not shipment:
        return None
    return next((c for c in COMMODITIES.values() if c["name"] == shipment.commodity), None)


def _rules(claim_id: str) -> List:
    return _context.claim_rules.get(claim_id, []) if _context else []


def _rule(claim_id: str, rule_id: str):
    return next((r for r in _rules(claim_id) if r.rule_id == rule_id), None)


def _triggered(claim_id: str) -> List:
    return [r for r in _rules(claim_id) if r.triggered]


def _name_of(entity_id: Optional[str]) -> str:
    if not entity_id or _context is None:
        return "N/A"
    for getter in (_context.get_consignee, _context.get_surveyor, _context.get_forwarder,
                   _context.get_shipper):
        try:
            e = getter(entity_id)
        except Exception:
            e = None
        if e:
            return e.name
    d = _context.get_director(entity_id)
    return d.full_name if d else entity_id


def _loss_label(claim_type: str) -> str:
    return (claim_type or "").replace("_", " ")


def _recommendation(claim_id: str) -> str:
    """Deterministic next-step recommendation from the rule results."""
    trig = _triggered(claim_id)
    ids = {r.rule_id for r in trig}
    coverage_blocks = [r for r in trig if r.severity == "BLOCK" and r.rule_id in ("R-001", "R-010")]
    fraud_blocks = [r for r in trig if r.severity == "BLOCK" and r.rule_id not in ("R-001", "R-010")]
    flags = [r for r in trig if r.severity == "FLAG"]
    parts = []
    if fraud_blocks:
        parts.append("HOLD PAYMENT and REFER to senior marine claims / SIU — "
                     + ", ".join(r.rule_id for r in fraud_blocks) + " require independent verification")
    elif coverage_blocks:
        parts.append("COVERAGE DECISION — consider declining under "
                     + ("the transit clause (ICC cl. 8)" if "R-001" in ids else "an ICC cl. 4 exclusion")
                     + "; this is not a fraud referral")
    elif flags:
        only_authority = all(r.rule_id == "R-012" for r in flags)
        if only_authority:
            parts.append("NO FRAUD INDICATORS — refer for settlement authority (above local limit) and settle on the survey figures")
        else:
            parts.append("HANDLER REVIEW — resolve " + ", ".join(r.rule_id for r in flags) + " before settlement")
    else:
        parts.append("APPROVE — settle subject to the excess")
    if "R-011" in ids:
        parts.append("pursue recovery from the carrier")
    elif "R-006" in ids and not coverage_blocks:
        parts.append("serve notice of claim on the carrier now to protect recovery")
    return "; ".join(parts)


# ── Coverage ─────────────────────────────────────────────────────────────────

@tool
@_safe
def check_eligibility(
    claim_id: Annotated[str, "Marine claim ID, e.g. MC-3107"],
) -> Dict:
    """Check cover: certificate/open cover valid, ICC clause covers the loss type, loss discovered within the insured transit (ICC cl. 8), claim within insured value, exclusions indicated."""
    _tool_log("check_eligibility", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}
    pol = _context.get_policy(claim.policy_id)
    shp = _context.get_shipment(claim.shipment_id)
    cne = _context.get_consignee(claim.consignee_id)

    issues, notes = [], []
    if not pol:
        issues.append("No insurance certificate found for this claim")
    else:
        if pol.status != "active":
            issues.append(f"Certificate status is {pol.status}")
        if shp and shp.shipped_on_board and not (pol.effective_date <= shp.shipped_on_board <= pol.expiration_date):
            issues.append(f"Shipment on board {shp.shipped_on_board} is outside the open cover period "
                          f"{pol.effective_date} to {pol.expiration_date}")
        clause = pol.clause or ""
        if "(A)" in clause:
            notes.append(f"{clause}: all risks of loss or damage, subject to the exclusions in cl. 4-7")
        elif "(B)" in clause or "(C)" in clause:
            issues.append(f"{clause} is a named-perils clause: {_loss_label(claim.claim_type)} is covered only if "
                          "reasonably attributable to a named peril (e.g. fire, stranding or sinking of the vessel, "
                          "contact of the vessel with an external object). "
                          "Confirm the cause before accepting cover.")
        if claim.claim_amount > pol.insured_value:
            issues.append(f"Claim {_money(claim.claim_amount)} exceeds the insured value {_money(pol.insured_value)}")

    days_after = _days(shp.discharge_date, claim.date_of_loss) if shp else None
    if days_after is not None:
        if days_after > ICC_POST_DISCHARGE_DAYS:
            issues.append(f"Loss discovered {days_after} days after discharge — beyond the ICC 2009 cl. 8.1.4 limit "
                          f"of {ICC_POST_DISCHARGE_DAYS} days after discharge from the ocean vessel")
        else:
            notes.append(f"Loss discovered {days_after} days after discharge (limit {ICC_POST_DISCHARGE_DAYS} days)")
        if shp.gate_out_date and claim.date_of_loss and claim.date_of_loss > shp.gate_out_date:
            notes.append(f"Cargo left the terminal on {shp.gate_out_date}. Cover ends on unloading at the final "
                         "warehouse (cl. 8.1.1), so confirm the damage occurred before delivery was completed")

    r010 = _rule(claim_id, "R-010")
    if r010 and r010.triggered:
        cause = (r010.details or {}).get("cause_of_loss") or ""
        if "storage" in cause.lower() and "after delivery" in cause.lower():
            issues.append(f"Surveyed cause '{cause}' points to damage during storage after delivery — "
                          "outside the insured transit (ICC cl. 8), not an insured transit loss")
        else:
            issues.append(r010.explanation)

    if cne and cne.flagged:
        notes.append("Claimant is flagged for enhanced review — run all checks")

    net = max(0.0, claim.claim_amount - (pol.excess if pol else 0))
    return {
        "claim_id": claim_id,
        "covered": len(issues) == 0,
        "coverage_issues": issues,
        "notes": notes,
        "claimant": cne.name if cne else claim.consignee_id,
        "claimant_id": claim.consignee_id,
        "claim_type": claim.claim_type,
        "claim_amount": claim.claim_amount,
        "certificate_no": claim.policy_id,
        "open_cover_no": pol.open_cover_no if pol else None,
        "clause": pol.clause if pol else None,
        "insured_value": pol.insured_value if pol else None,
        "excess": pol.excess if pol else None,
        "claim_net_of_excess": round(net, 2),
        "shipped_on_board": shp.shipped_on_board if shp else None,
        "discharge_date": shp.discharge_date if shp else None,
        "date_loss_discovered": claim.date_of_loss,
        "days_after_discharge": days_after,
        "claimant_flagged": bool(cne and cne.flagged),
    }


@tool
@_safe
def get_policy_details(
    claim_id: Annotated[str, "Marine claim ID, e.g. MC-3107"],
) -> Dict:
    """Get the insurance certificate and open cover: ICC clause, insured value, basis of valuation, excess, cover period."""
    _tool_log("get_policy_details", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}
    pol = _context.get_policy(claim.policy_id)
    if not pol:
        return {"claim_id": claim_id, "error": "No insurance certificate found"}
    shp = _context.get_shipment(pol.shipment_id)
    assured = _context.get_consignee(pol.assured_id)
    clause_scope = ("All risks, subject to exclusions (cl. 4 general, cl. 5 unseaworthiness/unfitness, "
                    "cl. 6 war, cl. 7 strikes)" if "(A)" in pol.clause
                    else "Named perils only (major casualties); subject to the same exclusions")
    return {
        "claim_id": claim_id,
        "certificate_no": pol.policy_id,
        "open_cover_no": pol.open_cover_no,
        "assured": assured.name if assured else pol.assured_id,
        "assured_id": pol.assured_id,
        "shipment": f"B/L {shp.bl_number} — {shp.description}" if shp else pol.shipment_id,
        "incoterm": shp.incoterm if shp else None,
        "clause": pol.clause,
        "clause_scope": clause_scope,
        "insured_value": pol.insured_value,
        "basis_of_valuation": pol.basis_of_valuation,
        "invoice_value": shp.invoice_value if shp else None,
        "excess": pol.excess,
        "open_cover_period": f"{pol.effective_date} to {pol.expiration_date}",
        "status": pol.status,
        "transit_clause": "ICC cl. 8: warehouse to warehouse; ends on unloading at the final warehouse or "
                          "60 days after discharge from the ocean vessel, whichever first occurs",
    }


# ── Shipment & valuation ─────────────────────────────────────────────────────

@tool
@_safe
def cross_check_shipping_documents(
    claim_id: Annotated[str, "Marine claim ID, e.g. MC-3107"],
) -> Dict:
    """Cross-check bill of lading vs commercial invoice vs packing list vs VGM (verified gross mass), container seals at loading and discharge, and EIR remarks at gate-out."""
    _tool_log("cross_check_shipping_documents", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}
    shp = _context.get_shipment(claim.shipment_id)
    if not shp:
        return {"claim_id": claim_id, "error": "Shipment record not found"}
    com = _commodity_for(shp)
    unit = _unit(shp.unit)
    flags, explanations = [], []

    declared = shp.gross_weight_bl_kg
    vgm_cargo = shp.vgm_cargo_kg
    gap = (declared - vgm_cargo) / declared if declared else 0.0
    expected_from_invoice = round(shp.quantity * com["kg_per_unit"]) if com else None
    implied_qty = round(vgm_cargo / com["kg_per_unit"]) if com and com["kg_per_unit"] else None

    if abs(gap) > WEIGHT_TOLERANCE:
        flags.append(f"VGM cargo weight {vgm_cargo:,} kg vs {declared:,} kg on B/L and packing list "
                     f"({gap:.0%} short)")
        if implied_qty is not None and com["unit"] != "t":
            flags.append(f"VGM supports at most ~{implied_qty:,} {unit} loaded vs {shp.quantity:,.0f} {unit} invoiced")
        explanations.append(INNOCENT_EXPLANATIONS["R-003"])
    if "SHIPPER'S LOAD" in (shp.bl_clause or "").upper() or "SAID TO CONTAIN" in (shp.bl_clause or "").upper():
        explanations.append("The B/L is claused 'shipper's load, stow and count / said to contain': the carrier "
                            "did not verify the contents, so the B/L quantity rests on the shipper's declaration.")

    containers = []
    for c in shp.containers:
        match = c.seal_no_loading == c.seal_no_discharge
        containers.append({
            "container_no": c.container_no, "size_type": c.size_type,
            "seal_at_loading": c.seal_no_loading, "seal_at_discharge": c.seal_no_discharge,
            "seal_match": match, "tare_kg": c.tare_kg, "vgm_kg": c.vgm_kg,
        })
        if not match:
            flags.append(f"Seal on {c.container_no} changed in transit: {c.seal_no_loading} at loading, "
                         f"{c.seal_no_discharge} at discharge")
    eir = shp.eir_remarks_discharge or ""
    eir_clean = eir.lower().startswith("clean")
    if not eir_clean:
        flags.append(f"EIR exception at discharge: {eir}")

    docs = [d.doc_type for d in _context.supplemental_data.get("documents", []) if d.claim_id == claim_id]
    missing = [DOC_LABELS.get(d, d) for d in REQUIRED_DOCS if d not in docs]
    if missing:
        flags.append("Missing documents: " + ", ".join(missing))

    return {
        "claim_id": claim_id,
        "bill_of_lading": {
            "bl_number": shp.bl_number, "carrier": shp.carrier, "vessel": shp.vessel, "voyage": shp.voyage,
            "port_of_loading": shp.port_of_loading, "port_of_discharge": shp.port_of_discharge,
            "shipped_on_board": shp.shipped_on_board, "clause": shp.bl_clause,
            "packages": shp.packages, "package_type": shp.package_type,
            "gross_weight_declared_kg": declared,
        },
        "commercial_invoice": {
            "invoice_no": shp.invoice_no, "incoterm": shp.incoterm, "commodity": shp.commodity,
            "quantity": shp.quantity, "unit": unit, "unit_price": shp.unit_price,
            "invoice_value": shp.invoice_value,
            "expected_cargo_weight_kg": expected_from_invoice,
        },
        "packing_list": {"gross_weight_kg": declared, "packages": shp.packages,
                         "consistent_with_bl": True},
        "vgm": {
            "total_vgm_kg": shp.total_vgm_kg, "total_tare_kg": shp.total_tare_kg,
            "cargo_weight_kg": vgm_cargo, "gap_vs_declared_pct": round(gap * 100, 1),
            "vgm_implied_quantity": implied_qty,
        },
        "containers": containers,
        "seals_match": shp.seals_match,
        "eir_at_discharge": eir,
        "eir_clean": eir_clean,
        "discharge_date": shp.discharge_date,
        "gate_out_date": shp.gate_out_date,
        "documents_on_file": [DOC_LABELS.get(d, d) for d in docs],
        "flags": flags,
        "innocent_explanations": explanations,
        "consistent": not flags,
    }


@tool
@_safe
def verify_declared_value(
    claim_id: Annotated[str, "Marine claim ID, e.g. MC-3107"],
) -> Dict:
    """Verify the invoiced unit price against the commodity market benchmark, and the insured value against the CIF + 10% basis; estimate the value supported by the evidence."""
    _tool_log("verify_declared_value", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}
    shp = _context.get_shipment(claim.shipment_id)
    pol = _context.get_policy(claim.policy_id)
    if not shp or not pol:
        return {"claim_id": claim_id, "error": "Shipment or certificate not found"}
    com = _commodity_for(shp)
    shipper = _context.get_shipper(shp.shipper_id)
    unit = _unit(shp.unit)
    flags, explanations, verify = [], [], []

    result = {
        "claim_id": claim_id,
        "commodity": shp.commodity,
        "incoterm": shp.incoterm,
        "quantity_invoiced": shp.quantity,
        "unit": unit,
        "unit_price_invoiced": shp.unit_price,
        "invoice_value": shp.invoice_value,
        "insured_value": pol.insured_value,
        "basis_of_valuation": pol.basis_of_valuation,
        "insured_to_invoice_ratio": round(pol.insured_value / shp.invoice_value, 3) if shp.invoice_value else None,
        "claim_amount": claim.claim_amount,
    }
    if com:
        lo, hi = com["price"]
        mid = (lo + hi) / 2
        ratio = shp.unit_price / mid if mid else 0
        result.update({
            "benchmark_range": f"${lo:,.2f} to ${hi:,.2f} per {unit}",
            "benchmark_mid": round(mid, 2),
            "price_vs_benchmark": round(ratio, 2),
            "invoice_value_at_benchmark": round(shp.quantity * mid, 2),
        })
        if ratio > VALUE_FLAG_RATIO:
            flags.append(f"Invoiced {_money(shp.unit_price)}/{unit} is {ratio:.2f}x the benchmark mid-point "
                         f"({_money(mid)}/{unit})")
            explanations.append(INNOCENT_EXPLANATIONS["R-002"])
            verify += ["Proof of payment to the seller (bank remittance or L/C documents)",
                       "Seller's export declaration showing the declared export value",
                       "Import customs declaration and duties paid at destination"]
        # Value supported by the evidence: VGM-implied quantity at benchmark price, on the policy basis.
        uplift = pol.insured_value / shp.invoice_value if shp.invoice_value else 1.1
        implied_qty = shp.vgm_cargo_kg / com["kg_per_unit"] if com["kg_per_unit"] else shp.quantity
        supported_qty = min(shp.quantity, implied_qty)
        supported_value = supported_qty * min(shp.unit_price, hi) * uplift
        svr = _context.get_survey(claim.survey_id) if claim.survey_id else None
        dmg = (svr.damage_pct / 100) if svr else (claim.claim_amount / pol.insured_value if pol.insured_value else 0)
        result.update({
            "supported_quantity": round(supported_qty, 2),
            "supported_insured_value": round(supported_value, 2),
            "supported_loss_at_surveyed_damage": round(supported_value * dmg, 2),
            "supported_value_method": "Lower of invoiced and VGM-implied quantity, at the lower of invoiced price and "
                                      "top of benchmark range, on the certificate's valuation uplift",
        })
    else:
        result["benchmark_range"] = "No market benchmark on file for this commodity"

    if shp.incoterm == "FOB":
        explanations.append("FOB sale: the insured value includes estimated freight and insurance to reach CIF, "
                            "so insured value above invoice + 10% is expected.")
    if shipper and shipper.incorporated and shp.shipped_on_board:
        age = _days(shipper.incorporated, shp.shipped_on_board)
        result["shipper"] = shipper.name
        result["shipper_incorporated"] = shipper.incorporated
        if age is not None and age < 365:
            flags.append(f"Seller {shipper.name} was incorporated {age} days before shipment")
            if shipper.notes:
                flags.append(f"Seller note: {shipper.notes}")
    result["flags"] = flags
    result["innocent_explanations"] = explanations
    result["documents_to_request"] = verify
    return result


# ── Survey & claimant ────────────────────────────────────────────────────────

@tool
@_safe
def check_surveyor(
    claim_id: Annotated[str, "Marine claim ID, e.g. MC-3107"],
) -> Dict:
    """Check the surveyor and survey: insurer panel status, watchlist, who appointed the surveyor, survey timing after discharge, joint survey with the carrier, links to the claimant, and prior claims by the same surveyor."""
    _tool_log("check_surveyor", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}
    svy = _context.get_surveyor(claim.surveyor_id) if claim.surveyor_id else None
    svr = _context.get_survey(claim.survey_id) if claim.survey_id else None
    if not svy:
        return {"claim_id": claim_id, "note": "No surveyor appointed on this claim",
                "flags": ["No survey on file — appoint an insurer panel surveyor"]}
    shp = _context.get_shipment(claim.shipment_id)
    cne = _context.get_consignee(claim.consignee_id)
    fwd = _context.get_forwarder(shp.forwarder_id) if shp else None
    flags, explanations = [], []

    if svy.on_watchlist:
        flags.append(f"Surveyor '{svy.name}' is on the surveyor watchlist")
    if not svy.insurer_panel:
        flags.append(f"Surveyor '{svy.name}' is not on the insurer's approved panel")
    shared_dirs_cne = sorted(set(svy.director_ids) & set(cne.director_ids)) if cne else []
    shared_dirs_fwd = sorted(set(svy.director_ids) & set(fwd.director_ids)) if fwd else []
    for did in shared_dirs_cne:
        flags.append(f"Surveyor shares director {_name_of(did)} ({did}) with the claimant")
    for did in shared_dirs_fwd:
        flags.append(f"Surveyor shares director {_name_of(did)} ({did}) with the forwarder {fwd.name}")
    if cne and svy.registered_address and svy.registered_address == cne.registered_address:
        flags.append(f"Surveyor and claimant share a registered address: {svy.registered_address}")

    days_after = None
    if svr:
        days_after = _days(shp.discharge_date, svr.survey_date) if shp else None
        if svr.appointed_by != "insurer":
            flags.append("Surveyor appointed by the assured, not by the insurer or its claims agent")
        if days_after is not None and days_after > SURVEY_LATE_DAYS:
            flags.append(f"Survey held {days_after} days after discharge (guideline: within {SURVEY_LATE_DAYS} days)")
        if not svr.joint_with_carrier and claim.claim_type in ("breakage", "shortage", "theft_pilferage"):
            flags.append("No joint survey with the carrier's representative")
        if "unstuffed" in (svr.survey_location or "").lower():
            flags.append("Cargo already unstuffed before survey — condition in the container not recorded")

    priors = _context.get_prior_claims(surveyor_id=svy.surveyor_id)
    open_claims = [c for c in _context.supplemental_claims
                   if c.surveyor_id == svy.surveyor_id and c.claim_id != claim_id]
    prior_consignees = sorted({p.consignee_id for p in priors})
    if priors and (not svy.insurer_panel or svy.on_watchlist):
        flags.append(f"{len(priors)} prior paid claims surveyed by this firm across {len(prior_consignees)} "
                     f"consignee(s), {_money(sum(p.amount_paid for p in priors))} in total")
    if flags:
        explanations += [INNOCENT_EXPLANATIONS["R-005"], INNOCENT_EXPLANATIONS["R-004"]]

    return {
        "claim_id": claim_id,
        "surveyor_id": svy.surveyor_id,
        "surveyor_name": svy.name,
        "city": svy.city,
        "insurer_panel": svy.insurer_panel,
        "on_watchlist": svy.on_watchlist,
        "registered_address": svy.registered_address,
        "notes": svy.notes,
        "survey": {
            "report_no": svr.report_no, "appointed_by": svr.appointed_by, "survey_date": svr.survey_date,
            "days_after_discharge": days_after, "location": svr.survey_location,
            "joint_with_carrier": svr.joint_with_carrier, "cause_of_loss": svr.cause_of_loss,
            "damage_pct": svr.damage_pct, "photos": svr.photos,
        } if svr else None,
        "shared_directors_with_claimant": shared_dirs_cne,
        "shared_directors_with_forwarder": shared_dirs_fwd,
        "prior_paid_claims": [
            {"claim_id": p.claim_id, "consignee": _name_of(p.consignee_id), "type": p.claim_type,
             "amount_paid": p.amount_paid, "date_paid": p.date_paid, "commodity": p.commodity}
            for p in priors[:10]
        ],
        "other_open_claims": [c.claim_id for c in open_claims[:10]],
        "flags": flags,
        "innocent_explanations": explanations,
        "recommendation": ("Appoint an independent insurer panel surveyor to re-inspect the cargo and review the "
                           "original photographs" if flags else "Survey appears independent and timely"),
    }


@tool
@_safe
def check_claim_history(
    claim_id: Annotated[str, "Marine claim ID to check the claimant's history for"],
) -> Dict:
    """Analyse the claimant's claim history: open claims, prior paid claims, and claim rate normalised by annual shipment volume versus peers."""
    _tool_log("check_claim_history", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}
    cne = _context.get_consignee(claim.consignee_id)
    if not cne:
        return {"claim_id": claim_id, "error": "Claimant not found"}
    open_claims = _context.get_consignee_claims(cne.party_id)
    priors = _context.get_prior_claims(party_id=cne.party_id)
    total = cne.claim_history_count + len(open_claims)
    shipments_24m = max(1, cne.shipments_per_year * 2)
    rate = total / shipments_24m

    peer_rates = []
    for p in _context.supplemental_data.get("consignees", []):
        n = p.claim_history_count + len(_context.get_consignee_claims(p.party_id))
        peer_rates.append(n / max(1, p.shipments_per_year * 2))
    peer_avg = sum(peer_rates) / len(peer_rates) if peer_rates else 0

    flags, explanations = [], []
    if total >= 3 and rate >= 0.05:
        flags.append(f"{total} claims in 24 months on ~{shipments_24m} shipments ({rate:.1%} claim rate; "
                     f"portfolio average {peer_avg:.1%})")
        explanations.append(INNOCENT_EXPLANATIONS["R-007"])
    elif total >= 3:
        explanations.append(f"{total} claims looks high but is normal for ~{cne.shipments_per_year} shipments a year "
                            f"({rate:.1%} claim rate)")
    surveyors = sorted({p.surveyor_id for p in priors})
    if priors and len(surveyors) == 1:
        flags.append(f"All {len(priors)} prior paid claims were surveyed by {_name_of(surveyors[0])}")
    if cne.incorporated and _days(cne.incorporated, claim.date_filed) is not None and _days(cne.incorporated, claim.date_filed) < 4 * 365:
        flags.append(f"Claimant incorporated {cne.incorporated} — relatively new trading history")

    return {
        "claim_id": claim_id,
        "claimant_id": cne.party_id,
        "claimant_name": cne.name,
        "city": cne.city,
        "incorporated": cne.incorporated,
        "shipments_per_year": cne.shipments_per_year,
        "claims_24m": total,
        "claim_rate_24m": round(rate, 4),
        "portfolio_avg_claim_rate": round(peer_avg, 4),
        "prior_paid_claims": [
            {"claim_id": p.claim_id, "type": p.claim_type, "amount_paid": p.amount_paid,
             "date_paid": p.date_paid, "commodity": p.commodity, "surveyor": _name_of(p.surveyor_id)}
            for p in priors[:10]
        ],
        "prior_paid_total": round(sum(p.amount_paid for p in priors), 2),
        "open_claims": [
            {"claim_id": c.claim_id, "type": c.claim_type, "amount": c.claim_amount, "date_filed": c.date_filed}
            for c in open_claims[:10]
        ],
        "flagged": cne.flagged,
        "flags": flags,
        "innocent_explanations": explanations,
    }


@tool
@_safe
def find_related_claims(
    claim_id: Annotated[str, "Marine claim ID, e.g. MC-3107"],
) -> Dict:
    """Find claims and entities linked to this claim through the same consignee, surveyor or forwarder, shared directors, or a shared registered address."""
    _tool_log("find_related_claims", f"Finding related for {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}
    shp = _context.get_shipment(claim.shipment_id)
    cne = _context.get_consignee(claim.consignee_id)
    svy = _context.get_surveyor(claim.surveyor_id) if claim.surveyor_id else None
    fwd = _context.get_forwarder(shp.forwarder_id) if shp else None
    shipments = {s.shipment_id: s for s in _context.supplemental_data.get("shipments", [])}

    def brief(c):
        return {"claim_id": c.claim_id, "type": c.claim_type, "amount": c.claim_amount,
                "date_filed": c.date_filed, "consignee": _name_of(c.consignee_id)}

    def brief_prior(p):
        return {"claim_id": p.claim_id, "type": p.claim_type, "amount_paid": p.amount_paid,
                "date_paid": p.date_paid, "consignee": _name_of(p.consignee_id), "status": "closed/paid"}

    others = [c for c in _context.supplemental_claims if c.claim_id != claim_id]
    same_cne = [brief(c) for c in others if c.consignee_id == claim.consignee_id] + \
               [brief_prior(p) for p in _context.get_prior_claims(party_id=claim.consignee_id)]
    same_svy = []
    if svy:
        same_svy = [brief(c) for c in others if c.surveyor_id == svy.surveyor_id] + \
                   [brief_prior(p) for p in _context.get_prior_claims(surveyor_id=svy.surveyor_id)]
    same_fwd = [brief(c) for c in others
                if fwd and shipments.get(c.shipment_id) and shipments[c.shipment_id].forwarder_id == fwd.forwarder_id]

    # Shared directors / registered address across consignees, surveyors and forwarders.
    network = []
    entities = ([("consignee", e.party_id, e) for e in _context.supplemental_data.get("consignees", [])] +
                [("surveyor", e.surveyor_id, e) for e in _context.supplemental_data.get("surveyors", [])] +
                [("forwarder", e.forwarder_id, e) for e in _context.supplemental_data.get("forwarders", [])])
    my_dirs = set(cne.director_ids) if cne else set()
    my_addr = cne.registered_address if cne else None
    for etype, eid, e in entities:
        if eid == claim.consignee_id:
            continue
        shared = sorted(my_dirs & set(getattr(e, "director_ids", []) or []))
        addr = bool(my_addr) and getattr(e, "registered_address", None) == my_addr
        if shared or addr:
            network.append({
                "entity_id": eid, "entity_type": etype, "name": e.name,
                "shared_directors": [f"{_name_of(d)} ({d})" for d in shared],
                "shared_registered_address": my_addr if addr else None,
            })

    flags = []
    if network:
        flags.append(f"Claimant shares directors or registered address with {len(network)} other entit"
                     f"{'y' if len(network) == 1 else 'ies'}: " + ", ".join(n["name"] for n in network))
    return {
        "claim_id": claim_id,
        "claimant": cne.name if cne else claim.consignee_id,
        "surveyor": svy.name if svy else None,
        "forwarder": fwd.name if fwd else None,
        "same_consignee": same_cne[:10],
        "same_surveyor": same_svy[:10],
        "same_forwarder": same_fwd[:10],
        "linked_entities": network,
        "total_related": len(same_cne) + len(same_svy) + len(same_fwd),
        "flags": flags,
    }


@tool
@_safe
def analyze_documents(
    claim_id: Annotated[str, "Marine claim ID, e.g. MC-3107"],
) -> Dict:
    """Review documents on file (B/L, invoice, packing list, survey report, EIR, survey photos), any vision forensics results on evidence images, and reused-photo matches against other claims."""
    _tool_log("analyze_documents", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}
    docs = [d for d in _context.supplemental_data.get("documents", []) if d.claim_id == claim_id]
    flags = []
    present = [d.doc_type for d in docs]
    for req in REQUIRED_DOCS:
        if req not in present:
            flags.append(f"MISSING: {DOC_LABELS.get(req, req)} not submitted")

    doc_summary = []
    for d in docs:
        entry = {"doc_id": d.doc_id, "type": DOC_LABELS.get(d.doc_type, d.doc_type),
                 "received": d.received_date, "format": d.format_type,
                 "has_signature": d.has_signature}
        if d.tampering_indicators:
            entry["tampering_indicators"] = d.tampering_indicators
            flags.append(f"{d.doc_id}: tampering indicators — {', '.join(d.tampering_indicators)}")
        doc_summary.append(entry)

    images = []
    try:
        from intelligence.document_vision import find_claim_images
        images = [p.name for p in find_claim_images(claim_id)]
    except Exception:
        images = []

    vision = _context.claim_doc_results.get(claim_id, []) or []
    failed = [v for v in vision if not getattr(v, "passed", True)]
    for v in failed:
        flags.append(f"{v.severity} [{v.check_id}] {v.check_name}: {v.explanation}")
    assessment = next((v.details.get("overall_assessment") for v in vision
                       if isinstance(getattr(v, "details", None), dict) and v.details.get("overall_assessment")), None)

    dups = _context.supplemental_data.get("duplicate_images", {}).get(claim_id, [])
    for m in dups:
        flags.append(f"Photo {m.get('image')} matches {m.get('other_image')} filed on {m.get('other_claim_id')} "
                     f"(hash distance {m.get('distance')}/64)")

    if images and not vision:
        vision_status = "Evidence images on file; vision forensics not yet run (open the checklist Document AI step)"
    elif vision:
        vision_status = f"{len(vision)} forensic checks run, {len(failed)} failed"
    else:
        vision_status = "No evidence images on file"

    return {
        "claim_id": claim_id,
        "total_documents": len(docs),
        "documents": doc_summary,
        "evidence_images": images,
        "vision_status": vision_status,
        "vision_failed_checks": [
            {"check_id": v.check_id, "check_name": v.check_name, "severity": v.severity,
             "explanation": v.explanation} for v in failed[:8]
        ],
        "vision_assessment": assessment,
        "reused_photo_matches": dups,
        "flags": flags,
        "flag_count": len(flags),
    }


# ── Recovery & workflow ──────────────────────────────────────────────────────

@tool
@_safe
def check_recovery_position(
    claim_id: Annotated[str, "Marine claim ID, e.g. MC-3094"],
) -> Dict:
    """Assess subrogation prospects against the carrier: notice of claim, EIR exceptions, seal discrepancies, joint survey, Hague-Visby notice and one-year time bar, and an indicative carrier liability limit."""
    _tool_log("check_recovery_position", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}
    shp = _context.get_shipment(claim.shipment_id)
    if not shp:
        return {"claim_id": claim_id, "error": "Shipment record not found"}
    svr = _context.get_survey(claim.survey_id) if claim.survey_id else None
    pol = _context.get_policy(claim.policy_id)

    eir = shp.eir_remarks_discharge or ""
    exception = eir.upper().startswith("EXCEPTION") or not shp.seals_match
    joint = bool(svr and svr.joint_with_carrier)
    notice_days = _days(claim.date_of_loss, claim.notice_to_carrier_date) if claim.notice_to_carrier_date else None
    notice_ok = notice_days is not None and notice_days <= CARRIER_NOTICE_DAYS

    strengths, weaknesses, actions = [], [], []
    if exception:
        strengths.append(f"Exception recorded at discharge: {eir}")
    else:
        weaknesses.append("Clean EIR and intact seals at gate-out. Taking delivery without written notice is prima "
                          "facie evidence the carrier delivered the goods as described in the B/L (HVR Art. III r.6)")
    if not shp.seals_match:
        strengths.append("Seal number at discharge differs from the B/L seal — container was opened in the carrier's custody")
    if joint:
        strengths.append("Joint survey with the carrier's representative (under HVR Art. III r.6 no written notice is "
                         "needed where the goods were jointly surveyed at receipt)")
    if claim.notice_to_carrier_date is None:
        weaknesses.append("No notice of claim served on the carrier — assured's duty to preserve rights (ICC cl. 16.2) not met")
        actions.append("Serve written notice of claim on the carrier and terminal immediately")
    elif notice_ok:
        strengths.append(f"Notice of claim served {notice_days} day(s) after discovery")
    else:
        weaknesses.append(f"Notice of claim served {notice_days} days after discovery (HVR: within 3 days where damage "
                          "is not apparent)")
    if "SAID TO CONTAIN" in (shp.bl_clause or "").upper() and claim.claim_type == "shortage":
        weaknesses.append("B/L 'said to contain' — carrier can dispute the quantity loaded")
    if svr and "packing" in (svr.cause_of_loss or "").lower():
        weaknesses.append("Surveyed cause is insufficient packing — carrier has a defence (HVR Art. IV r.2(n))")
    if svr and "storage after delivery" in (svr.cause_of_loss or "").lower():
        weaknesses.append("Damage occurred after delivery — outside the carrier's period of responsibility")

    delivery = shp.gate_out_date or shp.discharge_date
    time_bar = (_parse(delivery) + timedelta(days=365)).strftime("%Y-%m-%d") if _parse(delivery) else None
    if time_bar:
        actions.append(f"Diarise the one-year time bar ({time_bar}); obtain a written time extension from the "
                       "carrier or issue suit before then (HVR Art. III r.6)")

    if exception and (notice_ok or joint):
        prospects = "STRONG"
    elif exception or notice_ok:
        prospects = "MODERATE"
    elif claim.notice_to_carrier_date is None and not exception:
        prospects = "WEAK — rights prejudiced"
    else:
        prospects = "WEAK"

    # Indicative Hague-Visby limit (Art. IV r.5): higher of 666.67 SDR/package and 2 SDR/kg lost.
    dmg = (svr.damage_pct / 100) if svr else (claim.claim_amount / pol.insured_value if pol and pol.insured_value else 0)
    pkgs_lost = shp.packages * dmg
    kg_lost = shp.vgm_cargo_kg * dmg
    limit_sdr = max(pkgs_lost * HVR_SDR_PER_PACKAGE, kg_lost * HVR_SDR_PER_KG)
    limit_usd = limit_sdr * SDR_USD_INDICATIVE
    recoverable = min(claim.claim_amount, limit_usd) if prospects.startswith(("STRONG", "MODERATE")) else 0.0
    if prospects.startswith(("STRONG", "MODERATE")):
        actions.append("Retain the damaged container / seals and survey report for the recovery file")
        actions.append(f"Present the recovery claim to {shp.carrier} after settlement (subrogation, MIA 1906 s.79)")

    return {
        "claim_id": claim_id,
        "carrier": shp.carrier,
        "bl_number": shp.bl_number,
        "vessel_voyage": f"{shp.vessel} / {shp.voyage}",
        "eir_at_discharge": eir,
        "seals_match": shp.seals_match,
        "joint_survey": joint,
        "notice_to_carrier_date": claim.notice_to_carrier_date,
        "notice_days_after_discovery": notice_days,
        "delivery_date": delivery,
        "time_bar_date": time_bar,
        "recovery_prospects": prospects,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "indicative_carrier_limit_usd": round(limit_usd, 2),
        "indicative_recoverable_usd": round(recoverable, 2),
        "limit_basis": (f"Hague-Visby Art. IV r.5: higher of {HVR_SDR_PER_PACKAGE} SDR/package and "
                        f"{HVR_SDR_PER_KG:.0f} SDR/kg on ~{pkgs_lost:,.0f} packages / ~{kg_lost:,.0f} kg lost, at an "
                        f"indicative {SDR_USD_INDICATIVE} USD/SDR. Confirm the regime in the B/L clause paramount."),
        "recommended_actions": actions,
    }


@tool
@_safe
def check_workflow_tasks(
    claim_id: Annotated[str, "Marine claim ID, e.g. MC-3107"],
) -> Dict:
    """Check workflow task status for the claim: INITIAL_REVIEW, DOCUMENT_REVIEW, RECOVERY_NOTICE (including overdue tasks)."""
    _tool_log("check_workflow_tasks", f"Checking {claim_id}")
    tasks = _context.get_claim_tasks(claim_id)
    task_list = [{
        "task_id": t.task_id, "type": t.task_type, "status": t.status,
        "assigned_date": t.assigned_date, "due_date": t.due_date, "days_waiting": t.days_waiting,
        "notes": t.notes,
    } for t in tasks]
    overdue = [t for t in tasks if t.status == "overdue"]
    pending_docs = [t for t in tasks if t.task_type == "DOCUMENT_REVIEW" and t.status in ("pending", "in_progress")]
    return {
        "claim_id": claim_id,
        "total_tasks": len(tasks),
        "tasks": task_list,
        "overdue_count": len(overdue),
        "overdue": [f"{t.task_type}: {t.notes or 'past due'}" for t in overdue],
        "document_review_open": bool(pending_docs),
    }


# ── Summary tools ────────────────────────────────────────────────────────────

@tool
@_safe
def explain_risk_score(
    claim_id: Annotated[str, "Marine claim ID, e.g. MC-3107"],
) -> Dict:
    """Explain the risk score: total, tier, top factors, feature contributions, triggered rules with innocent explanations, and the recommended next step."""
    _tool_log("explain_risk_score", f"Explaining {claim_id}")
    risk = _context.claim_risk_scores.get(claim_id)
    if not risk:
        return {"claim_id": claim_id, "error": "No risk score found"}
    rules = _rules(claim_id)
    triggered = [r for r in rules if r.triggered]
    return {
        "claim_id": claim_id,
        "total_score": risk.total_score,
        "tier": risk.tier,
        "top_factors": risk.top_factors,
        "rules_boost": risk.rules_boost,
        "feature_contributions": [
            {"category": fc.category, "feature": fc.feature_name,
             "raw_value": round(fc.raw_value, 4) if isinstance(fc.raw_value, float) else fc.raw_value,
             "contribution": round(fc.contribution * 100, 1)}
            for fc in risk.feature_contributions
        ],
        "rules_triggered": [
            {"rule_id": r.rule_id, "name": r.rule_name, "severity": r.severity, "explanation": r.explanation,
             "innocent_explanation": INNOCENT_EXPLANATIONS.get(r.rule_id, "")}
            for r in triggered
        ],
        "rules_passed": [f"{r.rule_id} {r.rule_name}" for r in rules if not r.triggered],
        "recommendation": _recommendation(claim_id),
    }


def _checklist_context() -> Dict:
    """Context dict for intelligence.checklist_marine — same shape as main._context_dict + intelligence."""
    data = _context.supplemental_data
    keys = ["claims", "consignees", "shippers", "surveyors", "forwarders", "directors",
            "shipments", "policies", "surveys", "prior_claims", "workflow_tasks", "documents"]
    ctx = {k: data.get(k, []) for k in keys}
    ctx.update({
        "claim_rules": _context.claim_rules,
        "claim_risk_scores": _context.claim_risk_scores,
        "claim_doc_results": _context.claim_doc_results,
        "duplicate_images": data.get("duplicate_images", {}),
    })
    return ctx


@tool
@_safe
def run_fraud_checklist(
    claim_id: Annotated[str, "Marine claim ID, e.g. MC-3107"],
) -> Dict:
    """Run the 7-step marine cargo claims checklist: initial review, shipping documents, transit & coverage period, document AI, survey & surveyor, ICC coverage & exclusions, final determination."""
    _tool_log("run_fraud_checklist", f"Running for {claim_id}")
    if not _get_claim(claim_id):
        return {"error": f"Claim {claim_id} not found"}
    from intelligence.checklist_marine import run_full_checklist
    ctx = _checklist_context()
    try:
        from intelligence.document_vision import find_claim_images
        ctx["has_claim_images"] = bool(find_claim_images(claim_id))
    except Exception:
        ctx["has_claim_images"] = False
    results = run_full_checklist(claim_id, ctx)
    steps = [{"step": s.step_number, "name": s.step_name, "status": s.status,
              "findings": s.findings[:8]} for s in results]
    return {
        "claim_id": claim_id,
        "total_steps": len(steps),
        "passed": sum(1 for s in results if s.status == "pass"),
        "failed": sum(1 for s in results if s.status == "fail"),
        "needs_review": sum(1 for s in results if s.status == "needs_review"),
        "steps": steps,
        "recommendation": _recommendation(claim_id),
    }


def _dossier_markdown(claim_id: str) -> Optional[str]:
    claim = _get_claim(claim_id)
    if not claim:
        return None
    cne = _context.get_consignee(claim.consignee_id)
    pol = _context.get_policy(claim.policy_id)
    shp = _context.get_shipment(claim.shipment_id)
    svy = _context.get_surveyor(claim.surveyor_id) if claim.surveyor_id else None
    svr = _context.get_survey(claim.survey_id) if claim.survey_id else None
    fwd = _context.get_forwarder(shp.forwarder_id) if shp else None
    shipper = _context.get_shipper(shp.shipper_id) if shp else None
    risk = _context.claim_risk_scores.get(claim_id)
    triggered = _triggered(claim_id)
    unit = _unit(shp.unit) if shp else ""

    md = [f"# Marine Cargo Claim Dossier — {claim_id}", ""]
    md += ["## Claim",
           f"- **Loss type**: {_loss_label(claim.claim_type).title()}",
           f"- **Amount claimed**: {_money(claim.claim_amount)}",
           f"- **Loss discovered**: {claim.date_of_loss} · **Filed**: {claim.date_filed}",
           f"- **Notice to insurer**: {claim.notice_to_insurer_date or 'N/A'} · "
           f"**Notice to carrier**: {claim.notice_to_carrier_date or 'NONE'}",
           f"- **Description**: {claim.loss_description}", ""]
    md += ["## Claimant (Consignee)",
           f"- **Name**: {cne.name if cne else claim.consignee_id} ({claim.consignee_id})",
           f"- **Registered address**: {cne.registered_address if cne else 'N/A'}",
           f"- **Incorporated**: {cne.incorporated if cne else 'N/A'} · **Shipments/yr**: "
           f"{cne.shipments_per_year if cne else 'N/A'} · **Prior claims (24m)**: {cne.claim_history_count if cne else 0}",
           f"- **Flagged**: {'YES' if (cne and cne.flagged) else 'No'}", ""]
    if shp:
        md += ["## Shipment",
               f"- **B/L**: {shp.bl_number} — {shp.carrier}, {shp.vessel} voy. {shp.voyage}",
               f"- **Route**: {shp.port_of_loading} → {shp.port_of_discharge} · on board {shp.shipped_on_board} · "
               f"discharged {shp.discharge_date} · gate-out {shp.gate_out_date}",
               f"- **Cargo**: {shp.commodity} — {shp.quantity:,.0f} {unit} × {_money(shp.unit_price)} = "
               f"{_money(shp.invoice_value)} ({shp.incoterm})",
               f"- **Seller**: {shipper.name if shipper else shp.shipper_id}"
               f"{f' (incorporated {shipper.incorporated})' if shipper and shipper.incorporated else ''}",
               f"- **Forwarder**: {fwd.name if fwd else shp.forwarder_id}",
               f"- **Weights**: B/L {shp.gross_weight_bl_kg:,} kg declared · VGM cargo {shp.vgm_cargo_kg:,} kg",
               f"- **Seals match**: {'Yes' if shp.seals_match else 'NO'} · **EIR**: {shp.eir_remarks_discharge}", ""]
    if pol:
        md += ["## Cover",
               f"- **Certificate**: {pol.policy_id} under open cover {pol.open_cover_no}",
               f"- **Clause**: {pol.clause} · **Insured value**: {_money(pol.insured_value)} ({pol.basis_of_valuation})"
               f" · **Excess**: {_money(pol.excess)}", ""]
    if svy:
        md += ["## Survey",
               f"- **Surveyor**: {svy.name} ({'insurer panel' if svy.insurer_panel else 'NOT on insurer panel'}"
               f"{', WATCHLIST' if svy.on_watchlist else ''})"]
        if svr:
            md += [f"- **Report**: {svr.report_no}, {svr.survey_date}, appointed by {svr.appointed_by}, "
                   f"{'joint with carrier' if svr.joint_with_carrier else 'not joint with carrier'}",
                   f"- **Location**: {svr.survey_location}",
                   f"- **Cause / extent**: {svr.cause_of_loss} · {svr.damage_pct:.0f}%"]
        md.append("")
    md += ["## Risk Assessment",
           f"- **Score**: {risk.total_score if risk else 0}/100 ({risk.tier if risk else 'N/A'})",
           f"- **Top factors**: {'; '.join(risk.top_factors) if risk and risk.top_factors else 'None'}", "",
           f"## Rules Triggered ({len(triggered)})"]
    if triggered:
        for r in triggered:
            md.append(f"- **{r.rule_id}** [{r.severity}] {r.rule_name}: {r.explanation}")
            if r.severity == "INFO":
                md.append(f"  - _Note_: {INNOCENT_EXPLANATIONS.get(r.rule_id, '')}")
            elif INNOCENT_EXPLANATIONS.get(r.rule_id):
                md.append(f"  - _Innocent explanation_: {INNOCENT_EXPLANATIONS[r.rule_id]}")
    else:
        md.append("- None")
    md += ["", "## Recommendation", f"{_recommendation(claim_id)}"]
    if claim.notes:
        md += ["", "## Handler Notes", claim.notes]
    md += ["", "---", f"*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · Marine Cargo Claims Copilot*"]
    return "\n".join(md) + "\n"


@tool
@_safe
def compile_dossier(
    claim_id: Annotated[str, "Marine claim ID, e.g. MC-3107"],
) -> Dict:
    """Compile the escalation dossier for the claim: claimant, shipment, cover, survey, risk score, triggered rules with innocent explanations, and recommendation."""
    _tool_log("compile_dossier", f"Compiling for {claim_id}")
    md = _dossier_markdown(claim_id)
    if md is None:
        return {"error": f"Claim {claim_id} not found"}
    risk = _context.claim_risk_scores.get(claim_id)
    return {
        "claim_id": claim_id,
        "dossier": md,
        "risk_score": risk.total_score if risk else 0,
        "rules_triggered": len(_triggered(claim_id)),
        "recommendation": _recommendation(claim_id),
    }


# ── Deterministic chat fallback (no LLM) ─────────────────────────────────────

def build_system_summary(claim_id: str) -> str:
    """Readable markdown summary of a claim built from the tools only — used when the live LLM is unavailable."""
    try:
        if _context is None:
            return "Claims data is not loaded, so no system summary is available."
        claim = _get_claim(claim_id)
        if not claim:
            return f"Claim {claim_id} was not found."
        risk = explain_risk_score.invoke({"claim_id": claim_id})
        elig = check_eligibility.invoke({"claim_id": claim_id})
        rec = check_recovery_position.invoke({"claim_id": claim_id})
        cne = _context.get_consignee(claim.consignee_id)
        shp = _context.get_shipment(claim.shipment_id)

        lines = [f"### {claim_id} — {cne.name if cne else claim.consignee_id}",
                 f"**{_loss_label(claim.claim_type).title()}** claim for **{_money(claim.claim_amount)}**"
                 + (f" · B/L {shp.bl_number} ({shp.description})" if shp else ""), ""]
        if not risk.get("error"):
            lines.append(f"**Risk score:** {risk['total_score']}/100 ({risk['tier']})")
            lines.append(f"**Recommended next step:** {risk['recommendation']}")
            lines.append("")
            if risk["rules_triggered"]:
                lines.append("**Indicators**")
                for r in risk["rules_triggered"]:
                    lines.append(f"- **{r['rule_id']}** [{r['severity']}] {r['explanation']}")
                    if r["severity"] == "INFO":
                        continue
                    if r.get("innocent_explanation"):
                        lines.append(f"  - _Possible innocent explanation:_ {r['innocent_explanation']}")
            else:
                lines.append("No rules triggered — the claim is consistent with the shipping and survey records.")
            lines.append("")
        if not elig.get("error"):
            if elig["coverage_issues"]:
                lines.append("**Coverage**")
                lines += [f"- {i}" for i in elig["coverage_issues"]]
            else:
                lines.append(f"**Coverage:** {elig.get('clause')} — no coverage issues found; claim net of excess "
                             f"{_money(elig.get('claim_net_of_excess'))}.")
            lines.append("")
        if not rec.get("error"):
            lines.append(f"**Recovery against {rec['carrier']}:** {rec['recovery_prospects']}")
            for a in rec["recommended_actions"][:2]:
                lines.append(f"- {a}")
        return "\n".join(lines).strip()
    except Exception as e:
        return f"System summary unavailable for {claim_id}: {str(e)[:200]}"


# ── Tool Registry ────────────────────────────────────────────────────────────

ALL_MARINE_TOOLS = [
    check_eligibility,
    check_claim_history,
    cross_check_shipping_documents,
    verify_declared_value,
    check_surveyor,
    analyze_documents,
    find_related_claims,
    check_recovery_position,
    check_workflow_tasks,
    get_policy_details,
    explain_risk_score,
    run_fraud_checklist,
    compile_dossier,
]
