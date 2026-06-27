"""15 deterministic rules (R-001 to R-015) for supplemental health claims + 3 new rules from real cases (R-016 to R-018)."""

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


@dataclass
class Rule:
    rule_id: str
    name: str
    severity: str
    description: str
    evaluate: object = None  # callable


def _days_between(d1: str, d2: str) -> int:
    try:
        dt1 = datetime.strptime(d1, "%Y-%m-%d")
        dt2 = datetime.strptime(d2, "%Y-%m-%d")
        return abs((dt2 - dt1).days)
    except (ValueError, TypeError):
        return 9999


def _get_member_deps(context: Dict, member_id: str) -> List:
    return [d for d in context.get("dependents", []) if d.member_id == member_id]


def _get_member_claims(context: Dict, member_id: str) -> List:
    return [c for c in context.get("claims", []) if c.member_id == member_id]


def _get_provider_claims(context: Dict, provider_id: str) -> List:
    return [c for c in context.get("claims", []) if c.provider_id == provider_id]


def _get_member(context: Dict, member_id: str):
    return next((m for m in context.get("members", []) if m.member_id == member_id), None)


def _get_policy(context: Dict, policy_id: str):
    return next((p for p in context.get("policies", []) if p.policy_id == policy_id), None)


# ── Rule Definitions ─────────────────────────────────────────────────────────

def r001_excessive_dependents(claim, context) -> RuleResult:
    """R-001: More than 10 dependents under single member -> BLOCK"""
    deps = _get_member_deps(context, claim.member_id)
    count = len(deps)
    triggered = count > 10
    return RuleResult(
        rule_id="R-001", rule_name="Excessive Dependents",
        severity="BLOCK", triggered=triggered,
        explanation=f"Member has {count} dependents (threshold: 10)" if triggered else f"Member has {count} dependents (within normal range)",
        details={"dependent_count": count, "threshold": 10},
    )


def r002_rapid_dependent_filing(claim, context) -> RuleResult:
    """R-002: >5 dependent claims filed in 30 days -> BLOCK"""
    member_claims = _get_member_claims(context, claim.member_id)
    recent = [c for c in member_claims if c.dependent_id and
              _days_between(c.date_filed, claim.date_filed) <= 30]
    count = len(recent)
    triggered = count > 5
    return RuleResult(
        rule_id="R-002", rule_name="Rapid Dependent Filing",
        severity="BLOCK", triggered=triggered,
        explanation=f"{count} dependent claims in 30-day window (threshold: 5)" if triggered else f"{count} dependent claims in 30 days (normal)",
        details={"recent_dep_claims": count, "threshold": 5},
    )


def r003_termination_rush(claim, context) -> RuleResult:
    """R-003: Claim filed within 14 days of termination -> FLAG"""
    member = _get_member(context, claim.member_id)
    if not member or not member.termination_date:
        return RuleResult("R-003", "Termination Rush Filing", "FLAG", False, "No termination date on record")
    days = _days_between(claim.date_filed, member.termination_date)
    triggered = days <= 14
    return RuleResult(
        rule_id="R-003", rule_name="Termination Rush Filing",
        severity="FLAG", triggered=triggered,
        explanation=f"Claim filed {days} days from termination (threshold: 14)" if triggered else f"Termination {days} days away (no rush)",
        details={"days_to_termination": days, "threshold": 14},
    )


def r004_policy_change_proximity(claim, context) -> RuleResult:
    """R-004: Policy ownership/beneficiary changed within 90 days of claim -> FLAG"""
    policy = _get_policy(context, claim.policy_id)
    if not policy:
        return RuleResult("R-004", "Recent Policy Change", "FLAG", False, "Policy not found")
    triggered = False
    change_days = None
    if policy.owner_change_date:
        d = _days_between(policy.owner_change_date, claim.date_filed)
        if d <= 90:
            triggered = True
            change_days = d
    if policy.beneficiary_change_date:
        d = _days_between(policy.beneficiary_change_date, claim.date_filed)
        if d <= 90:
            triggered = True
            change_days = min(change_days or 9999, d)
    return RuleResult(
        rule_id="R-004", rule_name="Recent Policy Change",
        severity="FLAG", triggered=triggered,
        explanation=f"Policy changed {change_days} days before claim (threshold: 90)" if triggered else "No recent policy changes",
        details={"change_days": change_days, "threshold": 90},
    )


def r005_no_facility_record(claim, context) -> RuleResult:
    """R-005: Accident/hospital claim with no facility -> FLAG"""
    if claim.claim_type not in ("accident", "hospital_indemnity"):
        return RuleResult("R-005", "No Facility Record", "FLAG", False, "Not applicable to this claim type")
    triggered = claim.facility_id is None
    return RuleResult(
        rule_id="R-005", rule_name="No Facility Record",
        severity="FLAG", triggered=triggered,
        explanation="No facility record linked to claim" if triggered else "Facility record present",
        details={"has_facility": not triggered},
    )


