"""Generate 200 travel insurance claims with 5 embedded fraud scenarios for Zurich Travel Guard."""

import random
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta


# ── Entity Dataclasses ───────────────────────────────────────────────────────

@dataclass
class Traveler:
    traveler_id: str
    first_name: str
    last_name: str
    dob: str
    gender: str
    email: str
    phone: str
    passport_country: str
    address_state: str
    loyalty_tier: str = "standard"  # standard, silver, gold, platinum
    claim_history_count: int = 0
    flagged: bool = False
    notes: str = ""

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


@dataclass
class Companion:
    companion_id: str
    traveler_id: str
    first_name: str
    last_name: str
    relationship: str  # spouse, child, friend, parent
    dob: str


@dataclass
class Destination:
    destination_id: str
    country: str
    city: str
    region: str  # caribbean, europe, asia, latin_america, africa, oceania, north_america
    risk_level: str  # low, medium, high
    avg_medical_cost_per_day: float
    known_fraud_ring: bool = False
    seasonal_peak: str = ""  # summer, winter, spring


@dataclass
class Airline:
    airline_id: str
    name: str
    iata_code: str
    region: str
    on_time_rate: float = 0.82


@dataclass
class Hotel:
    hotel_id: str
    name: str
    destination_id: str
    star_rating: int
    avg_nightly_rate: float


@dataclass
class MedicalProvider:
    provider_id: str
    name: str
    provider_type: str  # hospital, clinic, pharmacy, dental
    destination_id: str
    on_watchlist: bool = False
    verified: bool = True
    notes: str = ""


@dataclass
class TravelAgent:
    agent_id: str
    name: str
    agency_name: str
    policies_sold: int = 0
    fraud_referrals: int = 0


@dataclass
class TravelPolicy:
    policy_id: str
    traveler_id: str
    plan_type: str  # single_trip, annual_multi, group
    purchase_date: str
    trip_start_date: str
    trip_end_date: str
    destination_id: str
    coverage_trip_cancel: float = 10000.0
    coverage_medical: float = 100000.0
    coverage_baggage: float = 2500.0
    coverage_delay: float = 1000.0
    premium: float = 0.0
    status: str = "active"
    agent_id: Optional[str] = None


@dataclass
class BookingRecord:
    booking_id: str
    policy_id: str
    booking_type: str  # flight, hotel, cruise, tour
    booking_reference: str
    provider_name: str  # airline name or hotel name
    amount: float
    booking_date: str
    confirmed: bool = True


@dataclass
class FlightRecord:
    flight_id: str
    airline_id: str
    flight_number: str
    origin: str
    destination: str
    scheduled_departure: str
    actual_departure: str
    delay_minutes: int = 0
    cancelled: bool = False


@dataclass
class DocumentMetadata:
    doc_id: str
    claim_id: str
    doc_type: str  # receipt, medical_report, police_report, boarding_pass, booking_confirmation, hotel_invoice
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
    task_type: str  # INITIAL_REVIEW, DOCUMENT_REQUEST, BOOKING_VERIFICATION, MEDICAL_REVIEW
    status: str = "pending"
    assigned_date: Optional[str] = None
    due_date: Optional[str] = None
    completed_date: Optional[str] = None
    days_waiting: int = 0
    notes: str = ""


@dataclass
class TravelClaim:
    claim_id: str
    claim_type: str  # trip_cancellation, trip_interruption, medical_emergency, baggage_loss, travel_delay
    traveler_id: str
    companion_id: Optional[str] = None
    policy_id: str = ""
    destination_id: str = ""
    provider_id: Optional[str] = None  # Medical provider if medical claim
    airline_id: Optional[str] = None
    hotel_id: Optional[str] = None
    flight_id: Optional[str] = None
    booking_id: Optional[str] = None
    date_filed: str = ""
    date_of_incident: str = ""
    claim_amount: float = 0.0
    approved_amount: float = 0.0
    status: str = "new"
    claim_source: str = "online_portal"
    cancellation_reason: str = ""  # illness, weather, family_emergency, work, fear_of_travel
    baggage_items: List[str] = field(default_factory=list)
    delay_hours: float = 0.0
    medical_diagnosis: str = ""
    fraud_scenario: Optional[str] = None
    false_positive_scenario: Optional[str] = None
    notes: str = ""
    is_resubmission: bool = False
    original_claim_id: Optional[str] = None
    photo_evidence: bool = False  # True when an evidence image (e.g. luggage photo) is on file


# ── Name / Data Pools ────────────────────────────────────────────────────────

FIRST_NAMES_M = ["James", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas",
                 "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Donald",
                 "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian", "George",
                 "Timothy", "Ronald"]

