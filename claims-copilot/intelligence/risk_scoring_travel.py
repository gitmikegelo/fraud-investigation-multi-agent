"""Weighted heuristic risk scoring (0-100) for Zurich Travel Guard claims."""

from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime


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


def score_travel_claim(claim, context: Dict, rules_results: List) -> RiskBreakdown:
    """Score a travel claim 0-100 using features (40%) + rules (60%)."""
    contributions = []
    top_factors = []

    # ── Feature-based scoring (40% of total) ─────────────────────────────────

    feature_score = 0.0

    # 1. Claim amount relative to average for type
    type_claims = [c for c in context.get("claims", []) if c.claim_type == claim.claim_type]
    avg_amount = sum(c.claim_amount for c in type_claims) / len(type_claims) if type_claims else 1000
    amount_ratio = claim.claim_amount / avg_amount if avg_amount > 0 else 0
    amount_norm = _normalize(amount_ratio, 0.5, 5.0)
    amount_contribution = amount_norm * 0.12
    feature_score += amount_contribution
    contributions.append(FeatureContribution("claim", "amount_ratio", amount_ratio, amount_norm, 0.12, amount_contribution))
    if amount_ratio > 3.0:
        top_factors.append(f"Claim amount {amount_ratio:.1f}x average for {claim.claim_type}")

    # 2. Destination risk
    dest = next((d for d in context.get("destinations", []) if d.destination_id == claim.destination_id), None)
    dest_risk_score = {"low": 0.1, "medium": 0.4, "high": 0.8}.get(dest.risk_level if dest else "low", 0.1)
    if dest and dest.known_fraud_ring:
        dest_risk_score = 1.0
    dest_contribution = dest_risk_score * 0.08
    feature_score += dest_contribution
    contributions.append(FeatureContribution("destination", "risk_level", dest_risk_score, dest_risk_score, 0.08, dest_contribution))
    if dest and dest.known_fraud_ring:
        top_factors.append(f"Destination {dest.city} has known fraud ring")

    # 3. Traveler claim history
    traveler = next((t for t in context.get("travelers", []) if t.traveler_id == claim.traveler_id), None)
    history_count = traveler.claim_history_count if traveler else 0
    # Also count claims in current dataset
    traveler_claims = [c for c in context.get("claims", []) if c.traveler_id == claim.traveler_id]
    total_history = max(history_count, len(traveler_claims))
    history_norm = _normalize(total_history, 0, 8)
    history_contribution = history_norm * 0.08
    feature_score += history_contribution
    contributions.append(FeatureContribution("traveler", "claim_history", total_history, history_norm, 0.08, history_contribution))
    if total_history >= 3:
        top_factors.append(f"Traveler has {total_history} claims (serial claimer pattern)")

    # 4. Policy timing (purchase to incident proximity)
    policy = next((p for p in context.get("policies", []) if p.policy_id == claim.policy_id), None)
    if policy and claim.date_of_incident:
        days_purchase_to_incident = _days_between(policy.purchase_date, claim.date_of_incident)
        timing_norm = _normalize(30 - days_purchase_to_incident, 0, 30) if days_purchase_to_incident <= 30 else 0.0
    else:
        timing_norm = 0.0
        days_purchase_to_incident = 9999
    timing_contribution = timing_norm * 0.06
    feature_score += timing_contribution
    contributions.append(FeatureContribution("policy", "purchase_proximity", days_purchase_to_incident, timing_norm, 0.06, timing_contribution))
    if days_purchase_to_incident <= 7:
        top_factors.append(f"Policy purchased only {days_purchase_to_incident} days before incident")

    # 5. Provider verification
    provider = next((p for p in context.get("providers", []) if p.provider_id == claim.provider_id), None) if claim.provider_id else None
    provider_risk = 0.0
    if provider:
        if provider.on_watchlist:
            provider_risk = 1.0
            top_factors.append(f"Provider '{provider.name}' is on watchlist")
        elif not provider.verified:
            provider_risk = 0.6
            top_factors.append(f"Provider '{provider.name}' not verified in network")
    provider_contribution = provider_risk * 0.06
    feature_score += provider_contribution
    contributions.append(FeatureContribution("provider", "watchlist_status", provider_risk, provider_risk, 0.06, provider_contribution))

    # ── Rules-based boost (60% of total) ─────────────────────────────────────

    rules_boost = 0.0
    block_count = sum(1 for r in rules_results if r.triggered and r.severity == "BLOCK")
    flag_count = sum(1 for r in rules_results if r.triggered and r.severity == "FLAG")

    # Each BLOCK adds 20 points, each FLAG adds 8 points (capped at 60)
    rules_boost = min(0.60, (block_count * 0.20 + flag_count * 0.08))

    if block_count > 0:
        top_factors.insert(0, f"{block_count} BLOCK rule(s) triggered")
    elif flag_count > 0:
        top_factors.insert(0, f"{flag_count} FLAG rule(s) triggered")

    # ── Final score ──────────────────────────────────────────────────────────

    total_score = round((feature_score + rules_boost) * 100, 1)
    total_score = min(100.0, max(0.0, total_score))

    # Photo-evidence baggage review (R-011) is a top-priority queue signal: claims with
    # submitted luggage photos are surfaced at the top of the examiner queue for forensic
    # image review before payout. Floor their score into the top of the HIGH tier.
    r011 = next((r for r in rules_results if r.rule_id == "R-011" and r.triggered), None)
    if r011 is not None:
        # Floor into the top of the HIGH tier; higher-value claims rank first within it.
        value_nudge = min(9.0, amount_ratio * 2.0)
        total_score = round(min(99.0, max(total_score, 90.0 + value_nudge)), 1)
        top_factors.insert(0, "Luggage photo submitted — priority forensic image review (R-011)")

    if total_score >= 60:
        tier = "HIGH"
    elif total_score >= 30:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    return RiskBreakdown(
        total_score=total_score,
        tier=tier,
        feature_contributions=contributions,
        top_factors=top_factors[:5],
        rules_boost=round(rules_boost * 100, 1),
    )
