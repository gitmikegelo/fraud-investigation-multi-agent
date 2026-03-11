"""
Generates 50 synthetic disability claims: 45 legitimate, 5 suspicious.
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta


@dataclass
class DisabilityPolicy:
    policy_id: str
    claimant_id: str
    claimant_name: str
    claimant_age: int
    occupation: str
    employer: str
    policy_purchase_date: datetime
    monthly_benefit: float
    elimination_period_days: int
    benefit_period_months: int
    annual_premium: float


@dataclass
class DisabilityClaim:
    claim_id: str
    policy: DisabilityPolicy
    claim_filed_date: datetime
    alleged_disability_date: datetime
    disability_type: str
    icd_codes: List[str]
    described_limitations: List[str]
    treating_providers: List[Dict]
    medical_records: List[Dict]
    ime_results: Optional[Dict]
    surveillance_notes: Optional[List[Dict]]
    employer_statement: Optional[Dict]
    prior_claims: List[Dict]
    social_media_flags: List[Dict]
    financial_records: Optional[Dict]
    red_flags: List[str]
    red_flag_score: float
    status: str


FIRST_NAMES = ["James", "Maria", "Robert", "Jennifer", "John", "Patricia", "Michael", "Linda",
               "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
               "Thomas", "Sarah", "Charles", "Karen", "Daniel", "Nancy", "Matthew", "Lisa",
               "Anthony", "Betty", "Mark", "Margaret", "Steven", "Sandra", "Paul", "Ashley",
               "Andrew", "Donna", "Joshua", "Dorothy", "Kenneth", "Kimberly", "Kevin", "Emily",
               "Brian", "Michelle", "Timothy", "Carol", "Ronald", "Amanda", "George", "Melissa",
               "Edward", "Deborah"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
              "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
              "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
              "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
              "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts"]

OCCUPATIONS = ["Software Engineer", "Accountant", "Sales Manager", "Nurse", "Teacher",
               "Construction Worker", "Warehouse Worker", "Office Manager", "Marketing Director",
               "Financial Analyst", "Physical Therapist", "Electrician", "Attorney",
               "Restaurant Manager", "Truck Driver", "Dental Hygienist", "Project Manager",
               "HR Coordinator", "Mechanic", "Graphic Designer"]

EMPLOYERS = ["TechCorp Solutions", "Midwest Manufacturing", "Pacific Health Group",
             "Summit Financial", "Greenfield Construction", "Metro Schools District",
             "Valley Logistics", "Coastal Retail Inc", "Heritage Insurance",
             "National Foods Corp", "Premier Auto Group", "Atlas Energy",
             "Skyline Properties", "Central Medical Center", "United Transport"]

DISABILITY_TYPES = {
    "musculoskeletal": {"weight": 0.40, "icd": ["M54.5", "M51.16", "M47.816", "M75.110"], "limitations": ["Cannot lift >10 lbs", "Cannot sit >30 minutes", "Cannot stand >20 minutes", "Cannot perform repetitive bending"]},
    "mental_health":   {"weight": 0.25, "icd": ["F32.1", "F33.1", "F41.1", "F43.10"],     "limitations": ["Cannot concentrate >15 minutes", "Cannot maintain regular schedule", "Cannot handle workplace stress", "Difficulty with interpersonal interaction"]},
    "neurological":    {"weight": 0.15, "icd": ["G43.909", "G89.29", "G25.0", "R51.9"],   "limitations": ["Frequent severe headaches", "Chronic pain limits all activity", "Tremor prevents fine motor tasks", "Cognitive impairment"]},
    "cardiovascular":  {"weight": 0.10, "icd": ["I25.10", "I50.9", "I10", "I48.91"],       "limitations": ["Cannot exert beyond light activity", "Shortness of breath on exertion", "Must avoid physical stress", "Requires frequent rest"]},
    "other":           {"weight": 0.10, "icd": ["E11.65", "M79.7", "G93.32", "R53.83"],   "limitations": ["Chronic fatigue limits all activity", "Pain prevents sustained focus", "Cannot maintain 8-hour workday", "Requires frequent medical appointments"]},
}

PROVIDER_NAMES = ["Dr. A. Patel", "Dr. S. Kim", "Dr. R. Martinez", "Dr. J. Chen", "Dr. M. Williams",
                  "Dr. L. Thompson", "Dr. K. Okafor", "Dr. B. Sharma", "Dr. T. Nguyen", "Dr. D. Brown",
                  "Dr. P. Anderson", "Dr. H. Lee", "Dr. C. Davis", "Dr. F. Garcia", "Dr. N. Robinson"]

SPECIALTIES = ["Orthopedics", "Psychiatry", "Neurology", "Cardiology", "Pain Management",
               "Physical Medicine", "Internal Medicine", "Family Medicine", "Rheumatology"]


def _rand_date(start: datetime, end: datetime) -> datetime:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 1)))


def _make_policy(idx: int, purchase_date: datetime, monthly_benefit: float = None) -> DisabilityPolicy:
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    age = random.randint(28, 62)
    mb = monthly_benefit or random.choice([2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000])
    return DisabilityPolicy(
        policy_id=f"POL-{2000+idx:04d}",
        claimant_id=f"CLM-{2000+idx:04d}",
        claimant_name=name,
        claimant_age=age,
        occupation=random.choice(OCCUPATIONS),
        employer=random.choice(EMPLOYERS),
        policy_purchase_date=purchase_date,
        monthly_benefit=mb,
        elimination_period_days=random.choice([90, 90, 90, 180]),
        benefit_period_months=random.choice([24, 60, 60]),
        annual_premium=round(mb * 12 * random.uniform(0.02, 0.04), 2),
    )


def _make_medical_records(n: int, providers: List[Dict], disability_type: str, start_date: datetime) -> List[Dict]:
    records = []
    for i in range(n):
        prov = random.choice(providers)
        visit_date = start_date + timedelta(days=random.randint(i * 20, (i + 1) * 30))
        records.append({
            "date": visit_date.strftime("%Y-%m-%d"),
            "provider": prov["provider_name"],
            "summary": f"Patient presents with {disability_type} complaints. "
                       f"Exam consistent with reported symptoms. Continued treatment recommended.",
            "supports_disability": True,
        })
    return records


def _make_treating_providers(n: int) -> List[Dict]:
    chosen = random.sample(PROVIDER_NAMES, min(n, len(PROVIDER_NAMES)))
    return [
        {"provider_name": p, "specialty": random.choice(SPECIALTIES),
         "relationship_months": random.randint(6, 48)}
        for p in chosen
    ]


def _generate_normal_claim(idx: int) -> DisabilityClaim:
    now = datetime(2026, 3, 1)
    purchase_date = _rand_date(now - timedelta(days=1200), now - timedelta(days=365))
    policy = _make_policy(idx, purchase_date)

    # Pick disability type by weight
    types = list(DISABILITY_TYPES.keys())
    weights = [DISABILITY_TYPES[t]["weight"] for t in types]
    dtype = random.choices(types, weights=weights, k=1)[0]
    dinfo = DISABILITY_TYPES[dtype]

    alleged_date = _rand_date(now - timedelta(days=180), now - timedelta(days=30))
    filed_date = alleged_date + timedelta(days=random.randint(7, 30))

    providers = _make_treating_providers(random.randint(2, 4))
    records = _make_medical_records(random.randint(3, 8), providers, dtype, alleged_date)

    red_flags = []
    if random.random() < 0.15:
        red_flags.append("Single treating provider")

    return DisabilityClaim(
        claim_id=f"DC-{2400+idx:04d}",
        policy=policy,
        claim_filed_date=filed_date,
        alleged_disability_date=alleged_date,
        disability_type=dtype,
        icd_codes=random.sample(dinfo["icd"], k=random.randint(1, 2)),
        described_limitations=random.sample(dinfo["limitations"], k=random.randint(2, 3)),
        treating_providers=providers,
        medical_records=records,
        ime_results=None,
        surveillance_notes=None,
        employer_statement={"duties": f"Standard {policy.occupation} duties", "accommodations_offered": random.choice([True, False])},
        prior_claims=[],
        social_media_flags=[],
        financial_records=None,
        red_flags=red_flags,
        red_flag_score=round(random.uniform(0.0, 0.3), 2),
        status="pending",
    )


def _generate_early_filer() -> DisabilityClaim:
    now = datetime(2026, 3, 1)
    purchase_date = now - timedelta(days=120)  # ~4 months ago
    policy = _make_policy(51, purchase_date, monthly_benefit=5500)

    alleged_date = now - timedelta(days=25)
    filed_date = now - timedelta(days=10)

    providers = [{"provider_name": "Dr. T. Nguyen", "specialty": "Pain Management", "relationship_months": 3}]
    records = [
        {"date": (alleged_date + timedelta(days=5)).strftime("%Y-%m-%d"), "provider": "Dr. T. Nguyen",
         "summary": "Patient reports acute lower back pain. Limited exam. Recommend MRI.", "supports_disability": True},
        {"date": (alleged_date + timedelta(days=20)).strftime("%Y-%m-%d"), "provider": "Dr. T. Nguyen",
         "summary": "Follow-up. Patient states pain unchanged. Unable to work. Total disability recommended.", "supports_disability": True},
    ]

    return DisabilityClaim(
        claim_id="DC-2451",
        policy=policy,
        claim_filed_date=filed_date,
        alleged_disability_date=alleged_date,
        disability_type="musculoskeletal",
        icd_codes=["M54.5"],
        described_limitations=["Cannot lift >10 lbs", "Cannot sit >30 minutes", "Cannot stand >20 minutes"],
        treating_providers=providers,
        medical_records=records,
        ime_results=None,
        surveillance_notes=None,
        employer_statement={"duties": "Software Engineer — primarily desk work", "accommodations_offered": False},
        prior_claims=[],
        social_media_flags=[],
        financial_records=None,
        red_flags=[
            "Policy purchased less than 6 months before claim",
            "Single treating physician with brief relationship",
            "No conservative treatment history documented",
            "Claimed disability onset within elimination period",
        ],
        red_flag_score=0.82,
        status="under_investigation",
    )


def _generate_activity_inconsistent() -> DisabilityClaim:
    now = datetime(2026, 3, 1)
    purchase_date = now - timedelta(days=730)
    policy = _make_policy(52, purchase_date, monthly_benefit=4500)
    policy.occupation = "Sales Manager"

    alleged_date = datetime(2025, 12, 1)
    filed_date = datetime(2025, 12, 15)

    providers = _make_treating_providers(2)
    records = _make_medical_records(5, providers, "musculoskeletal", alleged_date)

    return DisabilityClaim(
        claim_id="DC-2452",
        policy=policy,
        claim_filed_date=filed_date,
        alleged_disability_date=alleged_date,
        disability_type="musculoskeletal",
        icd_codes=["M54.5", "M51.16"],
        described_limitations=["Cannot sit >30 minutes", "Cannot lift >10 lbs", "Cannot perform repetitive bending"],
        treating_providers=providers,
        medical_records=records,
        ime_results={"date": "2026-01-20", "physician": "Dr. Independent", "opinion": "Moderate limitation, not total disability", "functional_capacity": "Sedentary with restrictions"},
        surveillance_notes=None,
        employer_statement={"duties": "Sales Manager — desk + travel", "accommodations_offered": False,
                            "notes": "Claimant was placed on PIP 2 weeks before disability claim filed"},
        prior_claims=[],
        social_media_flags=[
            {"date": "2026-01-15", "platform": "Instagram", "content": "Summit trail completed! 8 miles"},
            {"date": "2026-02-02", "platform": "Facebook", "content": "Great day at the slopes with family"},
        ],
        financial_records=None,
        red_flags=[
            "Social media activity inconsistent with claimed limitations",
            "Performance improvement plan preceded claim filing",
            "Claimed limitations (no sitting >30min) contradict documented activities",
        ],
        red_flag_score=0.88,
        status="under_investigation",
    )


def _generate_friendly_doctor() -> DisabilityClaim:
    now = datetime(2026, 3, 1)
    purchase_date = now - timedelta(days=900)
    policy = _make_policy(53, purchase_date, monthly_benefit=4000)

    alleged_date = datetime(2025, 6, 15)
    filed_date = datetime(2025, 7, 1)

    shared_doc = {"provider_name": "Dr. R. Martinez", "specialty": "Pain Management", "relationship_months": 10}
    providers = [shared_doc, {"provider_name": "Dr. A. Patel", "specialty": "Internal Medicine", "relationship_months": 24}]
    records = [
        {"date": "2025-06-20", "provider": "Dr. R. Martinez", "summary": "Patient presents with chronic pain syndrome. Functional capacity severely limited. Total disability.", "supports_disability": True},
        {"date": "2025-07-15", "provider": "Dr. R. Martinez", "summary": "Patient unable to perform any occupational duties. Continued total disability.", "supports_disability": True},
        {"date": "2025-08-20", "provider": "Dr. R. Martinez", "summary": "No improvement. Maximum disability persists. Patient cannot work in any capacity.", "supports_disability": True},
        {"date": "2025-10-01", "provider": "Dr. R. Martinez", "summary": "Ongoing total disability. No referral to specialist needed per patient preference.", "supports_disability": True},
        {"date": "2025-06-25", "provider": "Dr. A. Patel", "summary": "Mild chronic pain noted. Recommend conservative treatment and PT.", "supports_disability": False},
    ]

    return DisabilityClaim(
        claim_id="DC-2453",
        policy=policy,
        claim_filed_date=filed_date,
        alleged_disability_date=alleged_date,
        disability_type="other",
        icd_codes=["M79.7", "R53.83"],
        described_limitations=["Chronic fatigue limits all activity", "Pain prevents sustained focus", "Cannot maintain 8-hour workday"],
        treating_providers=providers,
        medical_records=records,
        ime_results=None,
        surveillance_notes=None,
        employer_statement={"duties": "Accountant — desk work", "accommodations_offered": True, "notes": "Offered ergonomic workstation, claimant declined"},
        prior_claims=[],
        social_media_flags=[],
        financial_records=None,
        red_flags=[
            "Treating physician supports 3 other active disability claims",
            "Clinical notes 94% similar across different patients",
            "Documentation supports maximum disability for mild-moderate condition",
            "No referral to specialist despite 8+ month disability duration",
        ],
        red_flag_score=0.78,
        status="under_investigation",
    )


def _generate_serial_claimant() -> DisabilityClaim:
    now = datetime(2026, 3, 1)
    purchase_date = now - timedelta(days=540)
    policy = _make_policy(54, purchase_date, monthly_benefit=5000)

    alleged_date = datetime(2025, 10, 1)
    filed_date = datetime(2025, 10, 20)

    providers = _make_treating_providers(2)
    records = _make_medical_records(4, providers, "other", alleged_date)

    return DisabilityClaim(
        claim_id="DC-2454",
        policy=policy,
        claim_filed_date=filed_date,
        alleged_disability_date=alleged_date,
        disability_type="other",
        icd_codes=["M79.7", "G93.32"],
        described_limitations=["Chronic fatigue limits all activity", "Cannot maintain 8-hour workday", "Pain prevents sustained focus"],
        treating_providers=providers,
        medical_records=records,
        ime_results={"date": "2025-12-15", "physician": "Dr. Independent B", "opinion": "Subjective complaints exceed objective findings", "functional_capacity": "Light to medium work"},
        surveillance_notes=None,
        employer_statement={"duties": "Project Manager — desk + meetings", "accommodations_offered": False},
        prior_claims=[
            {"carrier": "MetLife", "year": 2019, "duration_months": 24, "diagnosis": "Depression", "outcome": "Benefits exhausted"},
            {"carrier": "Prudential", "year": 2021, "duration_months": 12, "diagnosis": "Anxiety", "outcome": "Returned to work at max benefit"},
            {"carrier": "Lincoln", "year": 2023, "duration_months": 18, "diagnosis": "Chronic fatigue", "outcome": "Benefits exhausted"},
        ],
        social_media_flags=[],
        financial_records=None,
        red_flags=[
            "3 prior disability claims across 2 carriers in 7 years",
            "Each prior claim lasted until benefit period exhaustion",
            "Current diagnosis (fibromyalgia) is new but follows same pattern",
            "Returned to work within 30 days of each benefit exhaustion",
        ],
        red_flag_score=0.91,
        status="under_investigation",
    )


def _generate_financial_motive() -> DisabilityClaim:
    now = datetime(2026, 3, 1)
    purchase_date = now - timedelta(days=1095)
    policy = _make_policy(55, purchase_date, monthly_benefit=8200)
    policy.occupation = "Business Owner"

    alleged_date = datetime(2025, 12, 10)
    filed_date = datetime(2025, 12, 22)

    providers = _make_treating_providers(2)
    records = _make_medical_records(4, providers, "mental_health", alleged_date)

    return DisabilityClaim(
        claim_id="DC-2455",
        policy=policy,
        claim_filed_date=filed_date,
        alleged_disability_date=alleged_date,
        disability_type="mental_health",
        icd_codes=["F32.1", "F41.1"],
        described_limitations=["Cannot concentrate >15 minutes", "Cannot handle workplace stress", "Cannot maintain regular schedule"],
        treating_providers=providers,
        medical_records=records,
        ime_results={"date": "2026-01-30", "physician": "Dr. Independent C", "opinion": "Moderate depression, functional capacity higher than treating MD suggests", "functional_capacity": "Sedentary work with accommodations"},
        surveillance_notes=None,
        employer_statement=None,
        prior_claims=[],
        social_media_flags=[],
        financial_records={"business_name": "Summit Consulting LLC", "dissolved_date": "2025-12-01",
                           "last_tax_return_income": 72000, "monthly_benefit_requested": 8200,
                           "notes": "LLC dissolved 3 weeks before claim filed"},
        red_flags=[
            "Business (LLC) dissolved 3 weeks before claim filed",
            "Monthly benefit exceeds most recent documented income",
            "Disability timing coincides with financial hardship",
            "IME physician rates functional capacity higher than treating physician",
        ],
        red_flag_score=0.85,
        status="under_investigation",
    )


def generate_disability_data() -> List[DisabilityClaim]:
    random.seed(42)
    claims = []

    # 45 normal claims
    for i in range(45):
        claims.append(_generate_normal_claim(i))

    # 5 suspicious
    claims.append(_generate_early_filer())
    claims.append(_generate_activity_inconsistent())
    claims.append(_generate_friendly_doctor())
    claims.append(_generate_serial_claimant())
    claims.append(_generate_financial_motive())

    return claims
