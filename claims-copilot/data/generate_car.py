"""Generate ~50 car insurance claims with embedded fraud scenarios for the Car Insurance copilot.

Minimal POC dataset. Mirrors the structure of generate_travel.py but for auto claims:
  - Insured (policyholder/driver)        ← Traveler
  - Vehicle (vin/make/model/acv)         ← Destination
  - RepairShop (watchlist/verified)      ← MedicalProvider
  - CarPolicy (collision/comp/liability) ← TravelPolicy
  - RepairEstimate / PoliceReport        ← BookingRecord / FlightRecord
  - CarClaim                             ← TravelClaim

Returns a dict keyed by entity name; this becomes DataContext.entities.
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta


# ── Entity Dataclasses ───────────────────────────────────────────────────────

@dataclass
class Insured:
    insured_id: str
    first_name: str
    last_name: str
    dob: str
    gender: str
    email: str
    phone: str
    address_state: str
    license_years: int = 10
    claim_history_count: int = 0
    flagged: bool = False
    notes: str = ""

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


@dataclass
class Vehicle:
    vehicle_id: str
    insured_id: str
    vin: str
    make: str
    model: str
    year: int
    body_type: str          # sedan, suv, truck, coupe
    acv: float              # actual cash value (blue-book)
    salvage_flag: bool = False


@dataclass
class RepairShop:
    shop_id: str
    name: str
    state: str
    on_watchlist: bool = False
    verified: bool = True
    in_network: bool = True
    notes: str = ""


@dataclass
class CarPolicy:
    policy_id: str
    insured_id: str
    vehicle_id: str
    effective_date: str          # coverage start
    expiration_date: str         # coverage end
    coverage_collision: float = 50000.0
    coverage_comprehensive: float = 50000.0
    coverage_liability: float = 100000.0
    coverage_medical_payments: float = 10000.0
    deductible: float = 500.0
    premium: float = 0.0
    status: str = "active"


@dataclass
class RepairEstimate:
    estimate_id: str
    claim_id: str
    shop_id: str
    amount: float
    line_items: List[str] = field(default_factory=list)
    estimate_date: str = ""
    confirmed: bool = True


@dataclass
class PoliceReport:
    report_id: str
    claim_id: str
    report_number: str
    filed_date: str
    at_fault_party: str = "other_driver"   # insured, other_driver, no_fault
    on_file: bool = True


@dataclass
class DocumentMetadata:
    doc_id: str
    claim_id: str
    doc_type: str               # repair_estimate, police_report, damage_photo, medical_bill
    provider_name: str
    date_created: str
    received_date: str
    has_header: bool = True
    has_signature: bool = True
    format_type: str = "digital"
    resolution: str = "standard"
    tampering_indicators: List[str] = field(default_factory=list)
    currency: str = "USD"
    amount_on_doc: float = 0.0


@dataclass
class WorkflowTask:
    task_id: str
    claim_id: str
    task_type: str              # INITIAL_REVIEW, ESTIMATE_REVIEW, SHOP_VERIFICATION, INJURY_REVIEW
    status: str = "pending"
    assigned_date: Optional[str] = None
    due_date: Optional[str] = None
    completed_date: Optional[str] = None
    days_waiting: int = 0
    notes: str = ""


@dataclass
class CarClaim:
    claim_id: str
    claim_type: str             # collision, comprehensive, theft, liability, medical_payments
    insured_id: str
    vehicle_id: str = ""
    policy_id: str = ""
    shop_id: Optional[str] = None
    estimate_id: Optional[str] = None
    report_id: Optional[str] = None
    date_filed: str = ""
    date_of_incident: str = ""
    claim_amount: float = 0.0
    approved_amount: float = 0.0
    status: str = "new"
    claim_source: str = "online_portal"
    incident_description: str = ""
    injury_claimed: bool = False
    police_report_filed: bool = False
    fraud_scenario: Optional[str] = None
    false_positive_scenario: Optional[str] = None
    notes: str = ""
    is_resubmission: bool = False
    original_claim_id: Optional[str] = None
    photo_evidence: bool = False   # True when a damage photo (images/<id>.png) is on file


# ── Name / Data Pools ────────────────────────────────────────────────────────

FIRST_NAMES_M = ["James", "Robert", "Michael", "William", "David", "Richard", "Joseph",
                 "Thomas", "Daniel", "Matthew", "Anthony", "Mark", "Steven", "Paul", "Kevin"]
FIRST_NAMES_F = ["Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
                 "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Emily", "Michelle", "Amanda"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Wilson", "Anderson", "Taylor", "Moore", "Jackson",
              "Lee", "Thompson", "White", "Harris", "Clark"]
US_STATES = ["NY", "CA", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "NJ", "VA", "WA", "MA", "AZ", "CO"]

VEHICLES = [
    ("Toyota", "Camry", "sedan", 18000),
    ("Honda", "Accord", "sedan", 17000),
    ("Ford", "F-150", "truck", 32000),
    ("Chevrolet", "Silverado", "truck", 31000),
    ("Toyota", "RAV4", "suv", 24000),
    ("Honda", "CR-V", "suv", 23000),
    ("BMW", "3 Series", "sedan", 38000),
    ("Mercedes-Benz", "C-Class", "sedan", 42000),
    ("Tesla", "Model 3", "sedan", 39000),
    ("Jeep", "Grand Cherokee", "suv", 36000),
    ("Nissan", "Altima", "sedan", 16000),
    ("Subaru", "Outback", "suv", 27000),
]

REPAIR_SHOPS = [
    ("Premier Auto Body", True),
    ("Citywide Collision Center", True),
    ("Highway Auto Repair", True),
    ("Elite Body Works", True),
    ("Sunset Collision", True),
    ("Metro Auto Body", True),
    ("Discount Fender Fix", False),       # not in-network
    ("QuickCash Auto Body", False),       # not in-network — becomes watchlist hero
    ("Reliable Repairs Inc", True),
    ("AAA Certified Collision", True),
]

COLLISION_DESCRIPTIONS = [
    "Rear-ended at a stoplight on the highway off-ramp.",
    "Side-swiped while changing lanes on the interstate.",
    "Hit a guardrail avoiding debris in the road.",
    "Intersection collision; other driver ran a red light.",
    "Parking lot fender bender with a shopping cart corral.",
]
THEFT_DESCRIPTIONS = [
    "Vehicle stolen overnight from driveway.",
    "Catalytic converter theft from parking garage.",
    "Break-in; stereo and personal items taken.",
]
COMP_DESCRIPTIONS = [
    "Hail damage to hood and roof during a storm.",
    "Tree branch fell on parked vehicle.",
    "Windshield cracked by road debris.",
    "Flood damage from heavy rain.",
]
LIABILITY_DESCRIPTIONS = [
    "At-fault rear-end collision; other party claiming damages.",
    "Backed into another vehicle in a parking lot.",
]

REPAIR_LINE_ITEMS = [
    "Front bumper replacement", "Hood repair and repaint", "Headlight assembly",
    "Quarter panel replacement", "Door skin replacement", "Windshield replacement",
    "Frame alignment", "Airbag module reset", "Paint blend (3 panels)",
    "Radiator support", "Fender replacement", "Tail light assembly",
    "Wheel and tire", "Suspension control arm", "Bumper cover refinish",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _seed():
    random.seed(91)


def _rand_date(start_str: str, end_str: str) -> str:
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    delta = (end - start).days
    if delta <= 0:
        return start_str
    return (start + timedelta(days=random.randint(0, delta))).strftime("%Y-%m-%d")


def _rand_dob(min_age=22, max_age=70):
    today = datetime(2026, 3, 15)
    age = random.randint(min_age, max_age)
    dob = today - timedelta(days=age * 365 + random.randint(0, 364))
    return dob.strftime("%Y-%m-%d")


def _rand_gender():
    return random.choice(["M", "F"])


def _rand_name(gender):
    first = random.choice(FIRST_NAMES_M if gender == "M" else FIRST_NAMES_F)
    last = random.choice(LAST_NAMES)
    return first, last


def _rand_vin():
    chars = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
    return "".join(random.choice(chars) for _ in range(17))


def _claim_amount(claim_type):
    ranges = {
        "collision": (1500, 18000),
        "comprehensive": (500, 9000),
        "theft": (3000, 35000),
        "liability": (2000, 25000),
        "medical_payments": (800, 9000),
    }
    lo, hi = ranges.get(claim_type, (500, 8000))
    return round(random.uniform(lo, hi), 2)


SOURCE_WEIGHTS = {"online_portal": 0.45, "mobile_app": 0.25, "call_center": 0.20, "agent": 0.10}


def _pick_source(weights):
    return random.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]


# ── Generate Base Entities ───────────────────────────────────────────────────

def _generate_insureds(count: int) -> List[Insured]:
    insureds = []
    for i in range(count):
        gender = _rand_gender()
        first, last = _rand_name(gender)
        insureds.append(Insured(
            insured_id=f"INS-{i+1:04d}",
            first_name=first,
            last_name=last,
            dob=_rand_dob(),
            gender=gender,
            email=f"{first.lower()}.{last.lower()}@email.com",
            phone=f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}",
            address_state=random.choice(US_STATES),
            license_years=random.randint(1, 40),
        ))
    return insureds


def _generate_vehicles(insureds: List[Insured]) -> List[Vehicle]:
    vehicles = []
    v_id = 1
    for ins in insureds:
        make, model, body, base_acv = random.choice(VEHICLES)
        year = random.randint(2014, 2024)
        # depreciate older vehicles a bit
        acv = round(base_acv * (1 - (2025 - year) * 0.05) * random.uniform(0.85, 1.1), 2)
        vehicles.append(Vehicle(
            vehicle_id=f"VEH-{v_id:04d}",
            insured_id=ins.insured_id,
            vin=_rand_vin(),
            make=make,
            model=model,
            year=year,
            body_type=body,
            acv=max(acv, 3000.0),
        ))
        v_id += 1
    return vehicles


def _generate_repair_shops() -> List[RepairShop]:
    shops = []
    for i, (name, in_network) in enumerate(REPAIR_SHOPS):
        shops.append(RepairShop(
            shop_id=f"SHP-{i+1:03d}",
            name=name,
            state=random.choice(US_STATES),
            in_network=in_network,
            verified=in_network,
        ))
    return shops


def _generate_policies(insureds: List[Insured], vehicles: List[Vehicle]) -> List[CarPolicy]:
    veh_by_insured = {}
    for v in vehicles:
        veh_by_insured.setdefault(v.insured_id, []).append(v)

    policies = []
    pol_id = 1
    for ins in insureds:
        vehs = veh_by_insured.get(ins.insured_id, [])
        if not vehs:
            continue
        vehicle = vehs[0]
        effective = _rand_date("2025-01-01", "2025-09-30")
        expiration = (datetime.strptime(effective, "%Y-%m-%d") + timedelta(days=365)).strftime("%Y-%m-%d")
        policies.append(CarPolicy(
            policy_id=f"POL-{pol_id:04d}",
            insured_id=ins.insured_id,
            vehicle_id=vehicle.vehicle_id,
            effective_date=effective,
            expiration_date=expiration,
            coverage_collision=random.choice([25000, 50000, 75000]),
            coverage_comprehensive=random.choice([25000, 50000, 75000]),
            coverage_liability=random.choice([50000, 100000, 250000]),
            coverage_medical_payments=random.choice([5000, 10000, 25000]),
            deductible=random.choice([250, 500, 1000]),
            premium=round(random.uniform(800, 2200), 2),
            status="active",
        ))
        pol_id += 1
    return policies


# ── Claim Generation ─────────────────────────────────────────────────────────

def _generate_base_claims(
    insureds: List[Insured],
    vehicles: List[Vehicle],
    shops: List[RepairShop],
    policies: List[CarPolicy],
) -> List[CarClaim]:
    """Generate ~45 base claims distributed across the 5 claim types."""
    claims = []
    claim_counts = {
        "collision": 16,
        "comprehensive": 10,
        "theft": 7,
        "liability": 7,
        "medical_payments": 5,
    }
    prefixes = {"collision": "COL", "comprehensive": "COMP", "theft": "THEFT",
                "liability": "LIAB", "medical_payments": "MEDP"}
    descriptions = {
        "collision": COLLISION_DESCRIPTIONS,
        "comprehensive": COMP_DESCRIPTIONS,
        "theft": THEFT_DESCRIPTIONS,
        "liability": LIABILITY_DESCRIPTIONS,
        "medical_payments": COLLISION_DESCRIPTIONS,
    }

    policy_by_insured = {p.insured_id: p for p in policies}
    vehicle_by_id = {v.vehicle_id: v for v in vehicles}
    in_network_shops = [s for s in shops if s.in_network]

    for claim_type, count in claim_counts.items():
        prefix = prefixes[claim_type]
        type_id = 1
        for _ in range(count):
            insured = random.choice(insureds)
            policy = policy_by_insured.get(insured.insured_id)
            if not policy:
                continue
            vehicle = vehicle_by_id.get(policy.vehicle_id)

            # Incident within (or near) the coverage period
            date_of_incident = _rand_date(policy.effective_date, "2026-03-10")
            date_filed = _rand_date(date_of_incident, "2026-03-15")

            shop = random.choice(in_network_shops) if claim_type != "theft" else None
            injury = (claim_type in ("liability", "medical_payments")) or random.random() < 0.1
            police_filed = claim_type in ("theft", "liability") or random.random() < 0.4

            claims.append(CarClaim(
                claim_id=f"{prefix}-{type_id:03d}",
                claim_type=claim_type,
                insured_id=insured.insured_id,
                vehicle_id=policy.vehicle_id,
                policy_id=policy.policy_id,
                shop_id=shop.shop_id if shop else None,
                date_filed=date_filed,
                date_of_incident=date_of_incident,
                claim_amount=_claim_amount(claim_type),
                claim_source=_pick_source(SOURCE_WEIGHTS),
                incident_description=random.choice(descriptions[claim_type]),
                injury_claimed=injury,
                police_report_filed=police_filed,
            ))
            type_id += 1
    return claims


# ── Estimates / Police Reports ────────────────────────────────────────────────

def _generate_estimates(claims: List[CarClaim], shops: List[RepairShop]) -> List[RepairEstimate]:
    """One repair estimate per non-theft claim (theft total-loss handled separately)."""
    estimates = []
    est_id = 1
    for claim in claims:
        if claim.claim_type == "theft":
            continue
        if not claim.shop_id:
            continue
        num_items = random.randint(2, 5)
        items = random.sample(REPAIR_LINE_ITEMS, num_items)
        est = RepairEstimate(
            estimate_id=f"EST-{est_id:04d}",
            claim_id=claim.claim_id,
            shop_id=claim.shop_id,
            amount=round(claim.claim_amount * random.uniform(0.9, 1.05), 2),
            line_items=items,
            estimate_date=claim.date_filed,
            confirmed=True,
        )
        estimates.append(est)
        claim.estimate_id = est.estimate_id
        est_id += 1
    return estimates


def _generate_police_reports(claims: List[CarClaim]) -> List[PoliceReport]:
    reports = []
    rep_id = 1
    for claim in claims:
        if not claim.police_report_filed:
            continue
        rep = PoliceReport(
            report_id=f"PR-{rep_id:04d}",
            claim_id=claim.claim_id,
            report_number=f"{random.choice(US_STATES)}-{random.randint(100000, 999999)}",
            filed_date=claim.date_of_incident,
            at_fault_party=random.choice(["other_driver", "insured", "no_fault"]),
            on_file=True,
        )
        reports.append(rep)
        claim.report_id = rep.report_id
        rep_id += 1
    return reports


def _generate_documents(claims: List[CarClaim]) -> List[DocumentMetadata]:
    docs = []
    doc_id = 1
    doc_types_for_type = {
        "collision": ["repair_estimate", "damage_photo"],
        "comprehensive": ["repair_estimate", "damage_photo"],
        "theft": ["police_report"],
        "liability": ["police_report", "repair_estimate"],
        "medical_payments": ["medical_bill", "police_report"],
    }
    for claim in claims:
        dtypes = doc_types_for_type.get(claim.claim_type, ["repair_estimate"])
        for dtype in dtypes:
            docs.append(DocumentMetadata(
                doc_id=f"DOC-{doc_id:04d}",
                claim_id=claim.claim_id,
                doc_type=dtype,
                provider_name="Various",
                date_created=claim.date_of_incident or claim.date_filed,
                received_date=claim.date_filed,
                amount_on_doc=round(claim.claim_amount / len(dtypes), 2),
            ))
            doc_id += 1
    return docs


def _generate_workflow_tasks(claims: List[CarClaim]) -> List[WorkflowTask]:
    tasks = []
    task_id = 1
    for claim in claims:
        assigned = claim.date_filed
        due = (datetime.strptime(assigned, "%Y-%m-%d") + timedelta(days=3)).strftime("%Y-%m-%d")
        status = random.choices(["pending", "in_progress", "completed", "overdue"],
                                weights=[0.3, 0.3, 0.3, 0.1], k=1)[0]
        tasks.append(WorkflowTask(
            task_id=f"TSK-{task_id:04d}",
            claim_id=claim.claim_id,
            task_type="INITIAL_REVIEW",
            status=status,
            assigned_date=assigned,
            due_date=due,
            days_waiting=random.randint(0, 5),
        ))
        task_id += 1

        if claim.claim_type in ("collision", "comprehensive", "liability") and random.random() < 0.7:
            tasks.append(WorkflowTask(
                task_id=f"TSK-{task_id:04d}",
                claim_id=claim.claim_id,
                task_type="ESTIMATE_REVIEW",
                status="pending",
                assigned_date=assigned,
                due_date=(datetime.strptime(assigned, "%Y-%m-%d") + timedelta(days=5)).strftime("%Y-%m-%d"),
                days_waiting=random.randint(0, 4),
            ))
            task_id += 1

        if claim.injury_claimed and random.random() < 0.8:
            tasks.append(WorkflowTask(
                task_id=f"TSK-{task_id:04d}",
                claim_id=claim.claim_id,
                task_type="INJURY_REVIEW",
                status="pending",
                assigned_date=assigned,
                due_date=(datetime.strptime(assigned, "%Y-%m-%d") + timedelta(days=14)).strftime("%Y-%m-%d"),
                days_waiting=random.randint(0, 10),
            ))
            task_id += 1
    return tasks


# ── Fraud Scenarios ──────────────────────────────────────────────────────────

def _inject_fraud_scenarios(
    claims: List[CarClaim],
    insureds: List[Insured],
    vehicles: List[Vehicle],
    shops: List[RepairShop],
    policies: List[CarPolicy],
    estimates: List[RepairEstimate],
) -> None:
    """Inject 3 hero fraud cases into the car claims."""

    vehicle_by_id = {v.vehicle_id: v for v in vehicles}
    est_by_claim = {e.claim_id: e for e in estimates}

    # ── COL-107: Inflated Repair Estimate from a watchlisted shop
    # Promote the last non-network shop to a fraud-watchlist shop.
    watchlist_shop = next((s for s in shops if not s.in_network), shops[-1])
    watchlist_shop.on_watchlist = True
    watchlist_shop.verified = False
    watchlist_shop.notes = "WATCHLIST: Repeated inflated estimates; suspected staged-damage referrals."

    col_claims = [c for c in claims if c.claim_type == "collision" and c.fraud_scenario is None]
    if col_claims:
        hero = col_claims[0]
        original_id = hero.claim_id                       # look up the estimate by its pre-rename id
        hero.claim_id = "COL-107"
        hero.fraud_scenario = "inflated_estimate"
        hero.shop_id = watchlist_shop.shop_id
        vehicle = vehicle_by_id.get(hero.vehicle_id)
        acv = vehicle.acv if vehicle else 18000.0
        hero.claim_amount = round(acv * 1.4, 2)          # estimate well above the car's value
        hero.photo_evidence = True                       # damage photo on file (images/col107.png)
        hero.notes = ("Repair estimate from watchlisted shop is 1.4x the vehicle ACV. "
                      "Damage photo submitted — held for forensic review.")
        hero.insured_id = insureds[0].insured_id
        insureds[0].flagged = True
        insureds[0].notes = "FRAUD_SCENARIO: Inflated estimate via watchlisted body shop"
        # Re-key the estimate to the renamed claim and sync the inflated amount/shop.
        est = est_by_claim.get(original_id)
        if est:
            est.claim_id = hero.claim_id
            est.shop_id = watchlist_shop.shop_id
            est.amount = hero.claim_amount

    # ── THEFT-009: Staged theft / total-loss padding (policy bought just before incident)
    theft_claims = [c for c in claims if c.claim_type == "theft" and c.fraud_scenario is None]
    if theft_claims:
        hero = theft_claims[0]
        hero.claim_id = "THEFT-009"
        hero.fraud_scenario = "staged_theft"
        vehicle = vehicle_by_id.get(hero.vehicle_id)
        acv = vehicle.acv if vehicle else 20000.0
        hero.claim_amount = round(acv * 1.3, 2)          # claim well above vehicle ACV
        hero.police_report_filed = False                 # no police report for a "theft"
        hero.report_id = None
        hero.notes = ("Reported stolen 6 days after a max-coverage policy change. "
                      "Claim exceeds vehicle ACV; no police report and no signs of forced entry.")
        hero.insured_id = insureds[1].insured_id
        insureds[1].notes = "FRAUD_SCENARIO: Staged theft / total-loss padding"
        # Make the policy effective AFTER the incident date for this insured (R-001 BLOCK).
        policy = next((p for p in policies if p.insured_id == hero.insured_id), None)
        if policy:
            hero.policy_id = policy.policy_id
            incident = datetime.strptime(hero.date_of_incident, "%Y-%m-%d")
            policy.effective_date = (incident + timedelta(days=2)).strftime("%Y-%m-%d")

    # ── LIAB-006: Serial claimer — many claims in the period
    liab_claims = [c for c in claims if c.claim_type == "liability" and c.fraud_scenario is None]
    if liab_claims:
        hero = liab_claims[0]
        hero.claim_id = "LIAB-021"      # out of the base LIAB range to avoid ID collision
        hero.fraud_scenario = "serial_claimer"
        hero.injury_claimed = True
        hero.claim_amount = 18500.00
        hero.notes = ("6th auto claim in 12 months, always with a soft-tissue injury component. "
                      "Pattern consistent with staged-collision rings.")
        hero.insured_id = insureds[2].insured_id
        insureds[2].claim_history_count = 6
        insureds[2].flagged = True
        insureds[2].notes = "FRAUD_SCENARIO: Serial claimer — 6 auto claims in 12 months"


# ── False Positives ──────────────────────────────────────────────────────────

def _inject_false_positives(claims: List[CarClaim], insureds: List[Insured], vehicles: List[Vehicle]) -> None:
    """Add 2 false positives to test examiner judgment."""

    vehicle_by_id = {v.vehicle_id: v for v in vehicles}

    # FP1: Legitimate high-value collision (luxury vehicle, in-network shop, photo on file)
    # Pinned to COL-005 so a damage photo (images/col005.png) maps deterministically.
    col_claims = [c for c in claims if c.claim_type == "collision" and c.fraud_scenario is None]
    fp = next((c for c in col_claims if c.claim_id == "COL-005"), col_claims[-1] if col_claims else None)
    if fp:
        fp.false_positive_scenario = "legitimate_high_value_collision"
        vehicle = vehicle_by_id.get(fp.vehicle_id)
        fp.claim_amount = round((vehicle.acv if vehicle else 38000.0) * 0.45, 2)
        fp.photo_evidence = True
        fp.notes = ("High-dollar repair but consistent with a late-model luxury vehicle. "
                    "In-network shop, itemized estimate, police report on file. Damage photo submitted.")

    # FP2: Legitimate comprehensive (documented hail-storm event)
    comp_claims = [c for c in claims if c.claim_type == "comprehensive" and c.fraud_scenario is None]
    if comp_claims:
        fp = comp_claims[-1]
        fp.false_positive_scenario = "legitimate_weather_event"
        fp.claim_amount = 6200.00
        fp.notes = "Hail damage during a NOAA-confirmed storm; multiple area claims corroborate the event."


# ── Main Generator ───────────────────────────────────────────────────────────

def generate_car_data() -> Dict:
    """Generate all car insurance data. Returns dict of entity lists."""
    _seed()

    print("  Generating insureds (45)...")
    insureds = _generate_insureds(45)

    print("  Generating vehicles...")
    vehicles = _generate_vehicles(insureds)

    print("  Generating repair shops...")
    shops = _generate_repair_shops()

    print("  Generating policies...")
    policies = _generate_policies(insureds, vehicles)

    print("  Generating car claims...")
    claims = _generate_base_claims(insureds, vehicles, shops, policies)

    print("  Generating repair estimates...")
    estimates = _generate_estimates(claims, shops)

    print("  Generating police reports...")
    police_reports = _generate_police_reports(claims)

    print("  Injecting 3 fraud scenarios...")
    _inject_fraud_scenarios(claims, insureds, vehicles, shops, policies, estimates)

    print("  Injecting 2 false positives...")
    _inject_false_positives(claims, insureds, vehicles)

    print("  Generating documents...")
    documents = _generate_documents(claims)

    print("  Generating workflow tasks...")
    workflow_tasks = _generate_workflow_tasks(claims)

    return {
        "insureds": insureds,
        "vehicles": vehicles,
        "repair_shops": shops,
        "policies": policies,
        "claims": claims,
        "estimates": estimates,
        "police_reports": police_reports,
        "documents": documents,
        "workflow_tasks": workflow_tasks,
    }


if __name__ == "__main__":
    data = generate_car_data()
    print(f"\n✅ Generated:")
    print(f"  {len(data['insureds'])} insureds")
    print(f"  {len(data['vehicles'])} vehicles")
    print(f"  {len(data['policies'])} policies")
    print(f"  {len(data['claims'])} claims")
    print(f"  {len(data['estimates'])} estimates")
    fraud = [c for c in data['claims'] if c.fraud_scenario]
    print(f"  {len(fraud)} fraud scenarios: {[c.claim_id for c in fraud]}")
    fp = [c for c in data['claims'] if c.false_positive_scenario]
    print(f"  {len(fp)} false positives: {[c.claim_id for c in fp]}")
