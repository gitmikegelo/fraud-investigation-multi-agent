"""
Add a weak/borderline fraud case directly to fraud_cache.pkl
This case is designed to produce INSUFFICIENT evidence on first investigation.

Provider P-7777 (Pain Management) - Detectable but weak evidence
- HIGH anomaly score (will be detected)
- But WEAK evidence patterns:
  - Only 1-2 evidence points (needs 5+)
  - No clear temporal clustering
  - No network connections (isolated provider)
  - Ambiguous billing - could be legitimate specialty
"""

import pickle
import os
import pandas as pd
from datetime import datetime, timedelta
import random

random.seed(999)  # Different seed for this case

# Weak fraud provider config
WEAK_PROVIDER = "P-7777"
WEAK_FACILITY = "F-9999"
# Very few patients - weak network signal
WEAK_MEMBERS = [f"M-WEAK-{i:02d}" for i in range(1, 4)]  # Only 3 patients

def create_weak_fraud_claims():
    """
    Create a BORDERLINE fraud case that:
    1. HAS high anomaly score (will be detected by scan)
    2. But produces INSUFFICIENT evidence
    
    High anomaly triggers:
    - Very high billing per claim (outlier)
    - High claims_per_patient ratio
    - Weekend billing (unusual)
    
    Weak evidence patterns:
    - No referral network (isolated)
    - Claims spread over many months (no temporal cluster)
    - Only 3 patients (weak sample)
    - Single CPT code concentration (could be specialty)
    """
    claims = []
    claim_counter = 900000  # High number to avoid collision
    
    # Spread claims over 12 months (NO temporal clustering)
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 12, 31)
    
    # High claims per patient but few patients overall
    for member_id in WEAK_MEMBERS:
        # Many claims per patient (triggers claims_per_patient anomaly)
        n_claims = random.randint(12, 15)
        
        for i in range(n_claims):
            claim_counter += 1
            
            # Spread evenly (NO temporal clustering - weak evidence)
            # Each claim roughly 25-30 days apart
            days_offset = int((i / n_claims) * 365) + random.randint(-5, 5)
            days_offset = max(0, min(days_offset, 364))
            service_date = start_date + timedelta(days=days_offset)
            
            # HIGH billing - triggers anomaly detection
            # But use legitimate Pain Management codes (ambiguous)
            cpt_code = "64493"  # Facet joint injection - legitimate for pain mgmt
            
            # Very high billing (3x normal) - definite anomaly trigger
            base = 2500
            billed = round(base * random.uniform(2.8, 3.2), 2)  # $7000-8000 per injection
            paid = round(billed * 0.7, 2)
            
            # Some weekend billing (anomaly flag)
            if random.random() < 0.3:
                # Shift to weekend
                weekday = service_date.weekday()
                if weekday < 5:
                    service_date = service_date + timedelta(days=(5 - weekday))
            
            icd_code = "M54.5"  # Low back pain - legitimate
            
            claims.append({
                "claim_id": f"CLM-{claim_counter}",
                "member_id": member_id,
                "provider_id": WEAK_PROVIDER,
                "referring_provider_id": None,  # NO REFERRALS - weak network evidence
                "facility_id": WEAK_FACILITY,
                "cpt_code": cpt_code,
                "icd_code": icd_code,
                "billed_amount": billed,
                "paid_amount": paid,
                "service_date": service_date,
                "place_of_service": "11",  # Office
                "claim_type": "professional",
            })
    
    return pd.DataFrame(claims)


def main():
    fraud_cache_path = os.path.join(os.path.dirname(__file__), 'fraud_cache.pkl')
    
    # Load existing fraud cache
    if os.path.exists(fraud_cache_path):
        print(f"Loading existing fraud cache: {fraud_cache_path}")
        with open(fraud_cache_path, 'rb') as f:
            fraud_data = pickle.load(f)
        print(f"  - Network claims: {len(fraud_data['network'])}")
        print(f"  - Phantom claims: {len(fraud_data['phantom'])}")
        print(f"  - Shopping claims: {len(fraud_data['shopping'])}")
    else:
        print("No existing fraud cache found. Creating new one.")
        fraud_data = {
            'network': pd.DataFrame(),
            'phantom': pd.DataFrame(),
            'shopping': pd.DataFrame(),
        }
    
    # Create weak fraud case
    print("\nCreating weak fraud case (P-7777)...")
    weak_claims = create_weak_fraud_claims()
    print(f"  - Created {len(weak_claims)} claims")
    print(f"  - Members: {weak_claims['member_id'].unique().tolist()}")
    print(f"  - Total billed: ${weak_claims['billed_amount'].sum():,.2f}")
    print(f"  - Date range: {weak_claims['service_date'].min()} to {weak_claims['service_date'].max()}")
    
    # Add to fraud_data under a new key 'weak'
    fraud_data['weak'] = weak_claims
    
    # Save back
    print(f"\nSaving updated fraud cache...")
    with open(fraud_cache_path, 'wb') as f:
        pickle.dump(fraud_data, f)
    
    print("✅ Done! Weak fraud case added.")
    print("\n⚠️  IMPORTANT: You also need to delete data_cache.pkl to regenerate data:")
    print("    del data_cache.pkl")
    print("    python api.py")
    
    # Print sample
    print("\n=== Sample Weak Fraud Claims ===")
    print(weak_claims.head(10).to_string())


if __name__ == "__main__":
    main()
