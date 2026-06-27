"""Generate 500 supplemental health claims with embedded fraud scenarios and false positives."""

import random
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta


# ── Entity Dataclasses ───────────────────────────────────────────────────────

@dataclass
class Employer:
    employer_id: str
    name: str
    industry: str
    employee_count: int
    state: str
    group_number: str


@dataclass
class Member:
    member_id: str
    first_name: str
    last_name: str
    dob: str
    gender: str
    employer_id: str
    hire_date: str
    termination_date: Optional[str] = None
    address_id: Optional[str] = None
    suspicious_banner: bool = False
    notes: str = ""

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


@dataclass
class Dependent:
    dependent_id: str
    member_id: str
    first_name: str
    last_name: str
    relationship: str
    dob: str
    gender: str
    address_id: Optional[str] = None


@dataclass
class Provider:
    provider_id: str
    name: str
    npi: str
    specialty: str
    facility_id: Optional[str] = None
    state: str = ""
    is_mill: bool = False
    claims_volume: int = 0


@dataclass
class Facility:
    facility_id: str
    name: str
    type: str  # hospital, clinic, urgent_care, surgery_center
    state: str
    is_rural: bool = False
    releasepoint_enrolled: bool = False
    known_ehr_system: Optional[str] = None


@dataclass
class Address:
    address_id: str
    street: str
    city: str
    state: str
    zip_code: str
    is_shared: bool = False


@dataclass
class Policy:
    policy_id: str
    member_id: str
    plan_type: str  # wellness, accident, hospital_indemnity, critical_illness
    effective_date: str
    termination_date: Optional[str] = None
    status: str = "active"
    coverage_amount: float = 0.0
    premium: float = 0.0
    beneficiary_change_date: Optional[str] = None
    owner_change_date: Optional[str] = None


@dataclass
class DocumentMetadata:
    doc_id: str
    claim_id: str
    doc_type: str  # medical_record, receipt, invoice, discharge_summary, operative_report
    provider_name: str
    date_of_service: str
    received_date: str
    has_header: bool = True
    has_signature: bool = True
    has_date: bool = True
    format_type: str = "digital"  # digital, fax, scan
    resolution: str = "standard"  # standard, low, high
    metadata_hash: str = ""
    duplicate_of: Optional[str] = None
    tampering_indicators: List[str] = field(default_factory=list)
    # New SCHEMA fields
    source_type: str = "PROVIDER_PORTAL"  # RELEASEPOINT | PROVIDER_PORTAL | PROVIDER_FAX | MEMBER_UPLOAD_PDF | MOBILE_SCAN | UNKNOWN
    font_consistency_score: float = 1.0   # 0.0 - 1.0
    alignment_score: float = 1.0          # 0.0 - 1.0
    color_consistency_score: float = 1.0  # 0.0 - 1.0
    header_content_match: bool = True
    metadata_app_signature: Optional[str] = None  # "CamScanner", "Adobe Scan", etc.
    releasepoint_status: str = "NOT_REQUESTED"  # NOT_REQUESTED | REQUESTED | NOT_YET_PRINTED | RECORDS_RECEIVED | CONFIRMED_MATCH | CONFIRMED_DISCREPANT
    releasepoint_request_id: Optional[str] = None  # "RP 15751837"


@dataclass
class WorkflowTask:
    task_id: str
    claim_id: str
    task_type: str  # INITIAL_REVIEW, MEDICAL_RECORD_REQUEST, PMR, CBR
    status: str = "pending"  # pending, in_progress, completed, overdue
    assigned_date: Optional[str] = None
    due_date: Optional[str] = None
    completed_date: Optional[str] = None
    days_waiting: int = 0
    notes: str = ""


@dataclass
class Claim:
    claim_id: str
    claim_type: str
    member_id: str
    dependent_id: Optional[str] = None
    provider_id: str = ""
    facility_id: Optional[str] = None
    policy_id: str = ""
    date_filed: str = ""
    date_of_service: str = ""
    date_of_loss: Optional[str] = None
    diagnosis_codes: List[str] = field(default_factory=list)
    procedure_codes: List[str] = field(default_factory=list)
    claim_amount: float = 0.0
    approved_amount: float = 0.0
    status: str = "new"
    claim_source: str = "company_site"
    employer_id: str = ""
    fraud_scenario: Optional[str] = None
    false_positive_scenario: Optional[str] = None
    notes: str = ""
    contact_count: int = 1
    is_resubmission: bool = False
    original_claim_id: Optional[str] = None
    # New SCHEMA fields
    benefit_type: str = ""               # HOSPITAL_ADMISSION | HOSPITAL_CONFINEMENT | URGENT_CARE_VISIT | etc.
    relationship_type: str = "SELF"      # SELF | POLICYHOLDER | BENEFICIARY | INSURED
    batch_claim_id: Optional[str] = None # Groups related stacked claims
    stacked_with: List[str] = field(default_factory=list)
    related_claim_ids: List[str] = field(default_factory=list)


# ── Name / Data Pools ────────────────────────────────────────────────────────

FIRST_NAMES_M = ["James", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas",
                 "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Donald",
                 "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian", "George",
                 "Timothy", "Ronald", "Edward", "Jason", "Jeffrey", "Ryan", "Jacob"]

FIRST_NAMES_F = ["Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
                 "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra",
                 "Ashley", "Dorothy", "Kimberly", "Emily", "Donna", "Michelle", "Carol",
                 "Amanda", "Melissa", "Deborah", "Stephanie", "Rebecca", "Sharon", "Laura", "Cynthia"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
              "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
              "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
              "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen",
              "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera"]

STATES = ["NJ", "NY", "CT", "PA", "CA", "TX", "FL", "IL", "OH", "GA", "NC", "VA", "MA", "AZ", "WA"]