FIRST_NAMES_F = ["Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
                 "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra",
                 "Ashley", "Dorothy", "Kimberly", "Emily", "Donna", "Michelle", "Carol",
                 "Amanda", "Melissa", "Deborah"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson",
              "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson",
              "White", "Harris", "Clark", "Lewis", "Robinson", "Walker", "Young", "King", "Wright"]

US_STATES = ["NY", "CA", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "NJ", "VA", "WA", "MA", "AZ", "CO"]

DESTINATIONS = [
    ("Cancún", "Mexico", "latin_america", "high", 1800.0, True, "winter"),
    ("Bangkok", "Thailand", "asia", "medium", 600.0, False, "winter"),
    ("Paris", "France", "europe", "low", 2200.0, False, "summer"),
    ("London", "United Kingdom", "europe", "low", 2500.0, False, "summer"),
    ("Rome", "Italy", "europe", "low", 1900.0, False, "spring"),
    ("Punta Cana", "Dominican Republic", "caribbean", "high", 1500.0, True, "winter"),
    ("Tokyo", "Japan", "asia", "low", 2800.0, False, "spring"),
    ("Bali", "Indonesia", "asia", "medium", 500.0, False, "summer"),
    ("Barcelona", "Spain", "europe", "low", 2000.0, False, "summer"),
    ("Cabo San Lucas", "Mexico", "latin_america", "medium", 1600.0, False, "winter"),
    ("Montego Bay", "Jamaica", "caribbean", "high", 1400.0, True, "winter"),
    ("Bogotá", "Colombia", "latin_america", "medium", 700.0, False, ""),
    ("Sydney", "Australia", "oceania", "low", 3000.0, False, "winter"),
    ("Dubai", "UAE", "asia", "low", 3500.0, False, "winter"),
    ("Nairobi", "Kenya", "africa", "high", 900.0, False, "summer"),
]

AIRLINES = [
    ("United Airlines", "UA", "north_america", 0.79),
    ("Delta Air Lines", "DL", "north_america", 0.83),
    ("American Airlines", "AA", "north_america", 0.77),
    ("Southwest Airlines", "WN", "north_america", 0.80),
    ("JetBlue Airways", "B6", "north_america", 0.76),
    ("British Airways", "BA", "europe", 0.81),
    ("Lufthansa", "LH", "europe", 0.84),
    ("Air France", "AF", "europe", 0.78),
    ("Emirates", "EK", "asia", 0.86),
    ("AeroMexico", "AM", "latin_america", 0.72),
]

HOTELS = [
    ("Grand Hyatt Resort", 5, 450.0),
    ("Marriott Beachfront", 4, 320.0),
    ("Holiday Inn Express", 3, 140.0),
    ("Hilton Garden Inn", 4, 260.0),
    ("Best Western Plus", 3, 110.0),
    ("Ritz-Carlton", 5, 680.0),
    ("Courtyard by Marriott", 3, 180.0),
    ("Four Seasons Resort", 5, 890.0),
    ("Hampton Inn", 3, 130.0),
    ("W Hotel", 4, 380.0),
]

MEDICAL_PROVIDERS_NAMES = [
    ("Hospital General de Cancún", "hospital"),
    ("Clínica Internacional Playa", "clinic"),
    ("Bangkok International Hospital", "hospital"),
    ("Hôpital Américain de Paris", "hospital"),
    ("London Bridge Hospital", "hospital"),
    ("Policlinico Gemelli Roma", "hospital"),
    ("Punta Cana Medical Center", "clinic"),
    ("Bumrungrad Hospital Bangkok", "hospital"),
    ("Hospital CIMA Cabo", "hospital"),
    ("MoBay Hope Medical", "clinic"),
    ("Bogotá Medical Clinic", "clinic"),
    ("Royal Prince Alfred Hospital Sydney", "hospital"),
    ("American Hospital Dubai", "hospital"),
    ("Nairobi Hospital", "hospital"),
    ("Caribbean Dental Clinic", "dental"),
]

TRAVEL_AGENCIES = [
    ("Sarah Mitchell", "Virtuoso Travel"),
    ("James Chen", "AAA Travel"),
    ("Maria Santos", "Expedia Cruises"),
    ("Robert Kim", "Travel Leaders"),
    ("Jennifer Walsh", "Costco Travel"),
]

CANCELLATION_REASONS = ["illness", "weather", "family_emergency", "work_conflict", "fear_of_travel",
                        "airline_schedule_change", "natural_disaster", "jury_duty"]

