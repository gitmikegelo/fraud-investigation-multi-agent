"""Claims Examiner Workflow Copilot - Main Entry Point
Domain: Marine Cargo.
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

from domain_config import MARINE_CARGO, DomainConfig
from data.generate_marine import generate_marine_data, MarineClaim
from intelligence.rules_engine_marine import run_marine_rules_engine, RuleResult
from intelligence.risk_scoring_marine import score_marine_claim, RiskBreakdown
from case_queue_marine import build_marine_case_queue
from cases import Case, CaseType, ClaimType, CasePriority, CaseStatus

# Domain is locked to "marine".
DOMAIN_MODE = "marine"


@dataclass
class DataContext:
    """Container for all marine cargo data.

    Field names are kept as `supplemental_*` for backward compatibility with the
    rest of the codebase — they are domain-neutral containers that here hold marine data.
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

    def get_claim(self, claim_id: str) -> Optional[MarineClaim]:
        return next((c for c in self.supplemental_claims if c.claim_id == claim_id), None)

    def get_case(self, case_id: str) -> Optional[Case]:
        return next((c for c in self.case_queue if c.case_id == case_id), None)

    def _find(self, key: str, attr: str, value):
        return next((x for x in self.supplemental_data.get(key, []) if getattr(x, attr) == value), None)

    def get_consignee(self, party_id: str):
        return self._find("consignees", "party_id", party_id)

    def get_insured(self, party_id: str):
        """Alias — shared code refers to the claimant as the insured."""
        return self.get_consignee(party_id)

    def get_consignee_claims(self, party_id: str) -> List:
        return [c for c in self.supplemental_claims if c.consignee_id == party_id]

    def get_insured_claims(self, party_id: str) -> List:
        return self.get_consignee_claims(party_id)

    def get_prior_claims(self, party_id: str = None, surveyor_id: str = None) -> List:
        return [p for p in self.supplemental_data.get("prior_claims", [])
                if (party_id is None or p.consignee_id == party_id)
                and (surveyor_id is None or p.surveyor_id == surveyor_id)]

    def get_policy(self, policy_id: str):
        return self._find("policies", "policy_id", policy_id)

    def get_shipment(self, shipment_id: str):
        return self._find("shipments", "shipment_id", shipment_id)

    def get_shipper(self, shipper_id: str):
        return self._find("shippers", "shipper_id", shipper_id)

    def get_surveyor(self, surveyor_id: str):
        return self._find("surveyors", "surveyor_id", surveyor_id)

    def get_forwarder(self, forwarder_id: str):
        return self._find("forwarders", "forwarder_id", forwarder_id)

    def get_director(self, director_id: str):
        return self._find("directors", "director_id", director_id)

    def get_survey(self, survey_id: str):
        return self._find("surveys", "survey_id", survey_id)

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
        open_docs = sum(1 for t in tasks if t.task_type == "DOCUMENT_REVIEW" and t.status in ("pending", "in_progress"))
        overdue_recovery = sum(1 for t in tasks if t.task_type == "RECOVERY_NOTICE" and t.status == "overdue")
        past_tat = sum(1 for t in tasks if t.status == "overdue")

        return {
            "total_claims": len(self.case_queue),
            "risk_distribution": {"HIGH": high, "MEDIUM": medium, "LOW": low},
            "intercepts": {"count": high, "held_amount": round(total_held, 2)},
            "top_rules_triggered": sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "patterns_detected": len(self.detected_patterns),
            "pattern_types": [p.pattern_type for p in self.detected_patterns],
            "workflow_health": {"open_document_reviews": open_docs,
                                "overdue_recovery_notices": overdue_recovery, "past_tat": past_tat},
        }


def _context_dict(data: Dict) -> Dict:
    keys = ["claims", "consignees", "shippers", "surveyors", "forwarders", "directors",
            "shipments", "policies", "surveys", "prior_claims", "workflow_tasks", "documents"]
    return {k: data[k] for k in keys}


def _detect_duplicate_images(claims: List) -> Dict[str, list]:
    """Perceptual-hash match of every claim's evidence images against all other image files."""
    try:
        from intelligence.document_vision import find_duplicate_images, _claim_id_to_image_key
    except Exception as e:   # vision deps (boto3/PIL) missing — skip, rule stays untriggered
        print(f"  ⚠ Duplicate-image scan skipped: {e}")
        return {}
    result = {}
    for claim in claims:
        matches = find_duplicate_images(claim.claim_id)
        for m in matches:
            # Image keys look like "mc2988" → claim ID "MC-2988"
            m["other_claim_id"] = f"{m['other_key'][:2].upper()}-{m['other_key'][2:]}"
        if matches:
            result[claim.claim_id] = matches
    return result