CITIES = {
    "NJ": ["Newark", "Jersey City", "Trenton", "Edison", "Woodbridge"],
    "NY": ["New York", "Buffalo", "Rochester", "Albany", "Syracuse"],
    "CT": ["Hartford", "New Haven", "Stamford", "Bridgeport", "Waterbury"],
    "PA": ["Philadelphia", "Pittsburgh", "Allentown", "Erie", "Reading"],
    "CA": ["Los Angeles", "San Francisco", "San Diego", "Sacramento", "San Jose"],
    "TX": ["Houston", "Dallas", "Austin", "San Antonio", "Fort Worth"],
    "FL": ["Miami", "Orlando", "Tampa", "Jacksonville", "Fort Lauderdale"],
    "IL": ["Chicago", "Springfield", "Naperville", "Rockford", "Peoria"],
    "OH": ["Columbus", "Cleveland", "Cincinnati", "Toledo", "Akron"],
    "GA": ["Atlanta", "Savannah", "Augusta", "Columbus", "Macon"],
    "NC": ["Charlotte", "Raleigh", "Durham", "Greensboro", "Winston-Salem"],
    "VA": ["Richmond", "Virginia Beach", "Norfolk", "Arlington", "Alexandria"],
    "MA": ["Boston", "Worcester", "Springfield", "Cambridge", "Lowell"],
    "AZ": ["Phoenix", "Tucson", "Mesa", "Chandler", "Scottsdale"],
    "WA": ["Seattle", "Tacoma", "Spokane", "Vancouver", "Bellevue"],
}

STREETS = ["Main St", "Oak Ave", "Elm St", "Pine Rd", "Maple Dr", "Cedar Ln", "Birch Way",
           "Park Ave", "Church St", "Washington Blvd", "Lincoln Ave", "Highland Dr",
           "Forest Rd", "Valley View", "Sunset Blvd", "River Rd", "Lake Dr", "Hill St"]

EMPLOYERS = [
    ("Meridian Technologies", "Technology", "NJ", 4500),
    ("Summit Healthcare Group", "Healthcare", "NY", 3200),
    ("Coastal Manufacturing Inc", "Manufacturing", "CT", 2800),
    ("Pinnacle Financial Services", "Finance", "PA", 5100),
    ("Atlas Logistics Corp", "Logistics", "TX", 3800),
    ("Greenfield Energy Solutions", "Energy", "CA", 2200),
    ("Hawthorne Education Systems", "Education", "FL", 1900),
    ("Sterling Retail Holdings", "Retail", "IL", 6200),
    ("Ironbridge Construction", "Construction", "OH", 1500),
    ("Pacific Wellness Partners", "Healthcare", "WA", 2700),
]

SPECIALTIES = ["Internal Medicine", "Family Practice", "Orthopedics", "Cardiology",
               "Oncology", "Neurology", "General Surgery", "Emergency Medicine",
               "Physical Therapy", "Dermatology", "Radiology", "Psychiatry"]

FACILITY_NAMES = [
    ("Regional Medical Center", "hospital"), ("Community Hospital", "hospital"),
    ("University Health System", "hospital"), ("Memorial Hospital", "hospital"),
    ("City General Hospital", "hospital"),
    ("Valley Clinic", "clinic"), ("Parkside Medical Group", "clinic"),
    ("Downtown Urgent Care", "urgent_care"), ("Express Care Center", "urgent_care"),
    ("Midtown Surgery Center", "surgery_center"), ("Outpatient Surgical Associates", "surgery_center"),
    ("Mountain View Clinic", "clinic"), ("Harbor Health Clinic", "clinic"),
    ("Lakeside Medical Practice", "clinic"), ("Rural Health Center", "clinic"),
]

DIAGNOSIS_CODES = {
    "wellness": ["Z00.00", "Z00.01", "Z01.1", "Z01.30", "Z01.31", "Z13.220", "Z13.6"],
    "accident": ["S42.001A", "S52.501A", "S82.001A", "S62.101A", "S92.001A",
                  "S06.0X0A", "S13.4XXA", "S43.401A", "S83.511A", "T14.90"],
    "hospital_indemnity": ["I21.3", "I63.9", "J18.9", "K35.80", "K80.00",
                            "N20.0", "J96.00", "A41.9", "I50.9", "M54.5"],
    "critical_illness": ["C34.90", "C50.919", "I21.3", "I63.9", "C18.9",
                          "C61", "G35", "N18.6", "I42.0", "C71.9"],
}

