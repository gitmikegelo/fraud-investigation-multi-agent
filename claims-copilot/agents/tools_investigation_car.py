"""
Investigation Agent Tools (Car) — 7 tools for Car Insurance fraud detection.

Operates on car entities: insureds (INS), repair shops (SHP), and vehicles (VEH).
The DataContext stores car data under the (legacy-named) supplemental_* fields:
  - claims         → List[CarClaim]
  - entities["insureds"|"repair_shops"|"vehicles"|"policies"|...]
"""

import time
import json
import statistics
from typing import List, Dict, Annotated
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
_context = None


def set_context(ctx):
    global _context
    _context = ctx


# ---- entity accessors (car) -----------------------------------------------
def _insureds() -> List:
    return _context.entities.get("insureds", []) if _context else []


def _shops() -> List:
    return _context.entities.get("repair_shops", []) if _context else []


def _vehicles() -> List:
    return _context.entities.get("vehicles", []) if _context else []


def _policies() -> List:
    return _context.entities.get("policies", []) if _context else []


def _claims() -> List:
    return _context.claims if _context else []


def _get_insured(iid: str):
    return next((i for i in _insureds() if i.insured_id == iid), None)


def _get_shop(sid: str):
    return next((s for s in _shops() if s.shop_id == sid), None)


def _get_vehicle(vid: str):
    return next((v for v in _vehicles() if v.vehicle_id == vid), None)


def _insured_claims(iid: str) -> List:
    return [c for c in _claims() if c.insured_id == iid]


def _shop_claims(sid: str) -> List:
    return [c for c in _claims() if getattr(c, "shop_id", None) == sid]


