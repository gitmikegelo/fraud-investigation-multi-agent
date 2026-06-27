"""
Investigation Agent Tools â€” 7 tools for supplemental health fraud detection.
Adapted for Prudential supplemental health (dataclass-based DataContext).
"""

import time
import json
from typing import List, Dict, Optional, Annotated
from datetime import datetime, timedelta


MAX_TOOL_OUTPUT_CHARS = 2000


def _tool_log(name: str, msg: str):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"    [{ts}]   tool:{name} -> {msg}", flush=True)


def _truncate_tool_output(output, tool_name: str):
    """Truncate tool output if it exceeds context limits."""
    if output is None:
        return output
    output_str = json.dumps(output, default=str) if isinstance(output, (list, dict)) else str(output)
    if len(output_str) > MAX_TOOL_OUTPUT_CHARS:
        _tool_log(tool_name, f'OUTPUT TRUNCATED from {len(output_str)} to ~{MAX_TOOL_OUTPUT_CHARS} chars')
        if isinstance(output, list) and len(output) > 3:
            return output[:3] + [{"note": f"... {len(output) - 3} more items truncated ..."}]
        if isinstance(output, dict):
            truncated = {}
            for k, v in output.items():
                v_str = str(v)
                truncated[k] = v_str[:300] + "...(truncated)" if len(v_str) > 300 else v
            return truncated
    return output


# ---------------------------------------------------------------------------
# Global context
# ---------------------------------------------------------------------------
_context = None


def set_context(ctx):
    global _context
    _context = ctx


# ---------------------------------------------------------------------------
# 1. scan_suspicious_entities  (replaces scan_new_claims)
# ---------------------------------------------------------------------------
def scan_suspicious_entities(
    min_risk_score: Annotated[int, "Minimum risk score (0-100), default 40"] = 40,
) -> List[Dict]:
    """
    Scan the case queue for high-risk claims and the entities linked to them.

    Returns entities (members, providers, dependents) sorted by risk score.
    Each entry includes: entity_id, entity_type, risk_score, risk_tier,
    claim_id, claim_type, claim_amount, top_factors.
    """
    _tool_log('scan_suspicious_entities', f'Scanning case queue (risk >= {min_risk_score})...')
    t0 = time.time()
    if _context is None:
        return [{"error": "DataContext not initialised"}]

    results = []
    for case in _context.case_queue:
        risk = _context.claim_risk_scores.get(case.case_id)
        if not risk or risk.total_score < min_risk_score:
            continue
        claim = _context.get_claim(case.case_id)
        member_id = getattr(claim, 'member_id', None) or getattr(claim, 'traveler_id', None)
        member = _context.get_member(member_id) if claim and member_id else None

        results.append({
            'entity_id': case.subject_id,
            'entity_type': 'member',
            'entity_name': case.subject_name,
            'risk_score': risk.total_score,
            'risk_tier': risk.tier,
            'claim_id': case.case_id,
            'claim_type': case.claim_type.value if hasattr(case.claim_type, 'value') else str(case.claim_type),
            'claim_amount': float(claim.claim_amount) if claim else 0,
            'provider_id': claim.provider_id if claim else None,
            'top_factors': risk.top_factors[:5],
            'suspicious_banner': member.suspicious_banner if member else False,
        })

    results.sort(key=lambda r: r['risk_score'], reverse=True)
    _tool_log('scan_suspicious_entities', f'Found {len(results)} entities (risk >= {min_risk_score}) in {time.time()-t0:.1f}s')
    return _truncate_tool_output(results[:10], 'scan_suspicious_entities')


