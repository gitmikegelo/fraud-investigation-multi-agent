"""Unit tests for the car insurance rules engine (R-001 to R-006).

Each test uses a minimal in-line fake claim/context so these tests run with
zero I/O, no data generation, and no LLM calls — pure logic assertions.

Run:
    pytest tests/test_rules_engine.py
"""

import sys
import os
from dataclasses import dataclass, field
from typing import Optional, List

import importlib.util

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# core.engine has no heavy deps — import directly.
from core.engine import run_rules

# Import rules_engine_car via importlib to avoid
# intelligence/__init__.py pulling in document_vision -> boto3 at collection time.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_rspec = importlib.util.spec_from_file_location(
    "rules_engine_car",
    os.path.join(_ROOT, "intelligence", "rules_engine_car.py"),
)
_mod = importlib.util.module_from_spec(_rspec)
_rspec.loader.exec_module(_mod)

run_car_rules_engine = _mod.run_car_rules_engine
CAR_RULE_SPECS = _mod.CAR_RULE_SPECS


def _run_single_rule(rule_id: str, claim, ctx):
    """Run a single rule by ID and return its RuleResult."""
    spec = next(s for s in CAR_RULE_SPECS if s.id == rule_id)
    return run_rules(claim, ctx, [spec])[0]


# Aliases that preserve the original test call-sites unchanged.
def r001_policy_after_incident(claim, ctx): return _run_single_rule("R-001", claim, ctx)
def r002_no_repair_estimate(claim, ctx):    return _run_single_rule("R-002", claim, ctx)
def r003_duplicate_claim(claim, ctx):       return _run_single_rule("R-003", claim, ctx)
def r004_shop_on_watchlist(claim, ctx):     return _run_single_rule("R-004", claim, ctx)
def r005_amount_exceeds_acv(claim, ctx):    return _run_single_rule("R-005", claim, ctx)
def r006_serial_claimer(claim, ctx):        return _run_single_rule("R-006", claim, ctx)


# ── Minimal fake dataclasses ──────────────────────────────────────────────────

@dataclass
class FakePolicy:
    policy_id: str
    effective_date: str
    expiration_date: str = "2026-12-31"


@dataclass
class FakeVehicle:
    vehicle_id: str
    acv: float
    year: int = 2020
    make: str = "Toyota"
    model: str = "Camry"


@dataclass
class FakeShop:
    shop_id: str
    name: str
    on_watchlist: bool = False
    verified: bool = True
    in_network: bool = True


@dataclass
class FakeEstimate:
    estimate_id: str
    claim_id: str
    amount: float


@dataclass
class FakeInsured:
    insured_id: str
    full_name: str
    claim_history_count: int = 0


@dataclass
class FakeClaim:
    claim_id: str
    insured_id: str
    policy_id: str
    vehicle_id: str
    claim_type: str
    claim_amount: float
    date_of_incident: str
    date_filed: str = "2025-01-15"
    is_resubmission: bool = False
    original_claim_id: Optional[str] = None
    shop_id: Optional[str] = None
    estimate_id: Optional[str] = None
    injury_claimed: bool = False
    police_report_filed: bool = False
    photo_evidence: bool = False
    claim_source: str = "company_site"


def _base_context(
    policies=None, vehicles=None, shops=None, estimates=None,
    insureds=None, claims=None,
):
    return {
        "policies": policies or [],
        "vehicles": vehicles or [],
        "repair_shops": shops or [],
        "estimates": estimates or [],
        "insureds": insureds or [],
        "claims": claims or [],
    }


# ── R-001: Policy effective date after incident ───────────────────────────────

class TestR001PolicyAfterIncident:
    def test_triggered_when_policy_effective_after_incident(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "collision", 5000, "2025-01-10")
        policy = FakePolicy("P001", effective_date="2025-01-15")  # effective AFTER incident
        ctx = _base_context(policies=[policy])
        result = r001_policy_after_incident(claim, ctx)
        assert result.triggered is True
        assert result.severity == "BLOCK"
        assert result.rule_id == "R-001"

    def test_not_triggered_when_policy_effective_before_incident(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "collision", 5000, "2025-01-10")
        policy = FakePolicy("P001", effective_date="2025-01-01")  # effective BEFORE incident
        ctx = _base_context(policies=[policy])
        result = r001_policy_after_incident(claim, ctx)
        assert result.triggered is False

    def test_not_triggered_same_day(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "collision", 5000, "2025-01-10")
        policy = FakePolicy("P001", effective_date="2025-01-10")
        ctx = _base_context(policies=[policy])
        result = r001_policy_after_incident(claim, ctx)
        assert result.triggered is False

    def test_not_triggered_when_policy_missing(self):
        claim = FakeClaim("C001", "I001", "P-MISSING", "V001", "collision", 5000, "2025-01-10")
        ctx = _base_context()
        result = r001_policy_after_incident(claim, ctx)
        assert result.triggered is False


