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


MARINE_CARGO = DomainConfig(
    name="marine_cargo",
    display_name="Marine Cargo Claims Copilot",
    claim_types=[
        "breakage",
        "wet_damage",
        "contamination",
        "shortage",
        "theft_pilferage",
    ],
    claim_id_prefixes={
        "breakage": "MC",
        "wet_damage": "MC",
        "contamination": "MC",
        "shortage": "MC",
        "theft_pilferage": "MC",
    },
    claim_sources=["broker", "assured_direct", "settling_agent", "online_portal"],
    claim_source_weights={
        "broker": 0.50,
        "assured_direct": 0.20,
        "settling_agent": 0.20,
        "online_portal": 0.10,
    },
    risk_tiers={
        "HIGH": (60, 100),
        "MEDIUM": (30, 59),
        "LOW": (0, 29),
    },
    workflow_task_types=[
        "INITIAL_REVIEW",
        "SURVEY_APPOINTMENT",
        "DOCUMENT_REVIEW",
        "RECOVERY_NOTICE",
    ],
    checklist_steps=[
        "Initial Review",
        "Shipping Documents",
        "Transit & Coverage Period",
        "Document AI Review",
        "Survey & Surveyor",
        "ICC Coverage & Exclusions",
        "Final Determination",
    ],
    system_references={
        "policy_admin": "Open Cover / Certificate Register",
        "valuation": "Commodity Price Benchmark",
        "carrier_data": "Carrier B/L, VGM & EIR Records",
        "fraud_watchlist": "Surveyor & Intermediary Watchlist",
    },
    rules_prefix="R",
    doc_checks_prefix="DOC",
    entity_types=[
        "consignee",
        "shipper",
        "shipment",
        "surveyor",
        "forwarder",
        "policy",
    ],
)