# ---------------------------------------------------------------------------
# 2. profile_entity
# ---------------------------------------------------------------------------
def profile_entity(
    entity_id: Annotated[str, "Entity ID to profile (e.g. MBR-0001, PRV-001, DEP-0001)"],
) -> Dict:
    """
    Build a detailed profile for a member, provider, dependent, or employer.

    Returns biographical data, policy summary, claims history, risk indicators,
    and network connections.
    """
    _tool_log('profile_entity', f'Profiling {entity_id}...')
    if _context is None:
        return {"error": "DataContext not initialised"}

    profile: Dict = {"entity_id": entity_id}

    # --- Member ---
    member = _context.get_member(entity_id)
    if member:
        profile['entity_type'] = 'member'
        profile['name'] = member.full_name
        profile['dob'] = member.dob
        profile['gender'] = member.gender
        profile['employer_id'] = member.employer_id
        profile['hire_date'] = member.hire_date
        profile['termination_date'] = member.termination_date
        profile['suspicious_banner'] = member.suspicious_banner
        profile['notes'] = member.notes

        # Dependents
        deps = _context.get_member_dependents(entity_id)
        profile['dependent_count'] = len(deps)
        profile['dependents'] = [
            {'id': d.dependent_id, 'name': f"{d.first_name} {d.last_name}",
             'relationship': d.relationship, 'dob': d.dob}
            for d in deps[:5]
        ]

        # Policies
        policies = [p for p in _context.supplemental_data.get('policies', [])
                     if p.member_id == entity_id]
        profile['policy_count'] = len(policies)
        profile['policies'] = [
            {'id': p.policy_id, 'plan_type': p.plan_type, 'status': p.status,
             'coverage_amount': float(p.coverage_amount), 'premium': float(p.premium),
             'beneficiary_change_date': p.beneficiary_change_date,
             'owner_change_date': p.owner_change_date}
            for p in policies[:5]
        ]

        # Claims
        claims = _context.get_member_claims(entity_id)
        profile['claim_count'] = len(claims)
        profile['total_claimed'] = sum(c.claim_amount for c in claims)
        profile['claims'] = [
            {'id': c.claim_id, 'type': c.claim_type, 'amount': float(c.claim_amount),
             'date_filed': c.date_filed, 'status': c.status, 'provider_id': c.provider_id}
            for c in claims[:5]
        ]

        # Employer
        emp = _context.get_employer(member.employer_id)
        if emp:
            profile['employer_name'] = emp.name
            profile['employer_industry'] = emp.industry

        return _truncate_tool_output(profile, 'profile_entity')

    # --- Provider ---
    provider = _context.get_provider(entity_id)
    if provider:
        profile['entity_type'] = 'provider'
        profile['name'] = provider.name
        profile['specialty'] = provider.specialty
        profile['npi'] = provider.npi
        profile['state'] = provider.state
        profile['is_mill'] = provider.is_mill
        profile['claims_volume'] = provider.claims_volume
        profile['facility_id'] = provider.facility_id

        # Claims treated
        provider_claims = [c for c in _context.supplemental_claims
                           if c.provider_id == entity_id]
        profile['claim_count'] = len(provider_claims)
        profile['total_billed'] = sum(c.claim_amount for c in provider_claims)
        unique_members = set(c.member_id for c in provider_claims)
        profile['unique_members'] = len(unique_members)

        claim_types = {}
        for c in provider_claims:
            claim_types[c.claim_type] = claim_types.get(c.claim_type, 0) + 1
        profile['claim_type_breakdown'] = claim_types

        return _truncate_tool_output(profile, 'profile_entity')

    # --- Dependent ---
    for dep in _context.supplemental_data.get('dependents', []):
        if dep.dependent_id == entity_id:
            profile['entity_type'] = 'dependent'
            profile['name'] = f"{dep.first_name} {dep.last_name}"
            profile['relationship'] = dep.relationship
            profile['dob'] = dep.dob
            profile['member_id'] = dep.member_id
            dep_claims = [c for c in _context.supplemental_claims
                          if c.dependent_id == entity_id]
            profile['claim_count'] = len(dep_claims)
            profile['total_claimed'] = sum(c.claim_amount for c in dep_claims)
            return _truncate_tool_output(profile, 'profile_entity')

    return {"error": f"Entity {entity_id} not found"}


