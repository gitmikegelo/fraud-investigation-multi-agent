"""Car insurance claim tools for the Car Insurance examiner copilot."""

from typing import Dict, List, Annotated
from datetime import datetime

_context = None  # DataContext injected at startup


def set_context(ctx):
    global _context
    _context = ctx


def _tool_log(name: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"    [{ts}]   tool:{name} -> {msg}", flush=True)


def _get_claim(claim_id: str):
    return next((c for c in _context.supplemental_claims if c.claim_id == claim_id), None)


def _get_insured(insured_id: str):
    return next((i for i in _context.supplemental_data.get("insureds", []) if i.insured_id == insured_id), None)


def _get_policy(policy_id: str):
    return next((p for p in _context.supplemental_data.get("policies", []) if p.policy_id == policy_id), None)


def _get_vehicle(vehicle_id: str):
    return next((v for v in _context.supplemental_data.get("vehicles", []) if v.vehicle_id == vehicle_id), None)


def _get_shop(shop_id: str):
    return next((s for s in _context.supplemental_data.get("repair_shops", []) if s.shop_id == shop_id), None)


def _get_estimate(claim):
    ests = _context.supplemental_data.get("estimates", [])
    by_id = next((e for e in ests if e.estimate_id == getattr(claim, "estimate_id", None)), None)
    if by_id:
        return by_id
    return next((e for e in ests if e.claim_id == claim.claim_id), None)


def _coverage_for_type(policy, claim_type: str):
    if not policy:
        return 0
    return {
        "collision": policy.coverage_collision,
        "comprehensive": policy.coverage_comprehensive,
        "theft": policy.coverage_comprehensive,
        "liability": policy.coverage_liability,
        "medical_payments": policy.coverage_medical_payments,
    }.get(claim_type, 0)


# ── Fraud Tools ──────────────────────────────────────────────────────────────