# ── R-002: No repair estimate for damage claim ────────────────────────────────

class TestR002NoRepairEstimate:
    def test_triggered_when_collision_has_no_estimate(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "collision", 8000, "2025-01-10")
        ctx = _base_context()  # no estimates
        result = r002_no_repair_estimate(claim, ctx)
        assert result.triggered is True
        assert result.severity == "BLOCK"

    def test_not_triggered_when_estimate_exists(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "collision", 8000, "2025-01-10",
                          estimate_id="E001")
        estimate = FakeEstimate("E001", "C001", 7500)
        ctx = _base_context(estimates=[estimate])
        result = r002_no_repair_estimate(claim, ctx)
        assert result.triggered is False

    def test_not_triggered_for_theft_claim(self):
        # theft is not in (collision, comprehensive, liability) — rule N/A
        claim = FakeClaim("C001", "I001", "P001", "V001", "theft", 12000, "2025-01-10")
        ctx = _base_context()
        result = r002_no_repair_estimate(claim, ctx)
        assert result.triggered is False

    def test_not_triggered_for_medical_payments(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "medical_payments", 3000, "2025-01-10")
        ctx = _base_context()
        result = r002_no_repair_estimate(claim, ctx)
        assert result.triggered is False

    def test_triggered_for_comprehensive_no_estimate(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "comprehensive", 6000, "2025-01-10")
        ctx = _base_context()
        result = r002_no_repair_estimate(claim, ctx)
        assert result.triggered is True


# ── R-003: Duplicate / resubmission ──────────────────────────────────────────

class TestR003DuplicateClaim:
    def test_triggered_when_resubmission_flag_set(self):
        claim = FakeClaim("C002", "I001", "P001", "V001", "collision", 5000, "2025-01-10",
                          is_resubmission=True, original_claim_id="C001")
        ctx = _base_context()
        result = r003_duplicate_claim(claim, ctx)
        assert result.triggered is True
        assert result.severity == "BLOCK"

    def test_not_triggered_for_original_claim(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "collision", 5000, "2025-01-10")
        ctx = _base_context()
        result = r003_duplicate_claim(claim, ctx)
        assert result.triggered is False


# ── R-004: Repair shop on watchlist ──────────────────────────────────────────

class TestR004ShopOnWatchlist:
    def test_triggered_when_shop_on_watchlist(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "collision", 8000, "2025-01-10",
                          shop_id="S001")
        shop = FakeShop("S001", "Dodgy Motors", on_watchlist=True)
        ctx = _base_context(shops=[shop])
        result = r004_shop_on_watchlist(claim, ctx)
        assert result.triggered is True
        assert result.severity == "BLOCK"

    def test_not_triggered_for_clean_shop(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "collision", 8000, "2025-01-10",
                          shop_id="S001")
        shop = FakeShop("S001", "Honest Auto", on_watchlist=False, verified=True)
        ctx = _base_context(shops=[shop])
        result = r004_shop_on_watchlist(claim, ctx)
        assert result.triggered is False

    def test_not_triggered_when_no_shop_on_claim(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "theft", 12000, "2025-01-10",
                          shop_id=None)
        ctx = _base_context()
        result = r004_shop_on_watchlist(claim, ctx)
        assert result.triggered is False


# ── R-005: Claim amount exceeds vehicle ACV ───────────────────────────────────

class TestR005AmountExceedsACV:
    def test_triggered_when_claim_exceeds_110_percent_acv(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "collision", 12000, "2025-01-10")
        vehicle = FakeVehicle("V001", acv=10000)  # 12000/10000 = 1.2 > 1.1
        ctx = _base_context(vehicles=[vehicle])
        result = r005_amount_exceeds_acv(claim, ctx)
        assert result.triggered is True
        assert result.severity == "FLAG"

    def test_not_triggered_when_claim_at_exactly_110_percent(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "collision", 11000, "2025-01-10")
        vehicle = FakeVehicle("V001", acv=10000)  # 1.1 exactly — not > 1.1
        ctx = _base_context(vehicles=[vehicle])
        result = r005_amount_exceeds_acv(claim, ctx)
        assert result.triggered is False

    def test_not_triggered_when_claim_below_acv(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "collision", 7000, "2025-01-10")
        vehicle = FakeVehicle("V001", acv=10000)
        ctx = _base_context(vehicles=[vehicle])
        result = r005_amount_exceeds_acv(claim, ctx)
        assert result.triggered is False

    def test_not_triggered_when_no_vehicle(self):
        claim = FakeClaim("C001", "I001", "P001", "V-MISSING", "collision", 99999, "2025-01-10")
        ctx = _base_context()
        result = r005_amount_exceeds_acv(claim, ctx)
        assert result.triggered is False