PROCEDURE_CODES = {
    "wellness": ["99395", "99396", "99397", "36415", "80061", "G0438"],
    "accident": ["29881", "27447", "23472", "28292", "64721", "99283", "99284"],
    "hospital_indemnity": ["43239", "47562", "33533", "27447", "99291", "99223"],
    "critical_illness": ["38241", "32480", "33533", "61510", "50360", "77386"],
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _seed():
    random.seed(42)


def _rand_date(start_str: str, end_str: str) -> str:
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    delta = (end - start).days
    if delta <= 0:
        return start_str
    return (start + timedelta(days=random.randint(0, delta))).strftime("%Y-%m-%d")


def _rand_dob(min_age=22, max_age=68):
    today = datetime(2026, 3, 15)
    age = random.randint(min_age, max_age)
    dob = today - timedelta(days=age * 365 + random.randint(0, 364))
    return dob.strftime("%Y-%m-%d")


def _rand_child_dob():
    return _rand_dob(min_age=1, max_age=25)


def _rand_gender():
    return random.choice(["M", "F"])


def _rand_name(gender):
    first = random.choice(FIRST_NAMES_M if gender == "M" else FIRST_NAMES_F)
    last = random.choice(LAST_NAMES)
    return first, last


def _claim_amount(claim_type):
    ranges = {
        "wellness": (75, 500),
        "accident": (500, 15000),
        "hospital_indemnity": (1000, 50000),
        "critical_illness": (5000, 100000),
    }
    lo, hi = ranges.get(claim_type, (100, 5000))
    return round(random.uniform(lo, hi), 2)


def _pick_source(weights):
    sources = list(weights.keys())
    w = list(weights.values())
    return random.choices(sources, weights=w, k=1)[0]


# ── Generate All Entities ────────────────────────────────────────────────────

def _generate_employers() -> List[Employer]:
    employers = []
    for i, (name, industry, state, count) in enumerate(EMPLOYERS):
        employers.append(Employer(
            employer_id=f"EMP-{i+1:03d}",
            name=name,
            industry=industry,
            employee_count=count,
            state=state,
            group_number=f"GRP-{random.randint(100000, 999999)}",
        ))
    return employers


def _generate_addresses(count: int, shared_count: int = 15) -> List[Address]:
    addresses = []
    for i in range(count):
        state = random.choice(STATES)
        city = random.choice(CITIES[state])
        addresses.append(Address(
            address_id=f"ADDR-{i+1:04d}",
            street=f"{random.randint(1, 9999)} {random.choice(STREETS)}",
            city=city,
            state=state,
            zip_code=f"{random.randint(10000, 99999)}",
            is_shared=(i < shared_count),
        ))
    return addresses


def _generate_members(count: int, employers: List[Employer], addresses: List[Address]) -> List[Member]:
    members = []
    for i in range(count):
        gender = _rand_gender()
        first, last = _rand_name(gender)
        emp = random.choice(employers)
        addr = random.choice(addresses[:150])  # Most members get unique-ish addresses
        hire_date = _rand_date("2018-01-01", "2025-12-31")
        term_date = None
        if random.random() < 0.08:
            term_date = _rand_date(hire_date, "2026-03-15")

        members.append(Member(
            member_id=f"MBR-{i+1:04d}",
            first_name=first,
            last_name=last,
            dob=_rand_dob(),
            gender=gender,
            employer_id=emp.employer_id,
            hire_date=hire_date,
            termination_date=term_date,
            address_id=addr.address_id,
        ))
    return members


def _generate_dependents(members: List[Member], addresses: List[Address]) -> List[Dependent]:
    dependents = []
    dep_id = 1
    for member in members:
        num_deps = random.choices([0, 1, 2, 3, 4], weights=[0.3, 0.25, 0.25, 0.15, 0.05], k=1)[0]
        for j in range(num_deps):
            gender = _rand_gender()
            first, last = _rand_name(gender)
            rel = random.choice(["spouse", "child", "child", "child"])
            dob = _rand_child_dob() if rel == "child" else _rand_dob(min_age=22, max_age=65)
            dependents.append(Dependent(
                dependent_id=f"DEP-{dep_id:04d}",
                member_id=member.member_id,
                first_name=first,
                last_name=last if random.random() < 0.7 else member.last_name,
                relationship=rel,
                dob=dob,
                gender=gender,
                address_id=member.address_id,
            ))
            dep_id += 1
    return dependents


def _generate_providers(count: int, facilities: List[Facility]) -> List[Provider]:
    providers = []
    for i in range(count):
        gender = _rand_gender()
        first, last = _rand_name(gender)
        fac = random.choice(facilities) if random.random() < 0.7 else None
        providers.append(Provider(
            provider_id=f"PRV-{i+1:03d}",
            name=f"Dr. {first} {last}",
            npi=f"{random.randint(1000000000, 9999999999)}",
            specialty=random.choice(SPECIALTIES),
            facility_id=fac.facility_id if fac else None,
            state=fac.state if fac else random.choice(STATES),
        ))
    return providers


def _generate_facilities() -> List[Facility]:
    EHR_SYSTEMS = ["Epic", "Cerner", "Meditech", "CPSI", None]
    facilities = []
    for i, (name, ftype) in enumerate(FACILITY_NAMES):
        state = random.choice(STATES)
        is_rural = (i >= 12)
        # Hospitals and urgent care that are not rural are enrolled in ReleasePoint
        rp_enrolled = ftype in ("hospital", "urgent_care") and not is_rural
        facilities.append(Facility(
            facility_id=f"FAC-{i+1:03d}",
            name=name,
            type=ftype,
            state=state,
            is_rural=is_rural,
            releasepoint_enrolled=rp_enrolled,
            known_ehr_system=random.choice(EHR_SYSTEMS) if rp_enrolled else None,
        ))
    return facilities


def _generate_policies(members: List[Member]) -> List[Policy]:
    policies = []
    pol_id = 1
    for member in members:
        num_policies = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15], k=1)[0]
        plan_types_used = set()
        for _ in range(num_policies):
            plan_type = random.choice(["wellness", "accident", "hospital_indemnity", "critical_illness"])
            if plan_type in plan_types_used:
                continue
            plan_types_used.add(plan_type)

            coverage_amounts = {
                "wellness": random.choice([500, 1000, 2000]),
                "accident": random.choice([5000, 10000, 25000, 50000]),
                "hospital_indemnity": random.choice([100, 200, 500]),  # per day
                "critical_illness": random.choice([10000, 25000, 50000, 100000]),
            }
            premiums = {
                "wellness": random.uniform(10, 40),
                "accident": random.uniform(15, 60),
                "hospital_indemnity": random.uniform(20, 80),
                "critical_illness": random.uniform(25, 100),
            }

            eff_date = _rand_date("2020-01-01", "2025-12-01")
            policies.append(Policy(
                policy_id=f"POL-{pol_id:04d}",
                member_id=member.member_id,
                plan_type=plan_type,
                effective_date=eff_date,
                status="active" if not member.termination_date else "terminated",
                coverage_amount=coverage_amounts[plan_type],
                premium=round(premiums[plan_type], 2),
            ))
            pol_id += 1
    return policies


# ── Claim Generation ─────────────────────────────────────────────────────────

def _distribute_dates_across_business_days(count: int) -> List[str]:
    """Distribute claims across ~20 business days ending on 2026-03-15."""
    end_date = datetime(2026, 3, 15)
    business_days = []
    d = end_date
    while len(business_days) < 22:
        if d.weekday() < 5:
            business_days.append(d)
        d -= timedelta(days=1)
    business_days.reverse()

    dates = []
    for _ in range(count):
        day = random.choice(business_days)
        dates.append(day.strftime("%Y-%m-%d"))
    return dates