MEDICAL_DIAGNOSES = ["food_poisoning", "broken_bone", "dehydration", "allergic_reaction",
                     "chest_pain", "dengue_fever", "appendicitis", "diving_injury",
                     "heatstroke", "infection", "dental_emergency"]

BAGGAGE_ITEMS_POOL = [
    ("Samsonite suitcase", 350), ("Designer sunglasses", 400), ("Laptop", 1200),
    ("Camera equipment", 2500), ("Jewelry", 3000), ("Designer handbag", 2200),
    ("Watch (Rolex)", 8500), ("Watch (Seiko)", 350), ("Clothing items", 600),
    ("Toiletries and medications", 150), ("Books and electronics", 400),
    ("Sports equipment", 800), ("Business documents", 200), ("Shoes (2 pairs)", 300),
    ("Headphones (Sony)", 350), ("Tablet (iPad)", 900), ("Perfume collection", 500),
    ("Winter jacket (Canada Goose)", 1100), ("Golf clubs", 2000), ("Scuba gear", 1500),
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _seed():
    random.seed(77)


def _rand_date(start_str: str, end_str: str) -> str:
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    delta = (end - start).days
    if delta <= 0:
        return start_str
    return (start + timedelta(days=random.randint(0, delta))).strftime("%Y-%m-%d")


def _rand_dob(min_age=25, max_age=68):
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


def _claim_amount(claim_type):
    ranges = {
        "trip_cancellation": (800, 12000),
        "trip_interruption": (500, 8000),
        "medical_emergency": (1000, 80000),
        "baggage_loss": (300, 3500),
        "travel_delay": (150, 1200),
    }
    lo, hi = ranges.get(claim_type, (200, 5000))
    return round(random.uniform(lo, hi), 2)


def _pick_source(weights):
    sources = list(weights.keys())
    w = list(weights.values())
    return random.choices(sources, weights=w, k=1)[0]


# ── Generate All Entities ────────────────────────────────────────────────────

def _generate_destinations() -> List[Destination]:
    destinations = []
    for i, (city, country, region, risk, med_cost, fraud_ring, peak) in enumerate(DESTINATIONS):
        destinations.append(Destination(
            destination_id=f"DST-{i+1:03d}",
            country=country,
            city=city,
            region=region,
            risk_level=risk,
            avg_medical_cost_per_day=med_cost,
            known_fraud_ring=fraud_ring,
            seasonal_peak=peak,
        ))
    return destinations


def _generate_airlines() -> List[Airline]:
    airlines = []
    for i, (name, iata, region, otr) in enumerate(AIRLINES):
        airlines.append(Airline(
            airline_id=f"AIR-{i+1:03d}",
            name=name,
            iata_code=iata,
            region=region,
            on_time_rate=otr,
        ))
    return airlines


def _generate_hotels(destinations: List[Destination]) -> List[Hotel]:
    hotels = []
    h_id = 1
    for dest in destinations:
        # 2-3 hotels per destination
        num = random.randint(2, 3)
        for _ in range(num):
            name, stars, rate = random.choice(HOTELS)
            hotels.append(Hotel(
                hotel_id=f"HTL-{h_id:03d}",
                name=f"{name} {dest.city}",
                destination_id=dest.destination_id,
                star_rating=stars,
                avg_nightly_rate=rate * (1 + random.uniform(-0.2, 0.3)),
            ))
            h_id += 1
    return hotels


def _generate_medical_providers(destinations: List[Destination]) -> List[MedicalProvider]:
    providers = []
    for i, (name, ptype) in enumerate(MEDICAL_PROVIDERS_NAMES):
        dest = destinations[i % len(destinations)]
        providers.append(MedicalProvider(
            provider_id=f"MPR-{i+1:03d}",
            name=name,
            provider_type=ptype,
            destination_id=dest.destination_id,
            verified=(i < 12),  # Last 3 are unverified
        ))
    return providers


def _generate_travel_agents() -> List[TravelAgent]:
    agents = []
    for i, (name, agency) in enumerate(TRAVEL_AGENCIES):
        agents.append(TravelAgent(
            agent_id=f"AGT-{i+1:03d}",
            name=name,
            agency_name=agency,
            policies_sold=random.randint(50, 500),
        ))
    return agents


def _generate_travelers(count: int) -> List[Traveler]:
    travelers = []
    for i in range(count):
        gender = _rand_gender()
        first, last = _rand_name(gender)
        state = random.choice(US_STATES)
        travelers.append(Traveler(
            traveler_id=f"TRV-{i+1:04d}",
            first_name=first,
            last_name=last,
            dob=_rand_dob(),
            gender=gender,
            email=f"{first.lower()}.{last.lower()}@email.com",
            phone=f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}",
            passport_country="US",
            address_state=state,
            loyalty_tier=random.choices(
                ["standard", "silver", "gold", "platinum"],
                weights=[0.6, 0.2, 0.15, 0.05], k=1
            )[0],
        ))
    return travelers


