"""Car insurance scoring: four FeatureSpecs + shim over core.engine.score_claim.

CAR_FEATURE_SPECS is the single source of truth for the 40% feature side.
The 60% rules boost, tier thresholds, and BLOCK/photo floors come from
core.engine.score_claim defaults (matching the original hardcoded values).
"""

from typing import Dict, List, Optional

from core.engine import (
    FeatureSpec,
    FeatureContribution,
    RiskBreakdown,
    RuleResult,
    score_claim,
)


# ── Context accessors ─────────────────────────────────────────────────────────

def _get_vehicle(context: Dict, vehicle_id: str):
    return next((v for v in context.get("vehicles", []) if v.vehicle_id == vehicle_id), None)


def _get_shop(context: Dict, shop_id: Optional[str]):
    if not shop_id:
        return None
    return next((s for s in context.get("repair_shops", []) if s.shop_id == shop_id), None)


def _get_insured(context: Dict, insured_id: str):
    return next((i for i in context.get("insureds", []) if i.insured_id == insured_id), None)


# ── Feature extractors ────────────────────────────────────────────────────────

def _acv_ratio(claim, context: Dict) -> float:
    vehicle = _get_vehicle(context, claim.vehicle_id)
    acv = vehicle.acv if vehicle else 0
    return (claim.claim_amount / acv) if acv > 0 else 0.5


def _acv_factor(claim, context: Dict, raw: float) -> Optional[str]:
    vehicle = _get_vehicle(context, claim.vehicle_id)
    acv = vehicle.acv if vehicle else 0
    if raw > 1.0:
        return f"Claim is {raw:.1f}x the vehicle's value (${acv:,.0f})"
    return None


def _shop_risk(claim, context: Dict) -> float:
    shop = _get_shop(context, getattr(claim, "shop_id", None))
    if not shop:
        return 0.0
    if shop.on_watchlist:
        return 1.0
    if not shop.verified or not shop.in_network:
        return 0.6
    return 0.0


def _shop_factor(claim, context: Dict, raw: float) -> Optional[str]:
    shop = _get_shop(context, getattr(claim, "shop_id", None))
    if not shop or raw == 0.0:
        return None
    if raw == 1.0:
        return f"Repair shop '{shop.name}' is on the fraud watchlist"
    return f"Repair shop '{shop.name}' is out-of-network / unverified"


def _claim_history(claim, context: Dict) -> float:
    insured = _get_insured(context, claim.insured_id)
    history_count = insured.claim_history_count if insured else 0
    insured_claims = [c for c in context.get("claims", []) if c.insured_id == claim.insured_id]
    return float(max(history_count, len(insured_claims)))


def _history_factor(claim, context: Dict, raw: float) -> Optional[str]:
    if raw >= 3:
        return f"Insured has {int(raw)} claims (serial claimer pattern)"
    return None


def _injury_no_report(claim, context: Dict) -> float:
    return 1.0 if (claim.injury_claimed and not claim.police_report_filed) else 0.0


def _injury_factor(claim, context: Dict, raw: float) -> Optional[str]:
    if raw:
        return "Injury claimed but no police report on file"
    return None


# ── Feature spec list (single source of truth for car scoring features) ───────

CAR_FEATURE_SPECS: List[FeatureSpec] = [
    FeatureSpec(
        category="vehicle", name="amount_vs_acv",
        weight=0.15,
        extractor=_acv_ratio,
        normalizer_bounds=(0.2, 1.3),
        factor_fn=_acv_factor,
    ),
    FeatureSpec(
        category="shop", name="watchlist_status",
        weight=0.12,
        extractor=_shop_risk,
        normalizer_bounds=(0.0, 1.0),
        factor_fn=_shop_factor,
    ),
    FeatureSpec(
        category="insured", name="claim_history",
        weight=0.08,
        extractor=_claim_history,
        normalizer_bounds=(0.0, 6.0),
        factor_fn=_history_factor,
    ),
    FeatureSpec(
        category="claim", name="injury_no_report",
        weight=0.05,
        extractor=_injury_no_report,
        normalizer_bounds=(0.0, 1.0),
        factor_fn=_injury_factor,
    ),
]


# ── Backwards-compatible shim ─────────────────────────────────────────────────

def score_car_claim(claim, context: Dict, rules_results: List[RuleResult]) -> RiskBreakdown:
    """Score a car claim 0-100. Shim over core.engine.score_claim."""
    # Inject the acv_ratio hint so the photo-floor logic in core/engine can read it.
    acv_ratio = _acv_ratio(claim, context)
    ctx_with_hint = {**context, "_acv_ratio_hint": acv_ratio}
    return score_claim(claim, ctx_with_hint, rules_results, CAR_FEATURE_SPECS)