def check_eligibility(
    claim_id: Annotated[str, "Claim ID (e.g. COL-107, THEFT-009)"],
) -> Dict:
    """Check claim eligibility: policy active, coverage matches claim type, incident within coverage period."""
    _tool_log("check_eligibility", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    insured = _get_insured(claim.insured_id)
    policy = _get_policy(claim.policy_id)
    vehicle = _get_vehicle(claim.vehicle_id)

    issues = []
    if not policy:
        issues.append("No matching policy found")
    elif policy.status != "active":
        issues.append(f"Policy status is {policy.status}")

    if policy:
        try:
            incident = datetime.strptime(claim.date_of_incident, "%Y-%m-%d")
            eff = datetime.strptime(policy.effective_date, "%Y-%m-%d")
            exp = datetime.strptime(policy.expiration_date, "%Y-%m-%d")
            if incident < eff:
                issues.append(f"⚠ Incident {claim.date_of_incident} BEFORE policy effective {policy.effective_date}")
            elif incident > exp:
                issues.append(f"Incident {claim.date_of_incident} AFTER policy expiration {policy.expiration_date}")
        except (ValueError, TypeError):
            pass

    if insured and insured.flagged:
        issues.append("⚠ INSURED FLAGGED for prior fraud indicators")

    coverage_limit = _coverage_for_type(policy, claim.claim_type)
    if coverage_limit and claim.claim_amount > coverage_limit:
        issues.append(f"Claim ${claim.claim_amount:,.2f} exceeds coverage limit ${coverage_limit:,.2f}")

    return {
        "claim_id": claim_id,
        "eligible": len(issues) == 0,
        "issues": issues,
        "insured_name": insured.full_name if insured else "Unknown",
        "insured_id": claim.insured_id,
        "vehicle": f"{vehicle.year} {vehicle.make} {vehicle.model}" if vehicle else "Unknown",
        "vehicle_acv": vehicle.acv if vehicle else 0,
        "policy_id": claim.policy_id,
        "policy_status": policy.status if policy else "N/A",
        "coverage_limit": coverage_limit,
        "deductible": policy.deductible if policy else None,
        "claim_type": claim.claim_type,
        "claim_amount": claim.claim_amount,
        "insured_flagged": insured.flagged if insured else False,
    }


def check_claim_history(
    claim_id: Annotated[str, "Claim ID to check the insured's history for"],
) -> Dict:
    """Analyze the insured's claim history: frequency, patterns, serial claimer indicators."""
    _tool_log("check_claim_history", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    insured = _get_insured(claim.insured_id)
    all_claims = [c for c in _context.supplemental_claims if c.insured_id == claim.insured_id]

    type_counts = {}
    for c in all_claims:
        type_counts[c.claim_type] = type_counts.get(c.claim_type, 0) + 1
    total_claimed = sum(c.claim_amount for c in all_claims)

    flags = []
    history_count = insured.claim_history_count if insured else 0
    effective_count = max(len(all_claims), history_count)
    if effective_count >= 3:
        flags.append(f"Serial claimer: {effective_count} claims in tracking period")
    injury_claims = sum(1 for c in all_claims if c.injury_claimed)
    if injury_claims >= 2:
        flags.append(f"Repeat injury claims: {injury_claims}x with injury component")
    if total_claimed > 40000:
        flags.append(f"High total claimed: ${total_claimed:,.2f}")

    return {
        "claim_id": claim_id,
        "insured_id": claim.insured_id,
        "insured_name": insured.full_name if insured else "Unknown",
        "total_claims": effective_count,
        "claims_in_dataset": len(all_claims),
        "claim_history_count": history_count,
        "total_amount_claimed": round(total_claimed, 2),
        "type_distribution": type_counts,
        "flags": flags,
        "claims": [
            {"claim_id": c.claim_id, "type": c.claim_type, "amount": c.claim_amount,
             "date": c.date_filed, "injury": c.injury_claimed}
            for c in all_claims[:10]
        ],
    }


def verify_estimate(
    claim_id: Annotated[str, "Claim ID to verify the repair estimate for"],
) -> Dict:
    """Check the repair estimate against the vehicle ACV for inflation / total-loss padding."""
    _tool_log("verify_estimate", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    estimate = _get_estimate(claim)
    vehicle = _get_vehicle(claim.vehicle_id)
    shop = _get_shop(claim.shop_id) if claim.shop_id else None
    acv = vehicle.acv if vehicle else 0

    flags = []
    if claim.claim_type in ("collision", "comprehensive", "liability") and not estimate:
        flags.append("No repair estimate on file for a damage claim")
    if acv and claim.claim_amount > acv:
        flags.append(f"⚠ Claim ${claim.claim_amount:,.2f} EXCEEDS vehicle ACV ${acv:,.2f} — total-loss padding risk")
    if estimate and acv and estimate.amount > acv * 1.1:
        flags.append(f"⚠ Estimate ${estimate.amount:,.2f} is {estimate.amount/acv:.1f}x the vehicle ACV")
    if shop and shop.on_watchlist:
        flags.append(f"⚠ Estimate from WATCHLISTED shop: {shop.name}")

    return {
        "claim_id": claim_id,
        "estimate_amount": estimate.amount if estimate else None,
        "estimate_line_items": estimate.line_items if estimate else [],
        "vehicle_acv": acv,
        "claim_amount": claim.claim_amount,
        "amount_vs_acv_ratio": round(claim.claim_amount / acv, 2) if acv else None,
        "shop_name": shop.name if shop else "N/A",
        "shop_on_watchlist": shop.on_watchlist if shop else False,
        "flags": flags,
    }


def check_repair_shop_risk(
    claim_id: Annotated[str, "Claim ID to check the repair shop for"],
) -> Dict:
    """Check repair-shop watchlist and network status, and count other claims routed through it."""
    _tool_log("check_repair_shop_risk", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    shop = _get_shop(claim.shop_id) if claim.shop_id else None
    flags = []
    if not shop:
        return {"claim_id": claim_id, "note": "No repair shop on this claim", "flags": []}

    if shop.on_watchlist:
        flags.append(f"⚠ SHOP ON WATCHLIST: {shop.name}")
    if not shop.in_network:
        flags.append(f"Shop NOT in approved network: {shop.name}")
    if not shop.verified:
        flags.append(f"Shop unverified: {shop.name}")

    shop_claims = [c for c in _context.supplemental_claims
                   if c.shop_id == claim.shop_id and c.claim_id != claim_id]

    return {
        "claim_id": claim_id,
        "shop_id": claim.shop_id,
        "shop_name": shop.name,
        "state": shop.state,
        "on_watchlist": shop.on_watchlist,
        "in_network": shop.in_network,
        "verified": shop.verified,
        "notes": shop.notes,
        "other_claims_at_shop": len(shop_claims),
        "flags": flags,
    }


def analyze_documents(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Review documents submitted: repair estimates, police reports, damage photos, medical bills."""
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
            "doc_id": doc.doc_id, "type": doc.doc_type, "provider": doc.provider_name,
            "date": doc.date_created, "format": doc.format_type,
            "has_header": doc.has_header, "has_signature": doc.has_signature,
            "amount": doc.amount_on_doc,
        }
        if doc.tampering_indicators:
            d["tampering_indicators"] = doc.tampering_indicators
            flags.append(f"Document {doc.doc_id}: tampering — {', '.join(doc.tampering_indicators)}")
        doc_summary.append(d)

    expected = {
        "collision": ["repair_estimate"],
        "comprehensive": ["repair_estimate"],
        "theft": ["police_report"],
        "liability": ["police_report"],
        "medical_payments": ["medical_bill"],
    }
    present = [d.doc_type for d in docs]
    for req in expected.get(claim.claim_type, []):
        if req not in present:
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
    """Find related claims: same insured, same vehicle, same repair shop."""
    _tool_log("find_related_claims", f"Finding related for {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    same_insured = [c for c in _context.supplemental_claims
                    if c.insured_id == claim.insured_id and c.claim_id != claim_id]
    same_vehicle = [c for c in _context.supplemental_claims
                    if c.vehicle_id == claim.vehicle_id and c.claim_id != claim_id]
    same_shop = []
    if claim.shop_id:
        same_shop = [c for c in _context.supplemental_claims
                     if c.shop_id == claim.shop_id and c.claim_id != claim_id]

    def _brief(c):
        return {"claim_id": c.claim_id, "type": c.claim_type, "amount": c.claim_amount,
                "date_filed": c.date_filed}

    return {
        "claim_id": claim_id,
        "same_insured": [_brief(c) for c in same_insured[:10]],
        "same_vehicle": [_brief(c) for c in same_vehicle[:10]],
        "same_shop": [_brief(c) for c in same_shop[:10]],
        "total_related": len(same_insured) + len(same_vehicle) + len(same_shop),
    }


# ── Workflow Tools ───────────────────────────────────────────────────────────

def check_workflow_tasks(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Check workflow task status: INITIAL_REVIEW, ESTIMATE_REVIEW, SHOP_VERIFICATION, INJURY_REVIEW."""
    _tool_log("check_workflow_tasks", f"Checking {claim_id}")
    tasks = [t for t in _context.supplemental_data.get("workflow_tasks", []) if t.claim_id == claim_id]
    task_list = [{
        "task_id": t.task_id, "type": t.task_type, "status": t.status,
        "assigned_date": t.assigned_date, "due_date": t.due_date, "days_waiting": t.days_waiting,
    } for t in tasks]
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
    """Get full policy: coverage limits, effective/expiration dates, deductible, premium."""
    _tool_log("get_policy_details", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}
    policy = _get_policy(claim.policy_id)
    if not policy:
        return {"claim_id": claim_id, "error": "No policy found"}
    vehicle = _get_vehicle(policy.vehicle_id)
    return {
        "claim_id": claim_id,
        "policy_id": policy.policy_id,
        "insured_id": policy.insured_id,
        "vehicle": f"{vehicle.year} {vehicle.make} {vehicle.model}" if vehicle else policy.vehicle_id,
        "effective_date": policy.effective_date,
        "expiration_date": policy.expiration_date,
        "coverage_collision": policy.coverage_collision,
        "coverage_comprehensive": policy.coverage_comprehensive,
        "coverage_liability": policy.coverage_liability,
        "coverage_medical_payments": policy.coverage_medical_payments,
        "deductible": policy.deductible,
        "premium": policy.premium,
        "status": policy.status,
    }


def match_claim_to_coverage(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Verify claim type matches policy, amount within limits, incident within coverage period."""
    _tool_log("match_claim_to_coverage", f"Checking {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}
    policy = _get_policy(claim.policy_id)
    if not policy:
        return {"claim_id": claim_id, "error": "Policy not found"}

    issues = []
    coverage_name = {
        "collision": "Collision", "comprehensive": "Comprehensive", "theft": "Comprehensive (Theft)",
        "liability": "Liability", "medical_payments": "Medical Payments",
    }.get(claim.claim_type, "Unknown")
    coverage_limit = _coverage_for_type(policy, claim.claim_type)

    if coverage_limit and claim.claim_amount > coverage_limit:
        issues.append(f"Claim ${claim.claim_amount:,.2f} EXCEEDS {coverage_name} limit ${coverage_limit:,.2f}")

    try:
        incident = datetime.strptime(claim.date_of_incident, "%Y-%m-%d")
        eff = datetime.strptime(policy.effective_date, "%Y-%m-%d")
        exp = datetime.strptime(policy.expiration_date, "%Y-%m-%d")
        if incident < eff:
            issues.append(f"Incident {claim.date_of_incident} BEFORE coverage start {policy.effective_date}")
        if incident > exp:
            issues.append(f"Incident {claim.date_of_incident} AFTER coverage end {policy.expiration_date}")
    except (ValueError, TypeError):
        pass

    return {
        "claim_id": claim_id,
        "coverage_type": coverage_name,
        "coverage_limit": coverage_limit,
        "claim_amount": claim.claim_amount,
        "within_limits": (not coverage_limit) or claim.claim_amount <= coverage_limit,
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
    """Execute the full 7-step car claims adjuster checklist."""
    _tool_log("run_fraud_checklist", f"Running for {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    steps = []

    step1_issues = []
    if not claim.insured_id:
        step1_issues.append("Missing insured ID")
    if not claim.policy_id:
        step1_issues.append("Missing policy ID")
    if not claim.date_of_incident:
        step1_issues.append("Missing incident date")
    steps.append({"step": 1, "name": "Initial Claim Review", "status": "fail" if step1_issues else "pass", "issues": step1_issues})

    policy = _get_policy(claim.policy_id)
    step2_issues = []
    if not policy:
        step2_issues.append("Policy not found")
    elif policy.status != "active":
        step2_issues.append(f"Policy status: {policy.status}")
    steps.append({"step": 2, "name": "Policy Coverage Verification", "status": "fail" if step2_issues else "pass", "issues": step2_issues})

    estimate = _get_estimate(claim)
    step3_issues = []
    if claim.claim_type in ("collision", "comprehensive", "liability") and not estimate:
        step3_issues.append("No repair estimate found")
    steps.append({"step": 3, "name": "Damage Documentation Check", "status": "fail" if step3_issues else "pass", "issues": step3_issues})

    step4_issues = []
    if claim.shop_id:
        shop = _get_shop(claim.shop_id)
        if shop and shop.on_watchlist:
            step4_issues.append(f"Shop {shop.name} is on WATCHLIST")
        elif shop and (not shop.verified or not shop.in_network):
            step4_issues.append(f"Shop {shop.name} not in verified network")
    steps.append({"step": 4, "name": "Repair Shop Verification", "status": "fail" if step4_issues else "pass", "issues": step4_issues})

    rules = _context.claim_rules.get(claim_id, [])
    triggered = [r for r in rules if r.triggered]
    blocks = [r for r in triggered if r.severity == "BLOCK"]
    step5_issues = [f"{r.rule_id}: {r.rule_name}" for r in blocks]
    steps.append({"step": 5, "name": "Fraud Screening", "status": "fail" if blocks else ("needs_review" if triggered else "pass"), "issues": step5_issues})

    step6_issues = []
    vehicle = _get_vehicle(claim.vehicle_id)
    if vehicle and vehicle.acv and claim.claim_amount > vehicle.acv * 1.1:
        step6_issues.append(f"Claim {claim.claim_amount/vehicle.acv:.1f}x the vehicle ACV")
    steps.append({"step": 6, "name": "Valuation Review", "status": "fail" if step6_issues else "pass", "issues": step6_issues})

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
    """Generate escalation dossier with all car claim intelligence."""
    _tool_log("compile_dossier", f"Compiling for {claim_id}")
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    insured = _get_insured(claim.insured_id)
    policy = _get_policy(claim.policy_id)
    vehicle = _get_vehicle(claim.vehicle_id)
    shop = _get_shop(claim.shop_id) if claim.shop_id else None
    rules = _context.claim_rules.get(claim_id, [])
    risk = _context.claim_risk_scores.get(claim_id)
    triggered = [r for r in rules if r.triggered]

    dossier = f"""# Auto Claim Investigation Dossier

## Claim: {claim_id}
- **Type**: {claim.claim_type.replace('_', ' ').title()}
- **Amount**: ${claim.claim_amount:,.2f}
- **Date Filed**: {claim.date_filed}
- **Incident Date**: {claim.date_of_incident}
- **Status**: {claim.status}

## Insured
- **Name**: {insured.full_name if insured else 'Unknown'}
- **ID**: {claim.insured_id}
- **Flagged**: {'YES ⚠' if (insured and insured.flagged) else 'No'}
- **Prior Claims**: {insured.claim_history_count if insured else 0}

## Vehicle
- **Vehicle**: {f'{vehicle.year} {vehicle.make} {vehicle.model}' if vehicle else 'Unknown'}
- **VIN**: {vehicle.vin if vehicle else 'N/A'}
- **ACV**: ${vehicle.acv:,.2f}{'' if vehicle else ''}

## Repair Shop
- **Shop**: {shop.name if shop else 'N/A'}
- **Watchlist**: {'YES ⚠' if (shop and shop.on_watchlist) else 'No'}
- **In Network**: {'No ⚠' if (shop and not shop.in_network) else 'Yes' if shop else 'N/A'}

## Policy
- **Policy ID**: {policy.policy_id if policy else 'N/A'}
- **Coverage Period**: {policy.effective_date if policy else '?'} to {policy.expiration_date if policy else '?'}
- **Coverage ({claim.claim_type})**: ${_coverage_for_type(policy, claim.claim_type):,.2f}
- **Deductible**: ${policy.deductible:,.2f}{'' if policy else ''}

## Risk Assessment
- **Score**: {risk.total_score if risk else 0}/100 ({risk.tier if risk else 'N/A'})
- **Top Factors**: {', '.join(risk.top_factors) if risk else 'None'}

## Rules Triggered ({len(triggered)})
"""
    for r in triggered:
        dossier += f"- **{r.rule_id}** [{r.severity}]: {r.rule_name} — {r.explanation}\n"

    if claim.notes:
        dossier += f"\n## Investigation Notes\n{claim.notes}\n"

    dossier += f"\n---\n*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · Car Insurance SIU*\n"

    return {
        "claim_id": claim_id,
        "dossier": dossier,
        "risk_score": risk.total_score if risk else 0,
        "rules_triggered": len(triggered),
    }


# ── Tool Registry ────────────────────────────────────────────────────────────

ALL_CAR_TOOLS = [
    check_eligibility,
    check_claim_history,
    verify_estimate,
    check_repair_shop_risk,
    analyze_documents,
    find_related_claims,
    check_workflow_tasks,
    get_policy_details,
    match_claim_to_coverage,
    explain_risk_score,
    run_fraud_checklist,
    compile_dossier,
]