def _generate_companions(travelers: List[Traveler]) -> List[Companion]:
    companions = []
    comp_id = 1
    for traveler in travelers:
        if random.random() < 0.4:  # 40% travel with companion
            gender = _rand_gender()
            first, last = _rand_name(gender)
            rel = random.choice(["spouse", "child", "friend", "parent"])
            companions.append(Companion(
                companion_id=f"CMP-{comp_id:04d}",
                traveler_id=traveler.traveler_id,
                first_name=first,
                last_name=last if random.random() < 0.4 else traveler.last_name,
                relationship=rel,
                dob=_rand_dob(min_age=5, max_age=75),
            ))
            comp_id += 1
    return companions


def _generate_policies(
    travelers: List[Traveler],
    destinations: List[Destination],
    agents: List[TravelAgent],
) -> List[TravelPolicy]:
    policies = []
    pol_id = 1
    for traveler in travelers:
        # 1-3 trips per traveler
        num_trips = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15], k=1)[0]
        for _ in range(num_trips):
            dest = random.choice(destinations)
            purchase_date = _rand_date("2025-09-01", "2026-02-28")
            trip_start = _rand_date(purchase_date, "2026-03-15")
            trip_days = random.randint(4, 14)
            trip_end = (datetime.strptime(trip_start, "%Y-%m-%d") + timedelta(days=trip_days)).strftime("%Y-%m-%d")

            plan_type = random.choices(
                ["single_trip", "annual_multi", "group"],
                weights=[0.7, 0.2, 0.1], k=1
            )[0]

            base_premium = random.uniform(50, 400)
            # Higher risk destinations cost more
            if dest.risk_level == "high":
                base_premium *= 1.4
            elif dest.risk_level == "medium":
                base_premium *= 1.15

            agent = random.choice(agents) if random.random() < 0.3 else None

            policies.append(TravelPolicy(
                policy_id=f"TPL-{pol_id:04d}",
                traveler_id=traveler.traveler_id,
                plan_type=plan_type,
                purchase_date=purchase_date,
                trip_start_date=trip_start,
                trip_end_date=trip_end,
                destination_id=dest.destination_id,
                coverage_trip_cancel=random.choice([5000, 10000, 15000, 20000]),
                coverage_medical=random.choice([50000, 100000, 250000, 500000]),
                coverage_baggage=random.choice([1500, 2500, 5000]),
                coverage_delay=random.choice([500, 1000, 1500]),
                premium=round(base_premium, 2),
                status="active",
                agent_id=agent.agent_id if agent else None,
            ))
            pol_id += 1
    return policies


def _generate_bookings(policies: List[TravelPolicy], airlines: List[Airline], hotels: List[Hotel]) -> List[BookingRecord]:
    bookings = []
    bk_id = 1
    for policy in policies:
        # Flight booking
        airline = random.choice(airlines)
        bookings.append(BookingRecord(
            booking_id=f"BKG-{bk_id:04d}",
            policy_id=policy.policy_id,
            booking_type="flight",
            booking_reference=f"{airline.iata_code}{random.randint(1000,9999)}",
            provider_name=airline.name,
            amount=round(random.uniform(300, 2500), 2),
            booking_date=policy.purchase_date,
            confirmed=True,
        ))
        bk_id += 1

        # Hotel booking (80% of trips)
        if random.random() < 0.8:
            dest_hotels = [h for h in hotels if h.destination_id == policy.destination_id]
            hotel = random.choice(dest_hotels) if dest_hotels else random.choice(hotels)
            trip_days = (datetime.strptime(policy.trip_end_date, "%Y-%m-%d") -
                        datetime.strptime(policy.trip_start_date, "%Y-%m-%d")).days
            bookings.append(BookingRecord(
                booking_id=f"BKG-{bk_id:04d}",
                policy_id=policy.policy_id,
                booking_type="hotel",
                booking_reference=f"H{random.randint(100000, 999999)}",
                provider_name=hotel.name,
                amount=round(hotel.avg_nightly_rate * trip_days, 2),
                booking_date=policy.purchase_date,
                confirmed=True,
            ))
            bk_id += 1
    return bookings