def _generate_base_claims(
    members: List[Member],
    dependents: List[Dependent],
    providers: List[Provider],
    facilities: List[Facility],
    policies: List[Policy],
    employers: List[Employer],
    source_weights: Dict[str, float],
) -> List[Claim]:
    """Generate 500 base claims distributed across claim types."""
    claims = []
    claim_counts = {"wellness": 250, "accident": 100, "hospital_indemnity": 100, "critical_illness": 50}
    prefixes = {"wellness": "WC", "accident": "AC", "hospital_indemnity": "HI", "critical_illness": "CI"}

    # Pre-build member->policy mapping
    member_policies = {}
    for p in policies:
        member_policies.setdefault(p.member_id, []).append(p)

    member_deps = {}
    for dep in dependents:
        member_deps.setdefault(dep.member_id, []).append(dep)

    member_employer = {}
    for m in members:
        member_employer[m.member_id] = m.employer_id

    filing_dates = _distribute_dates_across_business_days(500)
    random.shuffle(filing_dates)

    idx = 0
    for claim_type, count in claim_counts.items():
        prefix = prefixes[claim_type]
        type_id = 1
        for _ in range(count):
            member = random.choice(members)
            # Try to find matching policy
            matching_policies = [p for p in member_policies.get(member.member_id, []) if p.plan_type == claim_type]
            if not matching_policies:
                # Use any policy
                matching_policies = member_policies.get(member.member_id, [])
            if not matching_policies:
                continue

            policy = random.choice(matching_policies)
            provider = random.choice(providers)
            facility = random.choice(facilities) if random.random() < 0.6 else None

            # Dependent claim?
            dep = None
            deps = member_deps.get(member.member_id, [])
            if deps and random.random() < 0.3:
                dep = random.choice(deps)

            date_filed = filing_dates[idx % len(filing_dates)]
            dos = _rand_date("2025-12-01", date_filed) if date_filed > "2025-12-01" else date_filed

            claims.append(Claim(
                claim_id=f"{prefix}-{type_id:03d}",
                claim_type=claim_type,
                member_id=member.member_id,
                dependent_id=dep.dependent_id if dep else None,
                provider_id=provider.provider_id,
                facility_id=facility.facility_id if facility else None,
                policy_id=policy.policy_id,
                date_filed=date_filed,
                date_of_service=dos,
                diagnosis_codes=random.sample(DIAGNOSIS_CODES.get(claim_type, ["Z00.00"]), k=min(2, len(DIAGNOSIS_CODES.get(claim_type, ["Z00.00"])))),
                procedure_codes=random.sample(PROCEDURE_CODES.get(claim_type, ["99395"]), k=min(2, len(PROCEDURE_CODES.get(claim_type, ["99395"])))),
                claim_amount=_claim_amount(claim_type),
                claim_source=_pick_source(source_weights),
                employer_id=member_employer.get(member.member_id, ""),
                contact_count=random.choices([1, 2, 3, 4, 5], weights=[0.5, 0.25, 0.15, 0.07, 0.03], k=1)[0],
            ))
            type_id += 1
            idx += 1
    return claims


# ── Fraud Scenarios ──────────────────────────────────────────────────────────

