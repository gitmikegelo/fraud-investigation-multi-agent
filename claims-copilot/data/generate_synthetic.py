"""
Synthetic data generator for Prudential Life Insurance Investigation Copilot.
Generates policies, agents, policyholders, transactions with fraud patterns.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple
import random
import os

np.random.seed(42)
random.seed(42)

REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
PRODUCT_TYPES = ["Term Life", "Whole Life", "Universal Life", "Variable Life", "Indexed UL"]
BENEFIT_TIERS = [100_000, 250_000, 500_000, 750_000, 1_000_000, 2_000_000, 5_000_000]

FIRST_NAMES = [
    "James", "Maria", "Robert", "Jennifer", "John", "Patricia", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson", "Thomas",
]
OCCUPATIONS = [
    "Software Engineer", "Accountant", "Sales Manager", "Nurse", "Teacher",
    "Attorney", "Physician", "Business Owner", "Retired", "Executive",
]

MIB_CODES = {
    "001": "Hypertension", "002": "Diabetes", "003": "Heart Disease",
    "004": "Cancer History", "005": "Depression/Anxiety", "006": "Substance Abuse",
    "007": "Obesity", "008": "Asthma/COPD", "009": "Liver Disease",
}

RX_CATEGORIES = {
    "antihypertensive": ["Lisinopril", "Amlodipine", "Losartan"],
    "diabetes": ["Metformin", "Glipizide", "Insulin"],
    "cardiac": ["Atorvastatin", "Clopidogrel", "Warfarin"],
    "psychiatric": ["Sertraline", "Fluoxetine", "Alprazolam"],
    "pain": ["Oxycodone", "Tramadol", "Gabapentin"],
}

NET_PRIMARY = "AGT-0042"
NET_AGENTS = ["AGT-0042", "AGT-0043", "AGT-0044", "AGT-0045", "AGT-0046"]


def _rand_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def _rand_date(start, end):
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 1)))


def generate_agents(n=200):
    rows = []
    for i in range(n):
        rows.append({
            "agent_id": f"AGT-{i:04d}",
            "agent_name": _rand_name(),
            "region": random.choice(REGIONS),
            "license_state": random.choice(["NY", "NJ", "CA", "TX", "FL", "IL", "PA", "OH"]),
            "tenure_years": random.randint(1, 30),
            "agency": f"Agency-{random.randint(1, 50):03d}",
            "complaints": random.randint(0, 3),
            "active": True,
        })
    return pd.DataFrame(rows)


def generate_policyholders(n=3000):
    rows = []
    for i in range(n):
        rows.append({
            "policyholder_id": f"PH-{i:04d}",
            "name": _rand_name(),
            "age": random.randint(25, 75),
            "gender": random.choice(["M", "F"]),
            "state": random.choice(["NY", "NJ", "CA", "TX", "FL", "IL", "PA", "OH"]),
            "occupation": random.choice(OCCUPATIONS),
            "income": random.randint(40000, 500000),
            "smoker": random.random() < 0.15,
        })
    return pd.DataFrame(rows)


def generate_policies(agents_df, policyholders_df, n=5000):
    now = datetime(2026, 3, 1)
    rows = []
    for i in range(n):
        ph = policyholders_df.iloc[random.randint(0, len(policyholders_df) - 1)]
        agent = agents_df.iloc[random.randint(0, len(agents_df) - 1)]
        face = random.choice(BENEFIT_TIERS)
        issue_date = _rand_date(now - timedelta(days=2500), now - timedelta(days=30))
        premium = round(face * random.uniform(0.005, 0.025) / 12, 2)
        disclosed = []
        if random.random() < 0.3:
            disclosed = random.sample(list(MIB_CODES.values()), k=random.randint(1, 2))
        rows.append({
            "policy_id": f"POL-{i:04d}",
            "policyholder_id": ph["policyholder_id"],
            "policyholder_name": ph["name"],
            "agent_id": agent["agent_id"],
            "product_type": random.choice(PRODUCT_TYPES),
            "face_amount": face,
            "monthly_premium": premium,
            "issue_date": issue_date,
            "contestability_end": issue_date + timedelta(days=730),
            "status": "active",
            "disclosed_conditions": disclosed,
            "beneficiary": _rand_name(),
            "trust_owned": random.random() < 0.05,
            "premium_financed": False,
        })
    return pd.DataFrame(rows)


def generate_transactions(policies_df, n_per_policy=6):
    now = datetime(2026, 3, 1)
    rows = []
    for _, pol in policies_df.iterrows():
        n_months = min(n_per_policy, max(1, (now - pol["issue_date"]).days // 30))
        for m in range(n_months):
            pay_date = pol["issue_date"] + timedelta(days=30 * (m + 1))
            if pay_date > now:
                break
            rows.append({
                "txn_id": f"TXN-{len(rows):06d}",
                "policy_id": pol["policy_id"],
                "txn_type": "premium_payment",
                "amount": pol["monthly_premium"],
                "txn_date": pay_date,
                "source": "policyholder",
                "flagged": False,
            })
    return pd.DataFrame(rows)


def generate_mib_records(policyholders_df):
    rows = []
    for _, ph in policyholders_df.iterrows():
        if random.random() < 0.4:
            for code in random.sample(list(MIB_CODES.keys()), k=random.randint(1, 3)):
                rows.append({
                    "policyholder_id": ph["policyholder_id"],
                    "mib_code": code,
                    "condition": MIB_CODES[code],
                    "report_date": _rand_date(datetime(2020, 1, 1), datetime(2025, 12, 31)),
                    "reporting_carrier": random.choice(["MetLife", "AIG", "Lincoln", "Hartford"]),
                })
    return pd.DataFrame(rows)


def generate_rx_history(policyholders_df):
    rows = []
    for _, ph in policyholders_df.iterrows():
        if random.random() < 0.5:
            for cat in random.sample(list(RX_CATEGORIES.keys()), k=random.randint(1, 3)):
                rows.append({
                    "policyholder_id": ph["policyholder_id"],
                    "medication": random.choice(RX_CATEGORIES[cat]),
                    "category": cat,
                    "first_fill": _rand_date(datetime(2019, 1, 1), datetime(2025, 6, 1)),
                    "last_fill": _rand_date(datetime(2025, 6, 1), datetime(2026, 2, 28)),
                })
    return pd.DataFrame(rows)


def generate_claims(policies_df, n=500):
    now = datetime(2026, 3, 1)
    rows = []
    for i in range(n):
        pol = policies_df.iloc[random.randint(0, len(policies_df) - 1)]
        claim_date = _rand_date(pol["issue_date"] + timedelta(days=60), now)
        rows.append({
            "claim_id": f"CLM-{i:04d}",
            "policy_id": pol["policy_id"],
            "policyholder_id": pol["policyholder_id"],
            "agent_id": pol["agent_id"],
            "claim_type": random.choice(["death", "accelerated_benefit", "waiver_of_premium"]),
            "claim_date": claim_date,
            "face_amount": pol["face_amount"],
            "cause": random.choice(["natural", "accident", "illness", "unknown"]),
            "status": random.choice(["pending", "approved", "denied", "under_investigation"]),
            "within_contestability": claim_date <= pol["contestability_end"],
        })
    return pd.DataFrame(rows)


# ============================================================================
# FRAUD INJECTION
# ============================================================================

def inject_stoli_scheme(policies_df, agents_df, transactions_df):
    now = datetime(2026, 3, 1)
    trust_beneficiary = "Meridian Trust Holdings LLC"
    financing_entity = "Pacific Premium Finance Corp"
    stoli_policies = []
    for i, agt_id in enumerate(NET_AGENTS):
        for j in range(3):
            idx = len(policies_df) + len(stoli_policies)
            issue_date = _rand_date(now - timedelta(days=400), now - timedelta(days=100))
            face = random.choice([2_000_000, 5_000_000])
            stoli_policies.append({
                "policy_id": f"POL-S{idx:04d}",
                "policyholder_id": f"PH-S{idx:04d}",
                "policyholder_name": _rand_name(),
                "agent_id": agt_id,
                "product_type": "Universal Life",
                "face_amount": face,
                "monthly_premium": round(face * 0.02 / 12, 2),
                "issue_date": issue_date,
                "contestability_end": issue_date + timedelta(days=730),
                "status": "active",
                "disclosed_conditions": [],
                "beneficiary": trust_beneficiary,
                "trust_owned": True,
                "premium_financed": True,
            })
    stoli_df = pd.DataFrame(stoli_policies)
    policies_df = pd.concat([policies_df, stoli_df], ignore_index=True)

    stoli_txns = []
    for _, pol in stoli_df.iterrows():
        for m in range(4):
            stoli_txns.append({
                "txn_id": f"TXN-S{len(transactions_df) + len(stoli_txns):06d}",
                "policy_id": pol["policy_id"],
                "txn_type": "premium_payment",
                "amount": pol["monthly_premium"],
                "txn_date": pol["issue_date"] + timedelta(days=30 * (m + 1)),
                "source": financing_entity,
                "flagged": True,
            })
    transactions_df = pd.concat([transactions_df, pd.DataFrame(stoli_txns)], ignore_index=True)
    return policies_df, transactions_df


def inject_aml_scheme(policies_df, transactions_df):
    now = datetime(2026, 3, 1)
    aml_txns = []
    for i in range(5):
        pol = policies_df.iloc[random.randint(0, len(policies_df) - 1)]
        aml_txns.append({
            "txn_id": f"TXN-A{len(transactions_df) + len(aml_txns):06d}",
            "policy_id": pol["policy_id"],
            "txn_type": "lump_sum_premium",
            "amount": random.choice([95000, 98000, 99000, 97500]),
            "txn_date": _rand_date(now - timedelta(days=180), now - timedelta(days=30)),
            "source": "wire_transfer",
            "flagged": True,
        })
        aml_txns.append({
            "txn_id": f"TXN-A{len(transactions_df) + len(aml_txns):06d}",
            "policy_id": pol["policy_id"],
            "txn_type": "surrender",
            "amount": random.choice([85000, 88000, 92000]),
            "txn_date": _rand_date(now - timedelta(days=29), now),
            "source": "policyholder",
            "flagged": True,
        })
    transactions_df = pd.concat([transactions_df, pd.DataFrame(aml_txns)], ignore_index=True)
    return transactions_df


def inject_agent_misconduct(policies_df, agents_df):
    now = datetime(2026, 3, 1)
    churn = []
    for i in range(8):
        idx = len(policies_df) + len(churn)
        issue_date = _rand_date(now - timedelta(days=300), now - timedelta(days=30))
        churn.append({
            "policy_id": f"POL-C{idx:04d}",
            "policyholder_id": f"PH-{random.randint(0, 500):04d}",
            "policyholder_name": _rand_name(),
            "agent_id": NET_PRIMARY,
            "product_type": random.choice(["Universal Life", "Variable Life"]),
            "face_amount": random.choice([500_000, 1_000_000, 2_000_000]),
            "monthly_premium": round(random.uniform(500, 3000), 2),
            "issue_date": issue_date,
            "contestability_end": issue_date + timedelta(days=730),
            "status": "active",
            "disclosed_conditions": [],
            "beneficiary": _rand_name(),
            "trust_owned": False,
            "premium_financed": False,
        })
    policies_df = pd.concat([policies_df, pd.DataFrame(churn)], ignore_index=True)
    return policies_df


def generate_all_data():
    """Returns: (policies_df, agents_df, policyholders_df, transactions_df, claims_df, mib_df, rx_df)"""
    print("  Generating agents...")
    agents_df = generate_agents(200)
    print(f"  → {len(agents_df)} agents")

    print("  Generating policyholders...")
    policyholders_df = generate_policyholders(3000)
    print(f"  → {len(policyholders_df)} policyholders")

    print("  Generating policies...")
    policies_df = generate_policies(agents_df, policyholders_df, 5000)
    print(f"  → {len(policies_df)} policies")

    print("  Generating transactions...")
    transactions_df = generate_transactions(policies_df)
    print(f"  → {len(transactions_df)} transactions")

    print("  Generating MIB records...")
    mib_df = generate_mib_records(policyholders_df)
    print(f"  → {len(mib_df)} MIB records")

    print("  Generating Rx history...")
    rx_df = generate_rx_history(policyholders_df)
    print(f"  → {len(rx_df)} prescriptions")

    print("  Generating claims...")
    claims_df = generate_claims(policies_df, 500)
    print(f"  → {len(claims_df)} claims")

    print("  Injecting STOLI scheme...")
    policies_df, transactions_df = inject_stoli_scheme(policies_df, agents_df, transactions_df)

    print("  Injecting AML patterns...")
    transactions_df = inject_aml_scheme(policies_df, transactions_df)

    print("  Injecting agent misconduct...")
    policies_df = inject_agent_misconduct(policies_df, agents_df)

    print(f"  ✅ Final: {len(policies_df)} policies, {len(transactions_df)} txns, {len(claims_df)} claims")
    return policies_df, agents_df, policyholders_df, transactions_df, claims_df, mib_df, rx_df
