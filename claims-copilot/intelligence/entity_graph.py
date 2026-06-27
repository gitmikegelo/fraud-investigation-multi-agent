"""Entity graph for supplemental health: member/dependent/provider/facility/address/employer."""

import networkx as nx
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class PatternResult:
    pattern_type: str  # dependent_ring, provider_cluster, shared_address_group, termination_rush
    description: str
    entities: List[str]
    severity: str  # HIGH, MEDIUM, LOW
    details: Dict = field(default_factory=dict)


def build_supplemental_health_graph(data: Dict) -> nx.DiGraph:
    """Build a NetworkX DiGraph from supplemental health entities."""
    G = nx.DiGraph()

    # Add employer nodes
    for emp in data.get("employers", []):
        G.add_node(emp.employer_id, entity_type="employer", name=emp.name,
                   industry=emp.industry, state=emp.state)

    # Add member nodes
    for m in data.get("members", []):
        G.add_node(m.member_id, entity_type="member", name=m.full_name,
                   employer_id=m.employer_id, suspicious_banner=m.suspicious_banner)
        G.add_edge(m.member_id, m.employer_id, relationship="EMPLOYED_BY")
        if m.address_id:
            G.add_edge(m.member_id, m.address_id, relationship="LIVES_AT")

    # Add dependent nodes
    for d in data.get("dependents", []):
        G.add_node(d.dependent_id, entity_type="dependent",
                   name=f"{d.first_name} {d.last_name}", relationship=d.relationship,
                   member_id=d.member_id)
        G.add_edge(d.dependent_id, d.member_id, relationship="DEPENDENT_OF")
        if d.address_id:
            G.add_edge(d.dependent_id, d.address_id, relationship="LIVES_AT")

    # Add provider nodes
    for p in data.get("providers", []):
        G.add_node(p.provider_id, entity_type="provider", name=p.name,
                   specialty=p.specialty, is_mill=p.is_mill, state=p.state)
        if p.facility_id:
            G.add_edge(p.provider_id, p.facility_id, relationship="PRACTICES_AT")

    # Add facility nodes
    for f in data.get("facilities", []):
        G.add_node(f.facility_id, entity_type="facility", name=f.name,
                   facility_type=f.type, state=f.state, is_rural=f.is_rural)

    # Add address nodes
    for a in data.get("addresses", []):
        G.add_node(a.address_id, entity_type="address",
                   city=a.city, state=a.state, is_shared=a.is_shared)

    # Add policy nodes
    for p in data.get("policies", []):
        G.add_node(p.policy_id, entity_type="policy", plan_type=p.plan_type,
                   status=p.status, coverage_amount=p.coverage_amount)
        G.add_edge(p.policy_id, p.member_id, relationship="COVERS")

    # Add claim edges (claims connect members to providers)
    for c in data.get("claims", []):
        # Add claim node
        G.add_node(c.claim_id, entity_type="claim",
                   claim_type=c.claim_type,
                   benefit_type=getattr(c, "benefit_type", ""),
                   relationship_type=getattr(c, "relationship_type", "SELF"),
                   batch_claim_id=getattr(c, "batch_claim_id", None),
                   fraud_scenario=c.fraud_scenario,
                   amount=c.claim_amount)
        if c.provider_id:
            G.add_edge(c.member_id, c.provider_id, relationship="TREATED_BY",
                       claim_id=c.claim_id, claim_type=c.claim_type)
        if c.dependent_id and c.provider_id:
            G.add_edge(c.dependent_id, c.provider_id, relationship="TREATED_BY",
                       claim_id=c.claim_id)
        if c.facility_id:
            G.add_edge(c.member_id, c.facility_id, relationship="VISITED",
                       claim_id=c.claim_id)
        # FILED_BY edge: claim -> member
        G.add_edge(c.claim_id, c.member_id, relationship="FILED_BY")
        # SAME_EVENT and STACKED_WITH edges
        for related_id in getattr(c, "related_claim_ids", []):
            G.add_edge(c.claim_id, related_id, relationship="SAME_EVENT")
        for stacked_id in getattr(c, "stacked_with", []):
            G.add_edge(c.claim_id, stacked_id, relationship="STACKED_WITH")

    # Add document nodes
    for doc in data.get("documents", []):
        G.add_node(doc.doc_id, entity_type="document",
                   doc_type=doc.doc_type,
                   source_type=getattr(doc, "source_type", "PROVIDER_PORTAL"),
                   font_consistency=getattr(doc, "font_consistency_score", 1.0),
                   metadata_app=getattr(doc, "metadata_app_signature", None))
        if G.has_node(doc.claim_id):
            G.add_edge(doc.doc_id, doc.claim_id, relationship="SUBMITTED_FOR")

    return G