def r006_provider_volume(claim, context) -> RuleResult:
    """R-006: Provider >50 claims in quarter -> FLAG"""
    prov_claims = _get_provider_claims(context, claim.provider_id)
    count = len(prov_claims)
    triggered = count > 50
    return RuleResult(
        rule_id="R-006", rule_name="High-Volume Provider",
        severity="FLAG", triggered=triggered,
        explanation=f"Provider has {count} claims this period (threshold: 50)" if triggered else f"Provider has {count} claims (normal volume)",
        details={"provider_claim_count": count, "threshold": 50},
    )


def r007_duplicate_claim(claim, context) -> RuleResult:
    """R-007: Claim appears to be resubmission of existing claim -> BLOCK"""
    triggered = claim.is_resubmission
    return RuleResult(
        rule_id="R-007", rule_name="Duplicate/Resubmission",
        severity="BLOCK", triggered=triggered,
        explanation=f"Resubmission of {claim.original_claim_id}" if triggered else "No duplicate detected",
        details={"is_resubmission": triggered, "original": claim.original_claim_id},
    )


def r008_amount_outlier(claim, context) -> RuleResult:
    """R-008: Claim amount >3x average for claim type -> FLAG"""
    type_claims = [c for c in context.get("claims", []) if c.claim_type == claim.claim_type]
    if not type_claims:
        return RuleResult("R-008", "Amount Outlier", "FLAG", False, "No comparison data")
    avg = sum(c.claim_amount for c in type_claims) / len(type_claims)
    ratio = claim.claim_amount / avg if avg > 0 else 0
    triggered = ratio > 3.0
    return RuleResult(
        rule_id="R-008", rule_name="Amount Outlier",
        severity="FLAG", triggered=triggered,
        explanation=f"Claim amount ${claim.claim_amount:,.2f} is {ratio:.1f}x average ${avg:,.2f}" if triggered else f"Amount ${claim.claim_amount:,.2f} within normal range (avg ${avg:,.2f})",
        details={"claim_amount": claim.claim_amount, "avg_amount": round(avg, 2), "ratio": round(ratio, 2)},
    )


def r009_early_tenure_claim(claim, context) -> RuleResult:
    """R-009: Claim filed within 60 days of hire -> INFO"""
    member = _get_member(context, claim.member_id)
    if not member:
        return RuleResult("R-009", "Early Tenure Claim", "INFO", False, "Member not found")
    days = _days_between(member.hire_date, claim.date_filed)
    triggered = days <= 60
    return RuleResult(
        rule_id="R-009", rule_name="Early Tenure Claim",
        severity="INFO", triggered=triggered,
        explanation=f"Claim filed {days} days after hire (threshold: 60)" if triggered else f"Hired {days} days ago (established employee)",
        details={"days_since_hire": days, "threshold": 60},
    )


def r010_shared_address(claim, context) -> RuleResult:
    """R-010: Member shares address with 3+ other members -> FLAG"""
    member = _get_member(context, claim.member_id)
    if not member or not member.address_id:
        return RuleResult("R-010", "Shared Address", "FLAG", False, "No address on file")
    same_addr = [m for m in context.get("members", []) if m.address_id == member.address_id and m.member_id != member.member_id]
    count = len(same_addr)
    triggered = count >= 3
    return RuleResult(
        rule_id="R-010", rule_name="Shared Address",
        severity="FLAG", triggered=triggered,
        explanation=f"Address shared with {count} other members (threshold: 3)" if triggered else f"Address shared with {count} others (normal)",
        details={"shared_count": count, "threshold": 3},
    )


def r011_surgical_emergency_mismatch(claim, context) -> RuleResult:
    """R-011: Elective procedure coded as emergency -> FLAG"""
    elective_codes = ["27447", "28292", "23472"]  # Knee/bunion/shoulder replacements
    if claim.claim_type != "hospital_indemnity":
        return RuleResult("R-011", "Surgical/Emergency Mismatch", "FLAG", False, "Not applicable")
    has_elective = any(code in claim.procedure_codes for code in elective_codes)
    triggered = has_elective
    return RuleResult(
        rule_id="R-011", rule_name="Surgical/Emergency Mismatch",
        severity="FLAG", triggered=triggered,
        explanation="Elective procedure codes found on hospital indemnity claim" if triggered else "No elective procedure mismatch",
        details={"procedure_codes": claim.procedure_codes},
    )


