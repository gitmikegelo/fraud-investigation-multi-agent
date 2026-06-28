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


CAR_INSURANCE = DomainConfig(
    name="car_insurance",
    display_name="Car Insurance Claims Examiner Copilot",
    claim_types=[
        "collision",
        "comprehensive",
        "theft",
        "liability",
        "medical_payments",
    ],
    claim_id_prefixes={
        "collision": "COL",
        "comprehensive": "COMP",
        "theft": "THEFT",
        "liability": "LIAB",
        "medical_payments": "MEDP",
    },
    claim_sources=["online_portal", "mobile_app", "call_center", "agent"],
    claim_source_weights={
        "online_portal": 0.45,
        "mobile_app": 0.25,
        "call_center": 0.20,
        "agent": 0.10,
    },
    risk_tiers={
        "HIGH": (60, 100),
        "MEDIUM": (30, 59),
        "LOW": (0, 29),
    },
    workflow_task_types=[
        "INITIAL_REVIEW",
        "ESTIMATE_REVIEW",
        "SHOP_VERIFICATION",
        "INJURY_REVIEW",
    ],
    checklist_steps=[
        "Initial Review",
        "Damage Documentation",
        "Coverage Timeline",
        "Document AI Review",
        "Repair Shop Verification",
        "Policy & Coverage",
        "Final Determination",
    ],
    system_references={
        "policy_admin": "Policy Admin System",
        "valuation": "NADA/KBB Valuation",
        "shop_network": "Approved Repair Network",
        "fraud_watchlist": "NICB Watchlist",
    },
    rules_prefix="R",
    doc_checks_prefix="DOC",
    entity_types=[
        "insured",
        "vehicle",
        "repair_shop",
        "policy",
    ],
)
