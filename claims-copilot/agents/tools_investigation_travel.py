"""
Investigation Agent Tools (Travel) — 7 tools for Zurich Travel Guard fraud detection.

Mirrors agents/tools_investigation.py (supplemental health) but operates on travel
entities: travelers (TRV), overseas medical providers (MPR), and destinations (DST).
The DataContext stores travel data under the (legacy-named) supplemental_* fields:
  - supplemental_claims         → List[TravelClaim]
  - supplemental_data["travelers"|"providers"|"destinations"|"policies"|"companions"|...]
"""

import time
import json
import statistics
from typing import List, Dict, Optional, Annotated
from datetime import datetime


MAX_TOOL_OUTPUT_CHARS = 2000


def _tool_log(name: str, msg: str):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"    [{ts}]   tool:{name} -> {msg}", flush=True)


def _truncate_tool_output(output, tool_name: str):
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


# ---- entity accessors (travel) --------------------------------------------
def _travelers() -> List:
    return _context.supplemental_data.get("travelers", []) if _context else []


def _providers() -> List:
    return _context.supplemental_data.get("providers", []) if _context else []


def _destinations() -> List:
    return _context.supplemental_data.get("destinations", []) if _context else []


def _policies() -> List:
    return _context.supplemental_data.get("policies", []) if _context else []


def _claims() -> List:
    return _context.supplemental_claims if _context else []


def _get_traveler(tid: str):
    return next((t for t in _travelers() if t.traveler_id == tid), None)


def _get_provider(pid: str):
    return next((p for p in _providers() if p.provider_id == pid), None)


def _get_destination(did: str):
    return next((d for d in _destinations() if d.destination_id == did), None)


def _traveler_claims(tid: str) -> List:
    return [c for c in _claims() if c.traveler_id == tid]


def _provider_claims(pid: str) -> List:
    return [c for c in _claims() if getattr(c, "provider_id", None) == pid]