def r012_multiple_contact_attempts(claim, context) -> RuleResult:
    """R-012: >5 contact attempts on single claim -> INFO"""
    triggered = claim.contact_count > 5
    return RuleResult(
        rule_id="R-012", rule_name="Excessive Contact Attempts",
        severity="INFO", triggered=triggered,
        explanation=f"{claim.contact_count} contact attempts (threshold: 5)" if triggered else f"{claim.contact_count} contacts (normal)",
        details={"contact_count": claim.contact_count, "threshold": 5},
    )


def r013_disability_portal_critical(claim, context) -> RuleResult:
    """R-013: Critical illness claim filed through disability portal -> INFO"""
    triggered = claim.claim_source == "disability_portal" and claim.claim_type == "critical_illness"
    return RuleResult(
        rule_id="R-013", rule_name="Disability Portal Critical Illness",
        severity="INFO", triggered=triggered,
        explanation="Critical illness claim filed through disability portal — verify coordination" if triggered else "Standard filing channel",
        details={"claim_source": claim.claim_source, "claim_type": claim.claim_type},
    )


def r014_suspicious_banner(claim, context) -> RuleResult:
    """R-014: Member has existing suspicious banner -> BLOCK"""
    member = _get_member(context, claim.member_id)
    if not member:
        return RuleResult("R-014", "Suspicious Banner Active", "BLOCK", False, "Member not found")
    triggered = member.suspicious_banner
    return RuleResult(
        rule_id="R-014", rule_name="Suspicious Banner Active",
        severity="BLOCK", triggered=triggered,
        explanation="Member has active suspicious banner — full fraud review required" if triggered else "No suspicious banner",
        details={"suspicious_banner": triggered},
    )


def r015_family_claim_cluster(claim, context) -> RuleResult:
    """R-015: 3+ family members (member + dependents) filed claims in 100-day window -> FLAG"""
    member = _get_member(context, claim.member_id)
    if not member:
        return RuleResult("R-015", "Family Claim Cluster", "FLAG", False, "Member not found")

    deps = _get_member_deps(context, claim.member_id)
    dep_ids = {d.dependent_id for d in deps}

    # Find all claims by this member or their dependents within 100 days
    family_claims = []
    for c in context.get("claims", []):
        if _days_between(c.date_filed, claim.date_filed) <= 100:
            if c.member_id == claim.member_id or c.dependent_id in dep_ids:
                family_claims.append(c)

    # Count unique family members who filed
    filers = set()
    for fc in family_claims:
        if fc.dependent_id:
            filers.add(fc.dependent_id)
        else:
            filers.add(fc.member_id)

    count = len(filers)
    triggered = count >= 3
    return RuleResult(
        rule_id="R-015", rule_name="Family Claim Cluster",
        severity="FLAG", triggered=triggered,
        explanation=f"{count} family members filed claims in last 100 days (threshold: 3)" if triggered else f"{count} family filers in 100 days (normal)",
        details={"family_filer_count": count, "threshold": 3},
    )


# ── All Rules ────────────────────────────────────────────────────────────────

def r016_mobile_scan_app_source(claim, context) -> RuleResult:
    """R-016: Document submitted via mobile scan app (CamScanner etc.) -> FLAG"""
    docs = [d for d in context.get("documents", []) if d.claim_id == claim.claim_id]
    mobile_docs = [d for d in docs
                   if getattr(d, "source_type", "") == "MOBILE_SCAN"
                   or getattr(d, "metadata_app_signature", None) is not None]
    triggered = len(mobile_docs) > 0
    app_names = list({d.metadata_app_signature for d in mobile_docs if d.metadata_app_signature})
    return RuleResult(
        rule_id="R-016", rule_name="Mobile Scan App Source",
        severity="FLAG", triggered=triggered,
        explanation=(f"Document submitted via {app_names[0] if app_names else 'mobile scan app'} "
                     f"({len(mobile_docs)} doc(s))")
                    if triggered else "No mobile scan documents detected",
        details={"mobile_doc_count": len(mobile_docs), "app_signatures": app_names},
    )


def r017_hospital_indemnity_stacking(claim, context) -> RuleResult:
    """R-017: 4+ claims for same batch event with 2+ relationship types -> FLAG"""
    batch_id = getattr(claim, "batch_claim_id", None)
    if not batch_id:
        return RuleResult("R-017", "Hospital Indemnity Stacking", "FLAG", False,
                          "No batch claim ID — stacking not applicable")
    batch_claims = [c for c in context.get("claims", [])
                    if getattr(c, "batch_claim_id", None) == batch_id]
    rel_types = {getattr(c, "relationship_type", "SELF") for c in batch_claims}
    triggered = len(batch_claims) >= 4 and len(rel_types) >= 2
    return RuleResult(
        rule_id="R-017", rule_name="Hospital Indemnity Stacking",
        severity="FLAG", triggered=triggered,
        explanation=(f"{len(batch_claims)} claims in batch {batch_id} across "
                     f"{len(rel_types)} relationship types")
                    if triggered else (
                     f"Batch has {len(batch_claims)} claims, {len(rel_types)} rel-type(s) — below threshold"),
        details={"batch_claim_count": len(batch_claims),
                 "relationship_types": list(rel_types), "batch_id": batch_id},
    )


