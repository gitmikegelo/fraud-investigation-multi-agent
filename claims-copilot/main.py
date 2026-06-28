"""Claims Examiner Workflow Copilot - Main Entry Point
Domain: Car Insurance.
"""

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

from domain_config import CAR_INSURANCE, DomainConfig
from data.generate_car import generate_car_data, CarClaim
from intelligence.rules_engine_car import run_car_rules_engine, RuleResult
from intelligence.risk_scoring_car import score_car_claim, RiskBreakdown
from case_queue_car import build_car_case_queue
from cases import Case, CaseType, ClaimType, CasePriority, CaseStatus

# Domain is locked to "car".
DOMAIN_MODE = "car"


@dataclass
class DataContext:
    """Container for all car insurance data.

    Field names are kept as `supplemental_*` for backward compatibility with the
    rest of the codebase — they are domain-neutral containers that here hold car data.
    """
    domain_config: DomainConfig
    supplemental_data: Dict
    supplemental_claims: List
    supplemental_graph: nx.DiGraph
    detected_patterns: List
    case_queue: List[Case] = field(default_factory=list)
    claim_rules: Dict[str, List[RuleResult]] = field(default_factory=dict)
    claim_risk_scores: Dict[str, RiskBreakdown] = field(default_factory=dict)
    claim_doc_results: Dict[str, list] = field(default_factory=dict)

    def get_claim(self, claim_id: str) -> Optional[CarClaim]:
        return next((c for c in self.supplemental_claims if c.claim_id == claim_id), None)

    def get_case(self, case_id: str) -> Optional[Case]:
        return next((c for c in self.case_queue if c.case_id == case_id), None)

    def get_insured(self, insured_id: str):
        return next((i for i in self.supplemental_data.get("insureds", [])
                     if i.insured_id == insured_id), None)

    def get_insured_claims(self, insured_id: str) -> List:
        return [c for c in self.supplemental_claims if c.insured_id == insured_id]

    def get_policy(self, policy_id: str):
        return next((p for p in self.supplemental_data.get("policies", [])
                     if p.policy_id == policy_id), None)

    def get_vehicle(self, vehicle_id: str):
        return next((v for v in self.supplemental_data.get("vehicles", [])
                     if v.vehicle_id == vehicle_id), None)

    def get_shop(self, shop_id: str):
        return next((s for s in self.supplemental_data.get("repair_shops", [])
                     if s.shop_id == shop_id), None)

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

        rule_counts = {}
        for rules in self.claim_rules.values():
            for r in rules:
                if r.triggered:
                    rule_counts[r.rule_id] = rule_counts.get(r.rule_id, 0) + 1

        tasks = self.supplemental_data.get("workflow_tasks", [])
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


def initialize_car_data(force_regenerate: bool = False) -> DataContext:
    """Initialize Car Insurance domain data."""
    cache_file = 'data_cache_v1_car.pkl'

    if not force_regenerate and os.path.exists(cache_file):
        print("=" * 60)
        print("CAR INSURANCE COPILOT - Loading Cache")
        print("=" * 60)
        try:
            with open(cache_file, 'rb') as f:
                ctx = pickle.load(f)
            print(f"✅ Cache loaded ({len(ctx.case_queue)} claims)")
            return ctx
        except Exception as e:
            print(f"⚠️ Cache load failed: {e}\nRegenerating...")

    print("=" * 60)
    print("CAR INSURANCE COPILOT - Initializing")
    print("=" * 60)

    config = CAR_INSURANCE

    print("\n[1/5] Generating car insurance data...")
    data = generate_car_data()
    claims = data["claims"]

    context_dict = {
        "claims": claims,
        "insureds": data["insureds"],
        "vehicles": data["vehicles"],
        "repair_shops": data["repair_shops"],
        "policies": data["policies"],
        "estimates": data["estimates"],
        "police_reports": data["police_reports"],
        "workflow_tasks": data["workflow_tasks"],
        "documents": data["documents"],
    }

    print(f"\n[2/5] Running car rules engine on {len(claims)} claims...")
    claim_rules = {}
    for claim in claims:
        claim_rules[claim.claim_id] = run_car_rules_engine(claim, context_dict)
    triggered_count = sum(1 for rules in claim_rules.values() for r in rules if r.triggered)
    print(f"  → {triggered_count} total rule triggers across all claims")

    print(f"\n[3/5] Scoring claims...")
    claim_risk_scores = {}
    for claim in claims:
        claim_risk_scores[claim.claim_id] = score_car_claim(claim, context_dict, claim_rules.get(claim.claim_id, []))
    high = sum(1 for s in claim_risk_scores.values() if s.tier == "HIGH")
    med = sum(1 for s in claim_risk_scores.values() if s.tier == "MEDIUM")
    low = sum(1 for s in claim_risk_scores.values() if s.tier == "LOW")
    print(f"  → HIGH: {high}, MEDIUM: {med}, LOW: {low}")

    print(f"\n[4/5] Building case queue...")
    case_queue = build_car_case_queue(claims, claim_risk_scores, claim_rules, data)
    print(f"  → {len(case_queue)} cases in queue")

    # No cached vision results — vision runs live in api.py when an image exists.
    claim_doc_results = {doc.claim_id: [] for doc in data["documents"]}

    print(f"\n[5/5] Building entity graph...")
    graph = nx.DiGraph()
    for ins in data["insureds"]:
        graph.add_node(ins.insured_id, entity_type="insured", name=ins.full_name)
    for v in data["vehicles"]:
        graph.add_node(v.vehicle_id, entity_type="vehicle", name=f"{v.year} {v.make} {v.model}")
    for s in data["repair_shops"]:
        graph.add_node(s.shop_id, entity_type="repair_shop", name=s.name)
    for c in claims:
        if c.vehicle_id:
            graph.add_edge(c.insured_id, c.vehicle_id, relationship="OWNS", claim_id=c.claim_id)
        if c.shop_id:
            graph.add_edge(c.insured_id, c.shop_id, relationship="REPAIRED_AT", claim_id=c.claim_id)

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
    print("CAR INSURANCE INITIALIZATION COMPLETE")
    print(f"  {len(case_queue)} claims | {high} HIGH | {med} MEDIUM | {low} LOW")
    print("=" * 60)
    return ctx


def run_demo():
    ctx = initialize_car_data()
    stats = ctx.get_stats()

    print("\n" + "=" * 60)
    print("DEMO: Car Insurance Claims Overview")
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