def _generate_flights(policies: List[TravelPolicy], airlines: List[Airline]) -> List[FlightRecord]:
    flights = []
    fl_id = 1
    for policy in policies:
        airline = random.choice(airlines)
        # Outbound flight
        delay = 0
        if random.random() < 0.12:  # 12% of flights have some delay
            delay = random.choices(
                [30, 60, 120, 240, 480, 720],
                weights=[0.4, 0.25, 0.15, 0.1, 0.07, 0.03], k=1
            )[0]
        flights.append(FlightRecord(
            flight_id=f"FLT-{fl_id:04d}",
            airline_id=airline.airline_id,
            flight_number=f"{airline.iata_code}{random.randint(100, 9999)}",
            origin="JFK",  # Simplified
            destination=policy.destination_id,
            scheduled_departure=policy.trip_start_date,
            actual_departure=policy.trip_start_date,  # Simplified — delay applied in minutes
            delay_minutes=delay,
            cancelled=(random.random() < 0.02),
        ))
        fl_id += 1
    return flights


def _generate_documents(claims: List[TravelClaim]) -> List[DocumentMetadata]:
    docs = []
    doc_id = 1
    for claim in claims:
        doc_types_for_type = {
            "trip_cancellation": ["booking_confirmation", "cancellation_notice"],
            "trip_interruption": ["booking_confirmation", "receipt"],
            "medical_emergency": ["medical_report", "receipt", "boarding_pass"],
            "baggage_loss": ["police_report", "receipt", "boarding_pass"],
            "travel_delay": ["boarding_pass", "receipt"],
        }
        for dtype in doc_types_for_type.get(claim.claim_type, ["receipt"]):
            docs.append(DocumentMetadata(
                doc_id=f"DOC-{doc_id:04d}",
                claim_id=claim.claim_id,
                doc_type=dtype,
                provider_name="Various",
                date_created=claim.date_of_incident or claim.date_filed,
                received_date=claim.date_filed,
                amount_on_doc=claim.claim_amount / len(doc_types_for_type.get(claim.claim_type, ["receipt"])),
            ))
            doc_id += 1
    return docs


def _generate_workflow_tasks(claims: List[TravelClaim]) -> List[WorkflowTask]:
    tasks = []
    task_id = 1
    for claim in claims:
        # Every claim gets INITIAL_REVIEW
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

        # Medical claims get MEDICAL_REVIEW
        if claim.claim_type == "medical_emergency" and random.random() < 0.7:
            tasks.append(WorkflowTask(
                task_id=f"TSK-{task_id:04d}",
                claim_id=claim.claim_id,
                task_type="MEDICAL_REVIEW",
                status="pending",
                assigned_date=assigned,
                due_date=(datetime.strptime(assigned, "%Y-%m-%d") + timedelta(days=14)).strftime("%Y-%m-%d"),
                days_waiting=random.randint(0, 10),
            ))
            task_id += 1

        # Trip cancellation gets BOOKING_VERIFICATION
        if claim.claim_type in ("trip_cancellation", "trip_interruption") and random.random() < 0.6:
            tasks.append(WorkflowTask(
                task_id=f"TSK-{task_id:04d}",
                claim_id=claim.claim_id,
                task_type="BOOKING_VERIFICATION",
                status="pending",
                assigned_date=assigned,
                due_date=(datetime.strptime(assigned, "%Y-%m-%d") + timedelta(days=5)).strftime("%Y-%m-%d"),
                days_waiting=random.randint(0, 4),
            ))
            task_id += 1
    return tasks


# ── Claim Generation ─────────────────────────────────────────────────────────

SOURCE_WEIGHTS = {"online_portal": 0.45, "mobile_app": 0.25, "call_center": 0.20, "travel_agent": 0.10}