def detect_patterns(graph: nx.DiGraph, data: Dict) -> List[PatternResult]:
    """Detect cross-claim patterns in the entity graph."""
    patterns = []

    # 1. Dependent rings — members sharing addresses with many dependents
    address_members = {}
    for node, attrs in graph.nodes(data=True):
        if attrs.get("entity_type") == "member":
            for _, target, edata in graph.out_edges(node, data=True):
                if edata.get("relationship") == "LIVES_AT":
                    address_members.setdefault(target, []).append(node)

    for addr_id, member_ids in address_members.items():
        if len(member_ids) >= 3:
            # Count total dependents at this address
            dep_count = 0
            for m_id in member_ids:
                deps = [n for n, a in graph.nodes(data=True)
                        if a.get("entity_type") == "dependent" and a.get("member_id") == m_id]
                dep_count += len(deps)

            patterns.append(PatternResult(
                pattern_type="dependent_ring",
                description=f"Shared address {addr_id}: {len(member_ids)} members, {dep_count} dependents",
                entities=member_ids,
                severity="HIGH" if dep_count > 10 else "MEDIUM",
                details={"address_id": addr_id, "member_count": len(member_ids), "dependent_count": dep_count},
            ))

    # 2. Provider clusters — providers with excessive claim volumes
    provider_claims = {}
    for c in data.get("claims", []):
        provider_claims.setdefault(c.provider_id, []).append(c.claim_id)

    for prov_id, claim_ids in provider_claims.items():
        if len(claim_ids) > 30:
            prov_node = graph.nodes.get(prov_id, {})
            patterns.append(PatternResult(
                pattern_type="provider_cluster",
                description=f"Provider {prov_node.get('name', prov_id)}: {len(claim_ids)} claims",
                entities=[prov_id] + claim_ids[:10],
                severity="HIGH" if len(claim_ids) > 50 else "MEDIUM",
                details={"provider_id": prov_id, "claim_count": len(claim_ids),
                         "is_mill": prov_node.get("is_mill", False)},
            ))

    # 3. Shared address groups
    for addr_id, member_ids in address_members.items():
        addr_data = graph.nodes.get(addr_id, {})
        if addr_data.get("is_shared") and len(member_ids) >= 2:
            patterns.append(PatternResult(
                pattern_type="shared_address_group",
                description=f"Shared address cluster at {addr_id}: {len(member_ids)} members",
                entities=member_ids,
                severity="MEDIUM",
                details={"address_id": addr_id, "member_count": len(member_ids)},
            ))

    # 4. Termination rush — members filing near termination
    for m in data.get("members", []):
        if m.termination_date:
            member_claims = [c for c in data.get("claims", []) if c.member_id == m.member_id]
            rush_claims = []
            for c in member_claims:
                try:
                    from datetime import datetime
                    filed = datetime.strptime(c.date_filed, "%Y-%m-%d")
                    term = datetime.strptime(m.termination_date, "%Y-%m-%d")
                    if 0 <= (term - filed).days <= 14:
                        rush_claims.append(c.claim_id)
                except (ValueError, TypeError):
                    pass
            if len(rush_claims) >= 2:
                patterns.append(PatternResult(
                    pattern_type="termination_rush",
                    description=f"Member {m.member_id}: {len(rush_claims)} claims near termination",
                    entities=[m.member_id] + rush_claims,
                    severity="HIGH",
                    details={"member_id": m.member_id, "termination_date": m.termination_date,
                             "rush_claim_count": len(rush_claims)},
                ))

    # 5. Document tampering cluster
    tampered_claims = [c for c in data.get("claims", []) if c.fraud_scenario == "tampered_records"]
    if tampered_claims:
        patterns.append(PatternResult(
            pattern_type="document_tampering",
            description=f"{len(tampered_claims)} claims with document tampering indicators",
            entities=[c.claim_id for c in tampered_claims],
            severity="HIGH",
            details={"claim_count": len(tampered_claims)},
        ))

    # 6. GP-006: Indemnity Stacking Ring
    batch_groups: Dict = {}
    for c in data.get("claims", []):
        bid = getattr(c, "batch_claim_id", None)
        if bid:
            batch_groups.setdefault(bid, []).append(c)
    for batch_id, batch_claims in batch_groups.items():
        rel_types = {getattr(c, "relationship_type", "SELF") for c in batch_claims}
        if len(batch_claims) >= 4 and len(rel_types) >= 2:
            patterns.append(PatternResult(
                pattern_type="indemnity_stacking_ring",
                description=(f"Batch {batch_id}: {len(batch_claims)} claims across "
                             f"{len(rel_types)} relationship types"),
                entities=[c.claim_id for c in batch_claims],
                severity="HIGH" if len(batch_claims) >= 7 and len(rel_types) >= 3 else "MEDIUM",
                details={"batch_id": batch_id, "claim_count": len(batch_claims),
                         "relationship_types": list(rel_types)},
            ))

    # 7. GP-007: Document Source Mismatch
    facility_map = {f.facility_id: f for f in data.get("facilities", [])}
    claim_map = {c.claim_id: c for c in data.get("claims", [])}
    member_mobile: Dict = {}
    for doc in data.get("documents", []):
        if (getattr(doc, "source_type", "") == "MOBILE_SCAN"
                or getattr(doc, "metadata_app_signature", None)):
            claim = claim_map.get(doc.claim_id)
            if claim and claim.facility_id:
                facility = facility_map.get(claim.facility_id)
                if facility and getattr(facility, "releasepoint_enrolled", False):
                    member_mobile.setdefault(claim.member_id, []).append(doc.doc_id)
    for member_id, doc_ids in member_mobile.items():
        patterns.append(PatternResult(
            pattern_type="document_source_mismatch",
            description=(f"Member {member_id}: {len(doc_ids)} mobile-scan doc(s) when "
                         "facility has ReleasePoint enrolled"),
            entities=[member_id] + doc_ids,
            severity="HIGH" if len(doc_ids) >= 2 else "MEDIUM",
            details={"member_id": member_id, "mobile_doc_count": len(doc_ids)},
        ))

    # 8. GP-008: Cross-Claim Document Contradiction
    member_docs: Dict = {}
    for doc in data.get("documents", []):
        claim = claim_map.get(doc.claim_id)
        if claim:
            member_docs.setdefault(claim.member_id, []).append(doc)
    trusted = {"RELEASEPOINT", "PROVIDER_PORTAL", "PROVIDER_FAX"}
    untrusted = {"MOBILE_SCAN", "UNKNOWN", "MEMBER_UPLOAD_PDF", "MEMBER_EMAIL"}
    for member_id, mdocs in member_docs.items():
        if len(mdocs) < 2:
            continue
        src_types = {getattr(d, "source_type", "PROVIDER_PORTAL") for d in mdocs}
        if src_types & trusted and src_types & untrusted:
            bad_docs = [d.doc_id for d in mdocs
                        if getattr(d, "source_type", "") in untrusted]
            if bad_docs:
                patterns.append(PatternResult(
                    pattern_type="cross_claim_contradiction",
                    description=(f"Member {member_id}: contradictory document sources "
                                 "(trusted provider + untrusted member submission)"),
                    entities=[member_id] + bad_docs,
                    severity="HIGH",
                    details={"member_id": member_id,
                             "source_types": list(src_types),
                             "untrusted_docs": bad_docs},
                ))

    return patterns