# ---------------------------------------------------------------------------
# 1. scan_suspicious_entities
# ---------------------------------------------------------------------------
def scan_suspicious_entities(
    min_risk_score: Annotated[int, "Minimum risk score (0-100), default 40"] = 40,
) -> List[Dict]:
    """
    Scan the case queue for high-risk car claims and the entities linked to them.

    Returns entities (insureds, shops) sorted by risk score. Each entry includes:
    entity_id, entity_type, risk_score, risk_tier, claim_id, claim_type,
    claim_amount, vehicle, shop_id, top_factors.
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
        vehicle = _get_vehicle(getattr(claim, "vehicle_id", None)) if claim else None
        results.append({
            'entity_id': case.subject_id,
            'entity_type': 'insured',
            'entity_name': case.subject_name,
            'risk_score': risk.total_score,
            'risk_tier': risk.tier,
            'claim_id': case.case_id,
            'claim_type': case.claim_type.value if hasattr(case.claim_type, 'value') else str(case.claim_type),
            'claim_amount': float(claim.claim_amount) if claim else 0,
            'vehicle': f"{vehicle.year} {vehicle.make} {vehicle.model}" if vehicle else None,
            'shop_id': getattr(claim, 'shop_id', None) if claim else None,
            'fraud_scenario': getattr(claim, 'fraud_scenario', None) if claim else None,
            'top_factors': risk.top_factors[:5],
        })

    results.sort(key=lambda r: r['risk_score'], reverse=True)
    _tool_log('scan_suspicious_entities', f'Found {len(results)} entities in {time.time()-t0:.1f}s')
    return _truncate_tool_output(results[:10], 'scan_suspicious_entities')


# ---------------------------------------------------------------------------
# 2. profile_entity
# ---------------------------------------------------------------------------
def profile_entity(
    entity_id: Annotated[str, "Entity ID to profile (e.g. INS-0001, SHP-001, VEH-0001)"],
) -> Dict:
    """
    Build a detailed profile for an insured, repair shop, or vehicle.

    Returns profile data, policy summary, claims history, and risk indicators.
    """
    _tool_log('profile_entity', f'Profiling {entity_id}...')
    if _context is None:
        return {"error": "DataContext not initialised"}

    profile: Dict = {"entity_id": entity_id}

    insured = _get_insured(entity_id)
    if insured:
        profile['entity_type'] = 'insured'
        profile['name'] = insured.full_name
        profile['dob'] = insured.dob
        profile['address_state'] = insured.address_state
        profile['license_years'] = insured.license_years
        profile['stored_claim_history'] = insured.claim_history_count
        profile['flagged'] = insured.flagged
        profile['notes'] = insured.notes

        policies = [p for p in _policies() if p.insured_id == entity_id]
        profile['policy_count'] = len(policies)
        profile['policies'] = [
            {'id': p.policy_id, 'status': p.status,
             'coverage': f"{p.effective_date} → {p.expiration_date}",
             'collision': float(p.coverage_collision),
             'comprehensive': float(p.coverage_comprehensive)}
            for p in policies[:5]
        ]

        claims = _insured_claims(entity_id)
        profile['claim_count'] = len(claims)
        profile['total_claimed'] = sum(c.claim_amount for c in claims)
        profile['claims'] = [
            {'id': c.claim_id, 'type': c.claim_type, 'amount': float(c.claim_amount),
             'date_filed': c.date_filed, 'status': c.status, 'fraud_scenario': c.fraud_scenario}
            for c in claims[:5]
        ]
        return _truncate_tool_output(profile, 'profile_entity')

    shop = _get_shop(entity_id)
    if shop:
        profile['entity_type'] = 'shop'
        profile['name'] = shop.name
        profile['state'] = shop.state
        profile['on_watchlist'] = shop.on_watchlist
        profile['in_network'] = shop.in_network
        profile['verified'] = shop.verified
        profile['notes'] = shop.notes
        sclaims = _shop_claims(entity_id)
        profile['claim_count'] = len(sclaims)
        profile['total_billed'] = sum(c.claim_amount for c in sclaims)
        profile['unique_insureds'] = len({c.insured_id for c in sclaims})
        return _truncate_tool_output(profile, 'profile_entity')

    vehicle = _get_vehicle(entity_id)
    if vehicle:
        profile['entity_type'] = 'vehicle'
        profile['description'] = f"{vehicle.year} {vehicle.make} {vehicle.model}"
        profile['vin'] = vehicle.vin
        profile['body_type'] = vehicle.body_type
        profile['acv'] = vehicle.acv
        profile['salvage_flag'] = vehicle.salvage_flag
        vclaims = [c for c in _claims() if getattr(c, 'vehicle_id', None) == entity_id]
        profile['claim_count'] = len(vclaims)
        profile['total_claimed'] = sum(c.claim_amount for c in vclaims)
        return _truncate_tool_output(profile, 'profile_entity')

    return {"error": f"Entity {entity_id} not found"}


# ---------------------------------------------------------------------------
# 3. compare_to_peers
# ---------------------------------------------------------------------------
def compare_to_peers(
    entity_id: Annotated[str, "Entity ID to compare (insured or shop)"],
    metric: Annotated[str, "Metric: claim_amount | claim_count | shop_volume"],
) -> Dict:
    """
    Compare an entity's metric to its peer group.

    Insureds are compared against all insureds; shops against all shops.
    Returns entity_value, peer_avg, peer_std, z_score, peer_count.
    """
    _tool_log('compare_to_peers', f'Comparing {entity_id} on "{metric}"...')
    if _context is None:
        return {"error": "DataContext not initialised"}

    insured = _get_insured(entity_id)
    if insured:
        my_claims = _insured_claims(entity_id)
        peer_values = []
        for pi in _insureds():
            pc = _insured_claims(pi.insured_id)
            if metric == 'claim_amount':
                peer_values.append(sum(c.claim_amount for c in pc))
            elif metric == 'claim_count':
                peer_values.append(len(pc))
            else:
                peer_values.append(0)
        if metric == 'claim_amount':
            entity_value = sum(c.claim_amount for c in my_claims)
        elif metric == 'claim_count':
            entity_value = len(my_claims)
        else:
            entity_value = 0
    else:
        shop = _get_shop(entity_id)
        if not shop:
            return {"error": f"Entity {entity_id} not found"}
        my_claims = _shop_claims(entity_id)
        peer_values = []
        for ps in _shops():
            pc = _shop_claims(ps.shop_id)
            if metric == 'claim_amount':
                peer_values.append(sum(c.claim_amount for c in pc))
            elif metric in ('claim_count', 'shop_volume'):
                peer_values.append(len(pc))
            else:
                peer_values.append(0)
        if metric == 'claim_amount':
            entity_value = sum(c.claim_amount for c in my_claims)
        elif metric in ('claim_count', 'shop_volume'):
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
    entity_id: Annotated[str, "Entity ID (insured, shop, or claim ID) to get claims for"],
    limit: Annotated[int, "Maximum number of claims to return, default 10"] = 10,
) -> List[Dict]:
    """
    Get detailed claim records for an insured, shop, or single claim ID.

    Returns amounts, dates, claim-type-specific fields, document checks, risk score,
    and triggered rules.
    """
    _tool_log('get_claim_details', f'Fetching claims for {entity_id} (limit {limit})...')
    if _context is None:
        return [{"error": "DataContext not initialised"}]

    single = _context.get_claim(entity_id)
    if single:
        claims_list = [single]
    else:
        claims_list = [c for c in _claims()
                       if c.insured_id == entity_id
                       or getattr(c, 'shop_id', None) == entity_id
                       or getattr(c, 'vehicle_id', None) == entity_id]
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
            'insured_id': c.insured_id,
            'shop_id': getattr(c, 'shop_id', None),
            'vehicle_id': getattr(c, 'vehicle_id', None),
            'policy_id': c.policy_id,
            'claim_amount': float(c.claim_amount),
            'approved_amount': float(c.approved_amount) if c.approved_amount else None,
            'date_filed': c.date_filed,
            'date_of_incident': c.date_of_incident,
            'status': c.status,
            'is_resubmission': c.is_resubmission,
            'injury_claimed': c.injury_claimed,
            'police_report_filed': c.police_report_filed,
            'photo_evidence': getattr(c, 'photo_evidence', False),
            'fraud_scenario': c.fraud_scenario,
            'false_positive_scenario': c.false_positive_scenario,
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
    (insureds ↔ vehicles ↔ shops).
    """
    _tool_log('find_connections', f'Traversing graph from {entity_id} (depth={depth})...')
    if _context is None:
        return {"error": "DataContext not initialised"}

    G = _context.graph
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
    sub = G.subgraph(list(visited.keys()))
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
    otherwise derives repair-shop rings on the fly:
      - watchlisted/out-of-network shops with multiple high-value claims
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
        for shop in _shops():
            if not (shop.on_watchlist or not shop.in_network):
                continue
            sclaims = [c for c in _shop_claims(shop.shop_id)
                       if (rs.get(c.claim_id).total_score if rs.get(c.claim_id) else 0) >= min_risk_score]
            if sclaims:
                results.append({
                    'pattern_type': 'repair_shop_ring',
                    'description': f"{'Watchlisted' if shop.on_watchlist else 'Out-of-network'} shop "
                                   f"'{shop.name}' linked to {len(sclaims)} high-risk claim(s)",
                    'severity': 'CRITICAL' if shop.on_watchlist else 'HIGH',
                    'entity_count': 1 + len({c.insured_id for c in sclaims}),
                    'entities': [shop.shop_id] + [c.insured_id for c in sclaims][:9],
                    'details': {'shop_id': shop.shop_id,
                                'claims': [c.claim_id for c in sclaims],
                                'total_billed': round(sum(c.claim_amount for c in sclaims), 2)},
                })

    _tool_log('find_ring', f'Found {len(results)} patterns')
    return _truncate_tool_output(results, 'find_ring')