# ---------------------------------------------------------------------------
# 1. scan_suspicious_entities
# ---------------------------------------------------------------------------
def scan_suspicious_entities(
    min_risk_score: Annotated[int, "Minimum risk score (0-100), default 40"] = 40,
) -> List[Dict]:
    """
    Scan the case queue for high-risk travel claims and the entities linked to them.

    Returns entities (travelers, overseas providers) sorted by risk score. Each entry
    includes: entity_id, entity_type, risk_score, risk_tier, claim_id, claim_type,
    claim_amount, destination, provider_id, top_factors.
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
        dest = _get_destination(getattr(claim, "destination_id", None)) if claim else None
        results.append({
            'entity_id': case.subject_id,
            'entity_type': 'traveler',
            'entity_name': case.subject_name,
            'risk_score': risk.total_score,
            'risk_tier': risk.tier,
            'claim_id': case.case_id,
            'claim_type': case.claim_type.value if hasattr(case.claim_type, 'value') else str(case.claim_type),
            'claim_amount': float(claim.claim_amount) if claim else 0,
            'destination': f"{dest.city}, {dest.country}" if dest else None,
            'provider_id': getattr(claim, 'provider_id', None) if claim else None,
            'fraud_scenario': getattr(claim, 'fraud_scenario', None) if claim else None,
            'top_factors': risk.top_factors[:5],
        })

    results.sort(key=lambda r: r['risk_score'], reverse=True)
    _tool_log('scan_suspicious_entities', f'Found {len(results)} entities (risk >= {min_risk_score}) in {time.time()-t0:.1f}s')
    return _truncate_tool_output(results[:10], 'scan_suspicious_entities')


# ---------------------------------------------------------------------------
# 2. profile_entity
# ---------------------------------------------------------------------------
def profile_entity(
    entity_id: Annotated[str, "Entity ID to profile (e.g. TRV-0001, MPR-001, DST-001)"],
) -> Dict:
    """
    Build a detailed profile for a traveler, overseas provider, or destination.

    Returns biographical/profile data, policy summary, claims history, and risk indicators.
    """
    _tool_log('profile_entity', f'Profiling {entity_id}...')
    if _context is None:
        return {"error": "DataContext not initialised"}

    profile: Dict = {"entity_id": entity_id}

    # --- Traveler ---
    traveler = _get_traveler(entity_id)
    if traveler:
        profile['entity_type'] = 'traveler'
        profile['name'] = traveler.full_name
        profile['dob'] = traveler.dob
        profile['loyalty_tier'] = traveler.loyalty_tier
        profile['address_state'] = traveler.address_state
        profile['stored_claim_history'] = traveler.claim_history_count
        profile['flagged'] = traveler.flagged
        profile['notes'] = traveler.notes

        policies = [p for p in _policies() if p.traveler_id == entity_id]
        profile['policy_count'] = len(policies)
        profile['policies'] = [
            {'id': p.policy_id, 'plan_type': p.plan_type, 'status': p.status,
             'trip': f"{p.trip_start_date} → {p.trip_end_date}",
             'coverage_medical': float(p.coverage_medical),
             'coverage_baggage': float(p.coverage_baggage)}
            for p in policies[:5]
        ]

        claims = _traveler_claims(entity_id)
        profile['claim_count'] = len(claims)
        profile['total_claimed'] = sum(c.claim_amount for c in claims)
        profile['claims'] = [
            {'id': c.claim_id, 'type': c.claim_type, 'amount': float(c.claim_amount),
             'date_filed': c.date_filed, 'status': c.status,
             'fraud_scenario': c.fraud_scenario}
            for c in claims[:5]
        ]
        return _truncate_tool_output(profile, 'profile_entity')

    # --- Provider (overseas medical) ---
    provider = _get_provider(entity_id)
    if provider:
        profile['entity_type'] = 'provider'
        profile['name'] = provider.name
        profile['provider_type'] = provider.provider_type
        profile['on_watchlist'] = provider.on_watchlist
        profile['verified'] = provider.verified
        profile['notes'] = provider.notes
        dest = _get_destination(provider.destination_id)
        profile['location'] = f"{dest.city}, {dest.country}" if dest else provider.destination_id

        pclaims = _provider_claims(entity_id)
        profile['claim_count'] = len(pclaims)
        profile['total_billed'] = sum(c.claim_amount for c in pclaims)
        profile['unique_travelers'] = len({c.traveler_id for c in pclaims})
        return _truncate_tool_output(profile, 'profile_entity')

    # --- Destination ---
    dest = _get_destination(entity_id)
    if dest:
        profile['entity_type'] = 'destination'
        profile['city'] = dest.city
        profile['country'] = dest.country
        profile['region'] = dest.region
        profile['risk_level'] = dest.risk_level
        profile['known_fraud_ring'] = dest.known_fraud_ring
        profile['avg_medical_cost_per_day'] = dest.avg_medical_cost_per_day
        dclaims = [c for c in _claims() if getattr(c, 'destination_id', None) == entity_id]
        profile['claim_count'] = len(dclaims)
        profile['total_claimed'] = sum(c.claim_amount for c in dclaims)
        return _truncate_tool_output(profile, 'profile_entity')

    return {"error": f"Entity {entity_id} not found"}


# ---------------------------------------------------------------------------
# 3. compare_to_peers
# ---------------------------------------------------------------------------
def compare_to_peers(
    entity_id: Annotated[str, "Entity ID to compare (traveler or provider)"],
    metric: Annotated[str, "Metric: claim_amount | claim_count | baggage_value | provider_volume"],
) -> Dict:
    """
    Compare an entity's metric to its peer group.

    Travelers are compared against all travelers; providers against all providers.
    Returns entity_value, peer_avg, peer_std, z_score, peer_count.
    """
    _tool_log('compare_to_peers', f'Comparing {entity_id} on "{metric}"...')
    if _context is None:
        return {"error": "DataContext not initialised"}

    def _baggage_value(claims):
        # sum of claim amounts for baggage_loss claims (the padding signal)
        return sum(c.claim_amount for c in claims if c.claim_type == "baggage_loss")

    traveler = _get_traveler(entity_id)
    if traveler:
        my_claims = _traveler_claims(entity_id)
        peer_values = []
        for pt in _travelers():
            pc = _traveler_claims(pt.traveler_id)
            if metric == 'claim_amount':
                peer_values.append(sum(c.claim_amount for c in pc))
            elif metric == 'claim_count':
                peer_values.append(len(pc))
            elif metric == 'baggage_value':
                peer_values.append(_baggage_value(pc))
            else:
                peer_values.append(0)
        if metric == 'claim_amount':
            entity_value = sum(c.claim_amount for c in my_claims)
        elif metric == 'claim_count':
            entity_value = len(my_claims)
        elif metric == 'baggage_value':
            entity_value = _baggage_value(my_claims)
        else:
            entity_value = 0
    else:
        provider = _get_provider(entity_id)
        if not provider:
            return {"error": f"Entity {entity_id} not found"}
        my_claims = _provider_claims(entity_id)
        peer_values = []
        for pp in _providers():
            pc = _provider_claims(pp.provider_id)
            if metric == 'claim_amount':
                peer_values.append(sum(c.claim_amount for c in pc))
            elif metric in ('claim_count', 'provider_volume'):
                peer_values.append(len(pc))
            else:
                peer_values.append(0)
        if metric == 'claim_amount':
            entity_value = sum(c.claim_amount for c in my_claims)
        elif metric in ('claim_count', 'provider_volume'):
            entity_value = len(my_claims)
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
    entity_id: Annotated[str, "Entity ID (traveler, provider, or claim ID) to get claims for"],
    limit: Annotated[int, "Maximum number of claims to return, default 10"] = 10,
) -> List[Dict]:
    """
    Get detailed claim records for a traveler, provider, or single claim ID.

    Returns amounts, dates, claim-type-specific fields (delay hours, baggage items,
    medical diagnosis), document checks, risk score, and triggered rules.
    """
    _tool_log('get_claim_details', f'Fetching claims for {entity_id} (limit {limit})...')
    if _context is None:
        return [{"error": "DataContext not initialised"}]

    single = _context.get_claim(entity_id)
    if single:
        claims_list = [single]
    else:
        claims_list = [c for c in _claims()
                       if c.traveler_id == entity_id
                       or getattr(c, 'provider_id', None) == entity_id
                       or getattr(c, 'destination_id', None) == entity_id]
    claims_list = claims_list[:limit]

    results = []
    for c in claims_list:
        risk = _context.claim_risk_scores.get(c.claim_id)
        rules = _context.claim_rules.get(c.claim_id, [])
        triggered = [r for r in rules if r.triggered]
        doc_checks = _context.claim_doc_results.get(c.claim_id, [])

        entry = {
            'claim_id': c.claim_id,
            'claim_type': c.claim_type,
            'traveler_id': c.traveler_id,
            'provider_id': getattr(c, 'provider_id', None),
            'destination_id': getattr(c, 'destination_id', None),
            'policy_id': c.policy_id,
            'claim_amount': float(c.claim_amount),
            'approved_amount': float(c.approved_amount) if c.approved_amount else None,
            'date_filed': c.date_filed,
            'date_of_incident': c.date_of_incident,
            'status': c.status,
            'is_resubmission': c.is_resubmission,
            'fraud_scenario': c.fraud_scenario,
            'false_positive_scenario': c.false_positive_scenario,
        }
        # claim-type-specific signals
        if c.claim_type == "travel_delay":
            entry['delay_hours'] = c.delay_hours
        if c.claim_type == "baggage_loss":
            entry['baggage_items'] = c.baggage_items
            entry['photo_evidence'] = getattr(c, 'photo_evidence', False)
        if c.claim_type == "medical_emergency":
            entry['medical_diagnosis'] = c.medical_diagnosis
        if getattr(c, 'cancellation_reason', ''):
            entry['cancellation_reason'] = c.cancellation_reason

        if risk:
            entry['risk_score'] = risk.total_score
            entry['risk_tier'] = risk.tier
        if triggered:
            entry['triggered_rules'] = [
                {'rule_id': r.rule_id, 'severity': r.severity,
                 'rule_name': r.rule_name, 'explanation': r.explanation}
                for r in triggered[:5]
            ]
        if doc_checks:
            failed = [d for d in doc_checks if not d.passed]
            entry['failed_doc_checks'] = [
                {'check_id': d.check_id, 'severity': d.severity, 'explanation': d.explanation}
                for d in failed[:5]
            ]
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
    Traverse the entity graph to find all entities connected within N hops
    (travelers ↔ destinations ↔ providers).

    Returns connected_entities (with relationship, type, distance),
    connection_density, total_entities, and relationship_summary.
    """
    _tool_log('find_connections', f'Traversing graph from {entity_id} (depth={depth})...')
    if _context is None:
        return {"error": "DataContext not initialised"}

    G = _context.supplemental_graph
    if entity_id not in G:
        return {"error": f"Entity {entity_id} not in graph"}

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
# 6. find_ring
# ---------------------------------------------------------------------------
def find_ring(
    min_risk_score: Annotated[int, "Minimum risk score for pattern members, default 40"] = 40,
) -> List[Dict]:
    """
    Find cross-claim fraud patterns. Uses pre-computed detected_patterns when present;
    otherwise derives destination/provider rings on the fly:
      - watchlisted/unverified overseas providers with multiple high-value medical claims
      - destinations flagged as known fraud rings with clustered claims
    """
    _tool_log('find_ring', f'Detecting rings (risk >= {min_risk_score})...')
    if _context is None:
        return [{"error": "DataContext not initialised"}]

    results = []
    for p in (_context.detected_patterns or []):
        results.append({
            'pattern_type': p.pattern_type,
            'description': p.description,
            'severity': p.severity,
            'entity_count': len(p.entities),
            'entities': p.entities[:10],
            'details': p.details,
        })

    if not results:
        rs = _context.claim_risk_scores
        # Provider rings
        for prov in _providers():
            if not (prov.on_watchlist or not prov.verified):
                continue
            pclaims = [c for c in _provider_claims(prov.provider_id)
                       if (rs.get(c.claim_id).total_score if rs.get(c.claim_id) else 0) >= min_risk_score]
            if pclaims:
                dest = _get_destination(prov.destination_id)
                results.append({
                    'pattern_type': 'destination_fraud_ring',
                    'description': f"{'Watchlisted' if prov.on_watchlist else 'Unverified'} provider "
                                   f"'{prov.name}' in {dest.city if dest else prov.destination_id} "
                                   f"linked to {len(pclaims)} high-risk medical claim(s)",
                    'severity': 'CRITICAL' if prov.on_watchlist else 'HIGH',
                    'entity_count': 1 + len({c.traveler_id for c in pclaims}),
                    'entities': [prov.provider_id] + [c.traveler_id for c in pclaims][:9],
                    'details': {'provider_id': prov.provider_id,
                                'claims': [c.claim_id for c in pclaims],
                                'total_billed': round(sum(c.claim_amount for c in pclaims), 2)},
                })
        # Destination clusters
        for dst in _destinations():
            if not dst.known_fraud_ring:
                continue
            dclaims = [c for c in _claims()
                       if getattr(c, 'destination_id', None) == dst.destination_id
                       and (rs.get(c.claim_id).total_score if rs.get(c.claim_id) else 0) >= min_risk_score]
            if len(dclaims) >= 2:
                results.append({
                    'pattern_type': 'destination_cluster',
                    'description': f"Destination {dst.city}, {dst.country} (known fraud ring) has "
                                   f"{len(dclaims)} clustered high-risk claim(s)",
                    'severity': 'HIGH',
                    'entity_count': len({c.traveler_id for c in dclaims}),
                    'entities': [c.traveler_id for c in dclaims][:10],
                    'details': {'destination_id': dst.destination_id,
                                'claims': [c.claim_id for c in dclaims]},
                })

    _tool_log('find_ring', f'Found {len(results)} patterns')
    return _truncate_tool_output(results, 'find_ring')


