"""Claims Examiner Workflow Copilot - Main Entry Point."""

import os
import sys
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

import domains  # noqa: F401 — registers all domain plugins
from core.registry import get_active_plugin
from domain_config import DomainConfig
from intelligence.rules_engine_car import RuleResult
from intelligence.risk_scoring_car import RiskBreakdown
from cases import Case, CaseType, ClaimType, CasePriority, CaseStatus


@dataclass
class DataContext:
    """Domain-neutral container for all active domain data."""
    domain_config: DomainConfig
    entities: Dict           # keyed by entity-type plural, e.g. "insureds", "vehicles"
    claims: List             # the flat list of domain claim objects
    graph: nx.DiGraph        # entity relationship graph
    detected_patterns: List
    case_queue: List[Case] = field(default_factory=list)
    claim_rules: Dict[str, List[RuleResult]] = field(default_factory=dict)
    claim_risk_scores: Dict[str, RiskBreakdown] = field(default_factory=dict)
    claim_doc_results: Dict[str, list] = field(default_factory=dict)

    def get_claim(self, claim_id: str):
        return next((c for c in self.claims if c.claim_id == claim_id), None)

    def get_case(self, case_id: str) -> Optional[Case]:
        return next((c for c in self.case_queue if c.case_id == case_id), None)

    def get_insured(self, insured_id: str):
        return next((i for i in self.entities.get("insureds", [])
                     if i.insured_id == insured_id), None)

    def get_insured_claims(self, insured_id: str) -> List:
        return [c for c in self.claims if c.insured_id == insured_id]

    def get_policy(self, policy_id: str):
        return next((p for p in self.entities.get("policies", [])
                     if p.policy_id == policy_id), None)

    def get_vehicle(self, vehicle_id: str):
        return next((v for v in self.entities.get("vehicles", [])
                     if v.vehicle_id == vehicle_id), None)

    def get_shop(self, shop_id: str):
        return next((s for s in self.entities.get("repair_shops", [])
                     if s.shop_id == shop_id), None)

    def get_claim_tasks(self, claim_id: str) -> List:
        return [t for t in self.entities.get("workflow_tasks", [])
                if t.claim_id == claim_id]

    def get_document(self, claim_id: str):
        return next((d for d in self.entities.get("documents", [])
                     if d.claim_id == claim_id), None)

    def get_high_risk_claims(self, min_score: float = 65) -> List[Case]:
        return [c for c in self.case_queue if c.risk_score >= min_score]

    def get_stats(self) -> Dict:
        high = sum(1 for c in self.case_queue if c.priority == CasePriority.HIGH)
        medium = sum(1 for c in self.case_queue if c.priority == CasePriority.MEDIUM)
        low = sum(1 for c in self.case_queue if c.priority == CasePriority.LOW)
        total_held = sum(c.claim_amount for c in self.case_queue if c.priority == CasePriority.HIGH)

        rule_counts = {}
        for rules in self.claim_rules.values():
            for r in rules:
                if r.triggered:
                    rule_counts[r.rule_id] = rule_counts.get(r.rule_id, 0) + 1

        tasks = self.entities.get("workflow_tasks", [])
        open_estimate = sum(1 for t in tasks if t.task_type == "ESTIMATE_REVIEW" and t.status in ("pending", "in_progress"))
        pending_injury = sum(1 for t in tasks if t.task_type == "INJURY_REVIEW" and t.status in ("pending", "in_progress"))
        past_tat = sum(1 for t in tasks if t.status == "overdue")

        return {
            "total_claims": len(self.case_queue),
            "risk_distribution": {"HIGH": high, "MEDIUM": medium, "LOW": low},
            "intercepts": {"count": high, "held_amount": round(total_held, 2)},
            "top_rules_triggered": sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "patterns_detected": len(self.detected_patterns),
            "pattern_types": [p.pattern_type for p in self.detected_patterns],
            "workflow_health": {"open_estimate_reviews": open_estimate,
                                "pending_injury_reviews": pending_injury, "past_tat": past_tat},
        }


