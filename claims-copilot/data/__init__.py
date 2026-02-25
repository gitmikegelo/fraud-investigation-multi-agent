"""
Data module for Claims Investigation Copilot.
Handles synthetic data generation, feature computation, anomaly detection, and graph building.
"""

from .generate_synthetic import (
    generate_all_data,
    generate_providers,
    generate_members,
    generate_facilities,
    generate_normal_claims,
    generate_network_case_claims,
    NET_PROVIDERS,
    NET_PRIMARY,
    NET_REFERRERS,
    NET_MEMBERS,
)

from .features import (
    compute_provider_features,
    compute_member_features,
    compute_peer_statistics,
    calculate_z_scores,
    compute_all_features,
)

from .anomaly import (
    compute_all_anomaly_scores,
    train_provider_anomaly_model,
    train_member_anomaly_model,
    get_top_anomaly_features,
    PROVIDER_ANOMALY_FEATURES,
    MEMBER_ANOMALY_FEATURES,
)

from .graph import (
    build_claims_graph,
    find_connections,
    find_rings,
    get_ring_edges,
    get_referral_history,
    get_graph_summary,
)

__all__ = [
    # Data generation
    'generate_all_data',
    'generate_providers',
    'generate_members',
    'generate_facilities',
    'generate_normal_claims',
    'generate_network_case_claims',
    'NET_PROVIDERS',
    'NET_PRIMARY',
    'NET_REFERRERS',
    'NET_MEMBERS',
    
    # Features
    'compute_provider_features',
    'compute_member_features',
    'compute_peer_statistics',
    'calculate_z_scores',
    'compute_all_features',
    
    # Anomaly detection
    'compute_all_anomaly_scores',
    'train_provider_anomaly_model',
    'train_member_anomaly_model',
    'get_top_anomaly_features',
    'PROVIDER_ANOMALY_FEATURES',
    'MEMBER_ANOMALY_FEATURES',
    
    # Graph
    'build_claims_graph',
    'find_connections',
    'find_rings',
    'get_ring_edges',
    'get_referral_history',
    'get_graph_summary',
]
