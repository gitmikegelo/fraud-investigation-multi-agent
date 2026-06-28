"""Generic rules runner, feature-registry scorer, and declarative checklist runner.

All three pieces are data-driven:
  - Rules:     domain supplies List[RuleSpec]; engine iterates → List[RuleResult]
  - Scoring:   domain supplies List[FeatureSpec]; engine computes → RiskBreakdown
  - Checklist: domain supplies List[Step]; engine iterates → List[ChecklistStepResult]

Core files import from here.  Domain files (domains/car/*.py) supply the specs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# ── Shared result types (unchanged downstream shape) ─────────────────────────

@dataclass
class RuleResult:
    rule_id: str
    rule_name: str
    severity: str       # BLOCK | FLAG | INFO
    triggered: bool
    explanation: str
    details: Dict = field(default_factory=dict)


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
    tier: str           # HIGH | MEDIUM | LOW
    feature_contributions: List[FeatureContribution]
    top_factors: List[str]
    rules_boost: float = 0.0


@dataclass
class ChecklistStepResult:
    step_number: int
    step_name: str
    status: str         # pass | fail | needs_review | not_run | error
    auto_passed: bool
    findings: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


# ── Spec types (what domains supply) ─────────────────────────────────────────

@dataclass(frozen=True)
class RuleSpec:
    """A single declarative rule.  predicate(claim, context) -> bool."""
    id: str
    name: str
    severity: str                           # BLOCK | FLAG | INFO
    predicate: Callable[[Any, Dict], bool]
    explain: Callable[[Any, Dict, bool], str]
    details_fn: Optional[Callable[[Any, Dict], Dict]] = None


@dataclass(frozen=True)
class FeatureSpec:
    """A single scoring feature.  extractor(claim, context) -> float (raw value)."""
    category: str
    name: str
    weight: float                           # fraction of the 0-1 feature score
    extractor: Callable[[Any, Dict], float]
    normalizer_bounds: Tuple[float, float]  # (min, max) for linear normalisation
    factor_fn: Optional[Callable[[Any, Dict, float], Optional[str]]] = None


@dataclass(frozen=True)
class Step:
    """A single declarative checklist step.  check(claim, context) -> ChecklistStepResult."""
    id: str
    name: str
    check: Callable[[Any, Dict], ChecklistStepResult]
    config: Dict = field(default_factory=dict)


# ── Rules engine ─────────────────────────────────────────────────────────────

def run_rules(claim, context: Dict, specs: List[RuleSpec]) -> List[RuleResult]:
    """Run a list of RuleSpecs against a single claim. Returns one RuleResult per spec."""
    results = []
    for spec in specs:
        try:
            triggered = spec.predicate(claim, context)
            explanation = spec.explain(claim, context, triggered)
            details = spec.details_fn(claim, context) if spec.details_fn else {}
            results.append(RuleResult(
                rule_id=spec.id,
                rule_name=spec.name,
                severity=spec.severity,
                triggered=triggered,
                explanation=explanation,
                details=details,
            ))
        except Exception as exc:
            results.append(RuleResult(
                rule_id="ERR",
                rule_name=spec.name,
                severity="INFO",
                triggered=False,
                explanation=f"Rule error: {str(exc)[:100]}",
            ))
    return results


# ── Scoring engine ────────────────────────────────────────────────────────────

def _normalize(value: float, min_val: float, max_val: float) -> float:
    if max_val <= min_val:
        return 0.0
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))


def score_claim(
    claim,
    context: Dict,
    rules_results: List[RuleResult],
    feature_specs: List[FeatureSpec],
    *,
    feature_weight: float = 0.40,
    rules_weight: float = 0.60,
    block_boost: float = 0.20,
    flag_boost: float = 0.08,
    block_floor_base: float = 70.0,
    block_floor_step: float = 10.0,
    flag_floor_contrib: float = 3.0,
    photo_floor: float = 90.0,
    risk_tiers: Optional[Dict[str, Tuple[int, int]]] = None,
) -> RiskBreakdown:
    """Generic scorer.  feature_specs supply the 40% feature side; rules supply the 60% boost."""
    if risk_tiers is None:
        risk_tiers = {"HIGH": (60, 100), "MEDIUM": (30, 59), "LOW": (0, 29)}

    contributions: List[FeatureContribution] = []
    top_factors: List[str] = []
    feature_score = 0.0

    for spec in feature_specs:
        raw = spec.extractor(claim, context)
        norm = _normalize(raw, *spec.normalizer_bounds)
        contrib = norm * spec.weight
        feature_score += contrib
        contributions.append(FeatureContribution(
            category=spec.category,
            feature_name=spec.name,
            raw_value=raw,
            normalized=norm,
            weight=spec.weight,
            contribution=contrib,
        ))
        if spec.factor_fn:
            factor = spec.factor_fn(claim, context, raw)
            if factor:
                top_factors.append(factor)

    # Rules boost
    block_count = sum(1 for r in rules_results if r.triggered and r.severity == "BLOCK")
    flag_count = sum(1 for r in rules_results if r.triggered and r.severity == "FLAG")
    rules_boost = min(rules_weight, block_count * block_boost + flag_count * flag_boost)

    if block_count > 0:
        top_factors.insert(0, f"{block_count} BLOCK rule(s) triggered")
    elif flag_count > 0:
        top_factors.insert(0, f"{flag_count} FLAG rule(s) triggered")

    total_score = round((feature_score + rules_boost) * 100, 1)
    total_score = min(100.0, max(0.0, total_score))

    if block_count > 0:
        floor = block_floor_base + min(20.0, (block_count - 1) * block_floor_step + flag_count * flag_floor_contrib)
        total_score = round(min(99.0, max(total_score, floor)), 1)

    if getattr(claim, "photo_evidence", False):
        acv_ratio = context.get("_acv_ratio_hint", 0.0)
        value_nudge = min(9.0, acv_ratio * 6.0)
        total_score = round(min(99.0, max(total_score, photo_floor + value_nudge)), 1)
        top_factors.insert(0, "Damage photo submitted — priority forensic image review")

    # Tier
    tier = "LOW"
    for name, (lo, hi) in risk_tiers.items():
        if lo <= total_score <= hi:
            tier = name
            break

    return RiskBreakdown(
        total_score=total_score,
        tier=tier,
        feature_contributions=contributions,
        top_factors=top_factors[:5],
        rules_boost=round(rules_boost * 100, 1),
    )


# ── Checklist runner ──────────────────────────────────────────────────────────

def run_checklist_step_spec(step: Step, claim, context: Dict) -> ChecklistStepResult:
    """Run a single Step spec."""
    try:
        return step.check(claim, context)
    except Exception as exc:
        return ChecklistStepResult(
            step_number=0,
            step_name=step.name,
            status="error",
            auto_passed=False,
            findings=[f"Step error: {str(exc)[:200]}"],
        )


def run_checklist(steps: List[Step], claim_id: str, context: Dict) -> List[ChecklistStepResult]:
    """Run an ordered list of Steps for a single claim."""
    claim = next((c for c in context.get("claims", []) if c.claim_id == claim_id), None)
    if not claim:
        return [
            ChecklistStepResult(i + 1, s.name, "error", False, ["Claim not found"])
            for i, s in enumerate(steps)
        ]
    return [run_checklist_step_spec(step, claim, context) for step in steps]
