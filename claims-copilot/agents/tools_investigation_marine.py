"""
Investigation Agent Tools (Marine Cargo) — 7 tools for marine cargo fraud investigation.

Entities:
  - consignees / claimants (CNE-xxx)
  - surveyors              (SVY-xxx)
  - forwarders             (FWD-xxx)
  - shippers / sellers     (SHR-xxx)
  - directors              (DIR-xxx)

The DataContext stores marine data under the (legacy-named) supplemental_* fields:
  - supplemental_claims  → List[MarineClaim]
  - supplemental_data["consignees"|"surveyors"|"forwarders"|"shippers"|"directors"|"shipments"|...]
  - supplemental_graph   → DiGraph with SHIPPED_TO, BOOKED_VIA, SURVEYED_BY, DIRECTOR_OF edges

Every tool returns JSON-serialisable data and never raises.
"""

import time
import json
import functools
import statistics
from typing import List, Dict, Annotated, Optional
from datetime import datetime

from langchain_core.tools import tool


MAX_TOOL_OUTPUT_CHARS = 2500


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
                if isinstance(v, list) and len(v) > 6:
                    truncated[k] = v[:6] + [f"... {len(v) - 6} more"]
                else:
                    v_str = str(v)
                    truncated[k] = v_str[:400] + "...(truncated)" if len(v_str) > 400 else v
            return truncated
    return output


# ---------------------------------------------------------------------------
_context = None


def set_context(ctx):
    global _context
    _context = ctx


