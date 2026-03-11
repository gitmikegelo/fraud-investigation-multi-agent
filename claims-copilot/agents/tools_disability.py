"""
Disability claim investigation tools.
"""

from datetime import datetime
from typing import Dict, List, Annotated

_context = None


def set_context(ctx):
    global _context
    _context = ctx


def _find_claim(claim_id: str):
    if not _context or not _context.disability_claims:
        return None
    return next((c for c in _context.disability_claims if c.claim_id == claim_id), None)


def get_claim_timeline(
    claim_id: Annotated[str, "Disability claim ID, e.g. DC-2451"]
) -> Dict:
    """Get chronological timeline of key events for a disability claim."""
    claim = _find_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    events = []
    p = claim.policy

    events.append({"date": p.policy_purchase_date.strftime("%Y-%m-%d"), "event_type": "policy_purchase",
                    "description": f"Policy {p.policy_id} purchased. Benefit: ${p.monthly_benefit:,.0f}/mo"})

    for pc in claim.prior_claims:
        events.append({"date": f"{pc['year']}-01-01", "event_type": "prior_claim",
                        "description": f"Prior claim with {pc['carrier']}: {pc['diagnosis']}. Duration: {pc['duration_months']}mo. Outcome: {pc['outcome']}"})

    events.append({"date": claim.alleged_disability_date.strftime("%Y-%m-%d"), "event_type": "alleged_onset",
                    "description": f"Alleged disability onset ({claim.disability_type}). ICD: {', '.join(claim.icd_codes)}"})

    for rec in claim.medical_records:
        events.append({"date": rec["date"], "event_type": "medical_visit",
                        "description": f"{rec['provider']}: {rec['summary'][:120]}"})

    events.append({"date": claim.claim_filed_date.strftime("%Y-%m-%d"), "event_type": "claim_filed",
                    "description": f"Claim {claim_id} filed"})

    if claim.ime_results:
        events.append({"date": claim.ime_results.get("date", "unknown"), "event_type": "ime_ordered",
                        "description": f"IME by {claim.ime_results.get('physician', 'Unknown')}: {claim.ime_results.get('opinion', '')}"})

    for note in (claim.surveillance_notes or []):
        events.append({"date": note.get("date", "unknown"), "event_type": "surveillance",
                        "description": note.get("content", "Surveillance conducted")})

    for flag in claim.social_media_flags:
        events.append({"date": flag["date"], "event_type": "social_media_flag",
                        "description": f"{flag['platform']}: \"{flag['content']}\""})

    if claim.financial_records and claim.financial_records.get("dissolved_date"):
        events.append({"date": claim.financial_records["dissolved_date"], "event_type": "business_event",
                        "description": f"Business dissolved: {claim.financial_records.get('business_name', 'Unknown')}"})

    events.sort(key=lambda e: e["date"])
    return {"claim_id": claim_id, "claimant_name": p.claimant_name, "timeline": events}


def summarize_medical_records(
    claim_id: Annotated[str, "Disability claim ID"]
) -> Dict:
    """Analyze medical documentation for a disability claim."""
    claim = _find_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    records = claim.medical_records
    providers = claim.treating_providers
    claim_duration_days = (datetime(2026, 3, 1) - claim.alleged_disability_date).days

    consistency_flags = []
    gaps = []

    if len(records) < 3 and claim_duration_days > 90:
        gaps.append(f"Only {len(records)} records for {claim_duration_days}-day claim — thin documentation")
    if len(providers) == 1:
        consistency_flags.append("Single treating provider — no independent corroboration")
    if not any("imaging" in r.get("summary", "").lower() or "mri" in r.get("summary", "").lower() for r in records):
        if claim.disability_type == "musculoskeletal":
            gaps.append("No imaging studies documented for musculoskeletal claim")

    # Check IME vs treating
    supports = sum(1 for r in records if r.get("supports_disability"))
    contradicts = len(records) - supports
    if claim.ime_results:
        ime_opinion = claim.ime_results.get("opinion", "")
        if "not total" in ime_opinion.lower() or "higher" in ime_opinion.lower() or "exceed" in ime_opinion.lower():
            consistency_flags.append(f"IME disagrees with treating: \"{ime_opinion}\"")

    confidence = "strong" if supports > 4 and not consistency_flags else ("weak" if consistency_flags or len(records) < 3 else "moderate")

    return {
        "claim_id": claim_id,
        "treating_providers": [{"name": p["provider_name"], "specialty": p["specialty"],
                                 "relationship_months": p["relationship_months"]} for p in providers],
        "diagnosis_codes": claim.icd_codes,
        "record_count": len(records),
        "claim_duration_days": claim_duration_days,
        "supports_count": supports,
        "contradicts_count": contradicts,
        "consistency_flags": consistency_flags,
        "documentation_gaps": gaps,
        "supports_claimed_disability": supports > contradicts and not consistency_flags,
        "confidence": confidence,
    }