# ---------------------------------------------------------------------------
# 3. compare_to_peers
# ---------------------------------------------------------------------------
def compare_to_peers(
    entity_id: Annotated[str, "Entity ID to compare (member or provider)"],
    metric: Annotated[str, "Metric: claim_amount | claim_count | dependent_claims | provider_volume"],
) -> Dict:
    """
    Compare an entity's metric to their peer group.

    Returns entity_value, peer_avg, peer_std, z_score, peer_count.
    """
    _tool_log('compare_to_peers', f'Comparing {entity_id} on "{metric}"...')
    if _context is None:
        return {"error": "DataContext not initialised"}

    import statistics

    member = _context.get_member(entity_id)
    if member:
        member_claims = _context.get_member_claims(entity_id)
        # Peer group = all members at same employer
        emp_members = [m for m in _context.supplemental_data.get('members', [])
                       if m.employer_id == member.employer_id]
        peer_values = []
        for pm in emp_members:
            pm_claims = _context.get_member_claims(pm.member_id)
            if metric == 'claim_amount':
                peer_values.append(sum(c.claim_amount for c in pm_claims))
            elif metric == 'claim_count':
                peer_values.append(len(pm_claims))
            elif metric == 'dependent_claims':
                deps = _context.get_member_dependents(pm.member_id)
                dep_ids = {d.dependent_id for d in deps}
                dep_count = sum(1 for c in pm_claims if c.dependent_id in dep_ids)
                peer_values.append(dep_count)
            else:
                peer_values.append(0)

        if metric == 'claim_amount':
            entity_value = sum(c.claim_amount for c in member_claims)
        elif metric == 'claim_count':
            entity_value = len(member_claims)
        elif metric == 'dependent_claims':
            deps = _context.get_member_dependents(entity_id)
            dep_ids = {d.dependent_id for d in deps}
            entity_value = sum(1 for c in member_claims if c.dependent_id in dep_ids)
        else:
            entity_value = 0

    else:
        provider = _context.get_provider(entity_id)
        if not provider:
            return {"error": f"Entity {entity_id} not found"}
        provider_claims = [c for c in _context.supplemental_claims
                           if c.provider_id == entity_id]
        # Peer group = all providers
        all_providers = _context.supplemental_data.get('providers', [])
        peer_values = []
        for pp in all_providers:
            pp_claims = [c for c in _context.supplemental_claims
                         if c.provider_id == pp.provider_id]
            if metric == 'claim_amount':
                peer_values.append(sum(c.claim_amount for c in pp_claims))
            elif metric in ('claim_count', 'provider_volume'):
                peer_values.append(len(pp_claims))
            else:
                peer_values.append(0)

        if metric == 'claim_amount':
            entity_value = sum(c.claim_amount for c in provider_claims)
        elif metric in ('claim_count', 'provider_volume'):
            entity_value = len(provider_claims)
        else:
            entity_value = 0

    if len(peer_values) < 2:
        return {"error": "Not enough peers for comparison"}

    peer_avg = statistics.mean(peer_values)
    peer_std = statistics.stdev(peer_values) if len(peer_values) > 1 else 1
    if peer_std == 0:
        peer_std = 1
    z_score = (entity_value - peer_avg) / peer_std

    return _truncate_tool_output({
        'entity_id': entity_id,
        'metric': metric,
        'entity_value': round(float(entity_value), 2),
        'peer_avg': round(float(peer_avg), 2),
        'peer_std': round(float(peer_std), 2),
        'z_score': round(float(z_score), 2),
        'peer_count': len(peer_values),
    }, 'compare_to_peers')