def _generate_base_claims(
    travelers: List[Traveler],
    companions: List[Companion],
    policies: List[TravelPolicy],
    destinations: List[Destination],
    providers: List[MedicalProvider],
    airlines: List[Airline],
    hotels: List[Hotel],
    flights: List[FlightRecord],
    bookings: List[BookingRecord],
) -> List[TravelClaim]:
    """Generate 200 base travel claims distributed across claim types."""
    claims = []
    claim_counts = {
        "trip_cancellation": 50,
        "trip_interruption": 30,
        "medical_emergency": 50,
        "baggage_loss": 40,
        "travel_delay": 30,
    }
    prefixes = {"trip_cancellation": "TC", "trip_interruption": "TI",
                "medical_emergency": "ME", "baggage_loss": "BL", "travel_delay": "TD"}

    # Build traveler->policy mapping
    traveler_policies = {}
    for p in policies:
        traveler_policies.setdefault(p.traveler_id, []).append(p)

    traveler_companions = {}
    for c in companions:
        traveler_companions.setdefault(c.traveler_id, []).append(c)

    policy_bookings = {}
    for b in bookings:
        policy_bookings.setdefault(b.policy_id, []).append(b)

    policy_flights = {}
    for f in flights:
        # Map by destination
        policy_flights.setdefault(f.destination, []).append(f)

    for claim_type, count in claim_counts.items():
        prefix = prefixes[claim_type]
        type_id = 1
        for _ in range(count):
            traveler = random.choice(travelers)
            t_policies = traveler_policies.get(traveler.traveler_id, [])
            if not t_policies:
                continue
            policy = random.choice(t_policies)
            dest = next((d for d in destinations if d.destination_id == policy.destination_id), random.choice(destinations))

            # Find associated bookings/flights
            p_bookings = policy_bookings.get(policy.policy_id, [])
            flight_booking = next((b for b in p_bookings if b.booking_type == "flight"), None)
            d_flights = policy_flights.get(policy.destination_id, [])
            flight = random.choice(d_flights) if d_flights else None

            # Companions
            comps = traveler_companions.get(traveler.traveler_id, [])
            companion = random.choice(comps) if comps and random.random() < 0.2 else None

            date_filed = _rand_date(policy.trip_start_date, "2026-03-15")
            incident_date = _rand_date(policy.trip_start_date, date_filed) if date_filed > policy.trip_start_date else policy.trip_start_date

            # Type-specific fields
            cancellation_reason = ""
            baggage_items = []
            delay_hours = 0.0
            medical_diagnosis = ""
            provider_id = None
            airline_id = None
            hotel_id = None
            flight_id = None
            booking_id = flight_booking.booking_id if flight_booking else None

            if claim_type == "trip_cancellation":
                cancellation_reason = random.choice(CANCELLATION_REASONS)
                incident_date = _rand_date(policy.purchase_date, policy.trip_start_date)
            elif claim_type == "trip_interruption":
                cancellation_reason = random.choice(["illness", "family_emergency", "natural_disaster"])
            elif claim_type == "medical_emergency":
                medical_diagnosis = random.choice(MEDICAL_DIAGNOSES)
                dest_providers = [p for p in providers if p.destination_id == dest.destination_id]
                provider = random.choice(dest_providers) if dest_providers else random.choice(providers)
                provider_id = provider.provider_id
            elif claim_type == "baggage_loss":
                num_items = random.randint(3, 7)
                items = random.sample(BAGGAGE_ITEMS_POOL, min(num_items, len(BAGGAGE_ITEMS_POOL)))
                baggage_items = [item[0] for item in items]
                airline_id = flight.airline_id if flight else random.choice(airlines).airline_id
                flight_id = flight.flight_id if flight else None
            elif claim_type == "travel_delay":
                delay_hours = random.choice([4, 6, 8, 10, 12, 16, 20, 24])
                airline_id = flight.airline_id if flight else random.choice(airlines).airline_id
                flight_id = flight.flight_id if flight else None

            claims.append(TravelClaim(
                claim_id=f"{prefix}-{type_id:03d}",
                claim_type=claim_type,
                traveler_id=traveler.traveler_id,
                companion_id=companion.companion_id if companion else None,
                policy_id=policy.policy_id,
                destination_id=dest.destination_id,
                provider_id=provider_id,
                airline_id=airline_id,
                hotel_id=hotel_id,
                flight_id=flight_id,
                booking_id=booking_id,
                date_filed=date_filed,
                date_of_incident=incident_date,
                claim_amount=_claim_amount(claim_type),
                claim_source=_pick_source(SOURCE_WEIGHTS),
                cancellation_reason=cancellation_reason,
                baggage_items=baggage_items,
                delay_hours=delay_hours,
                medical_diagnosis=medical_diagnosis,
            ))
            type_id += 1
    return claims


# ── Fraud Scenarios ──────────────────────────────────────────────────────────

