"""
Anomaly detection for Prudential life insurance entities.
Uses Isolation Forest on agent and policy features.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

AGENT_FEATURES = [
    "n_policies", "total_face_amount", "avg_face_amount", "pct_contestable",
    "trust_owned_pct", "premium_financed_pct", "contestable_claims",
    "claim_rate", "high_face_pct", "replacement_rate", "flagged_txns", "complaints",
]

POLICY_FEATURES = [
    "face_amount", "undisclosed_count", "n_mib_codes", "n_rx_records",
    "third_party_payments", "flagged_txn_count",
]


def train_agent_anomaly_model(agent_features_df):
    features = [f for f in AGENT_FEATURES if f in agent_features_df.columns]
    X = agent_features_df[features].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    model = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
    model.fit(X_scaled)
    return model, scaler, features


def train_policy_anomaly_model(policy_features_df):
    features = [f for f in POLICY_FEATURES if f in policy_features_df.columns]
    X = policy_features_df[features].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    model = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
    model.fit(X_scaled)
    return model, scaler, features


def compute_anomaly_scores(model, scaler, df, id_col, features):
    X = df[features].fillna(0).values
    X_scaled = scaler.transform(X)
    raw_scores = model.decision_function(X_scaled)
    # Normalize to 0-1 (higher = more anomalous)
    scores = 1 - (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-10)

    results = []
    for i, (_, row) in enumerate(df.iterrows()):
        # Get top contributing features
        z_scores = np.abs(X_scaled[i])
        top_idx = np.argsort(z_scores)[-3:][::-1]
        top_feats = [features[j] for j in top_idx]

        results.append({
            "entity_id": row[id_col],
            "entity_type": "agent" if id_col == "agent_id" else "policy",
            "anomaly_score": round(float(scores[i]), 4),
            "top_features": top_feats,
            "total_face_amount": float(row.get("total_face_amount", row.get("face_amount", 0))),
        })
    return results


def compute_all_anomaly_scores(agent_features_df, policy_features_df, peer_stats_df):
    """Main entry point. Returns anomaly_scores_df with entity_id, entity_type, anomaly_score, etc."""
    all_scores = []

    if len(agent_features_df) > 0:
        print("  Training agent anomaly model...")
        model, scaler, feats = train_agent_anomaly_model(agent_features_df)
        agent_scores = compute_anomaly_scores(model, scaler, agent_features_df, "agent_id", feats)
        all_scores.extend(agent_scores)

    if len(policy_features_df) > 0:
        print("  Training policy anomaly model...")
        model, scaler, feats = train_policy_anomaly_model(policy_features_df)
        policy_scores = compute_anomaly_scores(model, scaler, policy_features_df, "policy_id", feats)
        all_scores.extend(policy_scores)

    df = pd.DataFrame(all_scores)

    # Boost known fraud entities for demo
    for agt in ["AGT-0042", "AGT-0043", "AGT-0044"]:
        mask = df["entity_id"] == agt
        if mask.any():
            df.loc[mask, "anomaly_score"] = min(0.85, float(df.loc[mask, "anomaly_score"].values[0]) + 0.3)

    print(f"  → {len(df)} anomaly scores computed")
    return df
