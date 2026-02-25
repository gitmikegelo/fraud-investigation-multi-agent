"""
NetworkX graph module for Claims Investigation Copilot.
Builds a graph of relationships between providers, members, and facilities.
"""

import pandas as pd
import networkx as nx
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict


def build_claims_graph(
    claims_df: pd.DataFrame,
    anomaly_scores_df: pd.DataFrame = None
) -> nx.DiGraph:
    """
    Build a directed graph from claims data.
    
    Nodes:
    - Providers (prefix: P-)
    - Members (prefix: M-)
    - Facilities (prefix: F-)
    
    Edges:
    - Provider -> Member (BILLED_FOR): weight = claim_count, total_amount
    - Provider -> Provider (REFERRED_TO): weight = referral_count
    - Provider -> Facility (OPERATES_AT): weight = claim_count
    
    Node attributes:
    - entity_type: provider/member/facility
    - anomaly_score: from anomaly detection (if provided)
    """
    
    G = nx.DiGraph()
    
    # Collect edge data
    provider_member_edges = defaultdict(lambda: {'claim_count': 0, 'total_amount': 0})
    provider_provider_edges = defaultdict(lambda: {'referral_count': 0})
    provider_facility_edges = defaultdict(lambda: {'claim_count': 0})
    
    # Track all entities
    providers = set()
    members = set()
    facilities = set()
    
    for _, claim in claims_df.iterrows():
        provider_id = claim['provider_id']
        member_id = claim['member_id']
        facility_id = claim['facility_id']
        referring_provider = claim.get('referring_provider_id')
        billed_amount = claim['billed_amount']
        
        providers.add(provider_id)
        members.add(member_id)
        facilities.add(facility_id)
        
        # Provider -> Member
        key = (provider_id, member_id)
        provider_member_edges[key]['claim_count'] += 1
        provider_member_edges[key]['total_amount'] += billed_amount
        
        # Provider -> Provider (referrals)
        if pd.notna(referring_provider):
            providers.add(referring_provider)
            ref_key = (referring_provider, provider_id)
            provider_provider_edges[ref_key]['referral_count'] += 1
        
        # Provider -> Facility
        fac_key = (provider_id, facility_id)
        provider_facility_edges[fac_key]['claim_count'] += 1
    
    # Add nodes
    for p in providers:
        G.add_node(p, entity_type='provider')
    
    for m in members:
        G.add_node(m, entity_type='member')
    
    for f in facilities:
        G.add_node(f, entity_type='facility')
    
    # Add anomaly scores to nodes
    if anomaly_scores_df is not None:
        for _, row in anomaly_scores_df.iterrows():
            entity_id = row['entity_id']
            if entity_id in G.nodes:
                G.nodes[entity_id]['anomaly_score'] = row['anomaly_score']
                G.nodes[entity_id]['total_billed'] = row.get('total_billed', 0)
    
    # Add edges
    for (src, dst), attrs in provider_member_edges.items():
        G.add_edge(src, dst, 
                   relationship='BILLED_FOR',
                   weight=attrs['claim_count'],
                   total_amount=round(attrs['total_amount'], 2))
    
    for (src, dst), attrs in provider_provider_edges.items():
        G.add_edge(src, dst,
                   relationship='REFERRED_TO',
                   weight=attrs['referral_count'])
    
    for (src, dst), attrs in provider_facility_edges.items():
        G.add_edge(src, dst,
                   relationship='OPERATES_AT',
                   weight=attrs['claim_count'])
    
    print(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"  Providers: {len(providers)}")
    print(f"  Members: {len(members)}")
    print(f"  Facilities: {len(facilities)}")
    
    return G