def _inject_fraud_scenarios(
    claims: List[Claim],
    members: List[Member],
    dependents: List[Dependent],
    providers: List[Provider],
    policies: List[Policy],
    addresses: List[Address],
) -> None:
    """Modify existing claims + entities to embed 10 fraud scenarios."""

    member_deps = {}
    for dep in dependents:
        member_deps.setdefault(dep.member_id, []).append(dep)

    # Scenario 1: 35 Dependents — WC-247
    # Find or create the mega-dependent member
    target_member = members[0]
    target_member.suspicious_banner = True
    target_member.notes = "FRAUD_SCENARIO: 35 dependents filed under single member"
    # Add extra dependents to this member
    existing_deps = member_deps.get(target_member.member_id, [])
    dep_id_start = len(dependents) + 1
    shared_addr = addresses[0]  # Shared address for fraud ring
    while len(existing_deps) < 35:
        gender = _rand_gender()
        first, last = _rand_name(gender)
        new_dep = Dependent(
            dependent_id=f"DEP-{dep_id_start:04d}",
            member_id=target_member.member_id,
            first_name=first,
            last_name=target_member.last_name,
            relationship=random.choice(["child", "spouse", "child"]),
            dob=_rand_child_dob(),
            gender=gender,
            address_id=shared_addr.address_id,
        )
        dependents.append(new_dep)
        existing_deps.append(new_dep)
        dep_id_start += 1

    # Tag WC-247
    wc247 = next((c for c in claims if c.claim_id == "WC-247"), None)
    if wc247:
        wc247.member_id = target_member.member_id
        wc247.fraud_scenario = "35_dependents"
        wc247.claim_amount = 12500.00
        wc247.notes = "35 dependents under single member — dependent abuse pattern"

    # Scenario 2: Termination Rush — multiple claims filed right before termination
    term_member = members[5]
    term_member.termination_date = "2026-03-20"
    term_member.notes = "FRAUD_SCENARIO: Termination rush filing"
    rush_claims = [c for c in claims if c.claim_type == "wellness" and c.fraud_scenario is None][:3]
    for i, rc in enumerate(rush_claims[:3]):
        rc.member_id = term_member.member_id
        rc.fraud_scenario = "termination_rush"
        rc.date_filed = "2026-03-14"
        rc.claim_amount = _claim_amount("wellness") * 2
        rc.notes = f"Filed {3-i} days before termination date"
        rc.employer_id = term_member.employer_id

    # Scenario 3: Owner/Beneficiary Change — policy ownership changed recently + large claim
    owner_member = members[10]
    owner_member.notes = "FRAUD_SCENARIO: Recent policy ownership change"
    owner_policies = [p for p in policies if p.member_id == owner_member.member_id]
    if owner_policies:
        owner_policies[0].owner_change_date = "2026-02-01"
        owner_policies[0].beneficiary_change_date = "2026-02-01"
    ci_claims = [c for c in claims if c.claim_type == "critical_illness" and c.fraud_scenario is None]
    if ci_claims:
        ci_claims[0].member_id = owner_member.member_id
        ci_claims[0].fraud_scenario = "owner_change"
        ci_claims[0].claim_amount = 95000.00
        ci_claims[0].notes = "Policy ownership changed 6 weeks before critical illness claim"
        # Wire the policy correctly
        if owner_policies:
            ci_claims[0].policy_id = owner_policies[0].policy_id

    # Scenario 4: Fabricated Accident — accident claim with no matching facility records
    acc_claims = [c for c in claims if c.claim_type == "accident"]
    if len(acc_claims) > 5:
        acc_claims[5].fraud_scenario = "fabricated_accident"
        acc_claims[5].facility_id = None
        acc_claims[5].claim_amount = 12000.00
        acc_claims[5].date_of_loss = acc_claims[5].date_of_service
        acc_claims[5].notes = "No facility record matches; accident report inconsistencies"

    # Scenario 5: Provider Mill — single provider with excessive claims (55+)
    mill_provider = providers[0]
    mill_provider.is_mill = True
    mill_provider.claims_volume = 85
    mill_provider.notes = "FRAUD_SCENARIO: Provider mill — excessive claims volume"
    # Assign 55 wellness claims to this provider so R-006 triggers
    mill_candidates = [c for c in claims if c.claim_type == "wellness" and c.fraud_scenario is None]
    for mc in mill_candidates[:55]:
        mc.provider_id = mill_provider.provider_id
        mc.fraud_scenario = "provider_mill"
        mc.notes = f"Provider {mill_provider.name} flagged as potential mill"

    # Scenario 6: Tampered Records — documents with metadata anomalies
    tamper_claims = [c for c in claims if c.claim_type == "hospital_indemnity"][:2]
    for tc in tamper_claims:
        tc.fraud_scenario = "tampered_records"
        tc.claim_amount *= 3
        tc.notes = "Document metadata shows editing after creation; inconsistent timestamps"

    # Scenario 7: Duplicate Resubmission
    if len(acc_claims) > 10:
        original = acc_claims[8]
        resubmit = acc_claims[9]
        resubmit.fraud_scenario = "duplicate_resubmission"
        resubmit.is_resubmission = True
        resubmit.original_claim_id = original.claim_id
        resubmit.member_id = original.member_id
        resubmit.provider_id = original.provider_id
        resubmit.claim_amount = original.claim_amount * 1.1
        resubmit.notes = f"Resubmission of {original.claim_id} with inflated amount"

    # Scenario 8: Dependent Ring — small ring of related dependents sharing address
    ring_member1 = members[20]
    ring_member2 = members[21]
    ring_member3 = members[22]
    shared_ring_addr = addresses[1]
    ring_member1.address_id = shared_ring_addr.address_id
    ring_member2.address_id = shared_ring_addr.address_id
    ring_member3.address_id = shared_ring_addr.address_id
    ring_wellness = [c for c in claims if c.claim_type == "wellness"][40:46]
    for i, rw in enumerate(ring_wellness):
        rw.member_id = [ring_member1, ring_member2, ring_member3][i % 3].member_id
        rw.fraud_scenario = "dependent_ring"
        rw.notes = "Part of dependent ring — shared address cluster"

    # Scenario 9: Surgical Repair Exploit — hospital indemnity claim for elective procedure coded as emergency
    hi_claims = [c for c in claims if c.claim_type == "hospital_indemnity"]
    if len(hi_claims) > 5:
        hi_claims[4].fraud_scenario = "surgical_repair_exploit"
        hi_claims[4].claim_amount = 45000.00
        hi_claims[4].diagnosis_codes = ["M17.11"]  # Knee osteoarthritis
        hi_claims[4].procedure_codes = ["27447"]  # Total knee replacement
        hi_claims[4].notes = "Elective knee replacement coded as emergency admission"

    # Scenario 10: Missing Headers — document without proper facility headers
    if len(hi_claims) > 8:
        hi_claims[7].fraud_scenario = "missing_headers"
        hi_claims[7].notes = "Medical records missing facility header and physician signature"

    # ── FS-001: Falsified Discharge Summary (CamScanner / MOBILE_SCAN) ───────
    fs001_candidates = [c for c in claims
                        if c.claim_type == "hospital_indemnity"
                        and c.fraud_scenario is None
                        and c.false_positive_scenario is None][:12]
    for c in fs001_candidates:
        c.fraud_scenario = "fs_001_camscanner"
        c.benefit_type = "HOSPITAL_ADMISSION"
        c.relationship_type = random.choice(["SELF", "POLICYHOLDER"])
        c.diagnosis_codes = random.sample(["J44", "J96", "I50", "J18", "N17"], k=2)
        c.claim_amount = round(random.uniform(500, 2000), 2)
        c.notes = "Fraud alert — CamScanner document detected. Request MR via ReleasePoint to confirm validity."

    # ── FS-002: Indemnity Stacking — Legitimate (FALSE POSITIVE) ─────────────
    female_members = [m for m in members
                      if m.gender == "F" and not m.suspicious_banner
                      and m.termination_date is None]
    stacking_member = random.choice(female_members[:30]) if len(female_members) >= 30 else (
        female_members[0] if female_members else members[30]
    )
    fs002_pool = [c for c in claims
                  if c.claim_type == "hospital_indemnity"
                  and c.fraud_scenario is None
                  and c.false_positive_scenario is None][:8]
    if len(fs002_pool) >= 4:
        batch_id = f"BC-2026-{random.randint(1000000, 9999999)}"
        rel_types_cycle = ["SELF", "POLICYHOLDER", "BENEFICIARY", "INSURED",
                           "SELF", "POLICYHOLDER", "BENEFICIARY", "INSURED"]
        base_dos = _rand_date("2026-01-01", "2026-02-28")
        for i, c in enumerate(fs002_pool):
            c.member_id = stacking_member.member_id
            c.false_positive_scenario = "fs_002_stacking"
            c.batch_claim_id = batch_id
            c.benefit_type = "HOSPITAL_INDEMNITY"
            c.relationship_type = rel_types_cycle[i]
            c.diagnosis_codes = ["O30", "Z38"]
            c.claim_amount = round(random.uniform(200, 1000), 2)
            c.date_of_service = base_dos
            c.date_filed = _rand_date(base_dos, "2026-03-15")
            c.stacked_with = [fc.claim_id for fc in fs002_pool if fc.claim_id != c.claim_id]
            c.notes = "Member gave birth to twins — stacking is legitimate for multiple birth event."

    # ── FS-003: Manipulated Urgent Care Records ───────────────────────────────
    fs003_pool = [c for c in claims
                  if c.claim_type == "wellness"
                  and c.fraud_scenario is None
                  and c.false_positive_scenario is None][:6]
    for c in fs003_pool:
        c.fraud_scenario = "fs_003_manipulated"
        c.benefit_type = "URGENT_CARE_VISIT"
        c.relationship_type = "SELF"
        c.diagnosis_codes = random.sample(["J06", "R05", "J02", "R50", "A08"], k=2)
        c.claim_amount = round(random.uniform(100, 500), 2)
        c.notes = "Inconsistencies with font color, quality. Accept records only via ReleasePoint."

    # ── FS-004: High-Volume Legitimate — Chronic Condition (FALSE POSITIVE) ───
    chronic_candidates = [m for m in members
                          if not m.suspicious_banner and m.termination_date is None
                          and m.member_id != stacking_member.member_id]
    chronic_member = chronic_candidates[80] if len(chronic_candidates) > 80 else chronic_candidates[-1]
    fs004_pool = [c for c in claims
                  if c.claim_type == "hospital_indemnity"
                  and c.fraud_scenario is None
                  and c.false_positive_scenario is None][:12]
    chronic_dos_start = datetime(2026, 1, 1)
    for i, c in enumerate(fs004_pool):
        c.member_id = chronic_member.member_id
        c.false_positive_scenario = "fs_004_chronic"
        c.benefit_type = "HOSPITAL_CONFINEMENT"
        c.relationship_type = "SELF"
        c.diagnosis_codes = random.sample(["Z51", "D70", "C50", "C34", "C18"], k=2)
        c.claim_amount = round(random.uniform(200, 1000), 2)
        dos = (chronic_dos_start + timedelta(days=i * 7 + random.randint(0, 5))).strftime("%Y-%m-%d")
        c.date_of_service = dos
        c.date_filed = _rand_date(dos, "2026-03-15")
        c.notes = "Chronic condition (oncology). Multiple claims over 3 months — after medical record review, no fraud found."