def _inject_fraud_scenarios(
    claims: List[TravelClaim],
    travelers: List[Traveler],
    policies: List[TravelPolicy],
    destinations: List[Destination],
    providers: List[MedicalProvider],
    bookings: List[BookingRecord],
    flights: List[FlightRecord],
) -> None:
    """Inject 5 hero fraud cases into the travel claims."""

    # ── ME-101: Destination Fraud Ring — $42K hospital bill in Cancún from watchlist provider
    me_claims = [c for c in claims if c.claim_type == "medical_emergency" and c.fraud_scenario is None]
    cancun_dest = next((d for d in destinations if d.city == "Cancún"), destinations[0])
    watchlist_provider = next((p for p in providers if "Cancún" in p.name or p.destination_id == cancun_dest.destination_id), providers[0])
    watchlist_provider.on_watchlist = True
    watchlist_provider.verified = False
    watchlist_provider.notes = "WATCHLIST: Multiple fraudulent claims linked to this facility"

    if me_claims:
        hero = me_claims[0]
        hero.claim_id = "ME-101"  # Override ID for demo
        hero.fraud_scenario = "destination_fraud_ring"
        hero.claim_amount = 42350.00
        hero.destination_id = cancun_dest.destination_id
        hero.provider_id = watchlist_provider.provider_id
        hero.medical_diagnosis = "appendicitis"
        hero.notes = "$42K hospital bill in Cancún from watchlisted provider. Destination known for coordinated fraud ring."
        hero.traveler_id = travelers[0].traveler_id
        travelers[0].flagged = True
        travelers[0].notes = "FRAUD_SCENARIO: Destination fraud ring — Cancún hospital"

    # ── TC-202: Phantom Booking — $6K cancellation claim with no actual booking
    tc_claims = [c for c in claims if c.claim_type == "trip_cancellation" and c.fraud_scenario is None]
    if tc_claims:
        hero = tc_claims[0]
        hero.claim_id = "TC-202"
        hero.fraud_scenario = "phantom_booking"
        hero.claim_amount = 6200.00
        hero.booking_id = None  # No booking exists
        hero.cancellation_reason = "illness"
        hero.notes = "Trip cancellation claim with NO matching booking confirmation. Traveler cannot produce airline or hotel records."
        hero.traveler_id = travelers[1].traveler_id
        travelers[1].notes = "FRAUD_SCENARIO: Phantom booking — no confirmation exists"
        # Remove any bookings for this traveler's policy
        hero_policy = hero.policy_id
        for b in bookings:
            if b.policy_id == hero_policy:
                b.confirmed = False

    # ── BL-303: Luxury Baggage Padding — $15K claim for designer items in lost bag
    bl_claims = [c for c in claims if c.claim_type == "baggage_loss" and c.fraud_scenario is None]
    if bl_claims:
        hero = bl_claims[0]
        hero.claim_id = "BL-303"
        hero.fraud_scenario = "baggage_padding"
        hero.claim_amount = 15200.00
        hero.baggage_items = [
            "Rolex Submariner watch",
            "Louis Vuitton carry-on bag",
            "MacBook Pro 16-inch",
            "Bose noise-cancelling headphones",
            "Designer sunglasses (Prada)",
            "Cashmere sweater (Brunello Cucinelli)",
            "Gold jewelry set",
        ]
        hero.notes = "Baggage claim 6x average value. All luxury items, no purchase receipts provided. Claim exceeds policy coverage limit. Damaged-luggage photo submitted as evidence."
        hero.photo_evidence = True  # luggage photo on file (images/bl303.png) → triggers R-011 forensic review
        hero.traveler_id = travelers[2].traveler_id
        travelers[2].notes = "FRAUD_SCENARIO: Luxury baggage padding"

    # ── TD-404: Fabricated Delay — Claims 22-hour delay but flight was on time
    td_claims = [c for c in claims if c.claim_type == "travel_delay" and c.fraud_scenario is None]
    if td_claims:
        hero = td_claims[0]
        hero.claim_id = "TD-404"
        hero.fraud_scenario = "fabricated_delay"
        hero.claim_amount = 1150.00
        hero.delay_hours = 22.0
        hero.notes = "Claims 22-hour delay. IATA FlightStats shows flight departed on-time (0 min delay). No corroborating evidence."
        hero.traveler_id = travelers[3].traveler_id
        travelers[3].notes = "FRAUD_SCENARIO: Fabricated delay — flight was on-time"
        # Ensure the flight record shows NO delay
        if hero.flight_id:
            matching_flight = next((f for f in flights if f.flight_id == hero.flight_id), None)
            if matching_flight:
                matching_flight.delay_minutes = 0
                matching_flight.cancelled = False

    # ── ME-505: Serial Claimer — 8th medical claim in 14 months
    if len(me_claims) > 5:
        hero = me_claims[5]
        hero.claim_id = "ME-505"
        hero.fraud_scenario = "serial_claimer"
        hero.claim_amount = 8900.00
        hero.medical_diagnosis = "food_poisoning"
        hero.notes = "8th medical emergency claim in 14 months. Pattern: always files within 3 days of trip start, always food poisoning or dehydration."
        hero.traveler_id = travelers[4].traveler_id
        travelers[4].claim_history_count = 8
        travelers[4].flagged = True
        travelers[4].notes = "FRAUD_SCENARIO: Serial claimer — 8 medical claims in 14 months"


# ── False Positives ──────────────────────────────────────────────────────────

