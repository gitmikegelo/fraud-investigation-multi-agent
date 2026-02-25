"""
Investigation Agent Tools - 7 tools for fraud detection
These tools access the DataContext to perform analysis.
"""

import time
import json
from typing import List, Dict, Optional, Annotated
from datetime import datetime, timedelta
import pandas as pd

# Max output size to prevent context overflow
MAX_TOOL_OUTPUT_CHARS = 2000


def _tool_log(name: str, msg: str):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"    [{ts}]   tool:{name} -> {msg}", flush=True)


def _truncate_tool_output(output, tool_name: str):
    """Truncate tool output if it's too large."""
    if output is None:
        return output
    
    output_str = json.dumps(output) if isinstance(output, (list, dict)) else str(output)
    original_len = len(output_str)
    
    if original_len > MAX_TOOL_OUTPUT_CHARS:
        _tool_log(tool_name, f'!!! OUTPUT TRUNCATED from {original_len} to {MAX_TOOL_OUTPUT_CHARS} chars')
        
        # If it's a list, truncate the list items
        if isinstance(output, list) and len(output) > 3:
            # Keep only first 3 items
            truncated = output[:3]
            truncated.append({"note": f"... {len(output) - 3} more items truncated for brevity ..."})
            return truncated
        
        # Otherwise, just truncate as string
        if isinstance(output, dict):
            # Keep structure but truncate long values
            truncated = {}
            for k, v in output.items():
                v_str = str(v)
                if len(v_str) > 300:
                    truncated[k] = v_str[:300] + "...(truncated)"
                else:
                    truncated[k] = v
            return truncated
    
    return output


# Global context - will be set by the agent runner
_context = None

def set_context(ctx):
    """Set the global DataContext for tools to use."""
    global _context
    _context = ctx


def scan_new_claims(
    since_days: Annotated[int, "Number of days to look back, default 90"] = 90
) -> List[Dict]:
    """
    Scan for entities with high anomaly scores in recent claims.
    
    Returns list of entities with anomaly_score > 0.5, sorted by score descending.
    Each entity includes: entity_id, entity_type, anomaly_score, total_billed
    
    If no results are found within the requested window, automatically widens
    the search window up to 365 days.
    """
    _tool_log('scan_new_claims', f'Scanning claims (last {since_days} days, anomaly > 0.5)...')
    t0 = time.time()
    if _context is None:
        return [{"error": "DataContext not initialized"}]
    
    # Filter for high anomaly scores
    high_anomaly = _context.anomaly_scores_df[
        _context.anomaly_scores_df['anomaly_score'] > 0.5
    ].sort_values('anomaly_score', ascending=False)
    
    # Filter by recent claims, with auto-widening if no results
    widen_steps = [since_days, 180, 365]
    filtered_anomaly = pd.DataFrame()
    used_window = since_days
    
    for window in widen_steps:
        if window < since_days:
            continue
        cutoff_date = datetime.now() - timedelta(days=window)
        recent_entity_ids = _context.claims_df[
            _context.claims_df['service_date'] >= cutoff_date
        ]['provider_id'].unique()
        
        filtered_anomaly = high_anomaly[
            high_anomaly['entity_id'].isin(recent_entity_ids)
        ]
        used_window = window
        
        if len(filtered_anomaly) > 0:
            break
    
    if used_window != since_days and len(filtered_anomaly) > 0:
        _tool_log('scan_new_claims', f'No results in {since_days}-day window, auto-widened to {used_window} days')
    
    results = []
    for _, row in filtered_anomaly.head(10).iterrows():  # Limit to 10 to save context
        results.append({
            'entity_id': row['entity_id'],
            'entity_type': row['entity_type'],
            'anomaly_score': round(float(row['anomaly_score']), 2),
            'total_billed': round(float(row['total_billed']), 2)
        })
    
    _tool_log('scan_new_claims', f'Found {len(results)} high-anomaly entities ({time.time()-t0:.1f}s)')
    return _truncate_tool_output(results, 'scan_new_claims')