# ---------------------------------------------------------------------------
# 4. get_claim_details
# ---------------------------------------------------------------------------
def get_claim_details(
    entity_id: Annotated[str, "Entity ID (member, provider, or claim ID) to get claims for"],
    limit: Annotated[int, "Maximum number of claims to return, default 10"] = 10,
) -> List[Dict]:
    """
    Get detailed claim records for a member, provider, or single claim ID.

    Returns diagnosis codes, procedures, amounts, dates, document status,
    risk score, and triggered rules.
    """
    _tool_log('get_claim_details', f'Fetching claims for {entity_id} (limit {limit})...')
    if _context is None:
        return [{"error": "DataContext not initialised"}]

    # Single claim lookup
    single = _context.get_claim(entity_id)
    if single:
        claims_list = [single]
    else:
        claims_list = [c for c in _context.supplemental_claims
                       if c.member_id == entity_id or c.provider_id == entity_id
                       or c.dependent_id == entity_id]
    claims_list = claims_list[:limit]

    results = []
    for c in claims_list:
        risk = _context.claim_risk_scores.get(c.claim_id)
        rules = _context.claim_rules.get(c.claim_id, [])
        triggered = [r for r in rules if r.triggered]
        doc = _context.get_document(c.claim_id)

        entry = {
            'claim_id': c.claim_id,
            'claim_type': c.claim_type,
            'member_id': c.member_id,
            'dependent_id': c.dependent_id,
            'provider_id': c.provider_id,
            'policy_id': c.policy_id,
            'claim_amount': float(c.claim_amount),
            'approved_amount': float(c.approved_amount) if c.approved_amount else None,
            'date_filed': c.date_filed,
            'date_of_service': c.date_of_service,
            'diagnosis_codes': c.diagnosis_codes,
            'procedure_codes': c.procedure_codes,
            'status': c.status,
            'is_resubmission': c.is_resubmission,
            'fraud_scenario': c.fraud_scenario,
        }
        if risk:
            entry['risk_score'] = risk.total_score
            entry['risk_tier'] = risk.tier
        if triggered:
            entry['triggered_rules'] = [
                {'rule_id': r.rule_id, 'severity': r.severity,
                 'rule_name': r.rule_name, 'explanation': r.explanation}
                for r in triggered[:5]
            ]
        if doc:
            entry['doc_has_header'] = doc.has_header
            entry['doc_has_signature'] = doc.has_signature
            entry['doc_tampering'] = doc.tampering_indicators
        results.append(entry)

    _tool_log('get_claim_details', f'Returned {len(results)} claims')
    return _truncate_tool_output(results, 'get_claim_details')


# ---------------------------------------------------------------------------
# 5. find_connections
# ---------------------------------------------------------------------------
def find_connections(
    entity_id: Annotated[str, "Entity ID to find connections for"],
    depth: Annotated[int, "Depth of network traversal (1-3), default 2"] = 2,
) -> Dict:
    """
    Traverse the entity graph to find all entities connected within N hops.

    Returns connected_entities (with relationship, type, distance),
    connection_density, total_entities, and relationship_summary.
    """
    _tool_log('find_connections', f'Traversing graph from {entity_id} (depth={depth})...')
    if _context is None:
        return {"error": "DataContext not initialised"}

    G = _context.supplemental_graph
    if entity_id not in G:
        return {"error": f"Entity {entity_id} not in graph"}

    import networkx as nx
    visited = {}
    queue = [(entity_id, 0)]
    while queue:
        node, dist = queue.pop(0)
        if node in visited:
            continue
        visited[node] = dist
        if dist < depth:
            for neighbor in list(G.successors(node)) + list(G.predecessors(node)):
                if neighbor not in visited:
                    queue.append((neighbor, dist + 1))

    connected = []
    rel_summary = {}
    for node, dist in visited.items():
        if node == entity_id:
            continue
        attrs = G.nodes.get(node, {})
        entity_type = attrs.get('entity_type', 'unknown')
        # Get relationship type from edge
        rel = 'connected'
        if G.has_edge(entity_id, node):
            rel = G[entity_id][node].get('relationship', 'connected')
        elif G.has_edge(node, entity_id):
            rel = G[node][entity_id].get('relationship', 'connected')
        rel_summary[rel] = rel_summary.get(rel, 0) + 1
        connected.append({
            'entity_id': node,
            'entity_type': entity_type,
            'name': attrs.get('name', ''),
            'distance': dist,
            'relationship': rel,
        })

    connected.sort(key=lambda e: e['distance'])

    # Density = edges / nodes in subgraph
    subgraph_nodes = list(visited.keys())
    sub = G.subgraph(subgraph_nodes)
    n = sub.number_of_nodes()
    density = sub.number_of_edges() / max(n, 1)

    return _truncate_tool_output({
        'entity_id': entity_id,
        'total_entities': len(connected),
        'connection_density': round(density, 2),
        'relationship_summary': rel_summary,
        'connected_entities': connected[:15],
    }, 'find_connections')


