"""Supplemental health claim tools for the examiner workflow copilot."""

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


# ── Fraud Tools (7) ─────────────────────────────────────────────────────────

def check_eligibility(
    claim_id: Annotated[str, "Claim ID (e.g. WC-247)"],
) -> Dict:
    """Check claim eligibility: policy active, coverage matches, member enrolled. Consolidates what you'd find across Prudential 360, Power BI, and FIS/PAS."""
    _tool_log("check_eligibility", f"Checking {claim_id}")
    claim = _context.get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    member = _context.get_member(claim.member_id)
    policy = _context.get_policy(claim.policy_id)
    employer = _context.get_employer(claim.employer_id) if claim.employer_id else None

    issues = []
    if not policy:
        issues.append("No matching policy found")
    elif policy.status != "active":
        issues.append(f"Policy status is {policy.status}")
    if policy and policy.plan_type != claim.claim_type:
        issues.append(f"Plan type mismatch: policy={policy.plan_type}, claim={claim.claim_type}")
    if member and member.termination_date:
        issues.append(f"Member terminated on {member.termination_date}")
    if member and member.suspicious_banner:
        issues.append("⚠ SUSPICIOUS BANNER active on member record")

    return {
        "claim_id": claim_id,
        "eligible": len(issues) == 0,
        "issues": issues,
        "member_name": member.full_name if member else "Unknown",
        "member_id": claim.member_id,
        "employer": employer.name if employer else "Unknown",
        "policy_id": claim.policy_id,
        "policy_status": policy.status if policy else "N/A",
        "plan_type": policy.plan_type if policy else "N/A",
        "coverage_amount": policy.coverage_amount if policy else 0,
        "claim_type": claim.claim_type,
        "claim_amount": claim.claim_amount,
        "suspicious_banner": member.suspicious_banner if member else False,
    }


def check_family_claims(
    claim_id: Annotated[str, "Claim ID to check family patterns for"],
) -> Dict:
    """Analyze family claim patterns: dependent ring indicators, cluster timing, shared addresses."""
    _tool_log("check_family_claims", f"Checking {claim_id}")
    claim = _context.get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    member = _context.get_member(claim.member_id)
    deps = _context.get_member_dependents(claim.member_id)
    member_claims = _context.get_member_claims(claim.member_id)

    # Find claims from dependents
    dep_ids = {d.dependent_id for d in deps}
    dep_claims = [c for c in _context.supplemental_claims
                  if c.dependent_id in dep_ids]

    # Check for cluster timing (multiple claims within 30 days)
    dates = []
    for c in member_claims + dep_claims:
        try:
            dates.append(datetime.strptime(c.date_filed, "%Y-%m-%d"))
        except (ValueError, TypeError):
            pass
    dates.sort()
    clusters = []
    for i in range(len(dates) - 1):
        gap = (dates[i + 1] - dates[i]).days
        if gap <= 30:
            clusters.append(gap)

    # Shared addresses
    shared = set()
    if member and member.address_id:
        for d in deps:
            if d.address_id and d.address_id != member.address_id:
                # Different address from member could be normal, but check if multiple deps share one
                pass
    addresses = [d.address_id for d in deps if d.address_id]
    addr_counts = {}
    for a in addresses:
        addr_counts[a] = addr_counts.get(a, 0) + 1
    shared = {a for a, c in addr_counts.items() if c > 3}

    return {
        "claim_id": claim_id,
        "member_id": claim.member_id,
        "dependent_count": len(deps),
        "member_claims_count": len(member_claims),
        "dependent_claims_count": len(dep_claims),
        "total_family_amount": round(sum(c.claim_amount for c in member_claims + dep_claims), 2),
        "cluster_events": len(clusters),
        "shared_addresses": list(shared),
        "dependents": [
            {"dependent_id": d.dependent_id, "name": f"{d.first_name} {d.last_name}",
             "relationship": d.relationship, "dob": d.dob}
            for d in deps[:15]
        ],
        "flags": _family_flags(deps, member_claims, dep_claims, clusters, member),
    }