# ---------------------------------------------------------------------------
# 7. get_referral_history  (overseas provider claim timeline)
# ---------------------------------------------------------------------------
def get_referral_history(
    provider_id: Annotated[str, "Overseas provider ID to analyse"],
    months: Annotated[int, "Number of months of history, default 12"] = 12,
) -> List[Dict]:
    """
    Get monthly claim volume and traveler concentration for an overseas provider.

    Returns monthly records with total_claims, unique_travelers, top_traveler,
    top_traveler_pct, avg_claim_amount — useful for detecting volume spikes or
    single-source concentration at a suspect facility.
    """
    _tool_log('get_referral_history', f'Pulling {months}-month history for {provider_id}...')
    if _context is None:
        return [{"error": "DataContext not initialised"}]

    pclaims = _provider_claims(provider_id)
    if not pclaims:
        return [{"note": f"No claims found for {provider_id}"}]

    monthly: Dict[str, list] = {}
    for c in pclaims:
        try:
            dt = datetime.strptime(c.date_of_incident or c.date_filed, '%Y-%m-%d')
        except (ValueError, TypeError):
            continue
        monthly.setdefault(dt.strftime('%Y-%m'), []).append(c)

    history = []
    for month_key in sorted(monthly.keys())[-months:]:
        mc = monthly[month_key]
        counts: Dict[str, int] = {}
        for c in mc:
            counts[c.traveler_id] = counts.get(c.traveler_id, 0) + 1
        top = max(counts, key=counts.get) if counts else None
        top_pct = (counts[top] / len(mc) * 100) if top else 0
        history.append({
            'month': month_key,
            'total_claims': len(mc),
            'unique_travelers': len(counts),
            'top_traveler': top,
            'top_traveler_pct': round(top_pct, 1),
            'avg_claim_amount': round(sum(c.claim_amount for c in mc) / len(mc), 2),
        })

    _tool_log('get_referral_history', f'Returned {len(history)} months of data')
    return _truncate_tool_output(history, 'get_referral_history')


# ---------------------------------------------------------------------------
# Tool Registry — names kept identical to the supplemental set so prompts/graph match
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