def _inject_false_positives(
    claims: List[Claim],
    members: List[Member],
    dependents: List[Dependent],
    providers: List[Provider],
    facilities: List[Facility],
) -> None:
    """Inject 5 false positive scenarios — legitimate claims that trigger some rules."""

    # FP1: New employee genuine accident — high claim right after hire, but legitimate
    new_emp = members[50]
    new_emp.hire_date = "2026-02-01"
    new_emp.notes = "FALSE_POSITIVE: Genuinely new employee with real workplace accident"
    acc_claims = [c for c in claims if c.claim_type == "accident"]
    if len(acc_claims) > 15:
        acc_claims[15].member_id = new_emp.member_id
        acc_claims[15].false_positive_scenario = "new_employee_accident"
        acc_claims[15].claim_amount = 8500.00
        acc_claims[15].date_of_loss = "2026-03-01"
        acc_claims[15].notes = "Legitimate workplace injury 4 weeks after hire. Triggers early-tenure flag but is genuine."

    # FP2: Complex claim multiple contacts — many follow-ups not fraud
    complex_member = members[60]
    complex_member.notes = "FALSE_POSITIVE: Complex claim requiring multiple contacts"
    hi_claims = [c for c in claims if c.claim_type == "hospital_indemnity"]
    if len(hi_claims) > 12:
        hi_claims[12].member_id = complex_member.member_id
        hi_claims[12].false_positive_scenario = "complex_multiple_contacts"
        hi_claims[12].contact_count = 7
        hi_claims[12].claim_amount = 35000.00
        hi_claims[12].notes = "Complex multi-day hospitalization. 7 contacts = coordination, not fraud."

    # FP3: Rural clinic B&W — low-quality fax from rural clinic looks suspicious but legitimate
    rural_fac = next((f for f in facilities if f.is_rural), facilities[-1])
    well_claims = [c for c in claims if c.claim_type == "wellness"]
    if len(well_claims) > 50:
        well_claims[50].false_positive_scenario = "rural_bw_scan"
        well_claims[50].facility_id = rural_fac.facility_id
        well_claims[50].notes = "Rural clinic submits B&W faxed records. Low quality but legitimate provider."

    # FP4: Blended family — many dependents but legitimate blended family
    blended_member = members[70]
    blended_member.notes = "FALSE_POSITIVE: Legitimate blended family with 6 dependents"
    # Add dependents
    dep_id_start = len(dependents) + 1
    for i in range(6):
        gender = _rand_gender()
        first, last = _rand_name(gender)
        dependents.append(Dependent(
            dependent_id=f"DEP-{dep_id_start + i:04d}",
            member_id=blended_member.member_id,
            first_name=first,
            last_name=blended_member.last_name if random.random() < 0.5 else last,
            relationship="child" if i < 4 else "spouse",
            dob=_rand_child_dob() if i < 4 else _rand_dob(30, 55),
            gender=gender,
            address_id=blended_member.address_id,
        ))
    if len(well_claims) > 55:
        well_claims[55].member_id = blended_member.member_id
        well_claims[55].false_positive_scenario = "blended_family"
        well_claims[55].notes = "Large blended family. Triggers dependent count flag but is legitimate."

    # FP5: Genuine high hospital bill — expensive but real
    if len(hi_claims) > 15:
        hi_claims[15].false_positive_scenario = "genuine_high_bill"
        hi_claims[15].claim_amount = 48000.00
        hi_claims[15].notes = "Genuine ICU stay for severe pneumonia. High amount is legitimate."


# ── Document Metadata & Workflow Tasks ───────────────────────────────────────

