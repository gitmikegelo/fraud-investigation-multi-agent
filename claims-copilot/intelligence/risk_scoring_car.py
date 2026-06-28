"""Weighted heuristic risk scoring (0-100) for Car Insurance claims."""

from dataclasses import dataclass, field
from typing import List, Dict


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


def score_car_claim(claim, context: Dict, rules_results: List) -> RiskBreakdown:
    """Score a car claim 0-100 using features (40%) + rules (60%)."""
    contributions = []
    top_factors = []

    feature_score = 0.0

    # 1. Claim amount relative to the vehicle ACV (padding signal) — 15%
    vehicle = next((v for v in context.get("vehicles", []) if v.vehicle_id == claim.vehicle_id), None)
    acv = vehicle.acv if vehicle else 0
    acv_ratio = (claim.claim_amount / acv) if acv > 0 else 0.5
    acv_norm = _normalize(acv_ratio, 0.2, 1.3)
    acv_contribution = acv_norm * 0.15
    feature_score += acv_contribution
    contributions.append(FeatureContribution("vehicle", "amount_vs_acv", acv_ratio, acv_norm, 0.15, acv_contribution))
    if acv_ratio > 1.0:
        top_factors.append(f"Claim is {acv_ratio:.1f}x the vehicle's value (${acv:,.0f})")

    # 2. Repair-shop risk — 12%
    shop = next((s for s in context.get("repair_shops", []) if s.shop_id == claim.shop_id), None) if claim.shop_id else None
    shop_risk = 0.0
    if shop:
        if shop.on_watchlist:
            shop_risk = 1.0
            top_factors.append(f"Repair shop '{shop.name}' is on the fraud watchlist")
        elif not shop.verified or not shop.in_network:
            shop_risk = 0.6
            top_factors.append(f"Repair shop '{shop.name}' is out-of-network / unverified")
    shop_contribution = shop_risk * 0.12
    feature_score += shop_contribution
    contributions.append(FeatureContribution("shop", "watchlist_status", shop_risk, shop_risk, 0.12, shop_contribution))

    # 3. Insured claim history (serial-claimer signal) — 8%
    insured = next((i for i in context.get("insureds", []) if i.insured_id == claim.insured_id), None)
    history_count = insured.claim_history_count if insured else 0
    insured_claims = [c for c in context.get("claims", []) if c.insured_id == claim.insured_id]
    total_history = max(history_count, len(insured_claims))
    history_norm = _normalize(total_history, 0, 6)
    history_contribution = history_norm * 0.08
    feature_score += history_contribution
    contributions.append(FeatureContribution("insured", "claim_history", total_history, history_norm, 0.08, history_contribution))
    if total_history >= 3:
        top_factors.append(f"Insured has {total_history} claims (serial claimer pattern)")

    # 4. Injury claimed without a police report — 5%
    injury_no_report = claim.injury_claimed and not claim.police_report_filed
    injury_norm = 1.0 if injury_no_report else 0.0
    injury_contribution = injury_norm * 0.05
    feature_score += injury_contribution
    contributions.append(FeatureContribution("claim", "injury_no_report", injury_norm, injury_norm, 0.05, injury_contribution))
    if injury_no_report:
        top_factors.append("Injury claimed but no police report on file")

    # ── Rules-based boost (60% of total) ─────────────────────────────────────
    block_count = sum(1 for r in rules_results if r.triggered and r.severity == "BLOCK")
    flag_count = sum(1 for r in rules_results if r.triggered and r.severity == "FLAG")
    rules_boost = min(0.60, (block_count * 0.20 + flag_count * 0.08))

    if block_count > 0:
        top_factors.insert(0, f"{block_count} BLOCK rule(s) triggered")
    elif flag_count > 0:
        top_factors.insert(0, f"{flag_count} FLAG rule(s) triggered")

    # ── Final score ──────────────────────────────────────────────────────────
    total_score = round((feature_score + rules_boost) * 100, 1)
    total_score = min(100.0, max(0.0, total_score))

    # A triggered BLOCK rule is a hard stop (e.g. coverage backdating, watchlisted shop).
    # Floor blocked claims into the HIGH tier so they sort to the top of the examiner queue.
    if block_count > 0:
        total_score = max(total_score, 70.0 + min(20.0, (block_count - 1) * 10.0 + flag_count * 3.0))
        total_score = round(min(99.0, total_score), 1)

    # Damage-photo evidence is a top-priority queue signal: claims with submitted
    # damage photos are surfaced at the top of the queue for forensic image review
    # before payout. Floor their score into the top of the HIGH tier.
    if getattr(claim, "photo_evidence", False):
        value_nudge = min(9.0, acv_ratio * 6.0)
        total_score = round(min(99.0, max(total_score, 90.0 + value_nudge)), 1)
        top_factors.insert(0, "Damage photo submitted — priority forensic image review")

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