def r018_document_visual_inconsistencies(claim, context) -> RuleResult:
    """R-018: Font, alignment, or color consistency score < 0.7 -> FLAG"""
    docs = [d for d in context.get("documents", []) if d.claim_id == claim.claim_id]
    inconsistent = []
    for d in docs:
        font = getattr(d, "font_consistency_score", 1.0)
        align = getattr(d, "alignment_score", 1.0)
        color = getattr(d, "color_consistency_score", 1.0)
        if font < 0.7 or align < 0.7 or color < 0.7:
            inconsistent.append({"doc_id": d.doc_id, "font": font,
                                  "alignment": align, "color": color})
    triggered = len(inconsistent) > 0
    return RuleResult(
        rule_id="R-018", rule_name="Document Visual Inconsistencies",
        severity="FLAG", triggered=triggered,
        explanation=(f"{len(inconsistent)} doc(s) with visual inconsistencies "
                     f"(font/alignment/color < 0.7)")
                    if triggered else "All documents pass visual consistency checks",
        details={"inconsistent_docs": inconsistent},
    )

ALL_RULES = [
    Rule("R-001", "Excessive Dependents", "BLOCK", ">10 dependents under single member"),
    Rule("R-002", "Rapid Dependent Filing", "BLOCK", ">5 dependent claims in 30 days"),
    Rule("R-003", "Termination Rush Filing", "FLAG", "Claim within 14 days of termination"),
    Rule("R-004", "Recent Policy Change", "FLAG", "Policy changed within 90 days of claim"),
    Rule("R-005", "No Facility Record", "FLAG", "Accident/hospital claim with no facility"),
    Rule("R-006", "High-Volume Provider", "FLAG", "Provider >50 claims this period"),
    Rule("R-007", "Duplicate/Resubmission", "BLOCK", "Claim is resubmission of existing claim"),
    Rule("R-008", "Amount Outlier", "FLAG", "Claim amount >3x average for type"),
    Rule("R-009", "Early Tenure Claim", "INFO", "Claim within 60 days of hire"),
    Rule("R-010", "Shared Address", "FLAG", "Address shared with 3+ other members"),
    Rule("R-011", "Surgical/Emergency Mismatch", "FLAG", "Elective procedure coded as emergency"),
    Rule("R-012", "Excessive Contact Attempts", "INFO", ">5 contact attempts on claim"),
    Rule("R-013", "Disability Portal Critical Illness", "INFO", "CI claim from disability portal"),
    Rule("R-014", "Suspicious Banner Active", "BLOCK", "Member has suspicious banner"),
    Rule("R-015", "Family Claim Cluster", "FLAG", "3+ family members filed in 100 days"),
    Rule("R-016", "Mobile Scan App Source", "FLAG", "Document submitted via mobile scan app"),
    Rule("R-017", "Hospital Indemnity Stacking", "FLAG", "4+ claims same event, 2+ relationship types"),
    Rule("R-018", "Document Visual Inconsistencies", "FLAG", "Font/alignment/color score < 0.7"),
]

_RULE_FUNCS = [
    r001_excessive_dependents,
    r002_rapid_dependent_filing,
    r003_termination_rush,
    r004_policy_change_proximity,
    r005_no_facility_record,
    r006_provider_volume,
    r007_duplicate_claim,
    r008_amount_outlier,
    r009_early_tenure_claim,
    r010_shared_address,
    r011_surgical_emergency_mismatch,
    r012_multiple_contact_attempts,
    r013_disability_portal_critical,
    r014_suspicious_banner,
    r015_family_claim_cluster,
    r016_mobile_scan_app_source,
    r017_hospital_indemnity_stacking,
    r018_document_visual_inconsistencies,
]


def run_rules_engine(claim, context: Dict) -> List[RuleResult]:
    """Run all 15 rules against a claim. Returns list of RuleResult."""
    results = []
    for func in _RULE_FUNCS:
        try:
            result = func(claim, context)
            results.append(result)
        except Exception as e:
            results.append(RuleResult(
                rule_id="ERR", rule_name=func.__name__,
                severity="INFO", triggered=False,
                explanation=f"Rule evaluation error: {str(e)[:100]}",
            ))
    return results
