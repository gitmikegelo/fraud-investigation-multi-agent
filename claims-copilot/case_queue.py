"""
Builds case queue from provider fraud anomaly scores + disability claims.
"""

import pandas as pd
from typing import List
from cases import Case, CaseType, CasePriority, CaseStatus
from data.generate_disability import DisabilityClaim


def build_case_queue(
    anomaly_scores_df: pd.DataFrame,
    provider_features_df: pd.DataFrame,
    disability_claims: List[DisabilityClaim],
) -> List[Case]:
    cases = []

    # Provider fraud cases from anomaly scores
    provider_scores = anomaly_scores_df[
        (anomaly_scores_df['entity_type'] == 'provider') &
        (anomaly_scores_df['anomaly_score'] > 0.6)
    ].sort_values('anomaly_score', ascending=False)

    for _, row in provider_scores.iterrows():
        pid = row['entity_id']
        score = float(row['anomaly_score'])
        billed = float(row['total_billed'])
        top_feat = row.get('top_features', '')
        if isinstance(top_feat, list):
            top_feat = top_feat[0] if top_feat else 'High anomaly score'
        elif not top_feat:
            top_feat = 'High anomaly score'

        # Get specialty from features
        pf = provider_features_df[provider_features_df['provider_id'] == pid]
        specialty = pf.iloc[0].get('peer_group', 'Unknown') if len(pf) > 0 else 'Unknown'

        short_id = pid.split('-')[1] if '-' in pid else pid
        priority = CasePriority.HIGH if score > 0.75 else CasePriority.MEDIUM

        cases.append(Case(
            case_id=f"NET-{short_id}",
            case_type=CaseType.PROVIDER_FRAUD,
            subject_id=pid,
            subject_name=pid,
            priority=priority,
            flag_reason=str(top_feat)[:80],
            key_metrics={"anomaly_score": round(score, 2), "total_billed": round(billed, 2), "specialty": specialty},
        ))

    # Disability cases
    for claim in disability_claims:
        if claim.red_flag_score < 0.5:
            continue
        if claim.red_flag_score > 0.75:
            priority = CasePriority.HIGH
        elif claim.red_flag_score > 0.5:
            priority = CasePriority.MEDIUM
        else:
            priority = CasePriority.LOW

        policy_age_months = max(1, (claim.claim_filed_date - claim.policy.policy_purchase_date).days // 30)
        cases.append(Case(
            case_id=claim.claim_id,
            case_type=CaseType.DISABILITY_CLAIM,
            subject_id=claim.policy.claimant_id,
            subject_name=claim.policy.claimant_name,
            priority=priority,
            flag_reason=claim.red_flags[0] if claim.red_flags else "Elevated risk score",
            key_metrics={
                "red_flag_score": claim.red_flag_score,
                "policy_age_months": policy_age_months,
                "monthly_benefit": claim.policy.monthly_benefit,
                "red_flag_count": len(claim.red_flags),
                "disability_type": claim.disability_type,
            },
        ))

    # Sort: HIGH first, then by risk metric descending
    priority_order = {CasePriority.HIGH: 0, CasePriority.MEDIUM: 1, CasePriority.LOW: 2}
    cases.sort(key=lambda c: (
        priority_order[c.priority],
        -(c.key_metrics.get('anomaly_score', 0) + c.key_metrics.get('red_flag_score', 0))
    ))
    return cases