# ---------------------------------------------------------------------------
# 7. get_shop_history  (repair-shop claim timeline)
# ---------------------------------------------------------------------------
def get_shop_history(
    shop_id: Annotated[str, "Repair shop ID to analyse"],
    months: Annotated[int, "Number of months of history, default 12"] = 12,
) -> List[Dict]:
    """
    Get monthly claim volume and insured concentration for a repair shop.

    Returns monthly records with total_claims, unique_insureds, top_insured,
    top_insured_pct, avg_claim_amount — useful for detecting volume spikes or
    single-source concentration at a suspect shop.
    """
    _tool_log('get_shop_history', f'Pulling {months}-month history for {shop_id}...')
    if _context is None:
        return [{"error": "DataContext not initialised"}]

    sclaims = _shop_claims(shop_id)
    if not sclaims:
        return [{"note": f"No claims found for {shop_id}"}]

    monthly: Dict[str, list] = {}
    for c in sclaims:
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
            counts[c.insured_id] = counts.get(c.insured_id, 0) + 1
        top = max(counts, key=counts.get) if counts else None
        top_pct = (counts[top] / len(mc) * 100) if top else 0
        history.append({
            'month': month_key,
            'total_claims': len(mc),
            'unique_insureds': len(counts),
            'top_insured': top,
            'top_insured_pct': round(top_pct, 1),
            'avg_claim_amount': round(sum(c.claim_amount for c in mc) / len(mc), 2),
        })

    _tool_log('get_shop_history', f'Returned {len(history)} months of data')
    return _truncate_tool_output(history, 'get_shop_history')


# ---------------------------------------------------------------------------
INVESTIGATION_TOOLS = [
    scan_suspicious_entities,
    profile_entity,
    compare_to_peers,
    get_claim_details,
    find_connections,
    find_ring,
    get_shop_history,
]
