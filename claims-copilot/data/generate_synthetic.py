"""
Synthetic data generator for Claims Investigation Copilot.
Generates 50K claims with 95% normal patterns and 5% fraud.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple
import random

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

# ============================================================================
# CONFIGURATION
# ============================================================================

SPECIALTIES = [
    "Orthopedic Surgery", "Cardiology", "Internal Medicine", "Family Medicine",
    "Dermatology", "Neurology", "Oncology", "Gastroenterology", "Pulmonology",
    "Rheumatology", "Endocrinology", "Nephrology", "Urology", "Pain Management"
]

REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]

# CPT codes by specialty (realistic distribution)
CPT_BY_SPECIALTY = {
    "Orthopedic Surgery": {
        "27447": 0.23,  # Total knee replacement
        "27130": 0.15,  # Hip replacement
        "29881": 0.20,  # Knee arthroscopy
        "27446": 0.12,  # Knee revision
        "20610": 0.15,  # Joint injection
        "99213": 0.10,  # Office visit
        "99214": 0.05,  # Office visit complex
    },
    "Cardiology": {
        "93000": 0.25,  # ECG
        "93306": 0.20,  # Echocardiogram
        "93458": 0.15,  # Cardiac cath
        "99214": 0.20,  # Office visit
        "99215": 0.10,  # Office visit high complexity
        "93010": 0.10,  # ECG interpretation
    },
    "Internal Medicine": {
        "99213": 0.35,  # Office visit
        "99214": 0.30,  # Office visit extended
        "99215": 0.10,  # Office visit high complexity
        "36415": 0.15,  # Blood draw
        "80053": 0.10,  # Comprehensive metabolic panel
    },
    "Family Medicine": {
        "99213": 0.40,
        "99214": 0.25,
        "99215": 0.05,
        "36415": 0.15,
        "90471": 0.15,  # Immunization admin
    },
    "Pain Management": {
        "64493": 0.25,  # Facet joint injection
        "62322": 0.20,  # Epidural injection
        "20610": 0.15,  # Joint injection
        "99214": 0.20,
        "99215": 0.10,
        "64635": 0.10,  # Nerve destruction
    },
}

# Default CPT distribution for other specialties
DEFAULT_CPT = {
    "99213": 0.35, "99214": 0.30, "99215": 0.15,
    "36415": 0.10, "80053": 0.10
}

# ICD codes mapped to CPT codes (simplified)
ICD_BY_CPT = {
    "27447": ["M17.11", "M17.12", "M17.0"],  # Knee osteoarthritis
    "27130": ["M16.11", "M16.12", "M16.0"],  # Hip osteoarthritis
    "29881": ["M23.20", "M23.21", "S83.20"],  # Meniscus tear
    "93306": ["I25.10", "I50.9", "R00.0"],   # Heart conditions
    "64493": ["M54.5", "M54.16", "M47.816"], # Back pain
}
DEFAULT_ICD = ["R69", "Z00.00", "Z12.31"]

PLACES_OF_SERVICE = ["11", "22", "23", "24", "31"]  # Office, Outpatient, ASC, etc.
CLAIM_TYPES = ["professional", "institutional"]

# Billing amounts by CPT (mean, std)
BILLING_AMOUNTS = {
    "27447": (45000, 8000),   # Knee replacement
    "27130": (42000, 7500),   # Hip replacement
    "29881": (8500, 1500),    # Knee arthroscopy
    "93306": (1200, 300),     # Echo
    "93458": (15000, 3000),   # Cardiac cath
    "64493": (2500, 500),     # Facet injection
    "99213": (120, 30),       # Office visit
    "99214": (180, 40),       # Extended visit
    "99215": (250, 50),       # Complex visit
}
DEFAULT_BILLING = (150, 50)

# ============================================================================
# CARDIOLOGY NETWORK CASE CONFIGURATION
# A subtle multi-provider kickback/unbundling scheme across 5 providers.
# Designed so initial investigation is likely deemed INSUFFICIENT, forcing
# the agent loop to go back and gather more evidence.
# ============================================================================

NET_PROVIDERS = ["P-6610", "P-6620", "P-6630", "P-6640", "P-6650"]
NET_PRIMARY = "P-6610"  # Cardiology – elevated cardiac cath billing
NET_SECONDARY = "P-6640"  # Cardiology – elevated echo billing
NET_REFERRERS = ["P-6620", "P-6630", "P-6650"]  # IM / FM / Pulm referrers
NET_MEMBERS = [f"M-NET-{i:02d}" for i in range(1, 9)]  # 8 shared patients
NET_FACILITY = "F-8801"

# ============================================================================
# DATA GENERATORS
# ============================================================================

def generate_providers(n: int = 500) -> pd.DataFrame:
    """Generate provider master data."""
    providers = []
    
    # Add cardiology network providers (all in same region)
    net_specs = {
        "P-6610": "Cardiology",
        "P-6620": "Internal Medicine",
        "P-6630": "Family Medicine",
        "P-6640": "Cardiology",
        "P-6650": "Pulmonology",
    }
    
    for pid, specialty in net_specs.items():
        region = "Southeast"  # Network all in same region
        providers.append({
            "provider_id": pid,
            "specialty": specialty,
            "region": region,
            "peer_group": f"{specialty}_{region}",
        })
    
    # Add weak fraud case provider (isolated, no network)
    providers.append({
        "provider_id": "P-7777",
        "specialty": "Pain Management",
        "region": "West",  # Different region - isolated
        "peer_group": "Pain Management_West",
    })
    
    # Generate remaining providers
    existing_ids = set(NET_PROVIDERS) | {"P-7777"}
    for i in range(n - len(NET_PROVIDERS) - 1):  # -1 for P-7777
        while True:
            pid = f"P-{random.randint(1000, 9999)}"
            if pid not in existing_ids:
                existing_ids.add(pid)
                break
        
        specialty = random.choice(SPECIALTIES)
        region = random.choice(REGIONS)
        providers.append({
            "provider_id": pid,
            "specialty": specialty,
            "region": region,
            "peer_group": f"{specialty}_{region}",
        })
    
    return pd.DataFrame(providers)


def generate_members(n: int = 5000) -> pd.DataFrame:
    """Generate member master data."""
    members = []
    
    # First add cardiology network members (older patients with cardiac conditions)
    for mid in NET_MEMBERS:
        members.append({
            "member_id": mid,
            "age": random.randint(58, 78),
            "gender": random.choice(["M", "F"]),
            "region": "Southeast",
        })
    
    # Add weak fraud case members (chronic pain patients)
    weak_members = ["M-WEAK-01", "M-WEAK-02", "M-WEAK-03"]
    for mid in weak_members:
        members.append({
            "member_id": mid,
            "age": random.randint(40, 65),
            "gender": random.choice(["M", "F"]),
            "region": "West",
        })
    
    # Generate remaining members
    existing_ids = set(NET_MEMBERS) | set(weak_members)
    for i in range(n - len(NET_MEMBERS) - len(weak_members)):  # account for weak members
        while True:
            mid = f"M-{random.randint(10000, 99999)}"
            if mid not in existing_ids:
                existing_ids.add(mid)
                break
        
        members.append({
            "member_id": mid,
            "age": random.randint(18, 85),
            "gender": random.choice(["M", "F"]),
            "region": random.choice(REGIONS),
        })
    
    return pd.DataFrame(members)


def generate_facilities(n: int = 100) -> pd.DataFrame:
    """Generate facility master data."""
    facilities = []
    
    # Cardiology network facility first
    facilities.append({
        "facility_id": NET_FACILITY,
        "facility_type": "Hospital",
        "region": "Southeast",
    })
    
    # Weak fraud case facility
    facilities.append({
        "facility_id": "F-9999",
        "facility_type": "Ambulatory Surgery Center",
        "region": "West",
    })
    
    # Generate remaining facilities
    existing_ids = {NET_FACILITY, "F-9999"}
    for i in range(n - 2):  # -2 for the two pre-defined facilities
        while True:
            fid = f"F-{random.randint(1000, 9999)}"
            if fid not in existing_ids:
                existing_ids.add(fid)
                break
        
        facilities.append({
            "facility_id": fid,
            "facility_type": random.choice(["Hospital", "ASC", "Clinic", "Office"]),
            "region": random.choice(REGIONS),
        })
    
    return pd.DataFrame(facilities)


def get_cpt_for_provider(specialty: str, is_fraud: bool = False, fraud_role: str = None) -> str:
    """Get CPT code based on specialty distribution."""
    cpt_dist = CPT_BY_SPECIALTY.get(specialty, DEFAULT_CPT)
    
    if is_fraud and fraud_role == 'net_primary' and specialty == 'Cardiology':
        # Network primary: cardiac cath at ~55% (vs peer ~15%)
        if random.random() < 0.55:
            return "93458"
    elif is_fraud and fraud_role == 'net_secondary' and specialty == 'Cardiology':
        # Network secondary: echo at ~45% (vs peer ~20%)
        if random.random() < 0.45:
            return "93306"
    
    codes = list(cpt_dist.keys())
    probs = list(cpt_dist.values())
    return np.random.choice(codes, p=probs)


def get_icd_for_cpt(cpt_code: str) -> str:
    """Get appropriate ICD code for CPT."""
    icds = ICD_BY_CPT.get(cpt_code, DEFAULT_ICD)
    return random.choice(icds)


def get_billing_amount(cpt_code: str, is_fraud: bool = False) -> Tuple[float, float]:
    """Get billed and paid amounts."""
    mean, std = BILLING_AMOUNTS.get(cpt_code, DEFAULT_BILLING)
    
    if is_fraud:
        # Fraudulent claims bill moderately higher (25%)
        mean *= 1.25
    
    billed = max(50, np.random.normal(mean, std))
    # Payment ratio varies (insurance pays portion)
    paid = billed * random.uniform(0.65, 0.85)
    
    return round(billed, 2), round(paid, 2)


def generate_normal_claims(
    providers_df: pd.DataFrame,
    members_df: pd.DataFrame,
    facilities_df: pd.DataFrame,
    n_claims: int = 47500,
    start_date: datetime = None,
    end_date: datetime = None
) -> pd.DataFrame:
    """Generate normal (non-fraudulent) claims."""
    
    if start_date is None:
        start_date = datetime(2025, 1, 1)
    if end_date is None:
        end_date = datetime(2026, 2, 1)
    
    date_range = (end_date - start_date).days
    
    # Exclude network case entities from normal generation
    normal_providers = providers_df[~providers_df['provider_id'].isin(NET_PROVIDERS)]
    normal_members = members_df[~members_df['member_id'].isin(NET_MEMBERS)]
    normal_facilities = facilities_df[facilities_df['facility_id'] != NET_FACILITY]
    
    claims = []
    
    for i in range(n_claims):
        # Pick random provider
        provider = normal_providers.sample(1).iloc[0]
        provider_id = provider['provider_id']
        specialty = provider['specialty']
        region = provider['region']
        
        # Pick member from same region (more realistic)
        region_members = normal_members[normal_members['region'] == region]
        if len(region_members) < 10:
            region_members = normal_members
        member = region_members.sample(1).iloc[0]
        
        # Pick facility
        region_facilities = normal_facilities[normal_facilities['region'] == region]
        if len(region_facilities) < 1:
            region_facilities = normal_facilities
        facility = region_facilities.sample(1).iloc[0]
        
        # Random referral (30% of claims have referrals)
        referring_provider_id = None
        if random.random() < 0.30:
            # Referrals typically come from primary care
            ref_candidates = normal_providers[
                normal_providers['specialty'].isin(['Internal Medicine', 'Family Medicine'])
            ]
            if len(ref_candidates) > 0:
                referring_provider_id = ref_candidates.sample(1).iloc[0]['provider_id']
        
        # Generate claim details
        cpt_code = get_cpt_for_provider(specialty)
        icd_code = get_icd_for_cpt(cpt_code)
        billed, paid = get_billing_amount(cpt_code)
        
        # Service date
        service_date = start_date + timedelta(days=random.randint(0, date_range))
        
        claims.append({
            "claim_id": f"CLM-{i:06d}",
            "member_id": member['member_id'],
            "provider_id": provider_id,
            "referring_provider_id": referring_provider_id,
            "facility_id": facility['facility_id'],
            "cpt_code": cpt_code,
            "icd_code": icd_code,
            "billed_amount": billed,
            "paid_amount": paid,
            "service_date": service_date,
            "place_of_service": random.choice(PLACES_OF_SERVICE),
            "claim_type": random.choice(CLAIM_TYPES),
        })
    
    return pd.DataFrame(claims)


def generate_network_case_claims(
    start_date: datetime = None,
    end_date: datetime = None
) -> pd.DataFrame:
    """
    Generate the cardiology network case: Kickback & unbundling scheme.
    
    5 interconnected providers sharing 8 patients:
      P-6610 (Cardiology)  - bills cardiac cath (93458) at ~55% vs peer 15%
      P-6620 (IM)          - referrer A, gradual shift to P-6610
      P-6630 (FM)          - referrer B, gradual shift to P-6610
      P-6640 (Cardiology)  - elevated echo (93306) billing, shared patients
      P-6650 (Pulmonology) - peripheral, shares patients with P-6610 & P-6640
    
    The scheme is SUBTLE:
      - Moderate billing elevation (~25% above peers, not 115%)
      - Gradual referral shift over 10 months (not sudden)
      - Only 8 shared patients (not 12)
      - Total billed ~$600-800K (not $2.3M)
    
    This subtlety means the first investigation pass is likely to be
    deemed INSUFFICIENT, forcing the agent loop to go back.
    """
    if start_date is None:
        start_date = datetime(2025, 1, 1)
    if end_date is None:
        end_date = datetime(2026, 2, 1)
    
    # Referral shift was gradual starting ~10 months ago
    shift_start = end_date - timedelta(days=300)
    
    claims = []
    claim_counter = 900000
    
    # ----------------------------------------------------------------
    # 1) P-6610 (primary target): Cardiac cath claims for shared members
    # ----------------------------------------------------------------
    for member_id in NET_MEMBERS:
        # Each member gets 2-4 claims with P-6610
        n_claims = random.randint(2, 4)
        for _ in range(n_claims):
            claim_counter += 1
            referrer = random.choice(NET_REFERRERS)
            
            # Service date gradually shifts - older claims have less concentration
            days_offset = random.randint(0, (end_date - shift_start).days)
            service_date = shift_start + timedelta(days=days_offset)
            
            cpt_code = get_cpt_for_provider("Cardiology", is_fraud=True,
                                             fraud_role='net_primary')
            icd_code = get_icd_for_cpt(cpt_code)
            billed, paid = get_billing_amount(cpt_code, is_fraud=True)
            
            claims.append({
                "claim_id": f"CLM-{claim_counter}",
                "member_id": member_id,
                "provider_id": NET_PRIMARY,
                "referring_provider_id": referrer,
                "facility_id": NET_FACILITY,
                "cpt_code": cpt_code,
                "icd_code": icd_code,
                "billed_amount": billed,
                "paid_amount": paid,
                "service_date": service_date,
                "place_of_service": "22",  # Outpatient hospital
                "claim_type": "institutional",
            })
    
    # ----------------------------------------------------------------
    # 2) P-6640 (secondary): Echo & office visits for shared members
    # ----------------------------------------------------------------
    for member_id in NET_MEMBERS:
        n_claims = random.randint(1, 3)
        for _ in range(n_claims):
            claim_counter += 1
            # P-6640 sometimes refers patients TO P-6610 as well
            referrer = random.choice([NET_PRIMARY, None, None])
            
            days_offset = random.randint(0, (end_date - shift_start).days)
            service_date = shift_start + timedelta(days=days_offset)
            
            cpt_code = get_cpt_for_provider("Cardiology", is_fraud=True,
                                             fraud_role='net_secondary')
            icd_code = get_icd_for_cpt(cpt_code)
            billed, paid = get_billing_amount(cpt_code, is_fraud=True)
            
            claims.append({
                "claim_id": f"CLM-{claim_counter}",
                "member_id": member_id,
                "provider_id": NET_SECONDARY,
                "referring_provider_id": referrer,
                "facility_id": NET_FACILITY,
                "cpt_code": cpt_code,
                "icd_code": icd_code,
                "billed_amount": billed,
                "paid_amount": paid,
                "service_date": service_date,
                "place_of_service": "22",
                "claim_type": "institutional",
            })
    
    # ----------------------------------------------------------------
    # 3) Referrer claims (P-6620 IM, P-6630 FM, P-6650 Pulm)
    #    These providers see the shared patients for office visits and
    #    refer them to P-6610. They also see some non-shared patients.
    # ----------------------------------------------------------------
    referrer_specs = {
        "P-6620": "Internal Medicine",
        "P-6630": "Family Medicine",
        "P-6650": "Pulmonology",
    }
    
    for ref_id, ref_spec in referrer_specs.items():
        # Office visits for shared patients (with referral to P-6610)
        for member_id in NET_MEMBERS:
            n_claims = random.randint(1, 2)
            for _ in range(n_claims):
                claim_counter += 1
                days_offset = random.randint(0, (end_date - shift_start).days)
                service_date = shift_start + timedelta(days=days_offset)
                
                cpt_code = get_cpt_for_provider(ref_spec)
                icd_code = get_icd_for_cpt(cpt_code)
                billed, paid = get_billing_amount(cpt_code)
                
                claims.append({
                    "claim_id": f"CLM-{claim_counter}",
                    "member_id": member_id,
                    "provider_id": ref_id,
                    "referring_provider_id": None,
                    "facility_id": NET_FACILITY,
                    "cpt_code": cpt_code,
                    "icd_code": icd_code,
                    "billed_amount": billed,
                    "paid_amount": paid,
                    "service_date": service_date,
                    "place_of_service": "11",  # Office
                    "claim_type": "professional",
                })
    
    # ----------------------------------------------------------------
    # 4) Historical referrals BEFORE the shift (to show pattern change)
    #    Before shift: referrers sent patients to various cardiologists.
    #    After shift: gradually concentrated on P-6610.
    # ----------------------------------------------------------------
    for referrer in NET_REFERRERS:
        # Pre-shift: distributed referrals to random cardiologists
        for _ in range(random.randint(6, 10)):
            claim_counter += 1
            days_before = random.randint(30, 280)
            service_date = shift_start - timedelta(days=days_before)
            
            other_cardio = f"P-{random.randint(1000, 9999)}"
            cpt_code = random.choice(["93000", "93306", "93458", "99214"])
            icd_code = get_icd_for_cpt(cpt_code)
            billed, paid = get_billing_amount(cpt_code)
            
            claims.append({
                "claim_id": f"CLM-{claim_counter}",
                "member_id": f"M-{random.randint(10000, 99999)}",
                "provider_id": other_cardio,
                "referring_provider_id": referrer,
                "facility_id": f"F-{random.randint(1000, 9999)}",
                "cpt_code": cpt_code,
                "icd_code": icd_code,
                "billed_amount": billed,
                "paid_amount": paid,
                "service_date": service_date,
                "place_of_service": random.choice(PLACES_OF_SERVICE),
                "claim_type": random.choice(CLAIM_TYPES),
            })
    
    # ----------------------------------------------------------------
    # 5) Cross-referral between P-6640 and P-6610 (bi-directional)
    #    Strengthens the network connections.
    # ----------------------------------------------------------------
    for _ in range(random.randint(4, 8)):
        claim_counter += 1
        member_id = random.choice(NET_MEMBERS)
        days_offset = random.randint(0, (end_date - shift_start).days)
        service_date = shift_start + timedelta(days=days_offset)
        
        # P-6640 refers to P-6610
        cpt_code = "93458"  # Cardiac cath
        icd_code = get_icd_for_cpt(cpt_code)
        billed, paid = get_billing_amount(cpt_code, is_fraud=True)
        
        claims.append({
            "claim_id": f"CLM-{claim_counter}",
            "member_id": member_id,
            "provider_id": NET_PRIMARY,
            "referring_provider_id": NET_SECONDARY,
            "facility_id": NET_FACILITY,
            "cpt_code": cpt_code,
            "icd_code": icd_code,
            "billed_amount": billed,
            "paid_amount": paid,
            "service_date": service_date,
            "place_of_service": "22",
            "claim_type": "institutional",
        })
    
    # Also P-6610 refers back to P-6640 for follow-up echos
    for _ in range(random.randint(3, 6)):
        claim_counter += 1
        member_id = random.choice(NET_MEMBERS)
        days_offset = random.randint(0, (end_date - shift_start).days)
        service_date = shift_start + timedelta(days=days_offset)
        
        cpt_code = "93306"  # Echo
        icd_code = get_icd_for_cpt(cpt_code)
        billed, paid = get_billing_amount(cpt_code, is_fraud=True)
        
        claims.append({
            "claim_id": f"CLM-{claim_counter}",
            "member_id": member_id,
            "provider_id": NET_SECONDARY,
            "referring_provider_id": NET_PRIMARY,
            "facility_id": NET_FACILITY,
            "cpt_code": cpt_code,
            "icd_code": icd_code,
            "billed_amount": billed,
            "paid_amount": paid,
            "service_date": service_date,
            "place_of_service": "22",
            "claim_type": "institutional",
        })
    
    return pd.DataFrame(claims)


def generate_phantom_billing_claims() -> pd.DataFrame:
    """
    Secondary fraud case: Phantom billing.
    1 provider billing for services never rendered to 8 members.
    Total: ~$89,000
    """
    phantom_provider = "P-7799"
    phantom_members = [f"M-PHANTOM-{i}" for i in range(1, 9)]
    
    claims = []
    claim_counter = 800000
    
    for member_id in phantom_members:
        # Each "patient" gets 3-5 fake claims
        for _ in range(random.randint(3, 5)):
            claim_counter += 1
            
            # Varies CPT to avoid detection
            cpt_code = random.choice(["99214", "99215", "36415", "80053"])
            icd_code = random.choice(DEFAULT_ICD)
            billed, paid = get_billing_amount(cpt_code)
            
            # Spread over time
            service_date = datetime(2025, 6, 1) + timedelta(days=random.randint(0, 200))
            
            claims.append({
                "claim_id": f"CLM-{claim_counter}",
                "member_id": member_id,
                "provider_id": phantom_provider,
                "referring_provider_id": None,
                "facility_id": f"F-{random.randint(1000, 9999)}",
                "cpt_code": cpt_code,
                "icd_code": icd_code,
                "billed_amount": billed * 3,  # Inflated
                "paid_amount": paid * 2.5,
                "service_date": service_date,
                "place_of_service": "11",  # Office
                "claim_type": "professional",
            })
    
    return pd.DataFrame(claims)


def generate_doctor_shopping_claims() -> pd.DataFrame:
    """
    Secondary fraud case: Doctor shopping.
    5 members visiting 8+ providers for controlled substances.
    Total: ~$67,000
    """
    shopping_members = [f"M-SHOP-{i}" for i in range(1, 6)]
    pain_providers = [f"P-PAIN-{i}" for i in range(1, 9)]
    
    claims = []
    claim_counter = 700000
    
    for member_id in shopping_members:
        # Each shopper visits multiple providers
        providers_visited = random.sample(pain_providers, random.randint(5, 8))
        
        for provider_id in providers_visited:
            # Multiple visits to each
            for _ in range(random.randint(2, 4)):
                claim_counter += 1
                
                cpt_code = random.choice(["64493", "62322", "20610", "99214"])
                icd_code = random.choice(["M54.5", "M54.16", "G89.29"])
                billed, paid = get_billing_amount(cpt_code)
                
                service_date = datetime(2025, 3, 1) + timedelta(days=random.randint(0, 300))
                
                claims.append({
                    "claim_id": f"CLM-{claim_counter}",
                    "member_id": member_id,
                    "provider_id": provider_id,
                    "referring_provider_id": None,
                    "facility_id": f"F-{random.randint(1000, 9999)}",
                    "cpt_code": cpt_code,
                    "icd_code": icd_code,
                    "billed_amount": billed,
                    "paid_amount": paid,
                    "service_date": service_date,
                    "place_of_service": "11",
                    "claim_type": "professional",
                })
    
    return pd.DataFrame(claims)


def generate_all_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Generate all synthetic data.
    
    Fraud cases (network, phantom, doctor shopping) are generated ONCE and
    persisted to ``fraud_cache.pkl``.  Only the normal claims are regenerated
    on each call.
    
    Returns:
        claims_df, providers_df, members_df, facilities_df
    """
    import os, pickle
    
    fraud_cache = os.path.join(os.path.dirname(__file__), '..', 'fraud_cache.pkl')
    fraud_cache = os.path.normpath(fraud_cache)
    
    print("Generating providers...")
    providers_df = generate_providers(500)
    
    print("Generating members...")
    members_df = generate_members(5000)
    
    print("Generating facilities...")
    facilities_df = generate_facilities(100)
    
    print("Generating normal claims (~47.5K)...")
    normal_claims = generate_normal_claims(
        providers_df, members_df, facilities_df, n_claims=47500
    )
    
    # --- Fraud claims: load from cache or generate once ---
    if os.path.exists(fraud_cache):
        print("Loading fraud cases from cache (not regenerating)...")
        with open(fraud_cache, 'rb') as f:
            fraud_data = pickle.load(f)
        network_claims = fraud_data['network']
        phantom_claims = fraud_data['phantom']
        shopping_claims = fraud_data['shopping']
        # Load weak fraud case if it exists (added manually)
        weak_claims = fraud_data.get('weak', pd.DataFrame())
        if len(weak_claims) > 0:
            print(f"  - Loaded weak fraud case: {len(weak_claims)} claims (P-7777)")
    else:
        weak_claims = pd.DataFrame()
        print("Generating cardiology network claims (kickback scheme)...")
        network_claims = generate_network_case_claims()
        
        print("Generating phantom billing claims...")
        phantom_claims = generate_phantom_billing_claims()
        
        print("Generating doctor shopping claims...")
        shopping_claims = generate_doctor_shopping_claims()
        
        # Persist fraud claims so they are never regenerated
        print(f"💾 Saving fraud cases to {fraud_cache}...")
        with open(fraud_cache, 'wb') as f:
            pickle.dump({
                'network': network_claims,
                'phantom': phantom_claims,
                'shopping': shopping_claims,
            }, f)
    
    # Combine all claims (including weak fraud case if present)
    all_fraud_dfs = [normal_claims, network_claims, phantom_claims, shopping_claims]
    if len(weak_claims) > 0:
        all_fraud_dfs.append(weak_claims)
    claims_df = pd.concat(all_fraud_dfs, ignore_index=True)
    
    # Convert service_date to datetime
    claims_df['service_date'] = pd.to_datetime(claims_df['service_date'])
    
    # Sort by date
    claims_df = claims_df.sort_values('service_date').reset_index(drop=True)
    
    print(f"\n=== Data Generation Complete ===")
    print(f"Providers: {len(providers_df)}")
    print(f"Members: {len(members_df)}")
    print(f"Facilities: {len(facilities_df)}")
    print(f"Claims: {len(claims_df)}")
    print(f"Total billed: ${claims_df['billed_amount'].sum():,.2f}")
    
    # Verify network case
    net_claims_check = claims_df[claims_df['provider_id'] == NET_PRIMARY]
    print(f"\nNetwork case ({NET_PRIMARY}) claims: {len(net_claims_check)}")
    print(f"Network case total billed: ${net_claims_check['billed_amount'].sum():,.2f}")
    
    return claims_df, providers_df, members_df, facilities_df


if __name__ == "__main__":
    claims_df, providers_df, members_df, facilities_df = generate_all_data()
    
    # Quick validation
    print("\n=== Sample Claims ===")
    print(claims_df[claims_df['provider_id'] == NET_PRIMARY].head(10))
