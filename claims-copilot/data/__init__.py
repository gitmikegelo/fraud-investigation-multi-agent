"""
Data module for Prudential Life Insurance Investigation Copilot.
"""

from .generate_synthetic import generate_all_data, NET_PRIMARY, NET_AGENTS
from .features import compute_all_features
from .anomaly import compute_all_anomaly_scores
from .graph import build_insurance_graph, find_connections, find_rings, get_ring_edges, get_agent_network_history