# ── R-006: Serial claimer ─────────────────────────────────────────────────────

class TestR006SerialClaimer:
    def test_triggered_when_insured_has_3_or_more_claims(self):
        insured = FakeInsured("I001", "Bob Fraudster", claim_history_count=3)
        claim = FakeClaim("C003", "I001", "P001", "V001", "collision", 5000, "2025-01-10")
        ctx = _base_context(insureds=[insured])
        result = r006_serial_claimer(claim, ctx)
        assert result.triggered is True
        assert result.severity == "FLAG"

    def test_not_triggered_when_insured_has_2_claims(self):
        insured = FakeInsured("I001", "Normal Driver", claim_history_count=2)
        claim = FakeClaim("C001", "I001", "P001", "V001", "collision", 5000, "2025-01-10")
        ctx = _base_context(insureds=[insured])
        result = r006_serial_claimer(claim, ctx)
        assert result.triggered is False

    def test_triggered_when_context_claims_count_reaches_threshold(self):
        # claim_history_count = 0 but there are 3 claims in context
        insured = FakeInsured("I001", "Bob", claim_history_count=0)
        claims = [
            FakeClaim(f"C00{i}", "I001", "P001", "V001", "collision", 5000, "2025-01-10")
            for i in range(3)
        ]
        current_claim = claims[0]
        ctx = _base_context(insureds=[insured], claims=claims)
        result = r006_serial_claimer(current_claim, ctx)
        assert result.triggered is True

    def test_uses_max_of_history_count_and_context_count(self):
        # history says 5, context only has 1 — should use 5
        insured = FakeInsured("I001", "Bob", claim_history_count=5)
        claim = FakeClaim("C001", "I001", "P001", "V001", "collision", 5000, "2025-01-10")
        ctx = _base_context(insureds=[insured], claims=[claim])
        result = r006_serial_claimer(claim, ctx)
        assert result.triggered is True
        assert "5" in result.explanation


# ── Full engine runner ────────────────────────────────────────────────────────

class TestRunCarRulesEngine:
    def test_returns_six_results(self):
        claim = FakeClaim("C001", "I001", "P001", "V001", "collision", 5000, "2025-01-10")
        policy = FakePolicy("P001", "2025-01-01")
        vehicle = FakeVehicle("V001", acv=10000)
        insured = FakeInsured("I001", "Alice")
        estimate = FakeEstimate("E001", "C001", 4800)
        ctx = _base_context(policies=[policy], vehicles=[vehicle],
                            insureds=[insured], estimates=[estimate])
        results = run_car_rules_engine(claim, ctx)
        assert len(results) == 6

    def test_all_block_rules_fire_for_max_fraud_claim(self):
        """A claim that should trigger R-001, R-003, R-004 (BLOCK) simultaneously."""
        claim = FakeClaim(
            "C-BAD", "I001", "P001", "V001", "collision", 25000, "2025-01-10",
            is_resubmission=True, original_claim_id="C-PREV",
            shop_id="S-BAD",
            estimate_id=None,
        )
        policy = FakePolicy("P001", effective_date="2025-01-15")  # R-001: effective AFTER
        vehicle = FakeVehicle("V001", acv=10000)
        shop = FakeShop("S-BAD", "Shady Repairs", on_watchlist=True)  # R-004
        insured = FakeInsured("I001", "Fraud Suspect")
        ctx = _base_context(policies=[policy], vehicles=[vehicle],
                            shops=[shop], insureds=[insured])

        results = run_car_rules_engine(claim, ctx)
        triggered_ids = {r.rule_id for r in results if r.triggered}

        assert "R-001" in triggered_ids  # policy backdated
        assert "R-003" in triggered_ids  # resubmission
        assert "R-004" in triggered_ids  # watchlist shop

    def test_clean_claim_triggers_nothing(self):
        """A perfectly clean claim should trigger zero rules."""
        claim = FakeClaim(
            "C-CLEAN", "I001", "P001", "V001", "collision", 5000, "2025-01-10",
            shop_id="S001", estimate_id="E001",
        )
        policy = FakePolicy("P001", effective_date="2024-01-01")
        vehicle = FakeVehicle("V001", acv=10000)
        shop = FakeShop("S001", "Clean Auto", on_watchlist=False, verified=True, in_network=True)
        insured = FakeInsured("I001", "Good Driver", claim_history_count=1)
        estimate = FakeEstimate("E001", "C-CLEAN", 4800)
        ctx = _base_context(
            policies=[policy], vehicles=[vehicle], shops=[shop],
            insureds=[insured], estimates=[estimate], claims=[claim],
        )
        results = run_car_rules_engine(claim, ctx)
        triggered = [r for r in results if r.triggered]
        assert triggered == [], f"Expected no triggers, got: {[r.rule_id for r in triggered]}"
