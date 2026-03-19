"""
Feature engineering for Prudential life insurance investigation.
Computes agent-level and policy-level features for anomaly detection.
"""

import pandas as pd
import numpy as np
from datetime import datetime


def compute_agent_features(policies_df, agents_df, transactions_df, claims_df):
    """Compute per-agent features for anomaly detection."""
    now = datetime(2026, 3, 1)
    rows = []
    for _, agt in agents_df.iterrows():
        aid = agt["agent_id"]
        agt_pols = policies_df[policies_df["agent_id"] == aid]
        agt_claims = claims_df[claims_df["agent_id"] == aid]
        agt_txns = transactions_df[transactions_df["policy_id"].isin(agt_pols["policy_id"])]

        n_policies = len(agt_pols)
        if n_policies == 0:
            continue

        total_face = agt_pols["face_amount"].sum()
        avg_face = agt_pols["face_amount"].mean()
        contestable_pols = agt_pols[agt_pols["contestability_end"] >= now]
        pct_contestable = len(contestable_pols) / n_policies if n_policies > 0 else 0
        trust_owned_pct = agt_pols["trust_owned"].sum() / n_policies
        premium_financed_pct = agt_pols["premium_financed"].sum() / n_policies if "premium_financed" in agt_pols.columns else 0
        contestable_claims = len(agt_claims[agt_claims.get("within_contestability", pd.Series(dtype=bool)).fillna(False)])
        claim_rate = len(agt_claims) / n_policies if n_policies > 0 else 0
        high_face_pct = len(agt_pols[agt_pols["face_amount"] >= 1_000_000]) / n_policies
        flagged_txns = len(agt_txns[agt_txns["flagged"]]) if "flagged" in agt_txns.columns else 0

        # Replacement rate (policies on same policyholder)
        ph_counts = agt_pols["policyholder_id"].value_counts()
        replacement_rate = (ph_counts > 1).sum() / len(ph_counts) if len(ph_counts) > 0 else 0

        rows.append({
            "agent_id": aid,
            "region": agt["region"],
            "peer_group": agt["region"],
            "n_policies": n_policies,
            "total_face_amount": total_face,
            "avg_face_amount": avg_face,
            "pct_contestable": round(pct_contestable, 4),
            "trust_owned_pct": round(trust_owned_pct, 4),
            "premium_financed_pct": round(premium_financed_pct, 4),
            "contestable_claims": contestable_claims,
            "claim_rate": round(claim_rate, 4),
            "high_face_pct": round(high_face_pct, 4),
            "replacement_rate": round(replacement_rate, 4),
            "flagged_txns": flagged_txns,
            "complaints": agt["complaints"],
            "tenure_years": agt["tenure_years"],
        })
    return pd.DataFrame(rows)


def compute_policy_features(policies_df, transactions_df, mib_df, rx_df, claims_df):
    """Compute per-policy features for contestability analysis."""
    now = datetime(2026, 3, 1)
    rows = []
    for _, pol in policies_df.iterrows():
        pid = pol["policy_id"]
        phid = pol["policyholder_id"]
        pol_txns = transactions_df[transactions_df["policy_id"] == pid]
        ph_mib = mib_df[mib_df["policyholder_id"] == phid] if len(mib_df) > 0 else pd.DataFrame()
        ph_rx = rx_df[rx_df["policyholder_id"] == phid] if len(rx_df) > 0 else pd.DataFrame()
        pol_claims = claims_df[claims_df["policy_id"] == pid]

        disclosed = pol.get("disclosed_conditions", [])
        if not isinstance(disclosed, list):
            disclosed = []
        n_disclosed = len(disclosed)
        n_mib = len(ph_mib)
        n_rx = len(ph_rx)
        undisclosed_count = max(0, n_mib - n_disclosed)

        days_since_issue = (now - pol["issue_date"]).days
        is_contestable = pol["contestability_end"] >= now
        days_remaining = max(0, (pol["contestability_end"] - now).days) if is_contestable else 0

        third_party_payments = len(pol_txns[pol_txns["source"] != "policyholder"]) if "source" in pol_txns.columns else 0
        flagged_txn_count = len(pol_txns[pol_txns["flagged"]]) if "flagged" in pol_txns.columns else 0
        has_claim = len(pol_claims) > 0

        rows.append({
            "policy_id": pid,
            "policyholder_id": phid,
            "agent_id": pol["agent_id"],
            "face_amount": pol["face_amount"],
            "days_since_issue": days_since_issue,
            "is_contestable": is_contestable,
            "days_remaining": days_remaining,
            "n_disclosed": n_disclosed,
            "n_mib_codes": n_mib,
            "n_rx_records": n_rx,
            "undisclosed_count": undisclosed_count,
            "trust_owned": bool(pol.get("trust_owned", False)),
            "premium_financed": bool(pol.get("premium_financed", False)),
            "third_party_payments": third_party_payments,
            "flagged_txn_count": flagged_txn_count,
            "has_claim": has_claim,
        })
    return pd.DataFrame(rows)


def compute_peer_stats(agent_features_df):
    """Compute peer group statistics for agents by region."""
    metrics = [
        "n_policies", "avg_face_amount", "claim_rate", "high_face_pct",
        "trust_owned_pct", "premium_financed_pct", "replacement_rate",
        "pct_contestable", "flagged_txns", "complaints",
    ]
    stats = agent_features_df.groupby("peer_group")[metrics].agg(["mean", "std"]).reset_index()
    stats.columns = ["peer_group"] + [f"{m}_{s}" for m in metrics for s in ["mean", "std"]]
    # Fill NaN std with 1 to avoid division by zero
    for col in stats.columns:
        if col.endswith("_std"):
            stats[col] = stats[col].fillna(1).replace(0, 1)
    return stats


def compute_z_scores(agent_features_df, peer_stats_df):
    """Compute z-scores for each agent vs peer group."""
    metrics = [
        "n_policies", "avg_face_amount", "claim_rate", "high_face_pct",
        "trust_owned_pct", "premium_financed_pct", "replacement_rate",
        "pct_contestable", "flagged_txns", "complaints",
    ]
    merged = agent_features_df.merge(peer_stats_df, on="peer_group", how="left")
    for m in metrics:
        mean_col = f"{m}_mean"
        std_col = f"{m}_std"
        if mean_col in merged.columns and std_col in merged.columns:
            merged[f"{m}_z"] = (merged[m] - merged[mean_col]) / merged[std_col].replace(0, 1)
    return merged


def compute_all_features(policies_df, agents_df, policyholders_df, transactions_df, claims_df, mib_df, rx_df):
    """
    Main entry point. Returns:
    (agent_features_df, policy_features_df, peer_stats_df, z_scores_df)
    """
    print("  Computing agent features...")
    agent_features_df = compute_agent_features(policies_df, agents_df, transactions_df, claims_df)
    print(f"  → {len(agent_features_df)} agent feature rows")

    print("  Computing policy features...")
    policy_features_df = compute_policy_features(policies_df, transactions_df, mib_df, rx_df, claims_df)
    print(f"  → {len(policy_features_df)} policy feature rows")

    print("  Computing peer statistics...")
    peer_stats_df = compute_peer_stats(agent_features_df)

    print("  Computing z-scores...")
    z_scores_df = compute_z_scores(agent_features_df, peer_stats_df)

    return agent_features_df, policy_features_df, peer_stats_df, z_scores_df