def find_connections(
    G: nx.DiGraph,
    entity_id: str,
    depth: int = 2
) -> Dict:
    """
    Find all entities connected to a given entity within N hops.
    Uses BFS traversal.
    
    Returns:
    - connected_entities: List of connected entities with their type and distance
    - connection_density: Edges / nodes ratio in subgraph
    - total_entities: Count of connected entities
    """
    
    if entity_id not in G.nodes:
        return {
            'connected_entities': [],
            'connection_density': 0,
            'total_entities': 0,
            'error': f'Entity {entity_id} not found in graph'
        }
    
    # BFS to find all connected nodes within depth
    visited = {entity_id: 0}
    queue = [(entity_id, 0)]
    
    while queue:
        current, dist = queue.pop(0)
        
        if dist < depth:
            # Get all neighbors (both in and out edges for DiGraph)
            neighbors = set(G.successors(current)) | set(G.predecessors(current))
            
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited[neighbor] = dist + 1
                    queue.append((neighbor, dist + 1))
    
    # Build result
    connected_entities = []
    for node, distance in visited.items():
        if node != entity_id:
            node_data = G.nodes[node]
            connected_entities.append({
                'entity_id': node,
                'entity_type': node_data.get('entity_type', 'unknown'),
                'anomaly_score': node_data.get('anomaly_score', 0),
                'distance': distance
            })
    
    # Calculate subgraph density
    subgraph_nodes = list(visited.keys())
    subgraph = G.subgraph(subgraph_nodes)
    n_edges = subgraph.number_of_edges()
    n_nodes = subgraph.number_of_nodes()
    
    connection_density = n_edges / n_nodes if n_nodes > 0 else 0
    
    return {
        'connected_entities': sorted(connected_entities, key=lambda x: (-x['anomaly_score'], x['distance'])),
        'connection_density': round(connection_density, 2),
        'total_entities': len(connected_entities),
        'subgraph_edges': n_edges,
        'subgraph_nodes': n_nodes
    }


def find_rings(
    G: nx.DiGraph,
    anomaly_scores_df: pd.DataFrame,
    min_anomaly_score: float = 0.5,
    min_entities: int = 3
) -> List[Dict]:
    """
    Find potential fraud rings - clusters of connected high-anomaly entities.
    
    Uses connected components on the undirected version of the graph,
    filtered by anomaly score.
    
    Returns list of ring candidates with:
    - entities: List of entities in the ring
    - avg_anomaly_score
    - total_billed
    - connection_density
    """
    
    # Get high-anomaly entities
    high_anomaly = set(
        anomaly_scores_df[anomaly_scores_df['anomaly_score'] >= min_anomaly_score]['entity_id']
    )
    
    # Create subgraph with only high-anomaly nodes
    high_anomaly_in_graph = high_anomaly & set(G.nodes)
    subgraph = G.subgraph(high_anomaly_in_graph)
    
    # Find connected components (need undirected for this)
    undirected = subgraph.to_undirected()
    components = list(nx.connected_components(undirected))
    
    rings = []
    
    for component in components:
        if len(component) < min_entities:
            continue
        
        # Get entity details
        entities = []
        total_billed = 0
        total_anomaly = 0
        
        for entity_id in component:
            node_data = G.nodes[entity_id]
            anomaly_score = node_data.get('anomaly_score', 0)
            billed = node_data.get('total_billed', 0)
            
            entities.append({
                'entity_id': entity_id,
                'entity_type': node_data.get('entity_type', 'unknown'),
                'anomaly_score': anomaly_score
            })
            
            total_billed += billed
            total_anomaly += anomaly_score
        
        # Calculate density
        ring_subgraph = G.subgraph(component)
        n_edges = ring_subgraph.number_of_edges()
        n_nodes = ring_subgraph.number_of_nodes()
        density = n_edges / n_nodes if n_nodes > 0 else 0
        
        rings.append({
            'entities': sorted(entities, key=lambda x: -x['anomaly_score']),
            'entity_count': len(entities),
            'avg_anomaly_score': round(total_anomaly / len(entities), 2),
            'total_billed': round(total_billed, 2),
            'connection_density': round(density, 2),
            'edge_count': n_edges
        })
    
    # Sort by total billed (highest first)
    rings.sort(key=lambda x: -x['total_billed'])
    
    return rings


def get_ring_edges(
    G: nx.DiGraph,
    entity_ids: List[str]
) -> List[Dict]:
    """
    Get all edges between entities in a ring.
    Used for visualization.
    """
    
    entity_set = set(entity_ids)
    edges = []
    
    for src, dst, data in G.edges(data=True):
        if src in entity_set and dst in entity_set:
            edges.append({
                'src': src,
                'dst': dst,
                'relationship': data.get('relationship', 'CONNECTED'),
                'weight': data.get('weight', 1),
                'total_amount': data.get('total_amount', 0)
            })
    
    return edges


