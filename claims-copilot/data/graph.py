"""
Network graph for Prudential life insurance entity relationships.
Nodes: Agents, Policyholders, Trusts/Beneficiaries
Edges: SOLD_BY, BENEFICIARY_OF, FINANCED_BY, CONNECTED_TO
"""

import networkx as nx
import pandas as pd
from collections import defaultdict


def build_insurance_graph(policies_df, anomaly_scores_df):
    """Build directed graph from policies and relationships."""
    G = nx.DiGraph()

    # Build anomaly lookup
    anomaly_lookup = {}
    face_lookup = {}
    if len(anomaly_scores_df) > 0:
        for _, row in anomaly_scores_df.iterrows():
            anomaly_lookup[row["entity_id"]] = float(row["anomaly_score"])
            face_lookup[row["entity_id"]] = float(row.get("total_face_amount", 0))

    # Add agent nodes
    agent_ids = policies_df["agent_id"].unique()
    for aid in agent_ids:
        G.add_node(aid, entity_type="agent",
                    anomaly_score=anomaly_lookup.get(aid, 0),
                    total_face_amount=face_lookup.get(aid, 0))

    # Add policyholder nodes
    ph_ids = policies_df["policyholder_id"].unique()
    for phid in ph_ids:
        G.add_node(phid, entity_type="policyholder",
                    anomaly_score=anomaly_lookup.get(phid, 0),
                    total_face_amount=0)

    # Add beneficiary nodes and trust nodes
    beneficiaries = policies_df["beneficiary"].unique()
    for ben in beneficiaries:
        ben_id = f"BEN-{hash(ben) % 100000:05d}"
        G.add_node(ben_id, entity_type="beneficiary", label=ben, anomaly_score=0, total_face_amount=0)

    # Add edges: agent → policyholder (SOLD_BY)
    agent_ph = policies_df.groupby(["agent_id", "policyholder_id"]).agg(
        total_face=("face_amount", "sum"),
        n_policies=("policy_id", "count"),
    ).reset_index()
    for _, row in agent_ph.iterrows():
        G.add_edge(row["agent_id"], row["policyholder_id"],
                    relationship="SOLD_BY",
                    weight=row["n_policies"],
                    total_amount=float(row["total_face"]))

    # Add edges: policyholder → beneficiary (BENEFICIARY_OF)
    for _, pol in policies_df.iterrows():
        ben_id = f"BEN-{hash(pol['beneficiary']) % 100000:05d}"
        if G.has_node(ben_id):
            if G.has_edge(pol["policyholder_id"], ben_id):
                G[pol["policyholder_id"]][ben_id]["weight"] += 1
                G[pol["policyholder_id"]][ben_id]["total_amount"] += float(pol["face_amount"])
            else:
                G.add_edge(pol["policyholder_id"], ben_id,
                           relationship="BENEFICIARY_OF",
                           weight=1,
                           total_amount=float(pol["face_amount"]))

    # Trust-owned policies get extra edge: agent → trust/beneficiary
    trust_pols = policies_df[policies_df["trust_owned"] == True]
    for _, pol in trust_pols.iterrows():
        ben_id = f"BEN-{hash(pol['beneficiary']) % 100000:05d}"
        if not G.has_edge(pol["agent_id"], ben_id):
            G.add_edge(pol["agent_id"], ben_id,
                       relationship="TRUST_CONNECTED",
                       weight=1,
                       total_amount=float(pol["face_amount"]))

    return G


def find_connections(G, entity_id, depth=2):
    """BFS traversal from entity within N hops."""
    if entity_id not in G:
        return {"error": f"Entity {entity_id} not found in graph"}

    visited = {entity_id: 0}
    queue = [(entity_id, 0)]
    connected = []

    while queue:
        current, dist = queue.pop(0)
        if dist >= depth:
            continue
        # Check both successors and predecessors (undirected traversal)
        neighbors = set(G.successors(current)) | set(G.predecessors(current))
        for neighbor in neighbors:
            if neighbor not in visited:
                visited[neighbor] = dist + 1
                queue.append((neighbor, dist + 1))
                nd = G.nodes.get(neighbor, {})
                connected.append({
                    "entity_id": neighbor,
                    "entity_type": nd.get("entity_type", "unknown"),
                    "distance": dist + 1,
                    "anomaly_score": nd.get("anomaly_score", 0),
                })

    # Compute subgraph density
    subgraph_nodes = list(visited.keys())
    subgraph = G.subgraph(subgraph_nodes)
    n_nodes = len(subgraph_nodes)
    n_edges = subgraph.number_of_edges()
    density = n_edges / n_nodes if n_nodes > 0 else 0

    return {
        "center": entity_id,
        "connected_entities": connected,
        "total_entities": len(connected),
        "connection_density": round(density, 2),
    }