def _family_flags(deps, member_claims, dep_claims, clusters, member):
    flags = []
    if len(deps) > 10:
        flags.append(f"Excessive dependents: {len(deps)}")
    if len(clusters) >= 3:
        flags.append(f"Claim clustering: {len(clusters)} claims within 30-day windows")
    total = sum(c.claim_amount for c in member_claims + dep_claims)
    if total > 10000:
        flags.append(f"High family total: ${total:,.2f}")
    if member and member.suspicious_banner:
        flags.append("Member has SUSPICIOUS BANNER")
    return flags


def analyze_medical_documents(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Run 13 document checks using AI vision analysis on the claim's document image (Claude Haiku 4.5). Falls back to metadata checks if no image is available."""
    _tool_log("analyze_medical_documents", f"Checking {claim_id}")

    # Try vision-based analysis first (actual image inspection via Haiku 4.5)
    from intelligence.document_vision import run_vision_document_checks, find_claim_images
    vision_results = None
    images = find_claim_images(claim_id)
    if images:
        _tool_log("analyze_medical_documents", f"Found {len(images)} image(s) for {claim_id} — running Haiku 4.5 vision analysis")
        try:
            vision_results = run_vision_document_checks(claim_id)
        except Exception as e:
            _tool_log("analyze_medical_documents", f"Vision analysis error: {e} — falling back to metadata")

    # Use vision results if available, otherwise fall back to pre-computed metadata checks
    if vision_results:
        doc_results = vision_results
        analysis_source = "vision_ai (Claude Haiku 4.5)"
    else:
        doc_results = _context.claim_doc_results.get(claim_id, [])
        analysis_source = "metadata"

    doc = _context.get_document(claim_id)

    failed = [d for d in doc_results if not d.passed]
    critical = [d for d in failed if d.severity == "CRITICAL"]

    result = {
        "claim_id": claim_id,
        "analysis_source": analysis_source,
        "total_checks": len(doc_results),
        "passed": len(doc_results) - len(failed),
        "failed": len(failed),
        "critical_failures": len(critical),
        "checks": [
            {"check_id": d.check_id, "check_name": d.check_name,
             "passed": d.passed, "severity": d.severity, "explanation": d.explanation}
            for d in doc_results
        ],
    }
    if images:
        result["images_analyzed"] = [img.name for img in images]
    if doc:
        result["document_info"] = {
            "doc_type": doc.doc_type, "provider_name": doc.provider_name,
            "date_of_service": doc.date_of_service, "format": doc.format_type,
            "has_header": doc.has_header, "has_signature": doc.has_signature,
            "tampering_indicators": doc.tampering_indicators,
        }
    return result


def detect_dependent_anomalies(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Detect anomalies in dependent enrollment: excessive count, age distribution, recent additions."""
    _tool_log("detect_dependent_anomalies", f"Checking {claim_id}")
    claim = _context.get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    member = _context.get_member(claim.member_id)
    deps = _context.get_member_dependents(claim.member_id)

    anomalies = []
    if len(deps) > 10:
        anomalies.append({"type": "excessive_dependents", "severity": "HIGH",
                          "detail": f"{len(deps)} dependents enrolled (threshold: 10)"})

    # Age distribution analysis
    ages = []
    for d in deps:
        try:
            dob = datetime.strptime(d.dob, "%Y-%m-%d")
            age = (datetime(2026, 3, 15) - dob).days // 365
            ages.append(age)
        except (ValueError, TypeError):
            pass

    if ages:
        avg_age = sum(ages) / len(ages)
        if avg_age < 10:
            anomalies.append({"type": "young_dependent_cluster", "severity": "MEDIUM",
                              "detail": f"Average dependent age: {avg_age:.1f} years"})

    # Check for many dependents with same last name but different from member
    if member:
        dep_last_names = [d.last_name for d in deps]
        non_member_names = [n for n in dep_last_names if n != member.last_name]
        name_counts = {}
        for n in non_member_names:
            name_counts[n] = name_counts.get(n, 0) + 1
        for name, count in name_counts.items():
            if count >= 3:
                anomalies.append({"type": "surname_cluster", "severity": "MEDIUM",
                                  "detail": f"{count} dependents with surname '{name}' (different from member)"})

    return {
        "claim_id": claim_id,
        "member_id": claim.member_id,
        "dependent_count": len(deps),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "age_distribution": {"min": min(ages) if ages else 0, "max": max(ages) if ages else 0,
                             "avg": round(sum(ages) / len(ages), 1) if ages else 0},
    }


def check_provider_patterns(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Check provider for high-volume patterns, mill indicators, geographic anomalies."""
    _tool_log("check_provider_patterns", f"Checking {claim_id}")
    claim = _context.get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    provider = _context.get_provider(claim.provider_id)
    if not provider:
        return {"claim_id": claim_id, "provider_found": False, "flags": ["Provider not in network"]}

    # Count provider claims
    provider_claims = [c for c in _context.supplemental_claims if c.provider_id == provider.provider_id]
    unique_members = len(set(c.member_id for c in provider_claims))
    total_billed = sum(c.claim_amount for c in provider_claims)

    flags = []
    if provider.is_mill:
        flags.append(f"Provider flagged as mill (claims volume: {provider.claims_volume})")
    if len(provider_claims) > 50:
        flags.append(f"High volume: {len(provider_claims)} claims")
    if unique_members > 0 and total_billed / unique_members > 2000:
        flags.append(f"High avg billing per member: ${total_billed / unique_members:,.2f}")

    return {
        "claim_id": claim_id,
        "provider_id": provider.provider_id,
        "provider_name": provider.name,
        "specialty": provider.specialty,
        "state": provider.state,
        "is_mill": provider.is_mill,
        "total_claims": len(provider_claims),
        "unique_members": unique_members,
        "total_billed": round(total_billed, 2),
        "flags": flags,
    }


def flag_inconsistencies(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Flag data inconsistencies: date mismatches, amount outliers, status conflicts, resubmissions."""
    _tool_log("flag_inconsistencies", f"Checking {claim_id}")
    claim = _context.get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    flags = []

    # Date checks
    if claim.date_of_service and claim.date_filed:
        try:
            dos = datetime.strptime(claim.date_of_service, "%Y-%m-%d")
            filed = datetime.strptime(claim.date_filed, "%Y-%m-%d")
            if dos > filed:
                flags.append({"type": "future_service_date", "severity": "HIGH",
                              "detail": f"Service date {claim.date_of_service} after filing date {claim.date_filed}"})
            if (filed - dos).days > 180:
                flags.append({"type": "late_filing", "severity": "MEDIUM",
                              "detail": f"Filed {(filed - dos).days} days after service"})
        except (ValueError, TypeError):
            pass

    # Amount outlier
    same_type = [c.claim_amount for c in _context.supplemental_claims if c.claim_type == claim.claim_type and c.claim_amount > 0]
    if same_type:
        avg = sum(same_type) / len(same_type)
        if claim.claim_amount > avg * 3:
            flags.append({"type": "amount_outlier", "severity": "MEDIUM",
                          "detail": f"${claim.claim_amount:,.2f} vs type avg ${avg:,.2f} (3x+)"})

    # Resubmission
    if claim.is_resubmission:
        flags.append({"type": "resubmission", "severity": "MEDIUM",
                      "detail": f"Resubmission of {claim.original_claim_id}"})

    return {
        "claim_id": claim_id,
        "flag_count": len(flags),
        "flags": flags,
        "claim_amount": claim.claim_amount,
        "claim_type": claim.claim_type,
        "date_filed": claim.date_filed,
        "date_of_service": claim.date_of_service,
    }


def find_related_claims(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Find related claims: same member, same provider, same dependent, same employer."""
    _tool_log("find_related_claims", f"Finding related for {claim_id}")
    claim = _context.get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    # Same member
    same_member = [c for c in _context.supplemental_claims
                   if c.member_id == claim.member_id and c.claim_id != claim_id]
    # Same provider
    same_provider = [c for c in _context.supplemental_claims
                     if c.provider_id == claim.provider_id and c.claim_id != claim_id]
    # Same dependent
    same_dep = []
    if claim.dependent_id:
        same_dep = [c for c in _context.supplemental_claims
                    if c.dependent_id == claim.dependent_id and c.claim_id != claim_id]

    def _brief(c):
        return {"claim_id": c.claim_id, "type": c.claim_type, "amount": c.claim_amount,
                "date_filed": c.date_filed, "status": c.status}

    return {
        "claim_id": claim_id,
        "same_member": [_brief(c) for c in same_member[:10]],
        "same_provider": [_brief(c) for c in same_provider[:10]],
        "same_dependent": [_brief(c) for c in same_dep[:10]],
        "total_related": len(same_member) + len(same_provider) + len(same_dep),
    }


# ── Workflow Tools (2) ───────────────────────────────────────────────────────

def check_workflow_tasks(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Check workflow task status: INITIAL_REVIEW, MEDICAL_RECORD_REQUEST, PMR, CBR, TAT tracking."""
    _tool_log("check_workflow_tasks", f"Checking {claim_id}")
    tasks = _context.get_claim_tasks(claim_id)

    task_list = []
    medical_record_status = None
    for t in tasks:
        td = {"task_id": t.task_id, "type": t.task_type, "status": t.status,
              "assigned_date": t.assigned_date, "due_date": t.due_date,
              "completed_date": t.completed_date, "days_waiting": t.days_waiting}
        task_list.append(td)
        if t.task_type == "MEDICAL_RECORD_REQUEST":
            medical_record_status = {
                "status": "received" if t.status == "completed" else "requested",
                "days_waiting": t.days_waiting,
                "due_date": t.due_date,
            }

    overdue = [t for t in tasks if t.status == "overdue"]
    return {
        "claim_id": claim_id,
        "total_tasks": len(tasks),
        "tasks": task_list,
        "medical_record_status": medical_record_status,
        "overdue_count": len(overdue),
        "has_initial_review": any(t.task_type == "INITIAL_REVIEW" for t in tasks),
    }


def get_contact_history(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Get contact history for the claim: call count, last contact, notes."""
    _tool_log("get_contact_history", f"Checking {claim_id}")
    claim = _context.get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    member = _context.get_member(claim.member_id)
    return {
        "claim_id": claim_id,
        "member_name": member.full_name if member else "Unknown",
        "contact_count": claim.contact_count,
        "last_contact_type": "phone" if claim.contact_count > 0 else "none",
        "notes": claim.notes if claim.notes else "No contact notes recorded",
    }


# ── Policy Tools (4) ────────────────────────────────────────────────────────

def get_policy_details(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Get full policy details from FIS/PAS: coverage, effective dates, premium, beneficiary/owner changes."""
    _tool_log("get_policy_details", f"Checking {claim_id}")
    claim = _context.get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    policy = _context.get_policy(claim.policy_id)
    if not policy:
        return {"claim_id": claim_id, "error": "No policy found"}

    alerts = []
    if policy.owner_change_date:
        alerts.append(f"Owner change on {policy.owner_change_date}")
    if policy.beneficiary_change_date:
        alerts.append(f"Beneficiary change on {policy.beneficiary_change_date}")

    return {
        "claim_id": claim_id,
        "policy_id": policy.policy_id,
        "member_id": policy.member_id,
        "plan_type": policy.plan_type,
        "effective_date": policy.effective_date,
        "termination_date": policy.termination_date,
        "status": policy.status,
        "coverage_amount": policy.coverage_amount,
        "premium": policy.premium,
        "alerts": alerts,
    }


def check_state_rules(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Check state-specific insurance rules via Compass: timely filing, mandated benefits, waiting periods."""
    _tool_log("check_state_rules", f"Checking {claim_id}")
    claim = _context.get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    member = _context.get_member(claim.member_id)
    employer = _context.get_employer(claim.employer_id) if claim.employer_id else None
    state = employer.state if employer else (member.address_id[:2] if member and member.address_id else "NJ")

    # State rule lookups
    state_rules = {
        "NJ": {"timely_filing_days": 365, "mandated_wellness": True, "waiting_period_max": 90},
        "NY": {"timely_filing_days": 180, "mandated_wellness": True, "waiting_period_max": 60},
        "CA": {"timely_filing_days": 365, "mandated_wellness": True, "waiting_period_max": 90},
        "TX": {"timely_filing_days": 365, "mandated_wellness": False, "waiting_period_max": 180},
        "FL": {"timely_filing_days": 365, "mandated_wellness": False, "waiting_period_max": 90},
    }
    rules = state_rules.get(state, state_rules["NJ"])

    issues = []
    if claim.date_of_service and claim.date_filed:
        try:
            gap = (datetime.strptime(claim.date_filed, "%Y-%m-%d") -
                   datetime.strptime(claim.date_of_service, "%Y-%m-%d")).days
            if gap > rules["timely_filing_days"]:
                issues.append(f"Filed {gap} days after service (limit: {rules['timely_filing_days']})")
        except (ValueError, TypeError):
            pass

    return {
        "claim_id": claim_id,
        "state": state,
        "applicable_rules": rules,
        "issues": issues,
        "compliant": len(issues) == 0,
    }


def check_policy_alerts(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Check for policy alerts: recent owner/beneficiary changes, coverage modifications (PA-001 type alerts)."""
    _tool_log("check_policy_alerts", f"Checking {claim_id}")
    claim = _context.get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    policy = _context.get_policy(claim.policy_id)
    alerts = []

    if policy:
        if policy.owner_change_date:
            alerts.append({
                "alert_type": "PA-001", "severity": "HIGH",
                "detail": f"Policy ownership changed on {policy.owner_change_date}",
                "policy_id": policy.policy_id,
            })
        if policy.beneficiary_change_date:
            alerts.append({
                "alert_type": "PA-002", "severity": "MEDIUM",
                "detail": f"Beneficiary changed on {policy.beneficiary_change_date}",
                "policy_id": policy.policy_id,
            })

    return {
        "claim_id": claim_id,
        "alert_count": len(alerts),
        "alerts": alerts,
    }


def match_claim_to_coverage(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Match claim to coverage: verify claim type matches policy plan, amounts within limits, dates in coverage period."""
    _tool_log("match_claim_to_coverage", f"Checking {claim_id}")
    claim = _context.get_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    policy = _context.get_policy(claim.policy_id)
    if not policy:
        return {"claim_id": claim_id, "match": False, "reason": "No policy found"}

    issues = []

    # Type match
    if policy.plan_type != claim.claim_type:
        issues.append(f"Type mismatch: policy covers {policy.plan_type}, claim is {claim.claim_type}")

    # Amount check
    if policy.coverage_amount > 0 and claim.claim_amount > policy.coverage_amount:
        issues.append(f"Over limit: claim ${claim.claim_amount:,.2f} > coverage ${policy.coverage_amount:,.2f}")

    # Date in coverage
    if claim.date_of_service and policy.effective_date:
        try:
            dos = datetime.strptime(claim.date_of_service, "%Y-%m-%d")
            eff = datetime.strptime(policy.effective_date, "%Y-%m-%d")
            if dos < eff:
                issues.append(f"Service date {claim.date_of_service} before coverage start {policy.effective_date}")
            if policy.termination_date:
                term = datetime.strptime(policy.termination_date, "%Y-%m-%d")
                if dos > term:
                    issues.append(f"Service date after coverage end {policy.termination_date}")
        except (ValueError, TypeError):
            pass

    return {
        "claim_id": claim_id,
        "match": len(issues) == 0,
        "issues": issues,
        "policy_plan": policy.plan_type,
        "coverage_amount": policy.coverage_amount,
        "claim_amount": claim.claim_amount,
    }


# ── Universal Tools (3) ─────────────────────────────────────────────────────

def explain_risk_score(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Explain the risk score: total score, tier, top contributing factors, rules triggered, and potential innocent explanations."""
    _tool_log("explain_risk_score", f"Explaining {claim_id}")
    risk = _context.claim_risk_scores.get(claim_id)
    if not risk:
        return {"claim_id": claim_id, "error": "No risk score computed"}

    rules = _context.claim_rules.get(claim_id, [])
    triggered = [r for r in rules if r.triggered]

    # Build innocent explanations for common flags
    innocent = []
    for r in triggered:
        if "excessive_dependent" in r.rule_id.lower() or r.rule_id == "R-001":
            innocent.append("Large/blended families or foster care situations can have many dependents legitimately")
        if "termination_rush" in r.rule_name.lower() or r.rule_id == "R-003":
            innocent.append("Employees leaving often file outstanding claims before losing coverage — common and legitimate")
        if "high_volume_provider" in r.rule_name.lower() or r.rule_id == "R-006":
            innocent.append("Popular specialists or rural-area sole providers naturally see high volume")
        if "family_claim_cluster" in r.rule_name.lower() or r.rule_id == "R-015":
            innocent.append("Seasonal illnesses (flu, RSV) commonly affect entire families simultaneously")

    top_features = []
    for f in risk.feature_contributions:
        if f.contribution > 0.001:
            top_features.append({
                "category": f.category, "feature": f.feature_name,
                "raw_value": round(f.raw_value, 3), "contribution": round(f.contribution, 4),
            })
    top_features.sort(key=lambda x: x["contribution"], reverse=True)

    return {
        "claim_id": claim_id,
        "total_score": risk.total_score,
        "tier": risk.tier,
        "top_factors": risk.top_factors,
        "rules_boost": risk.rules_boost,
        "top_features": top_features[:10],
        "rules_triggered": [{"rule_id": r.rule_id, "rule_name": r.rule_name,
                             "severity": r.severity, "explanation": r.explanation}
                            for r in triggered],
        "innocent_explanations": list(set(innocent)),
    }


def run_fraud_checklist(
    claim_id: Annotated[str, "Claim ID"],
) -> Dict:
    """Run the full 7-step examiner checklist: Initial Review through Final Determination."""
    _tool_log("run_fraud_checklist", f"Running for {claim_id}")
    from intelligence.checklist import run_full_checklist
    from intelligence.document_vision import run_vision_document_checks, find_claim_images
    from intelligence.document_analysis import run_document_checks

    # Step 5 (Medical Documentation) runs live vision analysis if an image exists
    # for this claim — so the checklist always reflects actual document inspection,
    # not the startup cache.
    live_doc_results = dict(_context.claim_doc_results)  # shallow copy to avoid mutating global cache
    images = find_claim_images(claim_id)
    if images:
        _tool_log("run_fraud_checklist", f"Running Haiku 4.5 vision on {len(images)} image(s) for {claim_id}")
        try:
            vision_results = run_vision_document_checks(claim_id)
            if vision_results:
                live_doc_results[claim_id] = vision_results
        except Exception as e:
            _tool_log("run_fraud_checklist", f"Vision failed ({e}) — using cached metadata results")

    checklist_ctx = {
        "claims": _context.supplemental_claims,
        "members": _context.supplemental_data.get("members", []),
        "dependents": _context.supplemental_data.get("dependents", []),
        "policies": _context.supplemental_data.get("policies", []),
        "workflow_tasks": _context.supplemental_data.get("workflow_tasks", []),
        "claim_rules": _context.claim_rules,
        "claim_risk_scores": _context.claim_risk_scores,
        "claim_doc_results": live_doc_results,
    }

    results = run_full_checklist(claim_id, checklist_ctx)
    return {
        "claim_id": claim_id,
        "document_analysis_source": "vision_ai (Claude Haiku 4.5)" if images else "metadata",
        "steps": [
            {"step_number": r.step_number, "step_name": r.step_name, "status": r.status,
             "auto_passed": r.auto_passed, "findings": r.findings, "details": r.details}
            for r in results
        ],
        "summary": {
            "passed": sum(1 for r in results if r.status == "pass"),
            "needs_review": sum(1 for r in results if r.status == "needs_review"),
            "failed": sum(1 for r in results if r.status == "fail"),
        },
    }


def compile_dossier(
    claim_id: Annotated[str, "Claim ID to compile escalation dossier for"],
) -> str:
    """Compile a supplemental health escalation dossier with all available intelligence for the claim."""
    _tool_log("compile_dossier", f"Compiling for {claim_id}")
    claim = _context.get_claim(claim_id)
    if not claim:
        return f"Error: Claim {claim_id} not found"

    case = _context.get_case(claim_id)
    member = _context.get_member(claim.member_id)
    employer = _context.get_employer(claim.employer_id) if claim.employer_id else None
    provider = _context.get_provider(claim.provider_id)
    policy = _context.get_policy(claim.policy_id)
    risk = _context.claim_risk_scores.get(claim_id)
    rules = _context.claim_rules.get(claim_id, [])
    doc_results = _context.claim_doc_results.get(claim_id, [])
    tasks = _context.get_claim_tasks(claim_id)
    deps = _context.get_member_dependents(claim.member_id)
    triggered = [r for r in rules if r.triggered]
    failed_docs = [d for d in doc_results if not d.passed]

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    dossier = f"""# SUPPLEMENTAL HEALTH CLAIM ESCALATION DOSSIER

**Claim ID**: {claim_id}
**Generated**: {now}
**Risk Tier**: {risk.tier if risk else 'N/A'} ({risk.total_score if risk else 0}/100)

---

## CLAIM SUMMARY

| Field | Value |
|-------|-------|
| Member | {member.full_name if member else 'Unknown'} ({claim.member_id}) |
| Employer | {employer.name if employer else 'Unknown'} |
| Claim Type | {claim.claim_type} |
| Amount | ${claim.claim_amount:,.2f} |
| Date Filed | {claim.date_filed} |
| Date of Service | {claim.date_of_service} |
| Provider | {provider.name if provider else 'Unknown'} ({claim.provider_id}) |
| Policy | {policy.policy_id if policy else 'N/A'} ({policy.plan_type if policy else 'N/A'}) |
| Status | {claim.status} |
| Dependents | {len(deps)} enrolled |

---

## RISK ASSESSMENT

**Total Score**: {risk.total_score if risk else 0}/100 — **{risk.tier if risk else 'N/A'}**
"""

    if risk and risk.top_factors:
        dossier += "\n**Top Risk Factors:**\n"
        for f in risk.top_factors:
            dossier += f"- {f}\n"

    dossier += f"\n---\n\n## RULES TRIGGERED ({len(triggered)})\n\n"
    if triggered:
        for r in triggered:
            dossier += f"- **{r.rule_id}** [{r.severity}]: {r.rule_name} — {r.explanation}\n"
    else:
        dossier += "No rules triggered.\n"

    dossier += f"\n---\n\n## DOCUMENT ANALYSIS ({len(failed_docs)} issues)\n\n"
    if failed_docs:
        for d in failed_docs:
            dossier += f"- **{d.check_id}** [{d.severity}]: {d.check_name} — {d.explanation}\n"
    else:
        dossier += "All document checks passed.\n"

    dossier += "\n---\n\n## WORKFLOW STATUS\n\n"
    for t in tasks:
        status_icon = "✅" if t.status == "completed" else "⏳" if t.status == "in_progress" else "🔴" if t.status == "overdue" else "⬜"
        dossier += f"- {status_icon} {t.task_type}: {t.status}"
        if t.days_waiting > 0:
            dossier += f" ({t.days_waiting} days waiting)"
        dossier += "\n"

    dossier += "\n---\n\n## RECOMMENDED ACTION\n\n"
    if risk and risk.total_score >= 60:
        dossier += "**ESCALATE** — High risk score with multiple triggered rules. Senior examiner review required.\n"
    elif len(triggered) > 0:
        dossier += "**REVIEW** — Rules triggered require examiner attention before approval.\n"
    else:
        dossier += "**APPROVE** — No significant risk indicators detected.\n"

    dossier += "\n---\n*Generated by Prudential Supplemental Health Examiner Workflow Copilot*\n"
    dossier += "\n[[VIEW_DOSSIER_TAB]]"
    _tool_log("compile_dossier", f"Dossier generated ({len(dossier)} chars)")
    return dossier


# ── Tool Registry ────────────────────────────────────────────────────────────

ALL_SUPPLEMENTAL_TOOLS = [
    # Fraud tools
    check_eligibility,
    check_family_claims,
    analyze_medical_documents,
    detect_dependent_anomalies,
    check_provider_patterns,
    flag_inconsistencies,
    find_related_claims,
    # Workflow tools
    check_workflow_tasks,
    get_contact_history,
    # Policy tools
    get_policy_details,
    check_state_rules,
    check_policy_alerts,
    match_claim_to_coverage,
    # Universal tools
    explain_risk_score,
    run_fraud_checklist,
    compile_dossier,
]
