"""
Feature computation module for Claims Investigation Copilot.
Computes provider-level and member-level features for anomaly detection.
"""

import pandas as pd
import numpy as np
from typing import Tuple
from datetime import datetime


def compute_provider_features(
    claims_df: pd.DataFrame,
    providers_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute provider-level features for anomaly detection.
    
    Features:
    - claims_per_month: Average claims submitted per month
    - unique_patients_per_month: Average unique patients seen per month
    - claims_per_patient: Average claims per patient
    - pct_high_complexity: % E&M codes at 99214/99215
    - avg_billed_per_claim: Average billed amount per claim
    - top_cpt_concentration: % claims using most common CPT
    - weekend_billing_rate: % of claims on weekends
    - avg_patients_per_day: Average unique patients per service day
    - duplicate_claim_rate: % of potential duplicate claims
    - same_patient_same_day_rate: Rate of multiple claims for same patient same day
    - referral_concentration: % referrals from top 3 sources
    - referral_source_count: Number of unique referral sources
    - out_of_specialty_rate: % of claims for CPTs outside typical specialty
    """
    
    # Get date range for monthly calculations
    min_date = claims_df['service_date'].min()
    max_date = claims_df['service_date'].max()
    months_span = max((max_date - min_date).days / 30, 1)
    
    features_list = []
    
    for provider_id in providers_df['provider_id'].unique():
        provider_claims = claims_df[claims_df['provider_id'] == provider_id]
        
        if len(provider_claims) == 0:
            continue
        
        provider_info = providers_df[providers_df['provider_id'] == provider_id].iloc[0]
        
        # Basic volume metrics
        total_claims = len(provider_claims)
        unique_patients = provider_claims['member_id'].nunique()
        
        claims_per_month = total_claims / months_span
        unique_patients_per_month = unique_patients / months_span
        claims_per_patient = total_claims / max(unique_patients, 1)
        
        # Complexity metrics (E&M codes)
        high_complexity_codes = ['99214', '99215']
        em_codes = ['99211', '99212', '99213', '99214', '99215']
        em_claims = provider_claims[provider_claims['cpt_code'].isin(em_codes)]
        high_complexity_claims = provider_claims[provider_claims['cpt_code'].isin(high_complexity_codes)]
        
        pct_high_complexity = (
            len(high_complexity_claims) / len(em_claims) 
            if len(em_claims) > 0 else 0
        )
        
        # Billing metrics
        avg_billed_per_claim = provider_claims['billed_amount'].mean()
        total_billed = provider_claims['billed_amount'].sum()
        
        # CPT concentration
        cpt_counts = provider_claims['cpt_code'].value_counts()
        top_cpt_concentration = cpt_counts.iloc[0] / total_claims if len(cpt_counts) > 0 else 0
        
        # Weekend billing
        provider_claims = provider_claims.copy()
        provider_claims['is_weekend'] = provider_claims['service_date'].dt.dayofweek >= 5
        weekend_billing_rate = provider_claims['is_weekend'].mean()
        
        # Patients per day
        daily_patients = provider_claims.groupby('service_date')['member_id'].nunique()
        avg_patients_per_day = daily_patients.mean() if len(daily_patients) > 0 else 0
        
        # Duplicate claim detection (same patient, same CPT, same day)
        provider_claims['dup_key'] = (
            provider_claims['member_id'] + '_' + 
            provider_claims['cpt_code'] + '_' + 
            provider_claims['service_date'].astype(str)
        )
        dup_counts = provider_claims['dup_key'].value_counts()
        duplicate_claim_rate = (dup_counts > 1).sum() / len(dup_counts) if len(dup_counts) > 0 else 0
        
        # Same patient same day (any CPT)
        provider_claims['day_patient_key'] = (
            provider_claims['member_id'] + '_' + 
            provider_claims['service_date'].astype(str)
        )
        day_patient_counts = provider_claims['day_patient_key'].value_counts()
        same_patient_same_day_rate = (day_patient_counts > 1).sum() / len(day_patient_counts) if len(day_patient_counts) > 0 else 0
        
        # Referral metrics (claims where this provider received referrals)
        referred_to_provider = claims_df[claims_df['provider_id'] == provider_id]
        referral_sources = referred_to_provider[
            referred_to_provider['referring_provider_id'].notna()
        ]['referring_provider_id']
        
        referral_source_count = referral_sources.nunique()
        
        if len(referral_sources) > 0:
            ref_counts = referral_sources.value_counts()
            top_3_refs = ref_counts.head(3).sum()
            referral_concentration = top_3_refs / len(referral_sources)
        else:
            referral_concentration = 0
        
        # Out of specialty rate (simplified - flag if using CPTs unusual for specialty)
        # For now, just check if ortho providers are doing non-ortho codes
        specialty = provider_info['specialty']
        ortho_cpts = ['27447', '27130', '29881', '27446', '20610']
        cardio_cpts = ['93000', '93306', '93458', '93010']
        
        if specialty == "Orthopedic Surgery":
            specialty_claims = provider_claims[provider_claims['cpt_code'].isin(ortho_cpts)]
            out_of_specialty_rate = 1 - (len(specialty_claims) / total_claims) if total_claims > 0 else 0
        elif specialty == "Cardiology":
            specialty_claims = provider_claims[provider_claims['cpt_code'].isin(cardio_cpts)]
            out_of_specialty_rate = 1 - (len(specialty_claims) / total_claims) if total_claims > 0 else 0
        else:
            # For other specialties, assume mostly E&M codes
            em_claims_count = len(provider_claims[provider_claims['cpt_code'].isin(em_codes)])
            out_of_specialty_rate = 1 - (em_claims_count / total_claims) if total_claims > 0 else 0
        
        features_list.append({
            'provider_id': provider_id,
            'specialty': specialty,
            'peer_group': provider_info['peer_group'],
            'region': provider_info['region'],
            'claims_per_month': round(claims_per_month, 2),
            'unique_patients_per_month': round(unique_patients_per_month, 2),
            'claims_per_patient': round(claims_per_patient, 2),
            'pct_high_complexity': round(pct_high_complexity, 4),
            'avg_billed_per_claim': round(avg_billed_per_claim, 2),
            'top_cpt_concentration': round(top_cpt_concentration, 4),
            'weekend_billing_rate': round(weekend_billing_rate, 4),
            'avg_patients_per_day': round(avg_patients_per_day, 2),
            'duplicate_claim_rate': round(duplicate_claim_rate, 4),
            'same_patient_same_day_rate': round(same_patient_same_day_rate, 4),
            'referral_concentration': round(referral_concentration, 4),
            'referral_source_count': referral_source_count,
            'out_of_specialty_rate': round(out_of_specialty_rate, 4),
            'total_claims': total_claims,
            'total_billed': round(total_billed, 2),
            'unique_patients': unique_patients,
        })
    
    return pd.DataFrame(features_list)


def compute_member_features(
    claims_df: pd.DataFrame,
    members_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute member-level features for anomaly detection.
    
    Features useful for detecting doctor shopping, excessive utilization, etc.
    """
    
    min_date = claims_df['service_date'].min()
    max_date = claims_df['service_date'].max()
    months_span = max((max_date - min_date).days / 30, 1)
    
    features_list = []
    
    for member_id in members_df['member_id'].unique():
        member_claims = claims_df[claims_df['member_id'] == member_id]
        
        if len(member_claims) == 0:
            continue
        
        member_info = members_df[members_df['member_id'] == member_id].iloc[0]
        
        total_claims = len(member_claims)
        unique_providers = member_claims['provider_id'].nunique()
        unique_facilities = member_claims['facility_id'].nunique()
        
        claims_per_month = total_claims / months_span
        providers_per_month = unique_providers / months_span
        
        # Spending
        total_billed = member_claims['billed_amount'].sum()
        avg_billed_per_claim = member_claims['billed_amount'].mean()
        
        # Provider diversity (high might indicate doctor shopping)
        provider_concentration = 1 - (unique_providers / total_claims) if total_claims > 0 else 0
        
        # Same day multi-provider visits
        member_claims = member_claims.copy()
        daily_providers = member_claims.groupby('service_date')['provider_id'].nunique()
        multi_provider_days = (daily_providers > 1).sum()
        multi_provider_day_rate = multi_provider_days / len(daily_providers) if len(daily_providers) > 0 else 0
        
        # Pain management / controlled substance indicators
        pain_cpts = ['64493', '62322', '64635', '20610']
        pain_claims = member_claims[member_claims['cpt_code'].isin(pain_cpts)]
        pain_management_rate = len(pain_claims) / total_claims if total_claims > 0 else 0
        
        # Geographic spread
        unique_regions = claims_df[claims_df['member_id'] == member_id].merge(
            members_df[['member_id', 'region']], on='member_id', how='left'
        )['region'].nunique()
        
        features_list.append({
            'member_id': member_id,
            'age': member_info['age'],
            'gender': member_info['gender'],
            'region': member_info['region'],
            'claims_per_month': round(claims_per_month, 2),
            'unique_providers': unique_providers,
            'unique_facilities': unique_facilities,
            'providers_per_month': round(providers_per_month, 2),
            'total_billed': round(total_billed, 2),
            'avg_billed_per_claim': round(avg_billed_per_claim, 2),
            'provider_concentration': round(provider_concentration, 4),
            'multi_provider_day_rate': round(multi_provider_day_rate, 4),
            'pain_management_rate': round(pain_management_rate, 4),
            'total_claims': total_claims,
        })
    
    return pd.DataFrame(features_list)


def compute_peer_statistics(
    provider_features_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute peer group statistics for comparison.
    Used for z-score calculations.
    """
    
    numeric_cols = [
        'claims_per_month', 'unique_patients_per_month', 'claims_per_patient',
        'pct_high_complexity', 'avg_billed_per_claim', 'top_cpt_concentration',
        'weekend_billing_rate', 'avg_patients_per_day', 'duplicate_claim_rate',
        'same_patient_same_day_rate', 'referral_concentration', 'referral_source_count',
        'out_of_specialty_rate'
    ]
    
    peer_stats = provider_features_df.groupby('peer_group')[numeric_cols].agg(['mean', 'std'])
    peer_stats.columns = ['_'.join(col).strip() for col in peer_stats.columns.values]
    peer_stats = peer_stats.reset_index()
    
    return peer_stats


def calculate_z_scores(
    provider_features_df: pd.DataFrame,
    peer_stats_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate z-scores for each provider compared to their peer group.
    """
    
    metrics = [
        'claims_per_month', 'unique_patients_per_month', 'claims_per_patient',
        'pct_high_complexity', 'avg_billed_per_claim', 'top_cpt_concentration',
        'weekend_billing_rate', 'avg_patients_per_day', 'duplicate_claim_rate',
        'same_patient_same_day_rate', 'referral_concentration', 'out_of_specialty_rate'
    ]
    
    df = provider_features_df.merge(peer_stats_df, on='peer_group', how='left')
    
    z_scores = {}
    for metric in metrics:
        mean_col = f'{metric}_mean'
        std_col = f'{metric}_std'
        
        if mean_col in df.columns and std_col in df.columns:
            # Avoid division by zero
            std_vals = df[std_col].replace(0, 1)
            z_scores[f'{metric}_zscore'] = (df[metric] - df[mean_col]) / std_vals
    
    z_scores_df = pd.DataFrame(z_scores)
    z_scores_df['provider_id'] = df['provider_id']
    
    return z_scores_df


def compute_all_features(
    claims_df: pd.DataFrame,
    providers_df: pd.DataFrame,
    members_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Compute all features.
    
    Returns:
        provider_features_df, member_features_df, peer_stats_df, z_scores_df
    """
    
    print("Computing provider features...")
    provider_features_df = compute_provider_features(claims_df, providers_df)
    
    print("Computing member features...")
    member_features_df = compute_member_features(claims_df, members_df)
    
    print("Computing peer statistics...")
    peer_stats_df = compute_peer_statistics(provider_features_df)
    
    print("Computing z-scores...")
    z_scores_df = calculate_z_scores(provider_features_df, peer_stats_df)
    
    print(f"\n=== Feature Computation Complete ===")
    print(f"Provider features: {len(provider_features_df)} providers")
    print(f"Member features: {len(member_features_df)} members")
    print(f"Peer groups: {len(peer_stats_df)}")
    
    # Show network case stats
    net_features = provider_features_df[provider_features_df['provider_id'] == 'P-6610']
    if len(net_features) > 0:
        print(f"\nNetwork case (P-6610) features:")
        print(f"  CPT concentration: {net_features.iloc[0]['top_cpt_concentration']:.2%}")
        print(f"  Referral concentration: {net_features.iloc[0]['referral_concentration']:.2%}")
        print(f"  Total billed: ${net_features.iloc[0]['total_billed']:,.2f}")
    
    return provider_features_df, member_features_df, peer_stats_df, z_scores_df


if __name__ == "__main__":
    from generate_synthetic import generate_all_data
    
    claims_df, providers_df, members_df, _ = generate_all_data()
    
    provider_features_df, member_features_df, peer_stats_df, z_scores_df = compute_all_features(
        claims_df, providers_df, members_df
    )
    
    print("\n=== Top 10 Providers by Total Billed ===")
    print(provider_features_df.nlargest(10, 'total_billed')[['provider_id', 'specialty', 'total_billed', 'top_cpt_concentration']])
