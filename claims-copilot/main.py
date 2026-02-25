"""
Claims Investigation Copilot - Main Entry Point

This script loads all data, computes features, runs anomaly detection,
and builds the graph. It provides a DataContext object that can be used
by the LangGraph agents.
"""

import os
import sys
from dataclasses import dataclass
from typing import Dict, Optional
import pandas as pd
import networkx as nx

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.generate_synthetic import generate_all_data, NET_PRIMARY, NET_PROVIDERS
from data.features import compute_all_features
from data.anomaly import compute_all_anomaly_scores
from data.graph import build_claims_graph, find_connections, find_rings, get_ring_edges, get_referral_history
from billing_rules.index import get_billing_rules_index, search_billing_rules
import pickle


@dataclass
class DataContext:
    """
    Container for all data used by the investigation agents.
    """
    claims_df: pd.DataFrame
    providers_df: pd.DataFrame
    members_df: pd.DataFrame
    facilities_df: pd.DataFrame
    provider_features_df: pd.DataFrame
    member_features_df: pd.DataFrame
    peer_stats_df: pd.DataFrame
    z_scores_df: pd.DataFrame
    anomaly_scores_df: pd.DataFrame
    graph: nx.DiGraph
    
    def get_high_anomaly_providers(self, threshold: float = 0.5) -> pd.DataFrame:
        """Get providers with anomaly score above threshold."""
        provider_scores = self.anomaly_scores_df[
            (self.anomaly_scores_df['entity_type'] == 'provider') &
            (self.anomaly_scores_df['anomaly_score'] >= threshold)
        ].sort_values('anomaly_score', ascending=False)
        return provider_scores
    
    def get_provider_profile(self, provider_id: str) -> Optional[Dict]:
        """Get complete profile for a provider."""
        # Get basic info
        provider_info = self.providers_df[self.providers_df['provider_id'] == provider_id]
        if len(provider_info) == 0:
            return None
        provider_info = provider_info.iloc[0].to_dict()
        
        # Get features
        features = self.provider_features_df[
            self.provider_features_df['provider_id'] == provider_id
        ]
        if len(features) > 0:
            provider_info.update(features.iloc[0].to_dict())
        
        # Get anomaly score
        anomaly = self.anomaly_scores_df[
            self.anomaly_scores_df['entity_id'] == provider_id
        ]
        if len(anomaly) > 0:
            provider_info['anomaly_score'] = anomaly.iloc[0]['anomaly_score']
            provider_info['top_features'] = anomaly.iloc[0]['top_features']
        
        return provider_info
    
    def get_provider_claims(self, provider_id: str, limit: int = 20) -> pd.DataFrame:
        """Get claims for a specific provider."""
        claims = self.claims_df[self.claims_df['provider_id'] == provider_id]
        return claims.head(limit)
    
    def find_provider_connections(self, provider_id: str, depth: int = 2) -> Dict:
        """Find entities connected to a provider."""
        return find_connections(self.graph, provider_id, depth)
    
    def find_fraud_rings(self, min_anomaly: float = 0.5, min_entities: int = 3):
        """Find potential fraud rings."""
        return find_rings(self.graph, self.anomaly_scores_df, min_anomaly, min_entities)
    
    def get_referral_history(self, provider_id: str, months: int = 18):
        """Get referral history for a provider."""
        return get_referral_history(self.claims_df, provider_id, months)


def initialize_data(force_regenerate: bool = False) -> DataContext:
    """
    Initialize all data for the investigation copilot.
    
    This function:
    1. Checks for cached data (unless force_regenerate=True)
    2. Generates synthetic claims data if needed
    3. Computes provider and member features
    4. Runs anomaly detection
    5. Builds the network graph
    6. Initializes the billing rules index
    
    Args:
        force_regenerate: If True, regenerate data even if cache exists
    
    Returns:
        DataContext with all loaded data
    """
    
    cache_file = 'data_cache.pkl'
    
    # Try to load from cache first
    if not force_regenerate and os.path.exists(cache_file):
        print("=" * 60)
        print("CLAIMS INVESTIGATION COPILOT - Loading Cached Data")
        print("=" * 60)
        print(f"\nLoading from cache: {cache_file}...")
        
        try:
            with open(cache_file, 'rb') as f:
                ctx = pickle.load(f)
            
            print("✅ Cached data loaded successfully!")
            print("\n" + "=" * 60)
            print("DATA INITIALIZATION COMPLETE (from cache)")
            print("=" * 60)
            print("\n💡 To regenerate data, run with force_regenerate=True")
            
            return ctx
        except Exception as e:
            print(f"⚠️  Failed to load cache: {e}")
            print("Regenerating data...\n")
    
    print("=" * 60)
    print("CLAIMS INVESTIGATION COPILOT - Data Initialization")
    print("=" * 60)
    
    # Step 1: Generate synthetic data
    print("\n[1/5] Generating synthetic data...")
    claims_df, providers_df, members_df, facilities_df = generate_all_data()
    
    # Step 2: Compute features
    print("\n[2/5] Computing features...")
    provider_features_df, member_features_df, peer_stats_df, z_scores_df = compute_all_features(
        claims_df, providers_df, members_df
    )
    
    # Step 3: Run anomaly detection
    print("\n[3/5] Running anomaly detection...")
    anomaly_scores_df = compute_all_anomaly_scores(
        provider_features_df,
        member_features_df,
        peer_stats_df
    )
    
    # Step 4: Build graph
    print("\n[4/5] Building network graph...")
    graph = build_claims_graph(claims_df, anomaly_scores_df)
    
    # Step 5: Initialize billing rules
    print("\n[5/5] Initializing billing rules index...")
    _ = get_billing_rules_index()
    
    # Create context
    ctx = DataContext(
        claims_df=claims_df,
        providers_df=providers_df,
        members_df=members_df,
        facilities_df=facilities_df,
        provider_features_df=provider_features_df,
        member_features_df=member_features_df,
        peer_stats_df=peer_stats_df,
        z_scores_df=z_scores_df,
        anomaly_scores_df=anomaly_scores_df,
        graph=graph
    )
    
    # Save to cache
    print("\n💾 Saving to cache...")
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(ctx, f)
        print(f"✅ Data cached to {cache_file}")
    except Exception as e:
        print(f"⚠️  Failed to save cache: {e}")
    
    print("\n" + "=" * 60)
    print("DATA INITIALIZATION COMPLETE")
    print("=" * 60)
    
    return ctx