def _build_graph(data: Dict, claims: List) -> nx.DiGraph:
    g = nx.DiGraph()
    for p in data["consignees"]:
        g.add_node(p.party_id, entity_type="consignee", name=p.name)
    for s in data["shippers"]:
        g.add_node(s.shipper_id, entity_type="shipper", name=s.name)
    for s in data["surveyors"]:
        g.add_node(s.surveyor_id, entity_type="surveyor", name=s.name)
    for f in data["forwarders"]:
        g.add_node(f.forwarder_id, entity_type="forwarder", name=f.name)
    for d in data["directors"]:
        g.add_node(d.director_id, entity_type="director", name=d.full_name)

    shipments = {s.shipment_id: s for s in data["shipments"]}
    for c in claims:
        shp = shipments.get(c.shipment_id)
        if shp:
            g.add_edge(shp.shipper_id, c.consignee_id, relationship="SHIPPED_TO", claim_id=c.claim_id)
            g.add_edge(c.consignee_id, shp.forwarder_id, relationship="BOOKED_VIA", claim_id=c.claim_id)
        if c.surveyor_id:
            g.add_edge(c.consignee_id, c.surveyor_id, relationship="SURVEYED_BY", claim_id=c.claim_id)
    for pc in data["prior_claims"]:
        g.add_edge(pc.consignee_id, pc.surveyor_id, relationship="SURVEYED_BY", claim_id=pc.claim_id)

    for p in data["consignees"]:
        for did in p.director_ids:
            g.add_edge(did, p.party_id, relationship="DIRECTOR_OF")
    for s in data["surveyors"]:
        for did in s.director_ids:
            g.add_edge(did, s.surveyor_id, relationship="DIRECTOR_OF")
    for f in data["forwarders"]:
        for did in f.director_ids:
            g.add_edge(did, f.forwarder_id, relationship="DIRECTOR_OF")
    return g


def initialize_marine_data(force_regenerate: bool = False) -> DataContext:
    """Initialize Marine Cargo domain data."""
    cache_file = 'data_cache_v1_marine.pkl'

    if not force_regenerate and os.path.exists(cache_file):
        print("=" * 60)
        print("MARINE CARGO COPILOT - Loading Cache")
        print("=" * 60)
        try:
            with open(cache_file, 'rb') as f:
                ctx = pickle.load(f)
            if getattr(ctx.domain_config, "name", "") == MARINE_CARGO.name:
                print(f"[OK] Cache loaded ({len(ctx.case_queue)} claims)")
                return ctx
            print("[WARN] Cache is from another domain -- regenerating...")
        except Exception as e:
            print(f"[WARN] Cache load failed: {e}\nRegenerating...")

    print("=" * 60)
    print("MARINE CARGO COPILOT - Initializing")
    print("=" * 60)

    print("\n[1/5] Generating marine cargo data...")
    data = generate_marine_data()
    claims = data["claims"]
    context_dict = _context_dict(data)
    context_dict["duplicate_images"] = _detect_duplicate_images(claims)
    data["duplicate_images"] = context_dict["duplicate_images"]
    if context_dict["duplicate_images"]:
        print(f"  → Reused evidence photos on: {list(context_dict['duplicate_images'])}")

    print(f"\n[2/5] Running marine rules engine on {len(claims)} claims...")
    claim_rules = {c.claim_id: run_marine_rules_engine(c, context_dict) for c in claims}
    triggered_count = sum(1 for rules in claim_rules.values() for r in rules if r.triggered)
    print(f"  → {triggered_count} total rule triggers across all claims")

    print("\n[3/5] Scoring claims...")
    claim_risk_scores = {c.claim_id: score_marine_claim(c, context_dict, claim_rules[c.claim_id])
                         for c in claims}
    high = sum(1 for s in claim_risk_scores.values() if s.tier == "HIGH")
    med = sum(1 for s in claim_risk_scores.values() if s.tier == "MEDIUM")
    low = sum(1 for s in claim_risk_scores.values() if s.tier == "LOW")
    print(f"  → HIGH: {high}, MEDIUM: {med}, LOW: {low}")

    print("\n[4/5] Building case queue...")
    case_queue = build_marine_case_queue(claims, claim_risk_scores, claim_rules, data)
    print(f"  → {len(case_queue)} cases in queue")

    # Vision results are produced live (and disk-cached) in api.py when an image exists.
    claim_doc_results = {c.claim_id: [] for c in claims}

    print("\n[5/5] Building entity graph...")
    graph = _build_graph(data, claims)

    ctx = DataContext(
        domain_config=MARINE_CARGO,
        supplemental_data=data,
        supplemental_claims=claims,
        supplemental_graph=graph,
        detected_patterns=[],
        case_queue=case_queue,
        claim_rules=claim_rules,
        claim_risk_scores=claim_risk_scores,
        claim_doc_results=claim_doc_results,
    )

    print("\nSaving cache...")
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(ctx, f)
        print(f"[OK] Cached to {cache_file}")
    except Exception as e:
        print(f"[WARN] Cache save failed: {e}")

    print("\n" + "=" * 60)
    print("MARINE CARGO INITIALIZATION COMPLETE")
    print(f"  {len(case_queue)} claims | {high} HIGH | {med} MEDIUM | {low} LOW")
    print("=" * 60)
    return ctx


def run_demo():
    ctx = initialize_marine_data()
    stats = ctx.get_stats()

    print("\n" + "=" * 60)
    print("DEMO: Marine Cargo Claims Overview")
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
