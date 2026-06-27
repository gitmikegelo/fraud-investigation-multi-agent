"""Claims Examiner Workflow Copilot - Main Entry Point
Supports: Prudential Supplemental Health | Zurich Travel Guard
Set DOMAIN_MODE=travel to run Travel Guard. Default: supplemental.
"""

import os
import sys
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import networkx as nx
import pickle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'), override=False)
except ImportError:
    pass

from domain_config import PRUDENTIAL_SUPPLEMENTAL_HEALTH, ZURICH_TRAVEL_GUARD, DomainConfig
from data.generate_supplemental import generate_supplemental_data, Claim
from intelligence.rules_engine import run_rules_engine, RuleResult
from intelligence.risk_scoring import score_claim, RiskBreakdown
from intelligence.document_analysis import run_document_checks
from intelligence.document_vision import run_vision_document_checks, find_claim_images
from intelligence.entity_graph import build_supplemental_health_graph, detect_patterns, PatternResult
from billing_rules.index import get_insurance_rules_index
from cases import Case, CaseType, ClaimType, CasePriority, CaseStatus

# Domain is locked to "travel". Supplemental code remains in the repo but can no
# longer be activated via env/.env/.bat — the env var is intentionally ignored.
DOMAIN_MODE = "travel"


CACHE_VERSION = "v2_supplemental"


@dataclass
class DataContext:
    """Container for all supplemental health data."""
    domain_config: DomainConfig
    supplemental_data: Dict
    supplemental_claims: List
    supplemental_graph: nx.DiGraph
    detected_patterns: List[PatternResult]
    case_queue: List[Case] = field(default_factory=list)
    # Lookup dicts for fast access
    claim_rules: Dict[str, List[RuleResult]] = field(default_factory=dict)
    claim_risk_scores: Dict[str, RiskBreakdown] = field(default_factory=dict)
    claim_doc_results: Dict[str, list] = field(default_factory=dict)

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        return next((c for c in self.supplemental_claims if c.claim_id == claim_id), None)

    def get_case(self, case_id: str) -> Optional[Case]:
        return next((c for c in self.case_queue if c.case_id == case_id), None)

    def get_member(self, member_id: str):
        return next((m for m in self.supplemental_data.get("members", [])
                     if m.member_id == member_id), None)

    def get_member_claims(self, member_id: str) -> List:
        return [c for c in self.supplemental_claims if c.member_id == member_id]

    def get_member_dependents(self, member_id: str) -> List:
        return [d for d in self.supplemental_data.get("dependents", [])
                if d.member_id == member_id]

    def get_provider(self, provider_id: str):
        return next((p for p in self.supplemental_data.get("providers", [])
                     if p.provider_id == provider_id), None)

    def get_policy(self, policy_id: str):
        return next((p for p in self.supplemental_data.get("policies", [])
                     if p.policy_id == policy_id), None)

    def get_employer(self, employer_id: str):
        return next((e for e in self.supplemental_data.get("employers", [])
                     if e.employer_id == employer_id), None)

    def get_claim_tasks(self, claim_id: str) -> List:
        return [t for t in self.supplemental_data.get("workflow_tasks", [])
                if t.claim_id == claim_id]

    def get_document(self, claim_id: str):
        return next((d for d in self.supplemental_data.get("documents", [])
                     if d.claim_id == claim_id), None)

    def get_high_risk_claims(self, min_score: float = 65) -> List[Case]:
        return [c for c in self.case_queue if c.risk_score >= min_score]

    def get_stats(self) -> Dict:
        high = sum(1 for c in self.case_queue if c.priority == CasePriority.HIGH)
        medium = sum(1 for c in self.case_queue if c.priority == CasePriority.MEDIUM)
        low = sum(1 for c in self.case_queue if c.priority == CasePriority.LOW)
        total_held = sum(c.claim_amount for c in self.case_queue if c.priority == CasePriority.HIGH)

        # Top rules
        rule_counts = {}
        for rules in self.claim_rules.values():
            for r in rules:
                if r.triggered:
                    rule_counts[r.rule_id] = rule_counts.get(r.rule_id, 0) + 1

        # Workflow health
        tasks = self.supplemental_data.get("workflow_tasks", [])
        open_pmr = sum(1 for t in tasks if t.task_type == "PMR" and t.status in ("pending", "in_progress"))
        pending_cbr = sum(1 for t in tasks if t.task_type == "CBR" and t.status in ("pending", "in_progress"))
        past_tat = sum(1 for t in tasks if t.status == "overdue")

        return {
            "total_claims": len(self.case_queue),
            "risk_distribution": {"HIGH": high, "MEDIUM": medium, "LOW": low},
            "intercepts": {"count": high, "held_amount": round(total_held, 2)},
            "top_rules_triggered": sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "patterns_detected": len(self.detected_patterns),
            "pattern_types": [p.pattern_type for p in self.detected_patterns],
            "workflow_health": {"open_pmr": open_pmr, "pending_cbr": pending_cbr, "past_tat": past_tat},
        }