def _generate_document_metadata(claims: List[Claim], providers: List[Provider]) -> List[DocumentMetadata]:
    docs = []
    provider_map = {p.provider_id: p for p in providers}
    for claim in claims:
        prov = provider_map.get(claim.provider_id)
        prov_name = prov.name if prov else "Unknown Provider"

        # Defaults — clean document
        has_header = True
        has_signature = True
        has_date = True
        fmt_type = random.choice(["digital", "fax", "scan"])
        resolution = "standard"
        tampering = []
        source_type = "PROVIDER_PORTAL"
        font_score = round(random.uniform(0.85, 1.0), 2)
        align_score = round(random.uniform(0.85, 1.0), 2)
        color_score = round(random.uniform(0.85, 1.0), 2)
        header_match = True
        app_sig = None
        rp_status = "NOT_REQUESTED"
        rp_id = None
        doc_type = random.choice(["medical_record", "invoice", "receipt", "discharge_summary"])
        filename = f"{doc_type}_{claim.claim_id}.pdf"

        # Existing scenario overrides
        if claim.fraud_scenario == "tampered_records":
            tampering = ["metadata_edit_after_creation", "inconsistent_timestamps", "font_mismatch"]
            has_date = False
            source_type = "MEMBER_UPLOAD_PDF"
            font_score = round(random.uniform(0.3, 0.5), 2)
            align_score = round(random.uniform(0.4, 0.6), 2)
            color_score = round(random.uniform(0.3, 0.5), 2)
            header_match = False
        elif claim.fraud_scenario == "missing_headers":
            has_header = False
            has_signature = False
            fmt_type = "fax"
            resolution = "low"
            source_type = "MEMBER_FAX"
        elif claim.false_positive_scenario == "rural_bw_scan":
            fmt_type = "fax"
            resolution = "low"
            source_type = "PROVIDER_FAX"
        # New FS scenario overrides
        elif claim.fraud_scenario == "fs_001_camscanner":
            source_type = "MOBILE_SCAN"
            app_sig = "CamScanner"
            fmt_type = "scan"
            resolution = "low"
            doc_type = "discharge_summary"
            font_score = round(random.uniform(0.3, 0.6), 2)
            align_score = round(random.uniform(0.4, 0.7), 2)
            color_score = round(random.uniform(0.35, 0.6), 2)
            header_match = False
            rp_status = "REQUESTED"
            rp_id = f"RP {random.randint(10000000, 99999999)}"
            dos_parts = claim.date_of_service.replace("-", "-")
            filename = f"CamScanner_{dos_parts}_{random.randint(10,99)}.{random.randint(10,99)}_1.jpeg"
        elif claim.false_positive_scenario == "fs_002_stacking":
            source_type = "PROVIDER_PORTAL"
            fmt_type = "digital"
            font_score = round(random.uniform(0.88, 1.0), 2)
            align_score = round(random.uniform(0.90, 1.0), 2)
            color_score = round(random.uniform(0.88, 1.0), 2)
            header_match = True
        elif claim.fraud_scenario == "fs_003_manipulated":
            source_type = "MEMBER_UPLOAD_PDF"
            fmt_type = "scan"
            doc_type = "medical_record"
            font_score = round(random.uniform(0.3, 0.5), 2)
            align_score = round(random.uniform(0.3, 0.6), 2)
            color_score = round(random.uniform(0.4, 0.6), 2)
            header_match = False
            rp_status = "REQUESTED"
            rp_id = f"RP {random.randint(10000000, 99999999)}"
            safe_name = prov_name.replace("Dr. ", "").replace(" ", "_")
            filename = f"Notes_from_care_team_{safe_name}_{claim.date_of_service}.pdf"
        elif claim.false_positive_scenario == "fs_004_chronic":
            source_type = "PROVIDER_PORTAL"
            fmt_type = "digital"
            font_score = round(random.uniform(0.85, 1.0), 2)
            align_score = round(random.uniform(0.85, 1.0), 2)
            color_score = round(random.uniform(0.85, 1.0), 2)
            header_match = True
            rp_status = "RECORDS_RECEIVED"

        h = hashlib.md5(f"{claim.claim_id}-{claim.date_of_service}".encode()).hexdigest()[:16]
        dup_of = None
        if claim.fraud_scenario == "duplicate_resubmission" and claim.original_claim_id:
            dup_of = claim.original_claim_id

        docs.append(DocumentMetadata(
            doc_id=f"DOC-{claim.claim_id}",
            claim_id=claim.claim_id,
            doc_type=doc_type,
            provider_name=prov_name,
            date_of_service=claim.date_of_service,
            received_date=claim.date_filed,
            has_header=has_header,
            has_signature=has_signature,
            has_date=has_date,
            format_type=fmt_type,
            resolution=resolution,
            metadata_hash=h,
            duplicate_of=dup_of,
            tampering_indicators=tampering,
            source_type=source_type,
            font_consistency_score=font_score,
            alignment_score=align_score,
            color_consistency_score=color_score,
            header_content_match=header_match,
            metadata_app_signature=app_sig,
            releasepoint_status=rp_status,
            releasepoint_request_id=rp_id,
        ))

        # FS-003: Add a second document (After Visit Summary) with its own scores
        if claim.fraud_scenario == "fs_003_manipulated":
            safe_name = prov_name.replace("Dr. ", "").replace(" ", "_")
            docs.append(DocumentMetadata(
                doc_id=f"DOC-{claim.claim_id}-2",
                claim_id=claim.claim_id,
                doc_type="discharge_summary",
                provider_name=prov_name,
                date_of_service=claim.date_of_service,
                received_date=claim.date_filed,
                has_header=True,
                has_signature=True,
                has_date=True,
                format_type="scan",
                resolution="low",
                metadata_hash=hashlib.md5(f"{claim.claim_id}-2-avs".encode()).hexdigest()[:16],
                source_type="MEMBER_UPLOAD_PDF",
                font_consistency_score=round(random.uniform(0.4, 0.6), 2),
                alignment_score=round(random.uniform(0.5, 0.7), 2),
                color_consistency_score=round(random.uniform(0.4, 0.6), 2),
                header_content_match=False,
                releasepoint_status="REQUESTED",
                releasepoint_request_id=f"RP {random.randint(10000000, 99999999)}",
            ))

    return docs


