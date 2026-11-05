"""Generate ~40 marine cargo claims with embedded fraud scenarios for the Marine Cargo copilot.

All company names, people, vessels and addresses are FICTIONAL.

Entities (car → marine):
  - Party (consignee / assured claimant)     ← Insured
  - Shipment (B/L, containers, seals, VGM)   ← Vehicle
  - Surveyor (panel / assured-appointed)     ← RepairShop
  - Forwarder, Shipper, Director             (network entities)
  - CargoPolicy (open cover, ICC clause)     ← CarPolicy
  - SurveyReport                             ← RepairEstimate
  - MarineClaim                              ← CarClaim

Returns a dict keyed by entity name; this becomes DataContext.supplemental_data.
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta


# The data's "today" — claims filed on this date appear under the Today tab.
DEMO_TODAY = datetime(2026, 10, 2)


# ── Entity Dataclasses ───────────────────────────────────────────────────────

@dataclass
class Director:
    director_id: str
    full_name: str
    nationality: str = "Filipino"


@dataclass
class Party:
    """Consignee / assured — the claimant."""
    party_id: str
    name: str
    city: str
    country: str
    registered_address: str
    director_ids: List[str] = field(default_factory=list)
    incorporated: str = ""
    shipments_per_year: int = 40
    claim_history_count: int = 0          # prior closed claims in the last 24 months
    flagged: bool = False
    notes: str = ""

    @property
    def full_name(self):
        return self.name


@dataclass
class Shipper:
    shipper_id: str
    name: str
    city: str = "Singapore"
    country: str = "SG"
    incorporated: str = ""
    notes: str = ""


@dataclass
class Surveyor:
    surveyor_id: str
    name: str
    city: str
    insurer_panel: bool = True            # on the insurer's approved panel
    on_watchlist: bool = False
    registered_address: str = ""
    director_ids: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class Forwarder:
    forwarder_id: str
    name: str
    city: str
    registered_address: str = ""
    director_ids: List[str] = field(default_factory=list)
    on_watchlist: bool = False
    notes: str = ""


@dataclass
class Container:
    container_no: str
    size_type: str                        # 20GP, 40HC
    seal_no_loading: str
    seal_no_discharge: str
    tare_kg: int
    vgm_kg: int                           # verified gross mass (SOLAS) at load port


@dataclass
class Shipment:
    shipment_id: str
    bl_number: str
    carrier: str
    vessel: str
    voyage: str
    port_of_loading: str
    port_of_discharge: str
    shipper_id: str
    consignee_id: str
    forwarder_id: str
    incoterm: str
    commodity: str
    unit: str                             # m2, t, unit
    quantity: float
    unit_price: float                     # USD per unit as invoiced
    invoice_no: str
    invoice_value: float                  # USD
    containers: List[Container] = field(default_factory=list)
    packages: int = 0
    package_type: str = ""
    gross_weight_bl_kg: int = 0           # as declared on the B/L (shipper's figures)
    bl_clause: str = "SHIPPER'S LOAD, STOW AND COUNT — SAID TO CONTAIN"
    shipped_on_board: str = ""
    discharge_date: str = ""
    gate_out_date: str = ""               # container delivered from terminal
    eir_remarks_discharge: str = "Clean — no exceptions. Seals intact."

    @property
    def total_vgm_kg(self) -> int:
        return sum(c.vgm_kg for c in self.containers)

    @property
    def total_tare_kg(self) -> int:
        return sum(c.tare_kg for c in self.containers)

    @property
    def vgm_cargo_kg(self) -> int:
        """Cargo weight implied by the VGM (gross minus container tare)."""
        return self.total_vgm_kg - self.total_tare_kg

    @property
    def seals_match(self) -> bool:
        return all(c.seal_no_loading == c.seal_no_discharge for c in self.containers)

    @property
    def description(self) -> str:
        sizes = {}
        for c in self.containers:
            sizes[c.size_type] = sizes.get(c.size_type, 0) + 1
        boxes = " + ".join(f"{n}×{st}" for st, n in sizes.items())
        return f"{boxes} {self.commodity.split(',')[0]} · {POL_CODES.get(self.port_of_loading, '')}→{POD_CODES.get(self.port_of_discharge, '')}"


@dataclass
class CargoPolicy:
    policy_id: str                        # insurance certificate no. (one per shipment)
    open_cover_no: str                    # the assured's annual open cover
    assured_id: str
    shipment_id: str
    clause: str                           # "ICC (A) 2009" etc.
    basis_of_valuation: str = "CIF + 10%"
    insured_value: float = 0.0
    excess: float = 1000.0
    effective_date: str = ""              # open cover period
    expiration_date: str = ""
    status: str = "active"


@dataclass
class SurveyReport:
    survey_id: str
    claim_id: str
    surveyor_id: str
    appointed_by: str                     # "insurer" or "assured"
    survey_date: str
    survey_location: str
    joint_with_carrier: bool = False
    cause_of_loss: str = ""
    damage_pct: float = 0.0
    photos: int = 0
    report_no: str = ""


@dataclass
class PriorClaim:
    """Closed/paid claims from earlier periods (not in the working queue)."""
    claim_id: str
    consignee_id: str
    surveyor_id: str
    claim_type: str
    amount_paid: float
    date_paid: str
    commodity: str


@dataclass
class DocumentMetadata:
    doc_id: str
    claim_id: str
    doc_type: str                         # bill_of_lading, commercial_invoice, packing_list, survey_report, eir, survey_photo
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
    task_type: str                        # INITIAL_REVIEW, SURVEY_APPOINTMENT, DOCUMENT_REVIEW, RECOVERY_NOTICE
    status: str = "pending"
    assigned_date: Optional[str] = None
    due_date: Optional[str] = None
    completed_date: Optional[str] = None
    days_waiting: int = 0
    notes: str = ""


@dataclass
class MarineClaim:
    claim_id: str
    claim_type: str                       # breakage, wet_damage, contamination, shortage, theft_pilferage
    consignee_id: str
    shipment_id: str = ""
    policy_id: str = ""
    surveyor_id: Optional[str] = None
    survey_id: Optional[str] = None
    date_filed: str = ""
    date_of_loss: str = ""                # date loss/damage discovered
    notice_to_insurer_date: str = ""
    notice_to_carrier_date: Optional[str] = None
    claim_amount: float = 0.0
    approved_amount: float = 0.0
    status: str = "new"
    claim_source: str = "broker"
    loss_description: str = ""
    fraud_scenario: Optional[str] = None
    false_positive_scenario: Optional[str] = None
    notes: str = ""
    is_resubmission: bool = False
    original_claim_id: Optional[str] = None
    photo_evidence: bool = False          # True when survey photos (images/<id>*.png) are on file

    # Compatibility alias — shared code refers to the claimant as insured_id.
    @property
    def insured_id(self) -> str:
        return self.consignee_id


# ── Reference Data ───────────────────────────────────────────────────────────

POL_CODES = {"Singapore (PSA)": "SGSIN"}
POD_CODES = {
    "Manila (MICT)": "PHMNL", "Cebu": "PHCEB", "Batangas": "PHBTG",
    "Port Klang (Westports)": "MYPKG", "Jakarta (Tanjung Priok)": "IDJKT",
    "Ho Chi Minh City (Cat Lai)": "VNSGN", "Laem Chabang": "THLCH",
}
# Typical Singapore → destination transit days (direct/feeder services)
TRANSIT_DAYS = {
    "Manila (MICT)": 4, "Cebu": 6, "Batangas": 5, "Port Klang (Westports)": 1,
    "Jakarta (Tanjung Priok)": 2, "Ho Chi Minh City (Cat Lai)": 3, "Laem Chabang": 3,
}

# Commodity benchmarks — price range is a market reference (USD per unit), not the invoice.
# kg_per_unit converts invoiced quantity to expected cargo weight for the VGM cross-check.
COMMODITIES = {
    "igu_glass": dict(
        name="Insulated glass units, low-E, 6mm + 12A + 6mm, on steel A-frame racks",
        unit="m2", price=(28.0, 38.0), kg_per_unit=30.0, qty_per_box=(640, 720), box="20GP",
        package_type="A-frame racks", per_package=40, types=["breakage"]),
    "float_glass": dict(
        name="Clear float glass 5mm, in wooden crates",
        unit="t", price=(380.0, 480.0), kg_per_unit=1000.0, qty_per_box=(22, 25), box="20GP",
        package_type="wooden crates", per_package=1.2, types=["breakage"]),
    "pp_resin": dict(
        name="Polypropylene resin (homopolymer), 25 kg bags",
        unit="t", price=(950.0, 1150.0), kg_per_unit=1000.0, qty_per_box=(24.75, 24.75), box="20GP",
        package_type="bags", per_package=0.025, types=["wet_damage", "contamination", "shortage"]),
    "pc_resin": dict(
        name="Polycarbonate resin, 25 kg bags on pallets",
        unit="t", price=(2300.0, 2900.0), kg_per_unit=1000.0, qty_per_box=(24.0, 24.0), box="40HC",
        package_type="bags", per_package=0.025, types=["wet_damage", "contamination"]),
    "methanol": dict(
        name="Methanol, in 20ft ISO tank containers",
        unit="t", price=(300.0, 380.0), kg_per_unit=1000.0, qty_per_box=(19.5, 20.5), box="20TK",
        package_type="ISO tanks", per_package=20.0, types=["contamination", "shortage"]),
    "coating_chem": dict(
        name="Industrial coating resin, 200 L steel drums",
        unit="t", price=(3000.0, 4500.0), kg_per_unit=1000.0, qty_per_box=(16.0, 17.6), box="20GP",
        package_type="drums", per_package=0.22, types=["contamination", "wet_damage", "breakage"]),
    "steel_coils": dict(
        name="Cold-rolled steel coils",
        unit="t", price=(620.0, 720.0), kg_per_unit=1000.0, qty_per_box=(24.0, 26.0), box="20GP",
        package_type="coils", per_package=6.0, types=["wet_damage"]),
    "ceramic_tiles": dict(
        name="Porcelain floor tiles 600x600, on pallets",
        unit="m2", price=(6.5, 9.5), kg_per_unit=21.0, qty_per_box=(1150, 1250), box="20GP",
        package_type="pallets", per_package=57.6, types=["breakage"]),
    "laptops": dict(
        name="Notebook computers, cartons on pallets",
        unit="unit", price=(420.0, 650.0), kg_per_unit=3.2, qty_per_box=(2200, 2600), box="40HC",
        package_type="cartons", per_package=5, types=["theft_pilferage", "wet_damage"]),
    "auto_parts": dict(
        name="Automotive spare parts, cartons on pallets",
        unit="t", price=(6000.0, 9000.0), kg_per_unit=1000.0, qty_per_box=(9.0, 12.0), box="20GP",
        package_type="pallets", per_package=0.6, types=["theft_pilferage", "shortage", "wet_damage"]),
    "kraft_paper": dict(
        name="Kraft paper rolls",
        unit="t", price=(600.0, 750.0), kg_per_unit=1000.0, qty_per_box=(23.0, 25.0), box="40HC",
        package_type="rolls", per_package=0.8, types=["wet_damage", "breakage"]),
}

BOX_TARE = {"20GP": 2250, "40HC": 3900, "20TK": 3650}

CARRIERS = [
    ("Meridian Container Line", ["MERIDIAN HARMONY", "MERIDIAN VALOUR"]),
    ("Straits Orient Shipping", ["ORIENT CORAL", "ORIENT JADE"]),
    ("Coral Sea Feeder Lines", ["CORAL BREEZE", "CORAL TIDE"]),
]
CARRIER_PREFIX = {"Meridian Container Line": "MCLU", "Straits Orient Shipping": "SOSU",
                  "Coral Sea Feeder Lines": "CSFU"}

CONSIGNEES = [
    # name, city, country, shipments/yr
    ("Bayfront Builders Supply Inc.", "Pasig City", "PH", 60),
    ("Cebu Allied Trading Corp.", "Cebu City", "PH", 35),
    ("Pasig Industrial Resins Inc.", "Pasig City", "PH", 120),
    ("Northgate Home Centre Corp.", "Quezon City", "PH", 45),
    ("Visayas Agri-Chem Distributors Inc.", "Iloilo City", "PH", 30),
    ("Manila Bay Polymer Trading Corp.", "Valenzuela City", "PH", 80),
    ("Rizal Construction Materials Inc.", "Antipolo City", "PH", 25),
    ("Klang Valley Industrial Supplies Sdn. Bhd.", "Shah Alam", "MY", 70),
    ("Nusantara Kemas Plastik PT", "Bekasi", "ID", 55),
    ("Saigon Coatings Trading Co., Ltd.", "Ho Chi Minh City", "VN", 40),
    ("Eastern Seaboard Components Co., Ltd.", "Chonburi", "TH", 65),
    ("Luzon Premier Glass & Glazing Corp.", "Makati City", "PH", 14),   # hero fraud consignee
    ("Southport Electronics Distribution Inc.", "Parañaque City", "PH", 50),
    ("Batangas Steel Service Center Inc.", "Batangas City", "PH", 30),
    ("Laguna Technopark Assemblies Inc.", "Santa Rosa", "PH", 90),
    ("Cavite Export Zone Packaging Corp.", "Rosario", "PH", 45),
    ("Davao Gulf Commodities Inc.", "Davao City", "PH", 25),
    ("Clark Freeport Industrial Supply Inc.", "Angeles City", "PH", 35),
    ("Metro Manila Hardware Distributors Inc.", "Caloocan City", "PH", 55),
    ("Subic Bay Resin Compounders Inc.", "Olongapo City", "PH", 40),
    ("Penang Precision Parts Sdn. Bhd.", "Bayan Lepas", "MY", 60),
    ("Johor Selatan Building Supplies Sdn. Bhd.", "Johor Bahru", "MY", 30),
    ("Surabaya Kimia Utama PT", "Surabaya", "ID", 45),
    ("Karawang Otomotif Komponen PT", "Karawang", "ID", 75),
    ("Binh Duong Paper Converting Co., Ltd.", "Thu Dau Mot", "VN", 35),
    ("Hai Phong Steel Trading JSC", "Hai Phong", "VN", 50),
    ("Rayong Petrochem Logistics Co., Ltd.", "Rayong", "TH", 85),
    ("Bangkok Tile & Sanitaryware Co., Ltd.", "Bangkok", "TH", 30),
    ("Quezon Paper Products Corp.", "Quezon City", "PH", 40),
    ("Iloilo Agro-Industrial Supply Inc.", "Iloilo City", "PH", 20),
]
CONSIGNEE_POD = {"PH": ["Manila (MICT)", "Manila (MICT)", "Manila (MICT)", "Cebu", "Batangas"],
                 "MY": ["Port Klang (Westports)"], "ID": ["Jakarta (Tanjung Priok)"],
                 "VN": ["Ho Chi Minh City (Cat Lai)"], "TH": ["Laem Chabang"]}

SHIPPERS = [
    "Straits Glass Processing Pte. Ltd.",
    "Jurong Polymer Exports Pte. Ltd.",
    "Tuas Specialty Chemicals Pte. Ltd.",
    "Pioneer Coatings Asia Pte. Ltd.",
    "Lion City Metals Trading Pte. Ltd.",
    "Harbourfront Electronics Distribution Pte. Ltd.",
    "Kallang Auto Components Pte. Ltd.",
    "Orchid Trade Links Pte. Ltd.",           # hero shipper — recently incorporated trading shell
]

SURVEYORS = [
    # name, city, insurer_panel
    ("Pacific Adjusters & Surveyors Inc.", "Manila", True),
    ("Harbourline Marine Survey Services Inc.", "Manila", True),
    ("Visayas Cargo Surveyors Co.", "Cebu City", True),
    ("Northport Cargo Inspection Services Inc.", "Makati City", False),   # hero surveyor
    ("Selat Marine Surveyors Sdn. Bhd.", "Port Klang", True),
    ("Samudra Survey Indonesia PT", "Jakarta", True),
    ("Mekong Marine Inspection Co., Ltd.", "Ho Chi Minh City", True),
    ("Gulf of Siam Surveyors Co., Ltd.", "Laem Chabang", True),
]
SURVEYOR_FOR_POD = {
    "Manila (MICT)": [0, 1], "Batangas": [0, 1], "Cebu": [2],
    "Port Klang (Westports)": [4], "Jakarta (Tanjung Priok)": [5],
    "Ho Chi Minh City (Cat Lai)": [6], "Laem Chabang": [7],
}

FORWARDERS = [
    ("Asia Bridge Logistics Pte. Ltd.", "Singapore"),
    ("Swiftlink Freight Forwarding Inc.", "Makati City"),                # hero forwarder
    ("Portside Consolidators Pte. Ltd.", "Singapore"),
    ("Equator Cargo Services Pte. Ltd.", "Singapore"),
]

DIRECTORS = [
    ("Ramon T. Villareal", "Filipino"),       # hero — shared director
    ("Liza M. Carandang", "Filipino"),
    ("Tan Wei Ming", "Singaporean"),
]

HERO_ADDRESS = "Unit 1204, Paseo Meridian Tower, 88 Paseo de Roxas, Makati City"

LOSS_DESCRIPTIONS = {
    "breakage": [
        "Broken units found on unstuffing; racks shifted in container.",
        "Crates crushed; glass breakage on 2 of {pk} crates.",
        "Tiles cracked on several pallets; pallet collapse noted.",
    ],
    "wet_damage": [
        "Water-stained bags found on unstuffing; contents caked.",
        "Condensation damage to cartons along container walls.",
        "Rust on outer laps of coils; salt-water test requested.",
    ],
    "contamination": [
        "Off-spec on arrival — foreign particles found in sampled bags.",
        "Cargo sample failed purity spec at discharge; prior-cargo residue suspected.",
        "Drums leaking; adjacent drums contaminated.",
    ],
    "shortage": [
        "Short-landed: packages delivered below B/L count.",
        "Out-turn weight below loaded weight beyond normal tolerance.",
    ],
    "theft_pilferage": [
        "Cartons missing on unstuffing; seal number differs from B/L.",
        "Pallets opened and contents removed; container door tampered.",
    ],
}

# Claim numbers used by the hand-built scenarios — base claims skip these.
RESERVED_CLAIM_NOS = {3083, 3088, 3094, 3101, 3107}

CLAIM_SOURCE_WEIGHTS = {"broker": 0.50, "assured_direct": 0.20, "settling_agent": 0.20, "online_portal": 0.10}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _seed():
    random.seed(3107)


def _d(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _p(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def _pick_source():
    return random.choices(list(CLAIM_SOURCE_WEIGHTS), weights=list(CLAIM_SOURCE_WEIGHTS.values()), k=1)[0]


def _container_no(prefix: str) -> str:
    return f"{prefix}{random.randint(100000, 999999)}{random.randint(0, 9)}"


def _seal() -> str:
    return f"{random.choice(['ML', 'SO', 'CS'])}{random.randint(1000000, 9999999)}"


def _money(x: float) -> float:
    return round(x, 2)


# ── Base Entities ────────────────────────────────────────────────────────────

def _generate_directors() -> List[Director]:
    return [Director(f"DIR-{i+1:03d}", n, nat) for i, (n, nat) in enumerate(DIRECTORS)]


def _generate_parties() -> List[Party]:
    parties = []
    for i, (name, city, country, spy) in enumerate(CONSIGNEES):
        parties.append(Party(
            party_id=f"CNE-{i+1:03d}",
            name=name, city=city, country=country,
            registered_address=f"{random.randint(10, 999)} {random.choice(['Industrial Ave', 'Commerce St', 'Harbour Rd', 'Enterprise Blvd'])}, {city}",
            incorporated=f"{random.randint(1995, 2018)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            shipments_per_year=spy,
            claim_history_count=random.choice([0, 0, 0, 0, 1, 1]),
        ))
    return parties


def _generate_shippers() -> List[Shipper]:
    return [Shipper(f"SHR-{i+1:03d}", n, incorporated=f"{random.randint(1990, 2015)}-06-01")
            for i, n in enumerate(SHIPPERS)]


def _generate_surveyors() -> List[Surveyor]:
    return [Surveyor(f"SVY-{i+1:03d}", n, city, insurer_panel=panel,
                     registered_address=f"{random.randint(1, 40)}F Port Area Bldg, {city}")
            for i, (n, city, panel) in enumerate(SURVEYORS)]


def _generate_forwarders() -> List[Forwarder]:
    return [Forwarder(f"FWD-{i+1:03d}", n, city, registered_address=f"{random.randint(1, 80)} Logistics Way, {city}")
            for i, (n, city) in enumerate(FORWARDERS)]


def _build_shipment(idx: int, commodity_key: str, consignee: Party, shipper: Shipper,
                    forwarder: Forwarder, n_boxes: int, discharge: datetime,
                    unit_price: Optional[float] = None, pod: Optional[str] = None) -> Shipment:
    c = COMMODITIES[commodity_key]
    carrier, vessels = random.choice(CARRIERS)
    pod = pod or random.choice(CONSIGNEE_POD[consignee.country])
    transit = TRANSIT_DAYS[pod]
    sob = discharge - timedelta(days=transit)
    qty_per_box = round(random.uniform(*c["qty_per_box"]), 2)
    if c["unit"] in ("m2", "unit"):
        qty_per_box = int(qty_per_box)
    price = unit_price if unit_price is not None else round(random.uniform(*c["price"]), 2)
    quantity = round(qty_per_box * n_boxes, 2)
    tare = BOX_TARE[c["box"]]
    prefix = CARRIER_PREFIX[carrier]
    containers = []
    for _ in range(n_boxes):
        cargo_kg = qty_per_box * c["kg_per_unit"] * random.uniform(0.985, 1.015)
        seal = _seal()
        containers.append(Container(
            container_no=_container_no(prefix), size_type=c["box"],
            seal_no_loading=seal, seal_no_discharge=seal,
            tare_kg=tare, vgm_kg=int(cargo_kg + tare),
        ))
    invoice_value = _money(quantity * price)
    packages = int(round(quantity / c["per_package"])) if c["per_package"] else n_boxes
    return Shipment(
        shipment_id=f"SHM-{idx:04d}",
        bl_number=f"{prefix[:3]}SIN{random.randint(2600000, 2699999)}",
        carrier=carrier,
        vessel=random.choice(vessels),
        voyage=f"{random.randint(10, 60):03d}{random.choice(['N', 'E'])}",
        port_of_loading="Singapore (PSA)",
        port_of_discharge=pod,
        shipper_id=shipper.shipper_id,
        consignee_id=consignee.party_id,
        forwarder_id=forwarder.forwarder_id,
        incoterm=random.choice(["CIF", "CIF", "CIP", "FOB"]),
        commodity=c["name"], unit=c["unit"],
        quantity=quantity, unit_price=price,
        invoice_no=f"INV-{random.randint(26000, 26999)}",
        invoice_value=invoice_value,
        containers=containers,
        packages=packages,
        package_type=c["package_type"],
        gross_weight_bl_kg=int(sum(x.vgm_kg - x.tare_kg for x in containers)),
        shipped_on_board=_d(sob),
        discharge_date=_d(discharge),
        gate_out_date=_d(discharge + timedelta(days=random.randint(1, 3))),
    )


def _build_policy(idx: int, shipment: Shipment, assured: Party, clause: str = "ICC (A) 2009") -> CargoPolicy:
    freight_ins = shipment.invoice_value * random.uniform(0.03, 0.06)
    cif = shipment.invoice_value + freight_ins if shipment.incoterm == "FOB" else shipment.invoice_value
    return CargoPolicy(
        policy_id=f"CERT-26{idx:04d}",
        open_cover_no=f"OC-SG-2026-{100 + int(assured.party_id.split('-')[1]):04d}",
        assured_id=assured.party_id,
        shipment_id=shipment.shipment_id,
        clause=clause,
        insured_value=_money(cif * 1.10),
        excess=random.choice([500.0, 1000.0, 2500.0]),
        effective_date="2026-01-01",
        expiration_date="2026-12-31",
    )


# ── Base Claims ──────────────────────────────────────────────────────────────

def _generate_base_claims(parties, shippers, surveyors, forwarders):
    claims, shipments, policies, surveys = [], [], [], []
    type_counts = {"breakage": 9, "wet_damage": 10, "contamination": 7, "shortage": 6, "theft_pilferage": 5}
    commodity_by_type = {t: [k for k, v in COMMODITIES.items() if t in v["types"] and k != "igu_glass"]
                         for t in type_counts}
    normal_parties = [p for p in parties if p.name != "Luzon Premier Glass & Glazing Corp."]
    normal_shippers = [s for s in shippers if s.name != "Orchid Trade Links Pte. Ltd."]
    panel_surveyors = [s for s in surveyors if s.insurer_panel]
    normal_forwarders = [f for f in forwarders if f.name != "Swiftlink Freight Forwarding Inc."]

    consignee_cycle = []
    claim_no = 3050
    idx = 1
    for claim_type, count in type_counts.items():
        for _ in range(count):
            if not consignee_cycle:
                consignee_cycle = random.sample(normal_parties, len(normal_parties))
            consignee = consignee_cycle.pop()
            ckey = random.choice(commodity_by_type[claim_type])
            filed = DEMO_TODAY - timedelta(days=random.choice([0, 0, 1, 2, 3, 5, 8, 12, 16, 21, 27]))
            discharge = filed - timedelta(days=random.randint(6, 25))
            n_boxes = 1 if ckey == "laptops" else random.choice([1, 1, 2, 2, 3, 4])
            shp = _build_shipment(idx, ckey, consignee, random.choice(normal_shippers),
                                  random.choice(normal_forwarders), n_boxes, discharge)
            pol = _build_policy(idx, shp, consignee, clause=random.choice(["ICC (A) 2009"] * 5 + ["ICC (C) 2009"]))

            loss_pct = random.uniform(0.02, 0.22)
            amount = _money(pol.insured_value * loss_pct)
            discovered = _p(shp.gate_out_date) + timedelta(days=random.randint(0, 2))
            notice_ins = discovered + timedelta(days=random.randint(0, 2))

            pod_surveyors = [surveyors[i] for i in SURVEYOR_FOR_POD[shp.port_of_discharge]]
            svy = random.choice(pod_surveyors or panel_surveyors)
            survey_date = notice_ins + timedelta(days=random.randint(1, 3))
            while claim_no in RESERVED_CLAIM_NOS:
                claim_no += 1
            claim_id = f"MC-{claim_no}"
            survey = SurveyReport(
                survey_id=f"SR-{idx:04d}", claim_id=claim_id, surveyor_id=svy.surveyor_id,
                appointed_by="insurer", survey_date=_d(survey_date),
                survey_location=random.choice(["Container yard, port of discharge", "Consignee warehouse"]),
                joint_with_carrier=random.random() < 0.6,
                cause_of_loss={"breakage": "Rough handling / shifting in transit",
                               "wet_damage": random.choice(["Condensation (container sweat)", "Fresh-water ingress", "Sea-water ingress"]),
                               "contamination": "Contamination in transit",
                               "shortage": "Short delivery",
                               "theft_pilferage": "Theft / pilferage"}[claim_type],
                damage_pct=round(loss_pct * 100, 1),
                photos=random.randint(6, 24),
                report_no=f"{svy.name.split()[0][:3].upper()}-{random.randint(2600, 2699)}",
            )
            notice_carrier = discovered + timedelta(days=random.randint(0, 2)) if random.random() < 0.85 else None
            desc = random.choice(LOSS_DESCRIPTIONS[claim_type]).format(pk=shp.packages)

            claims.append(MarineClaim(
                claim_id=claim_id, claim_type=claim_type, consignee_id=consignee.party_id,
                shipment_id=shp.shipment_id, policy_id=pol.policy_id,
                surveyor_id=svy.surveyor_id, survey_id=survey.survey_id,
                date_filed=_d(filed), date_of_loss=_d(discovered),
                notice_to_insurer_date=_d(notice_ins),
                notice_to_carrier_date=_d(notice_carrier) if notice_carrier else None,
                claim_amount=amount, claim_source=_pick_source(), loss_description=desc,
            ))
            shipments.append(shp); policies.append(pol); surveys.append(survey)
            claim_no += 1
            idx += 1
    return claims, shipments, policies, surveys


# ── Hero Scenarios ───────────────────────────────────────────────────────────

def _inject_scenarios(claims, shipments, policies, surveys, parties, shippers,
                      surveyors, forwarders, directors, prior_claims):
    p_by_name = {p.name: p for p in parties}
    s_by_name = {s.name: s for s in shippers}
    v_by_name = {s.name: s for s in surveyors}
    f_by_name = {f.name: f for f in forwarders}
    ring_director = directors[0]
    idx = len(shipments) + 1

    # ── MC-3107: Over-valued, part-phantom glass shipment; colluding surveyor ring ──
    hero_cne = p_by_name["Luzon Premier Glass & Glazing Corp."]
    hero_svy = v_by_name["Northport Cargo Inspection Services Inc."]
    hero_fwd = f_by_name["Swiftlink Freight Forwarding Inc."]
    hero_shr = s_by_name["Orchid Trade Links Pte. Ltd."]

    for ent in (hero_cne, hero_svy, hero_fwd):
        ent.director_ids = [ring_director.director_id]
        ent.registered_address = HERO_ADDRESS
    hero_cne.incorporated = "2021-03-18"
    hero_cne.claim_history_count = 3
    hero_cne.flagged = True
    hero_cne.notes = "FRAUD_SCENARIO: Over-valued part-phantom cargo; surveyor/forwarder share director and address"
    hero_svy.notes = "Not on insurer panel. Appointed by assured on 5 breakage claims (3 consignees) in 20 months."
    hero_svy.on_watchlist = True
    hero_fwd.notes = "Booked all 3 prior Luzon Premier shipments that resulted in claims."
    hero_shr.incorporated = "2025-11-04"
    hero_shr.notes = "Trading company incorporated 10 months before shipment; no glass processing facility on record."

    discharge = datetime(2026, 8, 28)
    shp = _build_shipment(idx, "igu_glass", hero_cne, hero_shr, hero_fwd, 6, discharge,
                          unit_price=58.00, pod="Manila (MICT)")
    shp.incoterm = "FOB"
    shp.carrier, shp.vessel, shp.voyage = "Meridian Container Line", "MERIDIAN HARMONY", "034N"
    shp.bl_number = "MCLSIN2604417"
    shp.invoice_no = "OTL-INV-26-0917"
    # Invoice/packing list claim 720 m2 per box (≈ 21.6 t glass + 0.9 t racks per box)…
    qty_per_box = 720
    shp.quantity = qty_per_box * 6
    shp.invoice_value = _money(shp.quantity * shp.unit_price)
    shp.packages = 108                                    # 18 A-frame racks per box
    shp.gross_weight_bl_kg = 6 * (qty_per_box * 30 + 900)  # shipper-declared, matches packing list
    # …but the terminal VGM shows only ~57% of that cargo weight actually loaded.
    for c in shp.containers:
        c.vgm_kg = int(c.tare_kg + (qty_per_box * 30 + 900) * random.uniform(0.555, 0.585))
    shp.gate_out_date = "2026-08-31"
    shp.eir_remarks_discharge = "Clean — no exceptions. Seals intact."
    hero_pol = _build_policy(idx, shp, hero_cne, clause="ICC (A) 2009")
    hero_pol.policy_id = "CERT-264417"
    hero_pol.open_cover_no = "OC-SG-2026-0142"
    hero_pol.insured_value = _money(shp.invoice_value * 1.045 * 1.10)   # FOB + freight/ins → CIF, +10%
    hero_pol.excess = 2500.0

    hero_survey = SurveyReport(
        survey_id=f"SR-{idx:04d}", claim_id="MC-3107", surveyor_id=hero_svy.surveyor_id,
        appointed_by="assured", survey_date="2026-09-14",
        survey_location="Consignee warehouse, Valenzuela City (cargo already unstuffed)",
        joint_with_carrier=False,
        cause_of_loss="Breakage — rough handling in transit (per surveyor)",
        damage_pct=71.0, photos=14, report_no="NCIS-26-0388",
    )
    hero = MarineClaim(
        claim_id="MC-3107", claim_type="breakage", consignee_id=hero_cne.party_id,
        shipment_id=shp.shipment_id, policy_id=hero_pol.policy_id,
        surveyor_id=hero_svy.surveyor_id, survey_id=hero_survey.survey_id,
        date_filed=_d(DEMO_TODAY), date_of_loss="2026-09-02",
        notice_to_insurer_date="2026-09-11", notice_to_carrier_date=None,
        claim_amount=_money(hero_pol.insured_value * 0.71),
        claim_source="assured_direct",
        loss_description=("Consignee reports 71% of insulated glass units broken on unstuffing at its "
                          "Valenzuela warehouse; racks said to have shifted in transit."),
        fraud_scenario="overvalued_phantom_cargo",
        photo_evidence=True,
        notes=("Invoice unit price well above market; VGM cargo weight ~43% below invoiced quantity; "
               "survey by assured-appointed surveyor 17 days after discharge; no notice to carrier."),
    )
    claims.append(hero); shipments.append(shp); policies.append(hero_pol); surveys.append(hero_survey)
    idx += 1

    # Prior claims: the hero consignee's history + the surveyor's wider ring (closed/paid).
    prior_claims.extend([
        PriorClaim("MC-2711", hero_cne.party_id, hero_svy.surveyor_id, "breakage", 148_220.00, "2025-05-19",
                   "Laminated glass 10.38mm"),
        PriorClaim("MC-2846", hero_cne.party_id, hero_svy.surveyor_id, "breakage", 176_905.50, "2025-11-07",
                   "Insulated glass units, low-E"),
        PriorClaim("MC-2957", hero_cne.party_id, hero_svy.surveyor_id, "breakage", 121_340.00, "2026-02-26",
                   "Tempered glass panels"),
        PriorClaim("MC-2988", p_by_name["Rizal Construction Materials Inc."].party_id, hero_svy.surveyor_id,
                   "breakage", 139_460.00, "2026-04-15", "Insulated glass units, low-E"),
        PriorClaim("MC-3012", p_by_name["Northgate Home Centre Corp."].party_id, hero_svy.surveyor_id,
                   "breakage", 58_775.00, "2026-06-03", "Porcelain floor tiles"),
    ])

    # ── MC-3094: FALSE POSITIVE — large wet-damage claim, textbook-clean handling ──
    fp_cne = p_by_name["Pasig Industrial Resins Inc."]
    fp_cne.claim_history_count = 2
    fp_cne.notes = "High-volume importer (~120 shipments/yr). 3 claims in 24 months = 2.5% claim rate."
    discharge = datetime(2026, 9, 21)
    shp = _build_shipment(idx, "pc_resin", fp_cne, s_by_name["Jurong Polymer Exports Pte. Ltd."],
                          f_by_name["Asia Bridge Logistics Pte. Ltd."], 2, discharge,
                          unit_price=2650.00, pod="Manila (MICT)")
    shp.incoterm = "CIF"
    shp.gate_out_date = "2026-09-22"
    shp.eir_remarks_discharge = (f"EXCEPTION: container {shp.containers[0].container_no} roof holed approx. 4 cm "
                                 "near door end; water staining on internal roof panel. Seals intact.")
    fp_pol = _build_policy(idx, shp, fp_cne)
    fp_pol.open_cover_no = "OC-SG-2026-0118"
    fp_svy = v_by_name["Pacific Adjusters & Surveyors Inc."]
    fp_survey = SurveyReport(
        survey_id=f"SR-{idx:04d}", claim_id="MC-3094", surveyor_id=fp_svy.surveyor_id,
        appointed_by="insurer", survey_date="2026-09-23",
        survey_location="Container yard, MICT (joint survey with carrier's surveyor)",
        joint_with_carrier=True,
        cause_of_loss="Sea-water ingress through holed container roof (silver nitrate test positive)",
        damage_pct=46.0, photos=22, report_no="PAS-26-1172",
    )
    fp = MarineClaim(
        claim_id="MC-3094", claim_type="wet_damage", consignee_id=fp_cne.party_id,
        shipment_id=shp.shipment_id, policy_id=fp_pol.policy_id,
        surveyor_id=fp_svy.surveyor_id, survey_id=fp_survey.survey_id,
        date_filed="2026-10-01", date_of_loss="2026-09-22",
        notice_to_insurer_date="2026-09-22", notice_to_carrier_date="2026-09-22",
        claim_amount=_money(fp_pol.insured_value * 0.46),
        claim_source="broker",
        loss_description="Wet-damaged bags of polycarbonate resin in one of two containers; roof hole noted at gate-out.",
        false_positive_scenario="legitimate_seawater_ingress",
        notes=("Large loss but handled by the book: exception on EIR at discharge, joint survey within "
               "1 day, notice to carrier same day. Carrier liable for unseaworthy container → recovery."),
    )
    claims.append(fp); shipments.append(shp); policies.append(fp_pol); surveys.append(fp_survey)
    idx += 1

    # ── MC-3101: GENUINE THEFT — seal swapped between loading and discharge → recovery ──
    th_cne = p_by_name["Southport Electronics Distribution Inc."]
    discharge = datetime(2026, 9, 24)
    shp = _build_shipment(idx, "laptops", th_cne, s_by_name["Harbourfront Electronics Distribution Pte. Ltd."],
                          f_by_name["Equator Cargo Services Pte. Ltd."], 1, discharge,
                          unit_price=545.00, pod="Manila (MICT)")
    shp.incoterm = "CIP"
    shp.containers[0].seal_no_discharge = "ML" + str(random.randint(1000000, 9999999))
    shp.eir_remarks_discharge = (f"EXCEPTION: seal no. {shp.containers[0].seal_no_discharge} does not match B/L "
                                 f"seal {shp.containers[0].seal_no_loading}. Door rubber cut.")
    th_pol = _build_policy(idx, shp, th_cne)
    missing_cartons = int(round(shp.packages * 0.24))
    th_svy = v_by_name["Harbourline Marine Survey Services Inc."]
    th_survey = SurveyReport(
        survey_id=f"SR-{idx:04d}", claim_id="MC-3101", surveyor_id=th_svy.surveyor_id,
        appointed_by="insurer", survey_date="2026-09-26",
        survey_location="Container yard, MICT", joint_with_carrier=True,
        cause_of_loss=f"Theft — {missing_cartons} of {shp.packages} cartons missing; seal replaced in transit",
        damage_pct=24.0, photos=18, report_no="HMS-26-0904",
    )
    th = MarineClaim(
        claim_id="MC-3101", claim_type="theft_pilferage", consignee_id=th_cne.party_id,
        shipment_id=shp.shipment_id, policy_id=th_pol.policy_id,
        surveyor_id=th_svy.surveyor_id, survey_id=th_survey.survey_id,
        date_filed="2026-09-30", date_of_loss="2026-09-25",
        notice_to_insurer_date="2026-09-25", notice_to_carrier_date="2026-09-25",
        claim_amount=_money(th_pol.insured_value * 0.24),
        claim_source="broker",
        loss_description=f"{missing_cartons} cartons of notebook computers missing on unstuffing; seal number differs from B/L.",
        false_positive_scenario="genuine_theft_recovery",
        notes="Genuine theft: seal mismatch recorded on EIR at discharge. Recovery against carrier/terminal.",
    )
    claims.append(th); shipments.append(shp); policies.append(th_pol); surveys.append(th_survey)
    idx += 1

    # ── MC-3088: Honest claim, but loss discovered after cover ended (ICC cl. 8.1.4) ──
    late_cne = p_by_name["Batangas Steel Service Center Inc."]
    discharge = datetime(2026, 7, 10)
    shp = _build_shipment(idx, "steel_coils", late_cne, s_by_name["Lion City Metals Trading Pte. Ltd."],
                          f_by_name["Portside Consolidators Pte. Ltd."], 3, discharge, pod="Batangas")
    shp.incoterm = "CIF"
    late_pol = _build_policy(idx, shp, late_cne)
    late_svy = v_by_name["Pacific Adjusters & Surveyors Inc."]
    late_survey = SurveyReport(
        survey_id=f"SR-{idx:04d}", claim_id="MC-3088", surveyor_id=late_svy.surveyor_id,
        appointed_by="insurer", survey_date="2026-09-25",
        survey_location="Consignee open storage yard, Batangas",
        cause_of_loss="Rust — prolonged open-air storage after delivery",
        damage_pct=18.0, photos=12, report_no="PAS-26-1160",
    )
    late = MarineClaim(
        claim_id="MC-3088", claim_type="wet_damage", consignee_id=late_cne.party_id,
        shipment_id=shp.shipment_id, policy_id=late_pol.policy_id,
        surveyor_id=late_svy.surveyor_id, survey_id=late_survey.survey_id,
        date_filed="2026-09-29", date_of_loss="2026-09-22",
        notice_to_insurer_date="2026-09-23", notice_to_carrier_date=None,
        claim_amount=_money(late_pol.insured_value * 0.18),
        claim_source="broker",
        loss_description="Rust found on coils stored in consignee's open yard since delivery in July.",
        notes="Loss discovered 74 days after discharge — outside the ICC transit clause. Coverage decline, not fraud.",
    )
    claims.append(late); shipments.append(shp); policies.append(late_pol); surveys.append(late_survey)
    idx += 1

    # ── MC-3083: Breakage caused by insufficient packing (ICC cl. 4.3 exclusion) ──
    pk_cne = p_by_name["Cebu Allied Trading Corp."]
    discharge = datetime(2026, 9, 15)
    shp = _build_shipment(idx, "float_glass", pk_cne, s_by_name["Straits Glass Processing Pte. Ltd."],
                          f_by_name["Asia Bridge Logistics Pte. Ltd."], 2, discharge, pod="Cebu")
    pk_pol = _build_policy(idx, shp, pk_cne)
    pk_svy = v_by_name["Visayas Cargo Surveyors Co."]
    pk_survey = SurveyReport(
        survey_id=f"SR-{idx:04d}", claim_id="MC-3083", surveyor_id=pk_svy.surveyor_id,
        appointed_by="insurer", survey_date="2026-09-19",
        survey_location="Consignee warehouse, Mandaue", joint_with_carrier=True,
        cause_of_loss="Insufficient packing — unbraced wooden crates without A-frames or dunnage",
        damage_pct=27.0, photos=16, report_no="VCS-26-0231",
    )
    pk = MarineClaim(
        claim_id="MC-3083", claim_type="breakage", consignee_id=pk_cne.party_id,
        shipment_id=shp.shipment_id, policy_id=pk_pol.policy_id,
        surveyor_id=pk_svy.surveyor_id, survey_id=pk_survey.survey_id,
        date_filed="2026-09-26", date_of_loss="2026-09-17",
        notice_to_insurer_date="2026-09-17", notice_to_carrier_date="2026-09-18",
        claim_amount=_money(pk_pol.insured_value * 0.27),
        claim_source="settling_agent",
        loss_description="Float glass crates collapsed; survey attributes loss to inadequate crating and stowage.",
        notes="Genuine loss, but surveyor finds insufficient packing — ICC cl. 4.3 exclusion applies.",
    )
    claims.append(pk); shipments.append(shp); policies.append(pk_pol); surveys.append(pk_survey)


# ── Documents & Tasks ────────────────────────────────────────────────────────

def _generate_documents(claims: List[MarineClaim]) -> List[DocumentMetadata]:
    docs = []
    doc_id = 1
    base_set = ["bill_of_lading", "commercial_invoice", "packing_list", "survey_report", "eir"]
    for claim in claims:
        dtypes = base_set + (["survey_photo"] if claim.photo_evidence else [])
        for dtype in dtypes:
            docs.append(DocumentMetadata(
                doc_id=f"DOC-{doc_id:04d}", claim_id=claim.claim_id, doc_type=dtype,
                provider_name="Various", date_created=claim.date_of_loss or claim.date_filed,
                received_date=claim.date_filed,
            ))
            doc_id += 1
    return docs


def _generate_workflow_tasks(claims: List[MarineClaim]) -> List[WorkflowTask]:
    tasks = []
    task_id = 1

    def add(claim, ttype, status, due_days, notes=""):
        nonlocal task_id
        assigned = claim.date_filed
        tasks.append(WorkflowTask(
            task_id=f"TSK-{task_id:04d}", claim_id=claim.claim_id, task_type=ttype, status=status,
            assigned_date=assigned, due_date=_d(_p(assigned) + timedelta(days=due_days)),
            days_waiting=max(0, (DEMO_TODAY - _p(assigned)).days), notes=notes,
        ))
        task_id += 1

    for claim in claims:
        add(claim, "INITIAL_REVIEW",
            random.choices(["pending", "in_progress", "completed"], weights=[0.4, 0.3, 0.3])[0], 3)
        add(claim, "DOCUMENT_REVIEW", random.choice(["pending", "in_progress"]), 7)
        if claim.notice_to_carrier_date is None:
            add(claim, "RECOVERY_NOTICE", "overdue", 1, "No notice of claim sent to carrier")
        else:
            add(claim, "RECOVERY_NOTICE", "completed", 3)
    return tasks


# ── Main Generator ───────────────────────────────────────────────────────────

def generate_marine_data() -> Dict:
    """Generate all marine cargo data. Returns dict of entity lists."""
    _seed()
    directors = _generate_directors()
    parties = _generate_parties()
    shippers = _generate_shippers()
    surveyors = _generate_surveyors()
    forwarders = _generate_forwarders()

    print("  Generating marine cargo claims...")
    claims, shipments, policies, surveys = _generate_base_claims(parties, shippers, surveyors, forwarders)

    print("  Injecting hero scenarios (MC-3107 fraud, MC-3094 / MC-3101 legitimate, MC-3088 / MC-3083 coverage)...")
    prior_claims: List[PriorClaim] = []
    _inject_scenarios(claims, shipments, policies, surveys, parties, shippers,
                      surveyors, forwarders, directors, prior_claims)

    # Claim-history counts include prior closed claims for the same consignee.
    for p in parties:
        priors = sum(1 for pc in prior_claims if pc.consignee_id == p.party_id)
        p.claim_history_count = max(p.claim_history_count, priors)

    documents = _generate_documents(claims)
    workflow_tasks = _generate_workflow_tasks(claims)

    return {
        "consignees": parties,
        "shippers": shippers,
        "surveyors": surveyors,
        "forwarders": forwarders,
        "directors": directors,
        "shipments": shipments,
        "policies": policies,
        "surveys": surveys,
        "claims": claims,
        "prior_claims": prior_claims,
        "documents": documents,
        "workflow_tasks": workflow_tasks,
    }


if __name__ == "__main__":
    data = generate_marine_data()
    print(f"\nGenerated {len(data['claims'])} claims, {len(data['shipments'])} shipments, "
          f"{len(data['prior_claims'])} prior claims")
    for c in data["claims"]:
        if c.fraud_scenario or c.false_positive_scenario or c.claim_id in ("MC-3088", "MC-3083"):
            shp = next(s for s in data["shipments"] if s.shipment_id == c.shipment_id)
            print(f"  {c.claim_id} {c.claim_type:15} ${c.claim_amount:>12,.2f}  {shp.description}  "
                  f"VGM cargo {shp.vgm_cargo_kg:,} kg vs B/L {shp.gross_weight_bl_kg:,} kg")