# ---------------------------------------------------------------------------
# 6. find_ring  (detect fraud patterns in the graph)
# ---------------------------------------------------------------------------
def find_ring(
    min_risk_score: Annotated[int, "Minimum risk score for pattern members, default 40"] = 40,
) -> List[Dict]:
    """
    Find detected cross-claim fraud patterns: dependent rings, provider
    clusters, shared address groups, termination rushes, document tampering.

    Uses pre-computed pattern detection results from the entity graph.
    """
    _tool_log('find_ring', f'Returning detected patterns (risk >= {min_risk_score})...')
    if _context is None:
        return [{"error": "DataContext not initialised"}]

    patterns = _context.detected_patterns or []
    results = []
    for p in patterns:
        results.append({
            'pattern_type': p.pattern_type,
            'description': p.description,
            'severity': p.severity,
            'entity_count': len(p.entities),
            'entities': p.entities[:10],
            'details': p.details,
        })

    _tool_log('find_ring', f'Found {len(results)} patterns')
    return _truncate_tool_output(results, 'find_ring')


# ---------------------------------------------------------------------------
# 7. get_referral_history  (provider claim timeline)
# ---------------------------------------------------------------------------
def get_referral_history(
    provider_id: Annotated[str, "Provider ID to analyse"],
    months: Annotated[int, "Number of months of history, default 12"] = 12,
) -> List[Dict]:
    """
    Get monthly claim volume and member concentration for a provider.

    Returns monthly records with total_claims, unique_members,
    top_member, top_member_pct, avg_claim_amount â€” useful for
    detecting sudden volume spikes or single-source concentration.
    """
    _tool_log('get_referral_history', f'Pulling {months}-month history for {provider_id}...')
    if _context is None:
        return [{"error": "DataContext not initialised"}]

    provider_claims = [c for c in _context.supplemental_claims
                       if c.provider_id == provider_id]
    if not provider_claims:
        return [{"note": f"No claims found for {provider_id}"}]

    # Group by month
    monthly: Dict[str, list] = {}
    for c in provider_claims:
        try:
            dt = datetime.strptime(c.date_of_service, '%Y-%m-%d')
        except (ValueError, TypeError):
            continue
        key = dt.strftime('%Y-%m')
        monthly.setdefault(key, []).append(c)

    history = []
    for month_key in sorted(monthly.keys())[-months:]:
        month_claims = monthly[month_key]
        member_counts: Dict[str, int] = {}
        for c in month_claims:
            member_counts[c.member_id] = member_counts.get(c.member_id, 0) + 1
        top_member = max(member_counts, key=member_counts.get) if member_counts else None
        top_pct = (member_counts[top_member] / len(month_claims) * 100) if top_member else 0

        history.append({
            'month': month_key,
            'total_claims': len(month_claims),
            'unique_members': len(member_counts),
            'top_member': top_member,
            'top_member_pct': round(top_pct, 1),
            'avg_claim_amount': round(sum(c.claim_amount for c in month_claims) / len(month_claims), 2),
        })

    _tool_log('get_referral_history', f'Returned {len(history)} months of data')
    return _truncate_tool_output(history, 'get_referral_history')


# ---------------------------------------------------------------------------
# Tool Registry â€” names kept compatible with prompts
# ---------------------------------------------------------------------------
INVESTIGATION_TOOLS = [
    scan_suspicious_entities,
    profile_entity,
    compare_to_peers,
    get_claim_details,
    find_connections,
    find_ring,
    get_referral_history,
]