def initialize_data(force_regenerate: bool = False) -> DataContext:
    cache_file = f'data_cache_{CACHE_VERSION}.pkl'

    if not force_regenerate and os.path.exists(cache_file):
        print("=" * 60)
        print("PRUDENTIAL SUPPLEMENTAL HEALTH COPILOT - Loading Cache")
        print("=" * 60)
        try:
            with open(cache_file, 'rb') as f:
                ctx = pickle.load(f)
            print(f"✅ Cache loaded ({len(ctx.case_queue)} claims)")
            return ctx
        except Exception as e:
            print(f"⚠️ Cache load failed: {e}\nRegenerating...")

    print("=" * 60)
    print("PRUDENTIAL SUPPLEMENTAL HEALTH COPILOT - Initializing")
    print("=" * 60)

    config = PRUDENTIAL_SUPPLEMENTAL_HEALTH

    print("\n[1/7] Generating supplemental health data...")
    data = generate_supplemental_data()
    claims = data["claims"]

    # Build context dict for rules/scoring
    context_dict = {
        "claims": claims,
        "members": data["members"],
        "dependents": data["dependents"],
        "providers": data["providers"],
        "facilities": data["facilities"],
        "addresses": data["addresses"],
        "policies": data["policies"],
        "workflow_tasks": data["workflow_tasks"],
        "documents": data["documents"],
    }

    print(f"\n[2/7] Running rules engine on {len(claims)} claims...")
    claim_rules = {}
    for claim in claims:
        results = run_rules_engine(claim, context_dict)
        claim_rules[claim.claim_id] = results
    triggered_count = sum(1 for rules in claim_rules.values() for r in rules if r.triggered)
    print(f"  → {triggered_count} total rule triggers across all claims")

    print(f"\n[3/7] Scoring claims...")
    claim_risk_scores = {}
    for claim in claims:
        score = score_claim(claim, context_dict, claim_rules.get(claim.claim_id, []))
        claim_risk_scores[claim.claim_id] = score
    high = sum(1 for s in claim_risk_scores.values() if s.tier == "HIGH")
    med = sum(1 for s in claim_risk_scores.values() if s.tier == "MEDIUM")
    low = sum(1 for s in claim_risk_scores.values() if s.tier == "LOW")
    print(f"  → HIGH: {high}, MEDIUM: {med}, LOW: {low}")

    print(f"\n[4/7] Running document analysis...")
    claim_doc_results = {}
    vision_count = 0
    for doc in data["documents"]:
        # Try vision analysis first for claims that have images
        vision_results = None
        if find_claim_images(doc.claim_id):
            try:
                vision_results = run_vision_document_checks(doc.claim_id)
            except Exception as e:
                print(f"  ⚠ Vision failed for {doc.claim_id}: {e}")
        if vision_results:
            claim_doc_results[doc.claim_id] = vision_results
            vision_count += 1
        else:
            claim_doc_results[doc.claim_id] = run_document_checks(doc)
    doc_failures = sum(1 for results in claim_doc_results.values()
                       for r in results if not r.passed and r.severity == "CRITICAL")
    print(f"  → {vision_count} claims analyzed via Haiku 4.5 vision, rest via metadata")
    print(f"  → {doc_failures} critical document failures")

    print(f"\n[5/7] Building entity graph...")
    graph = build_supplemental_health_graph(data)
    print(f"  → {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

    print(f"\n[6/7] Detecting patterns...")
    patterns = detect_patterns(graph, data)
    print(f"  → {len(patterns)} patterns detected")

    print(f"\n[7/7] Building case queue...")
    from case_queue import build_case_queue
    case_queue = build_case_queue(claims, claim_risk_scores, claim_rules, data)
    print(f"  → {len(case_queue)} cases in queue")

    # Initialize insurance rules index
    _ = get_insurance_rules_index()

    ctx = DataContext(
        domain_config=config,
        supplemental_data=data,
        supplemental_claims=claims,
        supplemental_graph=graph,
        detected_patterns=patterns,
        case_queue=case_queue,
        claim_rules=claim_rules,
        claim_risk_scores=claim_risk_scores,
        claim_doc_results=claim_doc_results,
    )

    print("\n💾 Saving cache...")
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(ctx, f)
        print(f"✅ Cached to {cache_file}")
    except Exception as e:
        print(f"⚠️ Cache save failed: {e}")

    print("\n" + "=" * 60)
    print("INITIALIZATION COMPLETE")
    print(f"  {len(case_queue)} claims | {high} HIGH | {med} MEDIUM | {low} LOW")
    print(f"  {len(patterns)} patterns | {graph.number_of_nodes()} graph nodes")
    print("=" * 60)
    return ctx


# ══════════════════════════════════════════════════════════════════════════════
# TRAVEL GUARD INITIALIZATION
# ══════════════════════════════════════════════════════════════════════════════

def initialize_travel_data(force_regenerate: bool = False) -> DataContext:
    """Initialize Travel Guard domain data."""
    cache_file = 'data_cache_v1_travel.pkl'

    if not force_regenerate and os.path.exists(cache_file):
        print("=" * 60)
        print("ZURICH TRAVEL GUARD COPILOT - Loading Cache")
        print("=" * 60)
        try:
            with open(cache_file, 'rb') as f:
                ctx = pickle.load(f)
            print(f"✅ Cache loaded ({len(ctx.case_queue)} claims)")
            return ctx
        except Exception as e:
            print(f"⚠️ Cache load failed: {e}\nRegenerating...")

    print("=" * 60)
    print("ZURICH TRAVEL GUARD COPILOT - Initializing")
    print("=" * 60)

    config = ZURICH_TRAVEL_GUARD

    from data.generate_travel import generate_travel_data, TravelClaim
    from intelligence.rules_engine_travel import run_travel_rules_engine
    from intelligence.risk_scoring_travel import score_travel_claim

    print("\n[1/5] Generating travel insurance data...")
    data = generate_travel_data()
    claims = data["claims"]

    # Build context dict for rules/scoring
    context_dict = {
        "claims": claims,
        "travelers": data["travelers"],
        "companions": data["companions"],
        "destinations": data["destinations"],
        "airlines": data["airlines"],
        "hotels": data["hotels"],
        "providers": data["providers"],
        "policies": data["policies"],
        "bookings": data["bookings"],
        "flights": data["flights"],
        "workflow_tasks": data["workflow_tasks"],
        "documents": data["documents"],
        "travel_agents": data["travel_agents"],
    }

    print(f"\n[2/5] Running travel rules engine on {len(claims)} claims...")
    claim_rules = {}
    for claim in claims:
        results = run_travel_rules_engine(claim, context_dict)
        claim_rules[claim.claim_id] = results
    triggered_count = sum(1 for rules in claim_rules.values() for r in rules if r.triggered)
    print(f"  → {triggered_count} total rule triggers across all claims")

    print(f"\n[3/5] Scoring claims...")
    claim_risk_scores = {}
    for claim in claims:
        score = score_travel_claim(claim, context_dict, claim_rules.get(claim.claim_id, []))
        claim_risk_scores[claim.claim_id] = score
    high = sum(1 for s in claim_risk_scores.values() if s.tier == "HIGH")
    med = sum(1 for s in claim_risk_scores.values() if s.tier == "MEDIUM")
    low = sum(1 for s in claim_risk_scores.values() if s.tier == "LOW")
    print(f"  → HIGH: {high}, MEDIUM: {med}, LOW: {low}")

    print(f"\n[4/5] Building case queue...")
    from case_queue_travel import build_travel_case_queue
    case_queue = build_travel_case_queue(claims, claim_risk_scores, claim_rules, data)
    print(f"  → {len(case_queue)} cases in queue")

    # Document analysis (simplified — no vision for travel)
    claim_doc_results = {}
    for doc in data["documents"]:
        claim_doc_results[doc.claim_id] = []  # Placeholder

    print(f"\n[5/5] Complete.")

    # Build a minimal graph (reuse supplemental graph structure concept)
    graph = nx.DiGraph()
    for t in data["travelers"]:
        graph.add_node(t.traveler_id, entity_type="traveler", name=t.full_name)
    for d in data["destinations"]:
        graph.add_node(d.destination_id, entity_type="destination", name=f"{d.city}, {d.country}")
    for c in claims:
        if c.destination_id:
            graph.add_edge(c.traveler_id, c.destination_id, relationship="TRAVELED_TO", claim_id=c.claim_id)
        if c.provider_id:
            graph.add_edge(c.traveler_id, c.provider_id, relationship="TREATED_BY", claim_id=c.claim_id)

    ctx = DataContext(
        domain_config=config,
        supplemental_data=data,
        supplemental_claims=claims,
        supplemental_graph=graph,
        detected_patterns=[],
        case_queue=case_queue,
        claim_rules=claim_rules,
        claim_risk_scores=claim_risk_scores,
        claim_doc_results=claim_doc_results,
    )

    print("\n💾 Saving cache...")
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(ctx, f)
        print(f"✅ Cached to {cache_file}")
    except Exception as e:
        print(f"⚠️ Cache save failed: {e}")

    print("\n" + "=" * 60)
    print("TRAVEL GUARD INITIALIZATION COMPLETE")
    print(f"  {len(case_queue)} claims | {high} HIGH | {med} MEDIUM | {low} LOW")
    print("=" * 60)
    return ctx


def run_demo():
    ctx = initialize_data()
    stats = ctx.get_stats()

    print("\n" + "=" * 60)
    print("DEMO: Supplemental Health Claims Overview")
    print("=" * 60)

    print(f"\nTotal claims: {stats['total_claims']}")
    print(f"Risk distribution: {stats['risk_distribution']}")
    print(f"Intercepts: {stats['intercepts']['count']} claims, ${stats['intercepts']['held_amount']:,.2f} held")
    print(f"Patterns detected: {stats['patterns_detected']}")
    print(f"Workflow: {stats['workflow_health']}")

    print("\nTop triggered rules:")
    for rule_id, count in stats['top_rules_triggered'][:5]:
        print(f"  • {rule_id}: {count} triggers")

    print("\nHigh-risk claims:")
    for case in ctx.get_high_risk_claims()[:5]:
        print(f"  • {case.case_id} ({case.claim_type.value}): score={case.risk_score:.1f}, {case.flag_reason[:60]}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    return ctx


if __name__ == "__main__":
    run_demo()
