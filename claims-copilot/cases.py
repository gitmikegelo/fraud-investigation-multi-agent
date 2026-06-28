from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict
from datetime import datetime


class CaseType(str, Enum):
    CAR_INSURANCE = "car_insurance"


class ClaimType(str, Enum):
    # Car Insurance types
    COLLISION = "collision"
    COMPREHENSIVE = "comprehensive"
    THEFT = "theft"
    LIABILITY = "liability"
    MEDICAL_PAYMENTS = "medical_payments"


class CasePriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CaseStatus(str, Enum):
    NEW = "new"
    IN_REVIEW = "in_review"
    ESCALATED = "escalated"
    DISMISSED = "dismissed"
    APPROVED = "approved"
    DENIED = "denied"
    CLOSED = "closed"


@dataclass
class Case:
    case_id: str
    case_type: CaseType
    claim_type: ClaimType
    subject_id: str
    subject_name: str
    priority: CasePriority
    flag_reason: str
    risk_score: float = 0.0
    claim_source: str = "company_site"
    status: CaseStatus = CaseStatus.NEW
    created_at: datetime = field(default_factory=datetime.now)
    date_filed: datetime = field(default_factory=datetime.now)
    summary: Optional[str] = None
    key_metrics: Dict = field(default_factory=dict)
    rules_triggered: List[Dict] = field(default_factory=list)
    workflow_tasks: List[Dict] = field(default_factory=list)
    document_flags: List[Dict] = field(default_factory=list)
    checklist_state: Dict = field(default_factory=dict)
    employer_name: str = ""
    member_id: str = ""
    provider_name: str = ""
    claim_amount: float = 0.0
    coverage_start: Optional[str] = None
    coverage_end: Optional[str] = None
    investigation_history: List[Dict] = field(default_factory=list)
    dossier: Optional[str] = None
