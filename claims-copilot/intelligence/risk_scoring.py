"""Weighted heuristic risk scoring (0-100) for supplemental health claims."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta


@dataclass
class FeatureContribution:
    category: str
    feature_name: str
    raw_value: float
    normalized: float
    weight: float
    contribution: float


@dataclass
class RiskBreakdown:
    total_score: float
    tier: str  # HIGH, MEDIUM, LOW
    feature_contributions: List[FeatureContribution]
    top_factors: List[str]
    rules_boost: float = 0.0


# ── Feature Weights ──────────────────────────────────────────────────────────

CATEGORY_WEIGHTS = {
    "policy": 0.10,
    "member": 0.15,
    "claim": 0.15,
    "provider": 0.10,
    "network": 0.10,
    "temporal": 0.05,
    "rules_boost": 0.35,
}


def _normalize(value: float, min_val: float, max_val: float) -> float:
    if max_val <= min_val:
        return 0.0
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))


def _days_between(d1: str, d2: str) -> int:
    try:
        dt1 = datetime.strptime(d1, "%Y-%m-%d")
        dt2 = datetime.strptime(d2, "%Y-%m-%d")
        return abs((dt2 - dt1).days)
    except (ValueError, TypeError):
        return 9999


def _get_member(context, member_id):
    return next((m for m in context.get("members", []) if m.member_id == member_id), None)


def _get_policy(context, policy_id):
    return next((p for p in context.get("policies", []) if p.policy_id == policy_id), None)


def _get_member_deps(context, member_id):
    return [d for d in context.get("dependents", []) if d.member_id == member_id]


def _get_member_claims(context, member_id):
    return [c for c in context.get("claims", []) if c.member_id == member_id]


def _get_provider_claims(context, provider_id):
    return [c for c in context.get("claims", []) if c.provider_id == provider_id]


# ── Feature Extractors ───────────────────────────────────────────────────────

def _policy_features(claim, context) -> List[FeatureContribution]:
    features = []
    policy = _get_policy(context, claim.policy_id)

    # Policy age (newer = higher risk)
    if policy:
        age_days = _days_between(policy.effective_date, claim.date_filed)
        norm = 1.0 - _normalize(age_days, 0, 1825)  # 5 years
        features.append(FeatureContribution("policy", "policy_age", age_days, norm, 0.4, norm * 0.4))

        # Recent changes
        has_change = 1.0 if (policy.owner_change_date or policy.beneficiary_change_date) else 0.0
        features.append(FeatureContribution("policy", "recent_changes", has_change, has_change, 0.6, has_change * 0.6))
    else:
        features.append(FeatureContribution("policy", "policy_age", 0, 0.5, 0.4, 0.2))
        features.append(FeatureContribution("policy", "recent_changes", 0, 0, 0.6, 0))

    return features


def _member_features(claim, context) -> List[FeatureContribution]:
    features = []
    member = _get_member(context, claim.member_id)

    if member:
        # Tenure (shorter = higher risk)
        tenure_days = _days_between(member.hire_date, claim.date_filed)
        norm_tenure = 1.0 - _normalize(tenure_days, 0, 1095)  # 3 years
        features.append(FeatureContribution("member", "tenure", tenure_days, norm_tenure, 0.3, norm_tenure * 0.3))

        # Dependent count
        deps = _get_member_deps(context, member.member_id)
        dep_norm = _normalize(len(deps), 0, 15)
        features.append(FeatureContribution("member", "dependent_count", len(deps), dep_norm, 0.3, dep_norm * 0.3))

        # Termination proximity
        term_score = 0.0
        if member.termination_date:
            days_to_term = _days_between(claim.date_filed, member.termination_date)
            term_score = 1.0 - _normalize(days_to_term, 0, 90)
        features.append(FeatureContribution("member", "termination_proximity", term_score, term_score, 0.2, term_score * 0.2))

        # Suspicious banner
        banner = 1.0 if member.suspicious_banner else 0.0
        features.append(FeatureContribution("member", "suspicious_banner", banner, banner, 0.2, banner * 0.2))
    else:
        features.append(FeatureContribution("member", "tenure", 0, 0.5, 0.3, 0.15))
        features.append(FeatureContribution("member", "dependent_count", 0, 0, 0.3, 0))
        features.append(FeatureContribution("member", "termination_proximity", 0, 0, 0.2, 0))
        features.append(FeatureContribution("member", "suspicious_banner", 0, 0, 0.2, 0))

    return features


def _claim_features(claim, context) -> List[FeatureContribution]:
    features = []

    # Amount vs average
    type_claims = [c for c in context.get("claims", []) if c.claim_type == claim.claim_type]
    avg = sum(c.claim_amount for c in type_claims) / max(len(type_claims), 1)
    ratio = claim.claim_amount / max(avg, 1)
    amount_norm = _normalize(ratio, 0, 5)
    features.append(FeatureContribution("claim", "amount_ratio", ratio, amount_norm, 0.4, amount_norm * 0.4))

    # Resubmission
    resub = 1.0 if claim.is_resubmission else 0.0
    features.append(FeatureContribution("claim", "is_resubmission", resub, resub, 0.3, resub * 0.3))

    # Contact count
    contact_norm = _normalize(claim.contact_count, 0, 10)
    features.append(FeatureContribution("claim", "contact_count", claim.contact_count, contact_norm, 0.3, contact_norm * 0.3))

    return features


def _provider_features(claim, context) -> List[FeatureContribution]:
    features = []

    prov_claims = _get_provider_claims(context, claim.provider_id)
    volume_norm = _normalize(len(prov_claims), 0, 100)
    features.append(FeatureContribution("provider", "claim_volume", len(prov_claims), volume_norm, 0.5, volume_norm * 0.5))

    # No facility
    no_fac = 1.0 if (claim.facility_id is None and claim.claim_type in ("accident", "hospital_indemnity")) else 0.0
    features.append(FeatureContribution("provider", "no_facility", no_fac, no_fac, 0.5, no_fac * 0.5))

    return features


def _network_features(claim, context) -> List[FeatureContribution]:
    features = []

    member = _get_member(context, claim.member_id)
    if member and member.address_id:
        same_addr = [m for m in context.get("members", [])
                     if m.address_id == member.address_id and m.member_id != member.member_id]
        addr_norm = _normalize(len(same_addr), 0, 5)
        features.append(FeatureContribution("network", "shared_address_count", len(same_addr),
                                            addr_norm, 0.5, addr_norm * 0.5))
    else:
        features.append(FeatureContribution("network", "shared_address_count", 0, 0, 0.5, 0))

    # Family claim density
    member_claims = _get_member_claims(context, claim.member_id)
    deps = _get_member_deps(context, claim.member_id)
    dep_ids = {d.dependent_id for d in deps}
    family_claims = [c for c in context.get("claims", [])
                     if c.member_id == claim.member_id or c.dependent_id in dep_ids]
    family_norm = _normalize(len(family_claims), 0, 10)
    features.append(FeatureContribution("network", "family_claim_density", len(family_claims),
                                        family_norm, 0.5, family_norm * 0.5))

    return features


def _temporal_features(claim, context) -> List[FeatureContribution]:
    features = []

    # Days from service to filing
    dos_to_filed = _days_between(claim.date_of_service, claim.date_filed)
    dos_norm = _normalize(dos_to_filed, 0, 90)
    features.append(FeatureContribution("temporal", "service_to_filing_days", dos_to_filed,
                                        dos_norm, 0.5, dos_norm * 0.5))

    # Recent claim frequency for member
    member_claims = _get_member_claims(context, claim.member_id)
    recent = [c for c in member_claims if _days_between(c.date_filed, claim.date_filed) <= 30]
    freq_norm = _normalize(len(recent), 0, 5)
    features.append(FeatureContribution("temporal", "recent_claim_frequency", len(recent),
                                        freq_norm, 0.5, freq_norm * 0.5))

    return features


# ── Main Scoring Function ────────────────────────────────────────────────────

def score_claim(claim, context: Dict, rules_results: list = None) -> RiskBreakdown:
    """Score a claim 0-100 using weighted features. Returns RiskBreakdown."""

    all_features = []
    category_scores = {}

    extractors = {
        "policy": _policy_features,
        "member": _member_features,
        "claim": _claim_features,
        "provider": _provider_features,
        "network": _network_features,
        "temporal": _temporal_features,
    }

    for cat, func in extractors.items():
        feats = func(claim, context)
        all_features.extend(feats)
        if feats:
            cat_total = sum(f.contribution for f in feats)
            category_scores[cat] = cat_total
        else:
            category_scores[cat] = 0.0

    # Rules boost: add boost based on triggered rules — this is the primary driver
    rules_boost = 0.0
    if rules_results:
        block_count = sum(1 for r in rules_results if r.triggered and r.severity == "BLOCK")
        flag_count = sum(1 for r in rules_results if r.triggered and r.severity == "FLAG")
        info_count = sum(1 for r in rules_results if r.triggered and r.severity == "INFO")
        rules_boost = min(1.0, block_count * 0.5 + flag_count * 0.25 + info_count * 0.05)

    all_features.append(FeatureContribution("rules_boost", "triggered_rules", rules_boost,
                                            rules_boost, 1.0, rules_boost))
    category_scores["rules_boost"] = rules_boost

    # Weighted total — base score from features
    base_total = 0.0
    for cat, weight in CATEGORY_WEIGHTS.items():
        if cat != "rules_boost":
            base_total += category_scores.get(cat, 0.0) * weight

    # Rules boost applied as a direct additive: up to 60 points from rules alone
    rules_direct = rules_boost * 60.0
    # Feature-based score: up to 50 points
    feature_score = base_total * (100.0 / 0.65)  # Normalize since non-boost weights sum to 0.65

    # Combined score
    score = min(100.0, feature_score * 0.4 + rules_direct)

    # Determine tier
    if score >= 60:
        tier = "HIGH"
    elif score >= 30:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    # Top factors
    sorted_feats = sorted(all_features, key=lambda f: f.contribution, reverse=True)
    top_factors = [f"{f.category}.{f.feature_name}: {f.raw_value} (contrib: {f.contribution:.3f})"
                   for f in sorted_feats[:5] if f.contribution > 0]

    return RiskBreakdown(
        total_score=round(score, 1),
        tier=tier,
        feature_contributions=all_features,
        top_factors=top_factors,
        rules_boost=rules_boost,
    )