def find_rings(G, anomaly_scores_df, min_anomaly=0.5, min_entities=3):
    """Find clusters of connected high-anomaly entities.
    
    Agents connect through intermediate nodes (policyholders, beneficiaries),
    so we expand 1 hop from high-anomaly nodes to include bridging entities.
    """
    high_anomaly_ids = set(
        anomaly_scores_df[anomaly_scores_df["anomaly_score"] >= min_anomaly]["entity_id"]
    )

    # Get high-anomaly nodes that exist in the graph
    ha_in_graph = [n for n in G.nodes if n in high_anomaly_ids]
    if not ha_in_graph:
        return []

    # Expand 1 hop to include intermediate nodes (policyholders, beneficiaries)
    # that bridge high-anomaly agents together
    expanded_nodes = set(ha_in_graph)
    for n in ha_in_graph:
        expanded_nodes.update(G.successors(n))
        expanded_nodes.update(G.predecessors(n))

    subgraph = G.subgraph(expanded_nodes).to_undirected()
    components = list(nx.connected_components(subgraph))

    rings = []
    for comp in components:
        # Require at least min_entities high-anomaly nodes in the component
        ha_in_comp = [n for n in comp if n in high_anomaly_ids]
        if len(ha_in_comp) < min_entities:
            continue
        entities = []
        total_face = 0
        for nid in comp:
            nd = G.nodes.get(nid, {})
            entities.append({
                "entity_id": nid,
                "entity_type": nd.get("entity_type", "unknown"),
                "anomaly_score": nd.get("anomaly_score", 0),
            })
            total_face += nd.get("total_face_amount", 0)

        sub = G.subgraph(comp)
        n_edges = sub.number_of_edges()
        density = n_edges / len(comp) if comp else 0

        rings.append({
            "entities": entities,
            "entity_count": len(comp),
            "avg_anomaly_score": round(sum(e["anomaly_score"] for e in entities) / len(entities), 2),
            "total_face_amount": round(total_face, 2),
            "connection_density": round(density, 2),
        })

    rings.sort(key=lambda r: -r["avg_anomaly_score"])
    return rings


def get_ring_edges(G, entity_ids):
    """Get all edges between ring members."""
    id_set = set(entity_ids)
    edges = []
    for src, dst, data in G.edges(data=True):
        if src in id_set and dst in id_set:
            edges.append({
                "src": src,
                "dst": dst,
                "relationship": data.get("relationship", "CONNECTED"),
                "weight": data.get("weight", 1),
                "total_amount": data.get("total_amount", 0),
            })
    return edges


def get_agent_network_history(policies_df, agent_id, months=18):
    """Monthly breakdown of agent activity showing policy issuance patterns."""
    from datetime import datetime, timedelta
    now = datetime(2026, 3, 1)
    cutoff = now - timedelta(days=months * 30)

    agent_pols = policies_df[
        (policies_df["agent_id"] == agent_id) &
        (policies_df["issue_date"] >= cutoff)
    ].copy()

    if len(agent_pols) == 0:
        return []

    agent_pols["month"] = agent_pols["issue_date"].dt.to_period("M")
    monthly = agent_pols.groupby("month").agg(
        policies_issued=("policy_id", "count"),
        total_face=("face_amount", "sum"),
        trust_count=("trust_owned", "sum"),
    ).reset_index()

    return [
        {
            "month": str(row["month"]),
            "policies_issued": int(row["policies_issued"]),
            "total_face": float(row["total_face"]),
            "trust_count": int(row["trust_count"]),
        }
        for _, row in monthly.iterrows()
    ]
