"""Domain configuration for the Claims Copilot system."""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class DomainConfig:
    name: str
    display_name: str
    claim_types: List[str]
    claim_id_prefixes: Dict[str, str]
    claim_sources: List[str]
    claim_source_weights: Dict[str, float]
    risk_tiers: Dict[str, tuple]  # tier_name -> (min_score, max_score)
    workflow_task_types: List[str]
    checklist_steps: List[str]
    system_references: Dict[str, str]
    rules_prefix: str
    doc_checks_prefix: str
    entity_types: List[str]


PRUDENTIAL_SUPPLEMENTAL_HEALTH = DomainConfig(
    name="prudential_supplemental_health",
    display_name="Prudential Supplemental Health Examiner Workflow Copilot",
    claim_types=["wellness", "accident", "hospital_indemnity", "critical_illness"],
    claim_id_prefixes={
        "wellness": "WC",
        "accident": "AC",
        "hospital_indemnity": "HI",
        "critical_illness": "CI",
    },
    claim_sources=["company_site", "telephonic", "web", "disability_portal"],
    claim_source_weights={
        "company_site": 0.50,
        "telephonic": 0.10,
        "web": 0.30,
        "disability_portal": 0.10,
    },
    risk_tiers={
        "HIGH": (60, 100),
        "MEDIUM": (30, 59),
        "LOW": (0, 29),
    },
    workflow_task_types=[
        "INITIAL_REVIEW",
        "MEDICAL_RECORD_REQUEST",
        "PMR",
        "CBR",
    ],
    checklist_steps=[
        "Initial Review",
        "Eligibility Verification",
        "Fraud Screening",
        "Family & Network Check",
        "Medical Documentation Review",
        "Policy & Coverage Determination",
        "Final Determination",
    ],
    system_references={
        "eligibility": "Prudential 360",
        "analytics": "Power BI",
        "policy_admin": "FIS/PAS",
        "workflow": "Compass",
    },
    rules_prefix="R",
    doc_checks_prefix="DOC",
    entity_types=[
        "member",
        "dependent",
        "provider",
        "facility",
        "address",
        "employer",
        "policy",
    ],
)


ZURICH_TRAVEL_GUARD = DomainConfig(
    name="zurich_travel_guard",
    display_name="Zurich Travel Guard Claims Examiner Copilot",
    claim_types=[
        "trip_cancellation",
        "trip_interruption",
        "medical_emergency",
        "baggage_loss",
        "travel_delay",
    ],
    claim_id_prefixes={
        "trip_cancellation": "TC",
        "trip_interruption": "TI",
        "medical_emergency": "ME",
        "baggage_loss": "BL",
        "travel_delay": "TD",
    },
    claim_sources=["online_portal", "mobile_app", "call_center", "travel_agent"],
    claim_source_weights={
        "online_portal": 0.45,
        "mobile_app": 0.25,
        "call_center": 0.20,
        "travel_agent": 0.10,
    },
    risk_tiers={
        "HIGH": (60, 100),
        "MEDIUM": (30, 59),
        "LOW": (0, 29),
    },
    workflow_task_types=[
        "INITIAL_REVIEW",
        "DOCUMENT_REQUEST",
        "BOOKING_VERIFICATION",
        "MEDICAL_REVIEW",
    ],
    checklist_steps=[
        "Initial Claim Review",
        "Policy Coverage Verification",
        "Trip Documentation Check",
        "Provider/Vendor Verification",
        "Fraud Screening",
        "Medical Records Review",
        "Final Determination",
    ],
    system_references={
        "policy_admin": "TravelGuard Portal",
        "flight_tracking": "IATA FlightStats",
        "booking_verification": "GDS Partner API",
        "medical_network": "International SOS",
    },
    rules_prefix="R",
    doc_checks_prefix="DOC",
    entity_types=[
        "traveler",
        "companion",
        "airline",
        "hotel",
        "hospital",
        "destination",
        "travel_agent",
        "policy",
    ],
)