def run_demo():
    """
    Run a demonstration of the data layer.
    Shows how suspicious patterns can be discovered.
    """
    
    ctx = initialize_data()
    
    print("\n" + "=" * 60)
    print("DEMO: Discovering Suspicious Patterns")
    print("=" * 60)
    
    # Step 1: Find high anomaly providers
    print("\n[Step 1] Scanning for high-anomaly providers...")
    high_anomaly = ctx.get_high_anomaly_providers(threshold=0.5)
    print(f"Found {len(high_anomaly)} providers with anomaly score > 0.5:")
    for _, row in high_anomaly.head(10).iterrows():
        print(f"  \u2022 {row['entity_id']}: score={row['anomaly_score']:.2f}, billed=${row['total_billed']:,.0f}")
    
    # Step 2: Profile top entity
    top_entity = high_anomaly.iloc[0]['entity_id'] if len(high_anomaly) > 0 else NET_PRIMARY
    print(f"\n[Step 2] Profiling {top_entity}...")
    profile = ctx.get_provider_profile(top_entity)
    if profile:
        print(f"  Specialty: {profile.get('specialty')}")
        print(f"  Anomaly Score: {profile.get('anomaly_score', 0):.2f}")
        print(f"  Total Billed: ${profile.get('total_billed', 0):,.0f}")
        print(f"  CPT Concentration: {profile.get('top_cpt_concentration', 0):.1%}")
        print(f"  Referral Concentration: {profile.get('referral_concentration', 0):.1%}")
        
        if profile.get('top_features'):
            print("  Top anomaly features:")
            for feat in profile['top_features'][:3]:
                print(f"    - {feat['feature_name']}: {feat['value']} (z={feat['z_score']})")
    
    # Step 3: Find connections
    print(f"\n[Step 3] Finding connections to {top_entity}...")
    connections = ctx.find_provider_connections(top_entity, depth=2)
    print(f"  Total connected entities: {connections['total_entities']}")
    print(f"  Connection density: {connections['connection_density']}")
    
    connected_providers = [
        e for e in connections['connected_entities']
        if e['entity_type'] == 'provider' and e['anomaly_score'] > 0.3
    ]
    if connected_providers:
        print(f"  Connected providers with elevated anomaly:")
        for p in connected_providers[:5]:
            print(f"    \u2022 {p['entity_id']}: anomaly={p['anomaly_score']:.2f}")
    
    # Step 4: Find rings
    print("\n[Step 4] Finding fraud rings...")
    rings = ctx.find_fraud_rings(min_anomaly=0.5, min_entities=3)
    print(f"  Found {len(rings)} potential rings")
    
    if rings:
        ring = rings[0]
        print(f"\n  Top ring:")
        print(f"    Entities: {ring['entity_count']}")
        print(f"    Avg anomaly: {ring['avg_anomaly_score']}")
        print(f"    Total billed: ${ring['total_billed']:,.0f}")
        
        providers_in_ring = [e for e in ring['entities'] if e['entity_type'] == 'provider']
        print(f"    Providers: {[p['entity_id'] for p in providers_in_ring]}")
    
    # Step 5: Check referral history
    print(f"\n[Step 5] Analyzing referral history for {top_entity}...")
    history = ctx.get_referral_history(top_entity, months=12)
    if history:
        print("  Monthly referral concentration:")
        for record in history[-6:]:
            print(f"    {record['month']}: {record['total_referrals']} referrals, "
                  f"top source concentration: {record['concentration']:.0%}")
    
    # Step 6: Search billing rules
    print("\n[Step 6] Searching relevant billing rules...")
    rules = search_billing_rules(
        cpt_codes=['93458', '93306'],
        context="cardiology cardiac catheterization echocardiogram referral kickback unbundling"
    )
    print(f"  Found {len(rules)} relevant rules:")
    for rule in rules[:3]:
        print(f"    \u2022 {rule['section_id']}: {rule['title']}")
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nReady to be investigated by the LangGraph agents.")
    
    return ctx


if __name__ == "__main__":
    run_demo()