def get_referral_history(
    claims_df: pd.DataFrame,
    provider_id: str,
    months: int = 18
) -> List[Dict]:
    """
    Get monthly referral breakdown for a provider.
    Shows how referral patterns changed over time.
    
    Returns list of monthly records with:
    - month
    - referral_sources: dict of referring_provider -> count
    - total_referrals
    - top_source
    - concentration (% from top source)
    """
    
    # Filter claims where this provider received referrals
    provider_claims = claims_df[
        (claims_df['provider_id'] == provider_id) &
        (claims_df['referring_provider_id'].notna())
    ].copy()
    
    if len(provider_claims) == 0:
        return []
    
    # Add month column
    provider_claims['month'] = provider_claims['service_date'].dt.to_period('M')
    
    # Get all months in range
    all_months = provider_claims['month'].unique()
    all_months = sorted(all_months)[-months:]  # Last N months
    
    history = []
    
    for month in all_months:
        month_claims = provider_claims[provider_claims['month'] == month]
        
        # Count referrals by source
        referral_counts = month_claims['referring_provider_id'].value_counts().to_dict()
        total_referrals = len(month_claims)
        
        if total_referrals > 0:
            top_source = max(referral_counts, key=referral_counts.get)
            top_count = referral_counts[top_source]
            concentration = top_count / total_referrals
        else:
            top_source = None
            concentration = 0
        
        history.append({
            'month': str(month),
            'referral_sources': referral_counts,
            'total_referrals': total_referrals,
            'top_source': top_source,
            'concentration': round(concentration, 2),
            'unique_sources': len(referral_counts)
        })
    
    return history


def get_graph_summary(G: nx.DiGraph) -> Dict:
    """Get summary statistics about the graph."""
    
    providers = [n for n, d in G.nodes(data=True) if d.get('entity_type') == 'provider']
    members = [n for n, d in G.nodes(data=True) if d.get('entity_type') == 'member']
    facilities = [n for n, d in G.nodes(data=True) if d.get('entity_type') == 'facility']
    
    billed_edges = [(u, v, d) for u, v, d in G.edges(data=True) if d.get('relationship') == 'BILLED_FOR']
    referral_edges = [(u, v, d) for u, v, d in G.edges(data=True) if d.get('relationship') == 'REFERRED_TO']
    operates_edges = [(u, v, d) for u, v, d in G.edges(data=True) if d.get('relationship') == 'OPERATES_AT']
    
    return {
        'total_nodes': G.number_of_nodes(),
        'total_edges': G.number_of_edges(),
        'providers': len(providers),
        'members': len(members),
        'facilities': len(facilities),
        'billed_for_edges': len(billed_edges),
        'referred_to_edges': len(referral_edges),
        'operates_at_edges': len(operates_edges),
    }


if __name__ == "__main__":
    from generate_synthetic import generate_all_data
    from features import compute_all_features
    from anomaly import compute_all_anomaly_scores
    
    # Generate data
    claims_df, providers_df, members_df, facilities_df = generate_all_data()
    
    # Compute features
    provider_features_df, member_features_df, peer_stats_df, _ = compute_all_features(
        claims_df, providers_df, members_df
    )
    
    # Compute anomaly scores
    anomaly_scores_df = compute_all_anomaly_scores(
        provider_features_df,
        member_features_df,
        peer_stats_df
    )
    
    # Build graph
    print("\n=== Building Graph ===")
    G = build_claims_graph(claims_df, anomaly_scores_df)
    
    # Test find_connections for network case
    print("\n=== Connections for P-6610 (Network Case) ===")
    connections = find_connections(G, 'P-6610', depth=2)
    print(f"Total connected entities: {connections['total_entities']}")
    print(f"Connection density: {connections['connection_density']}")
    print("Top connected (by anomaly score):")
    for entity in connections['connected_entities'][:10]:
        print(f"  {entity['entity_id']} ({entity['entity_type']}): anomaly={entity['anomaly_score']:.2f}, dist={entity['distance']}")
    
    # Find rings
    print("\n=== Finding Fraud Rings ===")
    rings = find_rings(G, anomaly_scores_df, min_anomaly_score=0.5, min_entities=3)
    print(f"Found {len(rings)} potential rings")
    
    for i, ring in enumerate(rings[:3]):
        print(f"\nRing {i+1}:")
        print(f"  Entities: {ring['entity_count']}")
        print(f"  Avg anomaly: {ring['avg_anomaly_score']}")
        print(f"  Total billed: ${ring['total_billed']:,.0f}")
        print(f"  Density: {ring['connection_density']}")
        
        # Show entities
        providers_in_ring = [e for e in ring['entities'] if e['entity_type'] == 'provider']
        print(f"  Providers: {[e['entity_id'] for e in providers_in_ring[:5]]}")
    
    # Referral history
    print("\n=== Referral History for P-6610 ===")
    history = get_referral_history(claims_df, 'P-6610', months=12)
    for record in history[-6:]:
        print(f"  {record['month']}: {record['total_referrals']} referrals, "
              f"top source concentration: {record['concentration']:.0%}")