def profile_entity(
    entity_id: Annotated[str, "Entity ID to profile (e.g., P-6610)"]
) -> Dict:
    """
    Get detailed profile for a provider or member.
    
    Returns:
    - Basic info (specialty, region)
    - Features (claims_per_month, top_cpt_concentration, etc.)
    - Anomaly score and top contributing features
    """
    _tool_log('profile_entity', f'Profiling {entity_id}...')
    if _context is None:
        return {"error": "DataContext not initialized"}
    
    # Try provider first
    profile = _context.get_provider_profile(entity_id)
    
    if profile is None:
        # Try member
        member_info = _context.members_df[_context.members_df['member_id'] == entity_id]
        if len(member_info) == 0:
            return {"error": f"Entity {entity_id} not found"}
        
        member_info = member_info.iloc[0].to_dict()
        
        # Get member features
        features = _context.member_features_df[
            _context.member_features_df['member_id'] == entity_id
        ]
        if len(features) > 0:
            member_info.update(features.iloc[0].to_dict())
        
        # Get anomaly score
        anomaly = _context.anomaly_scores_df[
            _context.anomaly_scores_df['entity_id'] == entity_id
        ]
        if len(anomaly) > 0:
            member_info['anomaly_score'] = float(anomaly.iloc[0]['anomaly_score'])
            member_info['top_features'] = anomaly.iloc[0]['top_features']
        
        profile = member_info
    
    # Convert numpy types to native Python for JSON serialization
    clean_profile = {}
    for k, v in profile.items():
        if isinstance(v, (pd.Series, pd.DataFrame)):
            continue
        if isinstance(v, (int, float, str, bool, type(None))):
            clean_profile[k] = v
        elif isinstance(v, list):
            clean_profile[k] = v
        else:
            try:
                clean_profile[k] = float(v)
            except:
                clean_profile[k] = str(v)
    
    return _truncate_tool_output(clean_profile, 'profile_entity')


def compare_to_peers(
    entity_id: Annotated[str, "Entity ID to compare"],
    metric: Annotated[str, "Metric to compare (e.g., 'top_cpt_concentration')"]
) -> Dict:
    """
    Compare an entity's metric to their peer group average.
    
    Returns:
    - entity_value: The entity's value for this metric
    - peer_avg: Peer group average
    - z_score: Standard deviations from mean
    - peer_count: Number of peers in comparison group
    """
    _tool_log('compare_to_peers', f'Comparing {entity_id} on "{metric}"...')
    if _context is None:
        return {"error": "DataContext not initialized"}
    
    # Get provider info
    provider = _context.provider_features_df[
        _context.provider_features_df['provider_id'] == entity_id
    ]
    
    if len(provider) == 0:
        return {"error": f"Provider {entity_id} not found"}
    
    provider = provider.iloc[0]
    peer_group = provider['peer_group']
    entity_value = provider.get(metric, None)
    
    if entity_value is None:
        return {"error": f"Metric {metric} not found"}
    
    # Get peer stats
    peer_stats = _context.peer_stats_df[
        _context.peer_stats_df['peer_group'] == peer_group
    ]
    
    if len(peer_stats) == 0:
        return {"error": f"No peer stats found for {peer_group}"}
    
    peer_stats = peer_stats.iloc[0]
    mean_col = f'{metric}_mean'
    std_col = f'{metric}_std'
    
    peer_avg = peer_stats.get(mean_col, 0)
    peer_std = peer_stats.get(std_col, 1)
    
    if peer_std == 0:
        peer_std = 1
    
    z_score = (entity_value - peer_avg) / peer_std
    
    # Count peers
    peer_count = len(_context.provider_features_df[
        _context.provider_features_df['peer_group'] == peer_group
    ])
    
    return _truncate_tool_output({
        'entity_id': entity_id,
        'metric': metric,
        'entity_value': round(float(entity_value), 4),
        'peer_avg': round(float(peer_avg), 4),
        'peer_std': round(float(peer_std), 4),
        'z_score': round(float(z_score), 2),
        'peer_count': int(peer_count),
        'peer_group': peer_group
    }, 'compare_to_peers')