def _generate_workflow_tasks(claims: List[Claim]) -> List[WorkflowTask]:
    tasks = []
    task_id = 1
    today = datetime(2026, 3, 15)

    for claim in claims:
        # Every claim gets INITIAL_REVIEW
        assigned = claim.date_filed
        tasks.append(WorkflowTask(
            task_id=f"TASK-{task_id:04d}",
            claim_id=claim.claim_id,
            task_type="INITIAL_REVIEW",
            status="pending",
            assigned_date=assigned,
            due_date=(datetime.strptime(assigned, "%Y-%m-%d") + timedelta(days=3)).strftime("%Y-%m-%d"),
        ))
        task_id += 1

        # Some claims need medical records
        if claim.claim_type in ("hospital_indemnity", "critical_illness") or random.random() < 0.15:
            req_date = claim.date_filed
            days_wait = random.randint(0, 21)
            received = random.random() < 0.6
            tasks.append(WorkflowTask(
                task_id=f"TASK-{task_id:04d}",
                claim_id=claim.claim_id,
                task_type="MEDICAL_RECORD_REQUEST",
                status="completed" if received else "pending",
                assigned_date=req_date,
                due_date=(datetime.strptime(req_date, "%Y-%m-%d") + timedelta(days=14)).strftime("%Y-%m-%d"),
                completed_date=(datetime.strptime(req_date, "%Y-%m-%d") + timedelta(days=days_wait)).strftime("%Y-%m-%d") if received else None,
                days_waiting=days_wait if not received else 0,
            ))
            task_id += 1

        # PMR tasks (~15%)
        if random.random() < 0.15:
            tasks.append(WorkflowTask(
                task_id=f"TASK-{task_id:04d}",
                claim_id=claim.claim_id,
                task_type="PMR",
                status=random.choice(["pending", "in_progress", "completed"]),
                assigned_date=claim.date_filed,
                due_date=(datetime.strptime(claim.date_filed, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d"),
            ))
            task_id += 1

        # CBR tasks (~10%)
        if random.random() < 0.10:
            tasks.append(WorkflowTask(
                task_id=f"TASK-{task_id:04d}",
                claim_id=claim.claim_id,
                task_type="CBR",
                status=random.choice(["pending", "in_progress"]),
                assigned_date=claim.date_filed,
                due_date=(datetime.strptime(claim.date_filed, "%Y-%m-%d") + timedelta(days=5)).strftime("%Y-%m-%d"),
            ))
            task_id += 1

    # Mark ~8% as approaching/past TAT
    overdue_count = int(len(tasks) * 0.08)
    pending_tasks = [t for t in tasks if t.status == "pending" and t.due_date]
    for t in random.sample(pending_tasks, min(overdue_count, len(pending_tasks))):
        past_date = (today - timedelta(days=random.randint(1, 5))).strftime("%Y-%m-%d")
        t.due_date = past_date
        t.status = "overdue"

    return tasks


# ── Main Generation Function ────────────────────────────────────────────────

def generate_supplemental_data() -> Dict:
    """Generate all supplemental health data. Returns dict of entity lists."""
    _seed()

    print("  Generating employers...")
    employers = _generate_employers()

    print("  Generating addresses...")
    addresses = _generate_addresses(180, shared_count=15)

    print("  Generating facilities...")
    facilities = _generate_facilities()

    print("  Generating members (200)...")
    members = _generate_members(200, employers, addresses)

    print("  Generating dependents...")
    dependents = _generate_dependents(members, addresses)

    print("  Generating providers (40)...")
    providers = _generate_providers(40, facilities)

    print("  Generating policies...")
    policies = _generate_policies(members)

    source_weights = {"company_site": 0.50, "telephonic": 0.10, "web": 0.30, "disability_portal": 0.10}

    print("  Generating 500 claims...")
    claims = _generate_base_claims(members, dependents, providers, facilities, policies, employers, source_weights)

    print("  Injecting 10 fraud scenarios...")
    _inject_fraud_scenarios(claims, members, dependents, providers, policies, addresses)

    print("  Injecting 5 false positives...")
    _inject_false_positives(claims, members, dependents, providers, facilities)

    # ── Cap today's queue to 15 claims ──────────────────────────────────────
    # Ensures the default "Today" view shows a realistic daily workload (~15)
    # rather than a random ~23 out of 500. HIGH-risk and key fraud claims are
    # pinned to today; excess claims are pushed back one or two days.
    TODAY = "2026-03-15"
    YESTERDAY = "2026-03-14"
    DAY_BEFORE = "2026-03-13"
    TARGET_TODAY = 15

    # Priority claims that must appear in today's queue
    priority_ids = {"WC-247", "HI-003"}  # hero cases always visible today

    # Pin 2-3 other high-signal fraud claims to today (skip termination_rush —
    # it's intentionally dated to 2026-03-14 to show the rush pattern)
    fraud_today = [c for c in claims
                   if c.fraud_scenario
                   and c.claim_id != "WC-247"
                   and c.fraud_scenario != "termination_rush"][:3]
    for c in fraud_today:
        priority_ids.add(c.claim_id)

    # Force priority claims to today
    for c in claims:
        if c.claim_id in priority_ids:
            c.date_filed = TODAY

    # Count all claims currently set to today
    today_claims = [c for c in claims if c.date_filed == TODAY]

    if len(today_claims) > TARGET_TODAY:
        # Push excess non-priority claims to yesterday/day-before
        non_priority_today = [c for c in today_claims if c.claim_id not in priority_ids]
        random.shuffle(non_priority_today)
        to_move = non_priority_today[: len(today_claims) - TARGET_TODAY]
        for i, c in enumerate(to_move):
            c.date_filed = YESTERDAY if i % 2 == 0 else DAY_BEFORE
    elif len(today_claims) < 10:
        # Pull in a few more clean claims from the rest to reach at least 10
        others = [c for c in claims if c.date_filed != TODAY and c.claim_id not in priority_ids]
        random.shuffle(others)
        for c in others[: 10 - len(today_claims)]:
            c.date_filed = TODAY

    print("  Generating document metadata...")
    documents = _generate_document_metadata(claims, providers)

    print("  Generating workflow tasks...")
    workflow_tasks = _generate_workflow_tasks(claims)

    print(f"  ✅ Generated: {len(employers)} employers, {len(members)} members, "
          f"{len(dependents)} dependents, {len(providers)} providers, "
          f"{len(facilities)} facilities, {len(policies)} policies, "
          f"{len(claims)} claims, {len(documents)} docs, {len(workflow_tasks)} tasks")

    return {
        "employers": employers,
        "members": members,
        "dependents": dependents,
        "providers": providers,
        "facilities": facilities,
        "addresses": addresses,
        "policies": policies,
        "claims": claims,
        "documents": documents,
        "workflow_tasks": workflow_tasks,
    }
