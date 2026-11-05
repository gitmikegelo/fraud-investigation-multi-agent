"""Weighted heuristic risk scoring (0-100) for Marine Cargo claims."""

from dataclasses import dataclass
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


def _rule(rules_results, rule_id):
    return next((r for r in rules_results if r.rule_id == rule_id), None)


def score_marine_claim(claim, context: Dict, rules_results: List) -> RiskBreakdown:
    """Score a marine cargo claim 0-100 using features (40%) + rules (60%)."""
    contributions = []
    top_factors = []
    feature_score = 0.0

    def add(category, name, raw, norm, weight):
        nonlocal feature_score
        contribution = norm * weight
        feature_score += contribution
        contributions.append(FeatureContribution(category, name, raw, norm, weight, contribution))

    # 1. Loss severity — share of insured value claimed (15%)
    policy = next((p for p in context.get("policies", []) if p.policy_id == claim.policy_id), None)
    loss_pct = claim.claim_amount / policy.insured_value if policy and policy.insured_value else 0.0
    add("claim", "loss_pct_of_insured_value", loss_pct, _normalize(loss_pct, 0.1, 0.6), 0.15)
    if loss_pct >= 0.4:
        top_factors.append(f"Claim is {loss_pct:.0%} of the insured value")

    # 2. Declared value vs market benchmark (10%)
    r002 = _rule(rules_results, "R-002")
    ratio = (r002.details or {}).get("ratio", 1.0) if r002 else 1.0
    add("shipment", "value_vs_benchmark", ratio, _normalize(ratio, 1.1, 1.8), 0.10)
    if r002 and r002.triggered:
        top_factors.append(f"Declared unit value {ratio:.2f}x market benchmark")

    # 3. Weight discrepancy — VGM vs declared (8%)
    r003 = _rule(rules_results, "R-003")
    gap = abs((r003.details or {}).get("gap_pct", 0.0)) / 100 if r003 else 0.0
    add("shipment", "vgm_weight_gap", gap, _normalize(gap, 0.05, 0.40), 0.08)
    if gap > 0.15:
        top_factors.append(f"VGM cargo weight {gap:.0%} below declared weight")

    # 4. Survey independence / timing (6%)
    surveyor = next((s for s in context.get("surveyors", []) if s.surveyor_id == claim.surveyor_id), None)
    survey_risk = 0.0
    if surveyor and surveyor.on_watchlist:
        survey_risk = 1.0
        top_factors.append(f"Surveyor '{surveyor.name}' on watchlist")
    elif surveyor and not surveyor.insurer_panel:
        survey_risk = 0.6
    add("survey", "surveyor_risk", survey_risk, survey_risk, 0.03)

    # 5. Claim frequency normalised by shipment volume (4%)
    r007 = _rule(rules_results, "R-007")
    rate = (r007.details or {}).get("claim_rate", 0.0) if r007 else 0.0
    add("claimant", "claim_rate_24m", rate, _normalize(rate, 0.02, 0.10), 0.04)

    # ── Rules-based boost (60% of total) ─────────────────────────────────────
    block_count = sum(1 for r in rules_results if r.triggered and r.severity == "BLOCK")
    flag_count = sum(1 for r in rules_results if r.triggered and r.severity == "FLAG")
    rules_boost = min(0.60, (block_count * 0.20 + flag_count * 0.08))

    if block_count > 0:
        top_factors.insert(0, f"{block_count} BLOCK rule(s) triggered")
    elif flag_count > 0:
        top_factors.insert(0, f"{flag_count} FLAG rule(s) triggered")

    total_score = round((feature_score + rules_boost) * 100, 1)
    total_score = min(100.0, max(0.0, total_score))

    # A triggered BLOCK rule is a hard stop — floor into HIGH so it tops the queue.
    if block_count > 0:
        total_score = max(total_score, 70.0 + min(20.0, (block_count - 1) * 10.0 + flag_count * 3.0))
        total_score = round(min(99.0, total_score), 1)
    # A triggered FLAG needs examiner eyes — floor into MEDIUM.
    elif flag_count > 0:
        total_score = round(min(59.0, max(total_score, 30.0 + (flag_count - 1) * 8.0 + feature_score * 20)), 1)

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
