from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict
from datetime import datetime


class CaseType(str, Enum):
    PROVIDER_FRAUD = "provider_fraud"
    DISABILITY_CLAIM = "disability_claim"


class CasePriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CaseStatus(str, Enum):
    NEW = "new"
    IN_REVIEW = "in_review"
    ESCALATED = "escalated"
    DISMISSED = "dismissed"
    CLOSED = "closed"


@dataclass
class Case:
    case_id: str
    case_type: CaseType
    subject_id: str
    subject_name: str
    priority: CasePriority
    flag_reason: str
    status: CaseStatus = CaseStatus.NEW
    created_at: datetime = field(default_factory=datetime.now)
    summary: Optional[str] = None
    key_metrics: Dict = field(default_factory=dict)
    investigation_history: List[Dict] = field(default_factory=list)
    dossier: Optional[str] = None