def initialize_data(force_regenerate: bool = False) -> DataContext:
    """Initialize domain data using the active plugin."""
    PLUGIN = get_active_plugin()
    cache_file = f"data_cache_{PLUGIN.name}.pkl"
    domain_stamp = PLUGIN.name

    if not force_regenerate and os.path.exists(cache_file):
        print("=" * 60)
        print(f"{PLUGIN.config.display_name} - Loading Cache")
        print("=" * 60)
        try:
            with open(cache_file, 'rb') as f:
                cached = pickle.load(f)
            # Reject stale cache from a different domain.
            if isinstance(cached, tuple) and cached[0] == domain_stamp:
                ctx = cached[1]
                print(f"Cache loaded ({len(ctx.case_queue)} claims)")
                return ctx
            else:
                print("Cache domain mismatch — regenerating...")
        except Exception as e:
            print(f"Cache load failed: {e} — regenerating...")

    print("=" * 60)
    print(f"{PLUGIN.config.display_name} - Initializing")
    print("=" * 60)

    config = PLUGIN.config

    print(f"\n[1/5] Generating {PLUGIN.name} data...")
    data = PLUGIN.generate_fn()
    claims = data["claims"]

    context_dict = {"claims": claims}
    for key in PLUGIN.context_keys:
        if key != "claims" and key in data:
            context_dict[key] = data[key]

    print(f"\n[2/5] Running rules engine on {len(claims)} claims...")
    claim_rules = {}
    for claim in claims:
        claim_rules[claim.claim_id] = PLUGIN.rules_fn(claim, context_dict)
    triggered_count = sum(1 for rules in claim_rules.values() for r in rules if r.triggered)
    print(f"  -> {triggered_count} total rule triggers across all claims")

    print(f"\n[3/5] Scoring claims...")
    claim_risk_scores = {}
    for claim in claims:
        claim_risk_scores[claim.claim_id] = PLUGIN.score_fn(claim, context_dict, claim_rules.get(claim.claim_id, []))
    high = sum(1 for s in claim_risk_scores.values() if s.tier == "HIGH")
    med = sum(1 for s in claim_risk_scores.values() if s.tier == "MEDIUM")
    low = sum(1 for s in claim_risk_scores.values() if s.tier == "LOW")
    print(f"  -> HIGH: {high}, MEDIUM: {med}, LOW: {low}")

    print(f"\n[4/5] Building case queue...")
    case_queue = PLUGIN.build_queue_fn(claims, claim_risk_scores, claim_rules, data)
    print(f"  -> {len(case_queue)} cases in queue")

    # No cached vision results — vision runs live in api.py when an image exists.
    claim_doc_results = {doc.claim_id: [] for doc in data.get("documents", [])}

    print(f"\n[5/5] Building entity graph...")
    graph = nx.DiGraph()
    for et in PLUGIN.entity_types:
        for ent in data.get(et, []):
            node_id = getattr(ent, f"{et[:-1]}_id", None) or getattr(ent, "id", str(ent))
            label = getattr(ent, "full_name", None) or getattr(ent, "name", str(node_id))
            graph.add_node(node_id, entity_type=et[:-1], name=label)
    for c in claims:
        insured_id = getattr(c, "insured_id", None)
        vehicle_id = getattr(c, "vehicle_id", None)
        shop_id = getattr(c, "shop_id", None)
        if insured_id and vehicle_id:
            graph.add_edge(insured_id, vehicle_id, relationship="OWNS", claim_id=c.claim_id)
        if insured_id and shop_id:
            graph.add_edge(insured_id, shop_id, relationship="REPAIRED_AT", claim_id=c.claim_id)

    ctx = DataContext(
        domain_config=config,
        entities=data,
        claims=claims,
        graph=graph,
        detected_patterns=[],
        case_queue=case_queue,
        claim_rules=claim_rules,
        claim_risk_scores=claim_risk_scores,
        claim_doc_results=claim_doc_results,
    )

    print("\nSaving cache...")
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump((domain_stamp, ctx), f)
        print(f"Cached to {cache_file}")
    except Exception as e:
        print(f"Cache save failed: {e}")

    print("\n" + "=" * 60)
    print(f"{PLUGIN.name.upper()} INITIALIZATION COMPLETE")
    print(f"  {len(case_queue)} claims | {high} HIGH | {med} MEDIUM | {low} LOW")
    print("=" * 60)
    return ctx


def initialize_car_data(force_regenerate: bool = False) -> DataContext:
    """Shim kept for test compatibility — delegates to initialize_data()."""
    return initialize_data(force_regenerate=force_regenerate)


def run_demo():
    ctx = initialize_data()
    stats = ctx.get_stats()
    PLUGIN = get_active_plugin()

    print("\n" + "=" * 60)
    print(f"DEMO: {PLUGIN.config.display_name} Overview")
    print("=" * 60)

    print(f"\nTotal claims: {stats['total_claims']}")
    print(f"Risk distribution: {stats['risk_distribution']}")
    print(f"Intercepts: {stats['intercepts']['count']} claims, ${stats['intercepts']['held_amount']:,.2f} held")
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