def _inject_false_positives(claims: List[TravelClaim], travelers: List[Traveler]) -> None:
    """Add 3 false positives to test examiner judgment."""

    # FP1: Legitimate high-value baggage (frequent business traveler with receipts)
    # Pin to BL-040 so its luggage photo (images/bl040.png) maps deterministically.
    bl_claims = [c for c in claims if c.claim_type == "baggage_loss" and c.fraud_scenario is None]
    fp = next((c for c in bl_claims if c.claim_id == "BL-040"), bl_claims[-1] if bl_claims else None)
    if fp:
        fp.false_positive_scenario = "legitimate_high_value_traveler"
        fp.claim_amount = 4200.00
        fp.baggage_items = ["Laptop (work-issued)", "Business suit", "Presentation materials", "Tablet"]
        fp.notes = "High-value claim but traveler is platinum-tier business flyer with purchase receipts for all items. Damaged-luggage photo submitted as evidence."
        fp.photo_evidence = True  # luggage photo on file (images/bl040.png) → triggers R-011 forensic review
        fp.traveler_id = travelers[-1].traveler_id
        travelers[-1].loyalty_tier = "platinum"

    # FP2: Legitimate medical - elderly traveler with pre-existing but covered condition
    me_claims = [c for c in claims if c.claim_type == "medical_emergency" and c.fraud_scenario is None]
    if me_claims:
        fp = me_claims[-1]
        fp.false_positive_scenario = "legitimate_elderly_medical"
        fp.claim_amount = 35000.00
        fp.medical_diagnosis = "chest_pain"
        fp.notes = "High-cost medical claim for 72-year-old traveler. Pre-existing condition declared and covered under policy upgrade."

    # FP3: Legitimate delay — well-documented weather event
    td_claims = [c for c in claims if c.claim_type == "travel_delay" and c.fraud_scenario is None]
    if td_claims:
        fp = td_claims[-1]
        fp.false_positive_scenario = "legitimate_weather_delay"
        fp.delay_hours = 18.0
        fp.claim_amount = 950.00
        fp.notes = "18-hour delay due to Hurricane season. Airport-wide ground stop confirmed by FAA records."


# ── Main Generator ───────────────────────────────────────────────────────────

def generate_travel_data() -> Dict:
    """Generate all travel insurance data. Returns dict of entity lists."""
    _seed()

    print("  Generating destinations...")
    destinations = _generate_destinations()

    print("  Generating airlines...")
    airlines = _generate_airlines()

    print("  Generating hotels...")
    hotels = _generate_hotels(destinations)

    print("  Generating medical providers...")
    providers = _generate_medical_providers(destinations)

    print("  Generating travel agents...")
    agents = _generate_travel_agents()

    print("  Generating travelers (50)...")
    travelers = _generate_travelers(50)

    print("  Generating companions...")
    companions = _generate_companions(travelers)

    print("  Generating policies...")
    policies = _generate_policies(travelers, destinations, agents)

    print("  Generating bookings...")
    bookings = _generate_bookings(policies, airlines, hotels)

    print("  Generating flights...")
    flights = _generate_flights(policies, airlines)

    print("  Generating 200 travel claims...")
    claims = _generate_base_claims(
        travelers, companions, policies, destinations,
        providers, airlines, hotels, flights, bookings,
    )

    print("  Injecting 5 fraud scenarios...")
    _inject_fraud_scenarios(claims, travelers, policies, destinations, providers, bookings, flights)

    print("  Injecting 3 false positives...")
    _inject_false_positives(claims, travelers)

    print("  Generating documents...")
    documents = _generate_documents(claims)

    print("  Generating workflow tasks...")
    workflow_tasks = _generate_workflow_tasks(claims)

    return {
        "destinations": destinations,
        "airlines": airlines,
        "hotels": hotels,
        "providers": providers,
        "travel_agents": agents,
        "travelers": travelers,
        "companions": companions,
        "policies": policies,
        "bookings": bookings,
        "flights": flights,
        "claims": claims,
        "documents": documents,
        "workflow_tasks": workflow_tasks,
    }


if __name__ == "__main__":
    data = generate_travel_data()
    print(f"\n✅ Generated:")
    print(f"  {len(data['travelers'])} travelers")
    print(f"  {len(data['destinations'])} destinations")
    print(f"  {len(data['policies'])} policies")
    print(f"  {len(data['claims'])} claims")
    print(f"  {len(data['documents'])} documents")
    fraud = [c for c in data['claims'] if c.fraud_scenario]
    print(f"  {len(fraud)} fraud scenarios: {[c.claim_id for c in fraud]}")
    fp = [c for c in data['claims'] if c.false_positive_scenario]
    print(f"  {len(fp)} false positives")