def _safe(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if _context is None:
            return {"error": "DataContext not initialised"}
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            try:
                _tool_log(fn.__name__, f"ERROR: {str(e)[:150]}")
            except Exception:
                pass
            return {"error": f"{fn.__name__} failed: {str(e)[:200]}"}
    return wrapper


# ---- entity accessors (marine) ---------------------------------------------
def _data(key: str) -> List:
    return _context.supplemental_data.get(key, []) if _context else []


def _claims() -> List:
    return _context.supplemental_claims if _context else []


def _priors() -> List:
    return _data("prior_claims")


def _shipments() -> Dict:
    return {s.shipment_id: s for s in _data("shipments")}


def _entity(entity_id: str):
    """Return (entity_type, entity) for any marine entity ID."""
    for etype, key, attr in (("consignee", "consignees", "party_id"), ("surveyor", "surveyors", "surveyor_id"),
                             ("forwarder", "forwarders", "forwarder_id"), ("shipper", "shippers", "shipper_id"),
                             ("director", "directors", "director_id")):
        e = next((x for x in _data(key) if getattr(x, attr) == entity_id), None)
        if e:
            return etype, e
    return None, None


def _name(entity_id: Optional[str]) -> str:
    if not entity_id:
        return "N/A"
    etype, e = _entity(entity_id)
    if not e:
        return entity_id
    return e.full_name if etype == "director" else e.name


def _risk(claim_id: str) -> float:
    r = _context.claim_risk_scores.get(claim_id) if _context else None
    return r.total_score if r else 0.0


def _claims_for(entity_id: str) -> List:
    """Open (working-queue) claims linked to an entity."""
    etype, _ = _entity(entity_id)
    shp = _shipments()
    if etype == "consignee":
        return [c for c in _claims() if c.consignee_id == entity_id]
    if etype == "surveyor":
        return [c for c in _claims() if c.surveyor_id == entity_id]
    if etype == "forwarder":
        return [c for c in _claims() if shp.get(c.shipment_id) and shp[c.shipment_id].forwarder_id == entity_id]
    if etype == "shipper":
        return [c for c in _claims() if shp.get(c.shipment_id) and shp[c.shipment_id].shipper_id == entity_id]
    if etype == "director":
        linked = _directorships(entity_id)
        ids = {x["entity_id"] for x in linked}
        return [c for c in _claims() if c.consignee_id in ids or c.surveyor_id in ids
                or (shp.get(c.shipment_id) and shp[c.shipment_id].forwarder_id in ids)]
    return []


def _priors_for(entity_id: str) -> List:
    etype, _ = _entity(entity_id)
    if etype == "consignee":
        return [p for p in _priors() if p.consignee_id == entity_id]
    if etype == "surveyor":
        return [p for p in _priors() if p.surveyor_id == entity_id]
    if etype == "director":
        ids = {x["entity_id"] for x in _directorships(entity_id)}
        return [p for p in _priors() if p.consignee_id in ids or p.surveyor_id in ids]
    return []


def _directorships(director_id: str) -> List[Dict]:
    out = []
    for etype, key, attr in (("consignee", "consignees", "party_id"), ("surveyor", "surveyors", "surveyor_id"),
                             ("forwarder", "forwarders", "forwarder_id")):
        for e in _data(key):
            if director_id in (getattr(e, "director_ids", None) or []):
                out.append({"entity_id": getattr(e, attr), "entity_type": etype, "name": e.name,
                            "registered_address": getattr(e, "registered_address", "")})
    return out


def _address_peers(entity_id: str, address: str) -> List[Dict]:
    if not address:
        return []
    out = []
    for etype, key, attr in (("consignee", "consignees", "party_id"), ("surveyor", "surveyors", "surveyor_id"),
                             ("forwarder", "forwarders", "forwarder_id")):
        for e in _data(key):
            eid = getattr(e, attr)
            if eid != entity_id and getattr(e, "registered_address", None) == address:
                out.append({"entity_id": eid, "entity_type": etype, "name": e.name})
    return out


def _brief_claim(c) -> Dict:
    return {"claim_id": c.claim_id, "type": c.claim_type, "amount": float(c.claim_amount),
            "date_filed": c.date_filed, "risk_score": _risk(c.claim_id),
            "consignee": _name(c.consignee_id)}


def _brief_prior(p) -> Dict:
    return {"claim_id": p.claim_id, "type": p.claim_type, "amount_paid": float(p.amount_paid),
            "date_paid": p.date_paid, "consignee": _name(p.consignee_id), "status": "closed/paid"}


# ---------------------------------------------------------------------------
# 1. scan_suspicious_entities
# ---------------------------------------------------------------------------
@tool
@_safe
def scan_suspicious_entities(
    min_risk_score: Annotated[int, "Minimum risk score (0-100), default 40"] = 40,
) -> List[Dict]:
    """
    Scan the claims queue for high-risk marine cargo claims and the entities linked to them.

    Returns one entry per claim, sorted by risk score: claimant (consignee) ID and name,
    risk score/tier, claim type and amount, linked surveyor / forwarder / shipper IDs,
    entity alerts (watchlist, not on panel, flagged claimant) and top risk factors.
    """
    _tool_log('scan_suspicious_entities', f'Scanning claims queue (risk >= {min_risk_score})...')
    t0 = time.time()
    shp = _shipments()
    results = []
    for case in _context.case_queue:
        risk = _context.claim_risk_scores.get(case.case_id)
        if not risk or risk.total_score < min_risk_score:
            continue
        claim = _context.get_claim(case.case_id)
        if not claim:
            continue
        s = shp.get(claim.shipment_id)
        svy = _context.get_surveyor(claim.surveyor_id) if claim.surveyor_id else None
        fwd = _context.get_forwarder(s.forwarder_id) if s else None
        cne = _context.get_consignee(claim.consignee_id)
        alerts = []
        if cne and cne.flagged:
            alerts.append("claimant flagged")
        if svy and svy.on_watchlist:
            alerts.append(f"surveyor {svy.surveyor_id} on watchlist")
        if svy and not svy.insurer_panel:
            alerts.append(f"surveyor {svy.surveyor_id} not on insurer panel")
        if fwd and fwd.on_watchlist:
            alerts.append(f"forwarder {fwd.forwarder_id} on watchlist")
        results.append({
            'entity_id': claim.consignee_id,
            'entity_type': 'consignee',
            'entity_name': case.subject_name,
            'risk_score': risk.total_score,
            'risk_tier': risk.tier,
            'claim_id': claim.claim_id,
            'claim_type': claim.claim_type,
            'claim_amount': float(claim.claim_amount),
            'shipment': s.description if s else None,
            'surveyor_id': claim.surveyor_id,
            'forwarder_id': s.forwarder_id if s else None,
            'shipper_id': s.shipper_id if s else None,
            'entity_alerts': alerts,
            'top_factors': risk.top_factors[:4],
        })

    results.sort(key=lambda r: r['risk_score'], reverse=True)
    _tool_log('scan_suspicious_entities', f'Found {len(results)} claims in {time.time()-t0:.1f}s')
    return _truncate_tool_output(results[:8], 'scan_suspicious_entities')


# ---------------------------------------------------------------------------
# 2. profile_entity
# ---------------------------------------------------------------------------
@tool
@_safe
def profile_entity(
    entity_id: Annotated[str, "Entity ID to profile (e.g. CNE-012, SVY-004, FWD-002, SHR-008, DIR-001)"],
) -> Dict:
    """
    Build a detailed profile for a consignee (claimant), surveyor, forwarder, shipper or director.

    Returns registration details, directors and registered address, open and prior claims,
    and risk indicators (watchlist, panel status, claim rate, shared directors/addresses).
    """
    _tool_log('profile_entity', f'Profiling {entity_id}...')
    etype, e = _entity(entity_id)
    if not e:
        claim = _context.get_claim(entity_id)
        if claim:
            return {"error": f"{entity_id} is a claim ID — profile its claimant {claim.consignee_id} "
                             f"or surveyor {claim.surveyor_id} instead"}
        return {"error": f"Entity {entity_id} not found"}

    profile: Dict = {"entity_id": entity_id, "entity_type": etype}
    indicators = []
    if etype == "director":
        links = _directorships(entity_id)
        profile.update({"name": e.full_name, "nationality": e.nationality, "directorships": links})
        types = {x["entity_type"] for x in links}
        if len(types) >= 2:
            indicators.append(f"Director of {len(links)} entities across roles {sorted(types)} — "
                              "claimant and service providers under common control")
        claims = _claims_for(entity_id)
        priors = _priors_for(entity_id)
        profile["linked_open_claims"] = [_brief_claim(c) for c in claims[:6]]
        profile["linked_prior_claims"] = [_brief_prior(p) for p in priors[:6]]
        profile["linked_total_claimed"] = round(sum(c.claim_amount for c in claims) + sum(p.amount_paid for p in priors), 2)
        profile["risk_indicators"] = indicators
        return _truncate_tool_output(profile, 'profile_entity')

    profile["name"] = e.name
    profile["city"] = getattr(e, "city", None)
    if hasattr(e, "registered_address"):
        profile["registered_address"] = e.registered_address
        peers = _address_peers(entity_id, e.registered_address)
        if peers:
            profile["shares_address_with"] = peers
            indicators.append("Shares registered address with " + ", ".join(p["name"] for p in peers))
    if getattr(e, "director_ids", None):
        profile["directors"] = [f"{_name(d)} ({d})" for d in e.director_ids]
        for d in e.director_ids:
            others = [x for x in _directorships(d) if x["entity_id"] != entity_id]
            if others:
                indicators.append(f"Director {_name(d)} also directs " + ", ".join(o["name"] for o in others))
    if getattr(e, "notes", None):
        profile["notes"] = e.notes

    claims = _claims_for(entity_id)
    priors = _priors_for(entity_id)
    profile["open_claims"] = [_brief_claim(c) for c in claims[:6]]
    profile["open_claim_count"] = len(claims)
    profile["prior_paid_claims"] = [_brief_prior(p) for p in priors[:6]]
    profile["prior_paid_total"] = round(sum(p.amount_paid for p in priors), 2)
    profile["total_claimed_open"] = round(sum(c.claim_amount for c in claims), 2)

    if etype == "consignee":
        n = e.claim_history_count + len(claims)
        rate = n / max(1, e.shipments_per_year * 2)
        profile.update({"country": e.country, "incorporated": e.incorporated,
                        "shipments_per_year": e.shipments_per_year, "claims_24m": n,
                        "claim_rate_24m": round(rate, 4), "flagged": e.flagged})
        if e.flagged:
            indicators.append("Claimant flagged for enhanced review")
        if n >= 3 and rate >= 0.05:
            indicators.append(f"{n} claims on ~{e.shipments_per_year * 2} shipments in 24 months ({rate:.1%})")
    elif etype == "surveyor":
        surveys = [s for s in _data("surveys") if s.surveyor_id == entity_id]
        assured = sum(1 for s in surveys if s.appointed_by == "assured")
        profile.update({"insurer_panel": e.insurer_panel, "on_watchlist": e.on_watchlist,
                        "surveys_on_file": len(surveys), "assured_appointed": assured,
                        "distinct_consignees": len({c.consignee_id for c in claims} | {p.consignee_id for p in priors})})
        if e.on_watchlist:
            indicators.append("Surveyor on watchlist")
        if not e.insurer_panel:
            indicators.append("Not on insurer's approved panel")
    elif etype == "forwarder":
        shipments = [s for s in _data("shipments") if s.forwarder_id == entity_id]
        profile.update({"on_watchlist": e.on_watchlist, "shipments_booked": len(shipments),
                        "consignees_served": sorted({_name(s.consignee_id) for s in shipments})[:8]})
        if e.on_watchlist:
            indicators.append("Forwarder on watchlist")
    elif etype == "shipper":
        shipments = [s for s in _data("shipments") if s.shipper_id == entity_id]
        profile.update({"country": e.country, "incorporated": e.incorporated,
                        "shipments": len(shipments),
                        "consignees_served": sorted({_name(s.consignee_id) for s in shipments})[:8]})
    profile["risk_indicators"] = indicators
    return _truncate_tool_output(profile, 'profile_entity')


# ---------------------------------------------------------------------------
# 3. compare_to_peers
# ---------------------------------------------------------------------------
def _metric_value(entity_id: str, etype: str, metric: str) -> float:
    claims = _claims_for(entity_id)
    priors = _priors_for(entity_id)
    amounts = [c.claim_amount for c in claims] + [p.amount_paid for p in priors]
    if metric == "claim_count":
        return float(len(amounts))
    if metric == "avg_claim_amount":
        return float(sum(amounts) / len(amounts)) if amounts else 0.0
    if metric == "claim_rate" and etype == "consignee":
        _, e = _entity(entity_id)
        return (e.claim_history_count + len(claims)) / max(1, e.shipments_per_year * 2)
    if metric == "assured_appointed_rate" and etype == "surveyor":
        surveys = [s for s in _data("surveys") if s.surveyor_id == entity_id]
        return (sum(1 for s in surveys if s.appointed_by == "assured") / len(surveys)) if surveys else 0.0
    return float(sum(amounts))       # claim_amount (open claimed + prior paid)


@tool
@_safe
def compare_to_peers(
    entity_id: Annotated[str, "Entity ID to compare (consignee, surveyor, forwarder or shipper)"],
    metric: Annotated[str, "Metric: claim_amount | claim_count | avg_claim_amount | claim_rate (consignees) | assured_appointed_rate (surveyors)"] = "claim_amount",
) -> Dict:
    """
    Compare an entity's metric to its peer group (consignees vs consignees, surveyors vs surveyors, etc.).

    claim_amount and claim_count include open claims and prior paid claims. claim_rate normalises
    a consignee's claims by its shipment volume. Returns entity_value, peer_avg, peer_std, z_score,
    rank and peer_count.
    """
    _tool_log('compare_to_peers', f'Comparing {entity_id} on "{metric}"...')
    etype, e = _entity(entity_id)
    if not e or etype == "director":
        return {"error": f"Entity {entity_id} not found or not comparable (use CNE-, SVY-, FWD- or SHR- IDs)"}
    key, attr = {"consignee": ("consignees", "party_id"), "surveyor": ("surveyors", "surveyor_id"),
                 "forwarder": ("forwarders", "forwarder_id"), "shipper": ("shippers", "shipper_id")}[etype]
    peers = [getattr(p, attr) for p in _data(key)]
    values = {pid: _metric_value(pid, etype, metric) for pid in peers}
    if len(values) < 2:
        return {"error": "Not enough peers for comparison"}

    entity_value = values[entity_id]
    peer_values = [v for pid, v in values.items() if pid != entity_id]
    peer_avg = statistics.mean(peer_values)
    peer_std = statistics.stdev(peer_values) if len(peer_values) > 1 else 0.0
    z_score = (entity_value - peer_avg) / peer_std if peer_std else 0.0
    rank = 1 + sum(1 for v in values.values() if v > entity_value)

    return _truncate_tool_output({
        'entity_id': entity_id,
        'entity_name': e.name,
        'entity_type': etype,
        'metric': metric,
        'entity_value': round(float(entity_value), 4 if metric.endswith("rate") else 2),
        'peer_avg': round(float(peer_avg), 4 if metric.endswith("rate") else 2),
        'peer_std': round(float(peer_std), 4 if metric.endswith("rate") else 2),
        'z_score': round(float(z_score), 2),
        'rank': f"{rank} of {len(values)}",
        'peer_count': len(peer_values),
    }, 'compare_to_peers')


# ---------------------------------------------------------------------------
# 4. get_claim_details
# ---------------------------------------------------------------------------
@tool
@_safe
def get_claim_details(
    entity_id: Annotated[str, "Claim ID (MC-xxxx) or entity ID (CNE-, SVY-, FWD-, SHR-, DIR-) to get claims for"],
    limit: Annotated[int, "Maximum number of claims to return, default 10"] = 10,
) -> List[Dict]:
    """
    Get detailed marine claim records for a single claim or for all claims linked to an entity.

    Returns amounts, dates, shipment (B/L, weights, seals, EIR), survey details, risk score,
    triggered rules and failed document checks.
    """
    _tool_log('get_claim_details', f'Fetching claims for {entity_id} (limit {limit})...')
    single = _context.get_claim(entity_id)
    claims_list = [single] if single else _claims_for(entity_id)
    claims_list = claims_list[:max(1, int(limit or 10))]
    shp = _shipments()

    results = []
    for c in claims_list:
        risk = _context.claim_risk_scores.get(c.claim_id)
        triggered = [r for r in _context.claim_rules.get(c.claim_id, []) if r.triggered]
        doc_checks = _context.claim_doc_results.get(c.claim_id, []) or []
        s = shp.get(c.shipment_id)
        svr = _context.get_survey(c.survey_id) if c.survey_id else None
        pol = _context.get_policy(c.policy_id)
        entry = {
            'claim_id': c.claim_id,
            'claim_type': c.claim_type,
            'consignee_id': c.consignee_id,
            'consignee': _name(c.consignee_id),
            'surveyor_id': c.surveyor_id,
            'certificate_no': c.policy_id,
            'clause': pol.clause if pol else None,
            'insured_value': pol.insured_value if pol else None,
            'claim_amount': float(c.claim_amount),
            'date_filed': c.date_filed,
            'date_loss_discovered': c.date_of_loss,
            'notice_to_carrier': c.notice_to_carrier_date,
            'status': c.status,
            'fraud_scenario': c.fraud_scenario,
            'false_positive_scenario': c.false_positive_scenario,
        }
        if s:
            entry['shipment'] = {
                'bl_number': s.bl_number, 'carrier': s.carrier, 'forwarder_id': s.forwarder_id,
                'shipper_id': s.shipper_id, 'commodity': s.commodity, 'quantity': s.quantity,
                'unit': s.unit, 'unit_price': s.unit_price, 'invoice_value': s.invoice_value,
                'bl_weight_kg': s.gross_weight_bl_kg, 'vgm_cargo_kg': s.vgm_cargo_kg,
                'seals_match': s.seals_match, 'eir': s.eir_remarks_discharge,
                'discharge_date': s.discharge_date,
            }
        if svr:
            entry['survey'] = {'report_no': svr.report_no, 'appointed_by': svr.appointed_by,
                               'survey_date': svr.survey_date, 'joint_with_carrier': svr.joint_with_carrier,
                               'cause_of_loss': svr.cause_of_loss, 'damage_pct': svr.damage_pct}
        if risk:
            entry['risk_score'] = risk.total_score
            entry['risk_tier'] = risk.tier
        if triggered:
            entry['triggered_rules'] = [
                {'rule_id': r.rule_id, 'severity': r.severity, 'explanation': r.explanation}
                for r in triggered[:6]
            ]
        failed = [d for d in doc_checks if not getattr(d, "passed", True)]
        if failed:
            entry['failed_doc_checks'] = [
                {'check_id': d.check_id, 'severity': d.severity, 'explanation': d.explanation}
                for d in failed[:5]
            ]
        results.append(entry)

    if not results:
        priors = _priors_for(entity_id)
        if priors:
            results = [_brief_prior(p) for p in priors[:limit]]
        else:
            return [{"note": f"No claims found for {entity_id}"}]

    _tool_log('get_claim_details', f'Returned {len(results)} claims')
    return _truncate_tool_output(results, 'get_claim_details')


# ---------------------------------------------------------------------------
# 5. find_connections
# ---------------------------------------------------------------------------
@tool
@_safe
def find_connections(
    entity_id: Annotated[str, "Entity ID to find connections for (CNE-, SVY-, FWD-, SHR-, DIR-)"],
    depth: Annotated[int, "Depth of network traversal (1-3), default 2"] = 2,
) -> Dict:
    """
    Traverse the entity network to find everything connected within N hops:
    shipper → consignee (SHIPPED_TO), consignee → forwarder (BOOKED_VIA),
    consignee → surveyor (SURVEYED_BY, incl. prior paid claims), director → entity (DIRECTOR_OF),
    plus entities sharing the same registered address.
    """
    _tool_log('find_connections', f'Traversing graph from {entity_id} (depth={depth})...')
    G = _context.supplemental_graph
    if entity_id not in G:
        return {"error": f"Entity {entity_id} not in graph"}
    depth = max(1, min(3, int(depth or 2)))

    visited = {entity_id: (0, None, None)}   # node -> (distance, parent, relationship)
    queue = [entity_id]
    while queue:
        node = queue.pop(0)
        dist = visited[node][0]
        if dist >= depth:
            continue
        for nbr in list(G.successors(node)) + list(G.predecessors(node)):
            if nbr in visited:
                continue
            edge = G.get_edge_data(node, nbr) or G.get_edge_data(nbr, node) or {}
            visited[nbr] = (dist + 1, node, edge.get('relationship', 'connected'))
            queue.append(nbr)

    connected, rel_summary = [], {}
    for node, (dist, parent, rel) in visited.items():
        if node == entity_id:
            continue
        attrs = G.nodes.get(node, {})
        rel_summary[rel] = rel_summary.get(rel, 0) + 1
        connected.append({'entity_id': node, 'entity_type': attrs.get('entity_type', 'unknown'),
                          'name': attrs.get('name', ''), 'distance': dist,
                          'relationship': rel, 'via': parent})

    # Shared registered address is not a graph edge — add it explicitly.
    _, e = _entity(entity_id)
    shared_address = _address_peers(entity_id, getattr(e, "registered_address", "")) if e else []
    if shared_address:
        rel_summary['SHARED_ADDRESS'] = len(shared_address)

    # Shared directors (entities under common control)
    shared_directors = []
    for did in (getattr(e, "director_ids", None) or []) if e else []:
        others = [x for x in _directorships(did) if x["entity_id"] != entity_id]
        if others:
            shared_directors.append({"director": f"{_name(did)} ({did})",
                                     "also_directs": [f"{o['name']} ({o['entity_id']}, {o['entity_type']})" for o in others]})

    connected.sort(key=lambda x: (x['distance'], x['entity_type']))
    sub = G.subgraph(list(visited.keys()))
    n = sub.number_of_nodes()
    density = sub.number_of_edges() / max(n, 1)

    return _truncate_tool_output({
        'entity_id': entity_id,
        'entity_name': _name(entity_id),
        'total_entities': len(connected),
        'connection_density': round(density, 2),
        'relationship_summary': rel_summary,
        'shared_directors': shared_directors,
        'shared_registered_address': shared_address,
        'connected_entities': connected[:15],
    }, 'find_connections')


# ---------------------------------------------------------------------------
# 6. find_ring
# ---------------------------------------------------------------------------
@tool
@_safe
def find_ring(
    min_risk_score: Annotated[int, "Minimum risk score for open member claims, default 40"] = 40,
) -> List[Dict]:
    """
    Find cross-claim marine fraud patterns. Uses pre-computed detected_patterns when present;
    otherwise derives them on the fly:
      - shared-director networks linking a claimant with its surveyor and/or forwarder
      - shared registered-address clusters
      - surveyor concentration: non-panel or watchlisted surveyors on repeated paid claims
    """
    _tool_log('find_ring', f'Detecting rings (risk >= {min_risk_score})...')
    results = []
    for p in (_context.detected_patterns or []):
        results.append({'pattern_type': p.pattern_type, 'description': p.description,
                        'severity': p.severity, 'entity_count': len(p.entities),
                        'entities': p.entities[:10], 'details': p.details})
    if results:
        return _truncate_tool_output(results, 'find_ring')

    shp = _shipments()

    def claims_touching(ids: set):
        open_c = [c for c in _claims() if c.consignee_id in ids or c.surveyor_id in ids
                  or (shp.get(c.shipment_id) and shp[c.shipment_id].forwarder_id in ids)]
        prior_c = [p for p in _priors() if p.consignee_id in ids or p.surveyor_id in ids]
        return open_c, prior_c

    # 1. Shared-director networks
    for d in _data("directors"):
        links = _directorships(d.director_id)
        types = {x["entity_type"] for x in links}
        if len(links) < 2:
            continue
        ids = {x["entity_id"] for x in links}
        open_c, prior_c = claims_touching(ids)
        hot = [c for c in open_c if _risk(c.claim_id) >= min_risk_score]
        if not hot and not prior_c:
            continue
        results.append({
            'pattern_type': 'shared_director_network',
            'description': f"Director {d.full_name} ({d.director_id}) controls "
                           + ", ".join(f"{x['name']} ({x['entity_type']})" for x in links),
            'severity': 'CRITICAL' if {"consignee", "surveyor"} <= types else 'HIGH',
            'entity_count': len(links) + 1,
            'entities': [d.director_id] + sorted(ids),
            'details': {'open_claims': [c.claim_id for c in open_c],
                        'high_risk_open_claims': [c.claim_id for c in hot],
                        'prior_paid_claims': [p.claim_id for p in prior_c],
                        'total_exposure': round(sum(c.claim_amount for c in open_c)
                                                + sum(p.amount_paid for p in prior_c), 2)},
        })

    # 2. Shared registered-address clusters
    by_addr: Dict[str, list] = {}
    for key, attr, etype in (("consignees", "party_id", "consignee"), ("surveyors", "surveyor_id", "surveyor"),
                             ("forwarders", "forwarder_id", "forwarder")):
        for e in _data(key):
            if getattr(e, "registered_address", ""):
                by_addr.setdefault(e.registered_address, []).append((getattr(e, attr), etype, e.name))
    for addr, members in by_addr.items():
        if len(members) < 2:
            continue
        results.append({
            'pattern_type': 'shared_address_cluster',
            'description': f"{len(members)} entities registered at {addr}: "
                           + ", ".join(f"{m[2]} ({m[1]})" for m in members),
            'severity': 'HIGH',
            'entity_count': len(members),
            'entities': [m[0] for m in members],
            'details': {'address': addr},
        })

    # 3. Surveyor concentration
    for s in _data("surveyors"):
        if s.insurer_panel and not s.on_watchlist:
            continue
        open_c = [c for c in _claims() if c.surveyor_id == s.surveyor_id]
        prior_c = [p for p in _priors() if p.surveyor_id == s.surveyor_id]
        if len(open_c) + len(prior_c) < 3:
            continue
        cnes = {c.consignee_id for c in open_c} | {p.consignee_id for p in prior_c}
        results.append({
            'pattern_type': 'surveyor_concentration',
            'description': f"{'Watchlisted' if s.on_watchlist else 'Non-panel'} surveyor '{s.name}' on "
                           f"{len(open_c) + len(prior_c)} claims across {len(cnes)} consignee(s)",
            'severity': 'CRITICAL' if s.on_watchlist else 'HIGH',
            'entity_count': 1 + len(cnes),
            'entities': [s.surveyor_id] + sorted(cnes),
            'details': {'open_claims': [c.claim_id for c in open_c],
                        'prior_paid_claims': [p.claim_id for p in prior_c],
                        'prior_paid_total': round(sum(p.amount_paid for p in prior_c), 2)},
        })

    order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    results.sort(key=lambda r: order.get(r['severity'], 9))
    _tool_log('find_ring', f'Found {len(results)} patterns')
    return _truncate_tool_output(results, 'find_ring')


# ---------------------------------------------------------------------------
# 7. get_surveyor_history  (surveyor claim timeline)
# ---------------------------------------------------------------------------
@tool
@_safe
def get_surveyor_history(
    surveyor_id: Annotated[str, "Surveyor ID to analyse, e.g. SVY-004"],
    months: Annotated[int, "Number of months of history, default 24"] = 24,
) -> Dict:
    """
    Get the monthly claim timeline for a surveyor (open claims by filing date and prior paid claims
    by payment date): total claims, unique consignees, top consignee and its share, average amount,
    and how many surveys were appointed by the assured. Useful for spotting a surveyor
    concentrated on a few claimants.
    """
    _tool_log('get_surveyor_history', f'Pulling {months}-month history for {surveyor_id}...')
    svy = _context.get_surveyor(surveyor_id)
    if not svy:
        return {"error": f"Surveyor {surveyor_id} not found"}
    surveys = {s.claim_id: s for s in _data("surveys") if s.surveyor_id == surveyor_id}
    events = []
    for c in _claims():
        if c.surveyor_id == surveyor_id:
            svr = surveys.get(c.claim_id)
            events.append((c.date_filed, c.consignee_id, float(c.claim_amount),
                           bool(svr and svr.appointed_by == "assured"), c.claim_id))
    for p in _priors():
        if p.surveyor_id == surveyor_id:
            events.append((p.date_paid, p.consignee_id, float(p.amount_paid), None, p.claim_id))

    monthly: Dict[str, list] = {}
    for ev in events:
        try:
            key = datetime.strptime(ev[0], '%Y-%m-%d').strftime('%Y-%m')
        except (TypeError, ValueError):
            continue
        monthly.setdefault(key, []).append(ev)

    history = []
    for month_key in sorted(monthly.keys())[-max(1, int(months or 24)):]:
        mc = monthly[month_key]
        counts: Dict[str, int] = {}
        for ev in mc:
            counts[ev[1]] = counts.get(ev[1], 0) + 1
        top = max(counts, key=counts.get)
        history.append({
            'month': month_key,
            'total_claims': len(mc),
            'claims': [ev[4] for ev in mc],
            'unique_consignees': len(counts),
            'top_consignee': _name(top),
            'top_consignee_pct': round(counts[top] / len(mc) * 100, 1),
            'avg_claim_amount': round(sum(ev[2] for ev in mc) / len(mc), 2),
        })

    cne_counts: Dict[str, int] = {}
    for ev in events:
        cne_counts[ev[1]] = cne_counts.get(ev[1], 0) + 1
    top_all = max(cne_counts, key=cne_counts.get) if cne_counts else None
    _tool_log('get_surveyor_history', f'Returned {len(history)} months of data')
    return _truncate_tool_output({
        'surveyor_id': surveyor_id,
        'surveyor_name': svy.name,
        'insurer_panel': svy.insurer_panel,
        'on_watchlist': svy.on_watchlist,
        'total_claims': len(events),
        'unique_consignees': len(cne_counts),
        'top_consignee': _name(top_all) if top_all else None,
        'top_consignee_share_pct': round(cne_counts[top_all] / len(events) * 100, 1) if top_all else 0,
        'assured_appointed_open_claims': sum(1 for ev in events if ev[3]),
        'total_amount': round(sum(ev[2] for ev in events), 2),
        'monthly': history,
    }, 'get_surveyor_history')


# ---------------------------------------------------------------------------
INVESTIGATION_TOOLS = [
    scan_suspicious_entities,
    profile_entity,
    compare_to_peers,
    get_claim_details,
    find_connections,
    find_ring,
    get_surveyor_history,
]