def check_claimant_history(
    claim_id: Annotated[str, "Disability claim ID"]
) -> Dict:
    """Check claimant's prior claim history across carriers."""
    claim = _find_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    priors = claim.prior_claims
    flags = []
    total_benefit = 0

    if len(priors) >= 2:
        flags.append(f"Multiple prior disability claims ({len(priors)})")
    exhausted = [p for p in priors if "exhaust" in p.get("outcome", "").lower()]
    if exhausted:
        flags.append(f"Benefit exhaustion pattern ({len(exhausted)} claims ended at max benefit)")
    for p in priors:
        if "returned to work" in p.get("outcome", "").lower():
            flags.append(f"Quick recovery after benefits ended ({p['carrier']} {p['year']})")

    diagnoses = set(p["diagnosis"] for p in priors)
    if len(diagnoses) > 1:
        flags.append(f"Rotating diagnoses: {', '.join(diagnoses)}")

    for p in priors:
        total_benefit += p.get("duration_months", 0) * 4000  # rough estimate

    return {
        "claim_id": claim_id,
        "claimant_name": claim.policy.claimant_name,
        "prior_claims": priors,
        "pattern_flags": flags,
        "total_prior_claims": len(priors),
        "total_prior_benefit_received": total_benefit,
    }


def get_policy_details(
    claim_id: Annotated[str, "Disability claim ID"]
) -> Dict:
    """Get policy information and risk indicators."""
    claim = _find_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    p = claim.policy
    policy_age_months = max(1, (claim.claim_filed_date - p.policy_purchase_date).days // 30)
    total_premiums = p.annual_premium * (policy_age_months / 12)
    total_potential = p.monthly_benefit * p.benefit_period_months
    ratio = total_potential / total_premiums if total_premiums > 0 else 0

    flags = []
    if policy_age_months < 6:
        flags.append("Policy less than 6 months old at claim")
    elif policy_age_months < 12:
        flags.append("Policy less than 1 year old at claim")
    if ratio > 50:
        flags.append(f"Benefit-to-premium ratio very high ({ratio:.0f}x)")

    return {
        "claim_id": claim_id,
        "policy_id": p.policy_id,
        "claimant_name": p.claimant_name,
        "occupation": p.occupation,
        "employer": p.employer,
        "policy_purchase_date": p.policy_purchase_date.strftime("%Y-%m-%d"),
        "policy_age_months": policy_age_months,
        "monthly_benefit": p.monthly_benefit,
        "annual_premium": p.annual_premium,
        "benefit_to_premium_ratio": round(ratio, 1),
        "elimination_period_days": p.elimination_period_days,
        "benefit_period_months": p.benefit_period_months,
        "risk_flags": flags,
    }


def flag_inconsistencies(
    claim_id: Annotated[str, "Disability claim ID"]
) -> Dict:
    """
    Cross-reference all claim data to find contradictions and innocent explanations.
    
    Returns:
    - Social media flags and activity contradictions (dates, platforms, content)
    - IME vs treating physician disagreements
    - Employment context (PIP, terminations)
    - Financial motives (business closures)
    - Documentation quality issues
    - Suggested innocent explanations for each flag
    """
    claim = _find_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    inconsistencies = []
    innocent = []

    # Social media vs limitations
    if claim.social_media_flags:
        for flag in claim.social_media_flags:
            inconsistencies.append({
                "type": "activity_vs_limitation",
                "severity": "high",
                "description": f"Social media post contradicts claimed limitations",
                "evidence": f"{flag['platform']} ({flag['date']}): \"{flag['content']}\"",
            })
        innocent.append("Social media posts may be old/reposted or represent a brief good day")

    # IME vs treating
    if claim.ime_results:
        opinion = claim.ime_results.get("opinion", "")
        if "not total" in opinion.lower() or "higher" in opinion.lower() or "exceed" in opinion.lower():
            inconsistencies.append({
                "type": "documentation_vs_ime",
                "severity": "high",
                "description": "IME physician disagrees with treating physician on disability level",
                "evidence": f"IME: \"{opinion}\"",
            })
            innocent.append("IME exams are a single snapshot; treating physician sees the patient longitudinally")

    # Employer context
    if claim.employer_statement:
        notes = claim.employer_statement.get("notes", "")
        if "pip" in notes.lower() or "performance" in notes.lower():
            inconsistencies.append({
                "type": "employer_context",
                "severity": "medium",
                "description": "Employment issue preceded disability claim",
                "evidence": notes,
            })
            innocent.append("Workplace stress can genuinely trigger or worsen medical conditions")

    # Financial motive
    if claim.financial_records:
        fr = claim.financial_records
        if fr.get("dissolved_date"):
            inconsistencies.append({
                "type": "financial_motive",
                "severity": "high",
                "description": "Business closure shortly before claim filing",
                "evidence": f"{fr.get('business_name')} dissolved {fr['dissolved_date']}. Benefit ${claim.policy.monthly_benefit:,.0f}/mo vs last income ${fr.get('last_tax_return_income', 0):,.0f}/yr",
            })
            innocent.append("Business failure can cause genuine depression/anxiety that is disabling")

    # Thin documentation for long claim
    duration = (datetime(2026, 3, 1) - claim.alleged_disability_date).days
    if len(claim.medical_records) < 3 and duration > 90:
        inconsistencies.append({
            "type": "documentation_quality",
            "severity": "medium",
            "description": f"Only {len(claim.medical_records)} medical records for {duration}-day claim",
            "evidence": "Expected more frequent medical visits for active disability",
        })
        innocent.append("Patient may have limited access to healthcare or be receiving treatment elsewhere")

    level = "high" if any(i["severity"] == "high" for i in inconsistencies) else ("moderate" if inconsistencies else "low")

    return {
        "claim_id": claim_id,
        "inconsistencies": inconsistencies,
        "overall_concern_level": level,
        "innocent_explanations": innocent,
    }


def find_related_claims(
    claim_id: Annotated[str, "Disability claim ID"]
) -> Dict:
    """Check if treating providers appear in other suspicious claims."""
    claim = _find_claim(claim_id)
    if not claim:
        return {"error": f"Claim {claim_id} not found"}

    all_claims = _context.disability_claims
    provider_results = []
    pattern_detected = False

    for tp in claim.treating_providers:
        pname = tp["provider_name"]
        other = []
        for c in all_claims:
            if c.claim_id == claim_id:
                continue
            if any(p["provider_name"] == pname for p in c.treating_providers):
                other.append({
                    "claim_id": c.claim_id,
                    "claimant_name": c.policy.claimant_name,
                    "diagnosis": c.disability_type,
                    "status": c.status,
                    "red_flag_score": c.red_flag_score,
                })

        flags = []
        suspicious_others = [o for o in other if o["red_flag_score"] > 0.5]
        if len(suspicious_others) >= 2:
            flags.append(f"Supports {len(suspicious_others)} other flagged claims")
            pattern_detected = True

        provider_results.append({
            "provider_name": pname,
            "total_disability_claims_supported": len(other) + 1,
            "other_flagged_claims": suspicious_others,
            "flags": flags,
        })

    return {
        "claim_id": claim_id,
        "treating_providers": provider_results,
        "pattern_detected": pattern_detected,
        "pattern_description": "Enabling provider pattern detected" if pattern_detected else "No provider pattern found",
    }


DISABILITY_TOOLS = [
    get_claim_timeline,
    summarize_medical_records,
    check_claimant_history,
    get_policy_details,
    flag_inconsistencies,
    find_related_claims,
]