def get_claim_details(
    entity_id: Annotated[str, "Entity ID to get claims for"],
    limit: Annotated[int, "Maximum number of claims to return, default 10"] = 10
) -> List[Dict]:
    """
    Get raw claim records for an entity.
    
    Returns list of claims with CPT, ICD, amounts, dates, etc.
    """
    _tool_log('get_claim_details', f'Fetching up to {limit} claims for {entity_id}...')
    if _context is None:
        return [{"error": "DataContext not initialized"}]
    
    claims = _context.claims_df[
        (_context.claims_df['provider_id'] == entity_id) |
        (_context.claims_df['member_id'] == entity_id)
    ].head(limit)
    
    results = []
    for _, claim in claims.iterrows():
        results.append({
            'claim_id': claim['claim_id'],
            'member_id': claim['member_id'],
            'provider_id': claim['provider_id'],
            'referring_provider_id': claim.get('referring_provider_id'),
            'facility_id': claim['facility_id'],
            'cpt_code': claim['cpt_code'],
            'icd_code': claim['icd_code'],
            'billed_amount': round(float(claim['billed_amount']), 2),
            'paid_amount': round(float(claim['paid_amount']), 2),
            'service_date': str(claim['service_date'].date()),
            'place_of_service': claim['place_of_service'],
            'claim_type': claim['claim_type']
        })
    
    return _truncate_tool_output(results, 'get_claim_details')


def find_connections(
    entity_id: Annotated[str, "Entity ID to find connections for"],
    depth: Annotated[int, "Depth of network traversal (1-3), default 2"] = 2
) -> Dict:
    """
    Find all entities connected to a given entity within N hops using network analysis.
    
    Returns:
    - connected_entities: List of connected entities with distance and anomaly score
    - connection_density: Ratio of edges to nodes in subgraph
    - total_entities: Count of connected entities
    """
    _tool_log('find_connections', f'Traversing graph from {entity_id} (depth={depth})...')
    if _context is None:
        return {"error": "DataContext not initialized"}
    
    from data.graph import find_connections as graph_find_connections
    
    result = graph_find_connections(_context.graph, entity_id, depth)
    
    # Clean up for JSON serialization
    if 'connected_entities' in result:
        for entity in result['connected_entities']:
            for k, v in entity.items():
                if hasattr(v, 'item'):
                    entity[k] = v.item()
    
    return _truncate_tool_output(result, 'find_connections')


def find_ring(
    min_anomaly_score: Annotated[float, "Minimum anomaly score for ring members, default 0.5"] = 0.5,
    min_entities: Annotated[int, "Minimum number of entities in a ring, default 3"] = 3
) -> List[Dict]:
    """
    Find potential fraud rings - clusters of connected high-anomaly entities.
    
    Uses connected components analysis on the graph filtered by anomaly score.
    
    Returns list of ring candidates, each with:
    - entities: List of entities in the ring
    - avg_anomaly_score: Average anomaly across ring members
    - total_billed: Total amount billed by ring
    - connection_density: How interconnected the ring is
    """
    _tool_log('find_ring', f'Searching for fraud rings (anomaly >= {min_anomaly_score}, min entities={min_entities})...')
    if _context is None:
        return [{"error": "DataContext not initialized"}]
    
    from data.graph import find_rings
    
    rings = find_rings(
        _context.graph,
        _context.anomaly_scores_df,
        min_anomaly_score,
        min_entities
    )
    
    # Clean up for JSON
    clean_rings = []
    for ring in rings:
        clean_ring = {}
        for k, v in ring.items():
            if isinstance(v, (list, dict)):
                clean_ring[k] = v
            elif hasattr(v, 'item'):
                clean_ring[k] = v.item()
            else:
                clean_ring[k] = v
        clean_rings.append(clean_ring)
    
    return _truncate_tool_output(clean_rings, 'find_ring')


def get_referral_history(
    provider_id: Annotated[str, "Provider ID to analyze"],
    months: Annotated[int, "Number of months of history, default 12"] = 12
) -> List[Dict]:
    """
    Get monthly referral breakdown showing concentration changes over time.
    
    Returns monthly records with:
    - month: Month identifier
    - total_referrals: Number of referrals received
    - top_source: Most common referring provider
    - concentration: Percentage from top source
    - unique_sources: Count of unique referral sources
    
    Used to detect suspicious referral pattern shifts (potential kickback schemes).
    """
    _tool_log('get_referral_history', f'Pulling {months}-month referral history for {provider_id}...')
    if _context is None:
        return [{"error": "DataContext not initialized"}]
    
    from data.graph import get_referral_history as graph_get_history
    
    history = graph_get_history(_context.claims_df, provider_id, months)
    
    return _truncate_tool_output(history)


# Tool definitions for LangGraph
INVESTIGATION_TOOLS = [
    scan_new_claims,
    profile_entity,
    compare_to_peers,
    get_claim_details,
    find_connections,
    find_ring,
    get_referral_history,
]
