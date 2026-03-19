Reasoning: The user wants me to modify the existing v2 schematic to align with the Prudential supplemental health plan from the PRUDENTIAL_PLAN.md document, incorporating the reframing we discussed (examiner workflow platform with embedded fraud intelligence, not just fraud detection).

Key changes needed:
1. Replace "disability_claim" with Prudential supplemental health claim types (wellness, accident, hospital_indemnity, critical_illness)
2. Add the three-layer intelligence pipeline (rules engine, risk scoring, network analysis)
3. Add document analysis engine (simulated via metadata)
4. Add workflow task management (PMR, CBR, TAT)


5. Add policy intelligence (policy alerts, state/ET rules)
6. Add the 7-step checklist framework
7. Replace disability tools with supplemental health tools
8. Update the claims queue to show 500 claims with risk scores
9. Add the risk dashboard
10. Reframe everything as "examiner workflow platform"
11. Keep the domain-agnostic architecture so provider fraud still works

Now I'm thinking through how to restructure the schematic to capture all these requirements while keeping it at the right abstraction level for implementation—I need to be careful about what actually changes from the original v2 design versus what's just a reframing of existing components.

The core model shifts from a generic Case to a Claims model with richer attributes, the data generation moves from disability-specific scenarios to 500 supplemental health claims with 10 fraud patterns and 5 false positives, and the tool layer expands significantly to include fraud detection, workflow orchestration, and policy rule evaluation. I'm also adding intelligence layers for rules, risk scoring, and entity relationships, plus document metadata simulation to make the fraud scenarios more realistic. The frontend gets a Claims Queue view with risk scores, a dedicated Risk Dashboard, and checklist progress tracking integrated into the chat interface, while keeping provider fraud as a parallel domain to demonstrate the architecture's flexibility. The whole framing becomes about examiner productivity and case throughput rather than disability case management.



# Claims Copilot v2 — Prudential Supplemental Health Build Schematic

## Positioning Note for the Coding Agent

> This platform is an **examiner workflow copilot with embedded fraud intelligence**. The primary value is making examiners faster on every claim. The fraud detection layer is what makes it exciting, but the workflow consolidation is what makes it useful every single day. Build accordingly — the copilot and claims queue should feel like a daily-use tool, not just a fraud alert system.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                      │
│                                                                     │
│  ┌────────────┐ ┌────────────┐ ┌─────────────┐ ┌───────────────┐  │
│  │ ClaimsQueue │ │ ChatPanel  │ │ RiskDash    │ │ NetworkGraph  │  │
│  │ (NEW)       │ │ (NEW)      │ │ (NEW)       │ │ (MODIFY)      │  │
│  └──────┬──────┘ └─────┬──────┘ └─────────────┘ └───────────────┘  │
│         │              │                                            │
│  ┌──────┴──────┐ ┌─────┴──────────────┐  ┌──────────┐             │
│  │ DossierPanel│ │ useCopilotChat.js  │  │ Activity │             │
│  │ (MODIFY)    │ │ (NEW)              │  │ (KEEP)   │             │
│  └─────────────┘ └─────────┬──────────┘  └──────────┘             │
│                            │ WebSocket                              │
└────────────────────────────┼────────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────────┐
│                    API LAYER (FastAPI)                               │
│                                                                     │
│  EXISTING (KEEP):                    NEW:                           │
│  ├─ GET  /api/health                 ├─ GET  /api/claims            │
│  ├─ GET  /api/graph-schema           ├─ GET  /api/claims/{id}       │
│  ├─ GET  /api/anomaly-summary        ├─ POST /api/claims/{id}/stat  │
│  ├─ GET  /api/fraud-network          ├─ GET  /api/claims/{id}/risk  │
│  └─ WS   /ws/investigate             ├─ GET  /api/claims/{id}/docs  │
│                                      ├─ GET  /api/claims/{id}/tasks │
│                                      ├─ GET  /api/claims/stats      │
│                                      ├─ GET  /api/policy-alerts     │
│                                      ├─ GET  /api/config            │
│                                      └─ WS   /ws/chat/{claim_id}   │
│                                                                     │
└────────────────────────────┼────────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────────┐
│                   INTELLIGENCE LAYER                                │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐ │
│  │ Rules Engine  │  │ Risk Scoring │  │ Network/Link Analysis     │ │
│  │ (NEW)         │  │ (NEW)        │  │ (MODIFY existing graph)   │ │
│  │ 14 rules      │  │ Weighted     │  │ Member/Dep/Provider/Addr  │ │
│  │ deterministic │  │ heuristic    │  │ pattern detection         │ │
│  └──────┬────────┘  └──────┬───────┘  └───────────┬───────────────┘ │
│         │                  │                       │                │
│  ┌──────▼──────────────────▼───────────────────────▼──────────────┐ │
│  │              Composite Risk Score (0-100) + Route              │ │
│  └───────────────────────────┬────────────────────────────────────┘ │
│                              │                                      │
│  ┌───────────────────────────▼────────────────────────────────────┐ │
│  │              COPILOT AGENT (LangGraph)                         │ │
│  │  ┌──────────────┐ ┌───────────────┐ ┌───────────────────────┐ │ │
│  │  │ Fraud Tools   │ │ Workflow Tools│ │ Policy Intel Tools    │ │ │
│  │  │ (eligibility, │ │ (PMR, CBR,   │ │ (state rules, ET,     │ │ │
│  │  │  docs, family │ │  TAT, notes) │ │  benefit changes,     │ │ │
│  │  │  provider)    │ │              │ │  coverage matching)   │ │ │
│  │  └──────────────┘ └───────────────┘ └───────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              DOCUMENT ANALYSIS ENGINE (simulated)              │ │
│  │  DOC-001 through DOC-013 checks on metadata flags             │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  EXISTING (KEEP):                    NEW:                           │
│  ├─ graph.py (autonomous loop)       ├─ copilot.py (chat agent)    │
│  ├─ nodes.py                         ├─ tools_supplemental.py      │
│  ├─ prompts.py                       ├─ prompts_supplemental.py    │
│  ├─ tools_investigation.py           ├─ rules_engine.py            │
│  └─ tools_dossier.py                 ├─ risk_scoring.py            │
│                                      ├─ document_analysis.py       │
│                                      └─ checklist.py               │
│                                                                     │
└────────────────────────────┼────────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────────┐
│                    DATA LAYER                                       │
│                                                                     │
│  EXISTING (KEEP):                    NEW:                           │
│  ├─ generate_synthetic.py            ├─ generate_supplemental.py   │
│  ├─ features.py                      ├─ domain_config.py           │
│  ├─ anomaly.py                       └─ supplemental_cache.pkl     │
│  ├─ graph.py                                                        │
│  └─ data_cache.pkl                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## PART 1: Domain Configuration & Data Models

### 1.1 Domain Configuration Model

```python
# NEW FILE: claims-copilot/domain_config.py

"""
Domain-agnostic configuration model. Each line of business registers 
a config that the platform reads at startup. No LOB-specific logic hardcoded.

The platform currently supports two domains:
  - "provider_fraud" (existing prototype)
  - "prudential_supplemental_health" (new)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

@dataclass
class DomainConfig:
    domain_id: str
    domain_label: str
    claim_types: List[str]
    entity_types: List[str]
    fraud_rules: List[Dict]          # rule definitions for rules engine
    risk_features: List[Dict]        # features for risk scoring
    relationship_types: List[Dict]   # for entity graph
    document_checks: List[Dict]      # DOC-001 through DOC-013 style checks
    workflow_tasks: List[str]        # PMR, CBR, etc.
    policy_alerts: List[Dict]       # active policy changes
    tools: List[str]                # tool names available for this domain
    checklist_steps: List[Dict]     # investigation checklist
    copilot_system_prompt: str
    dossier_template: str

# Prudential Supplemental Health configuration
PRUDENTIAL_SUPPLEMENTAL_HEALTH = DomainConfig(
    domain_id="prudential_supplemental_health",
    domain_label="Supplemental Health",
    claim_types=["wellness", "accident", "hospital_indemnity", "critical_illness"],
    entity_types=["member", "dependent", "provider", "facility", "employer", "policy"],
    
    fraud_rules=[
        # Full rule definitions — see Part 3 (rules_engine.py)
        # Referenced here by ID for the config; engine loads full definitions
    ],
    
    risk_features=[
        # Feature categories: policy, member, claim, provider, network, temporal, document
        # See Part 4 (risk_scoring.py)
    ],
    
    relationship_types=[
        {"source": "member", "target": "dependent", "type": "has_dependent"},
        {"source": "member", "target": "provider", "type": "treated_by"},
        {"source": "member", "target": "employer", "type": "employed_by"},
        {"source": "member", "target": "address", "type": "lives_at"},
        {"source": "member", "target": "policy", "type": "has_policy"},
        {"source": "dependent", "target": "provider", "type": "treated_by"},
        {"source": "dependent", "target": "address", "type": "lives_at"},
    ],
    
    document_checks=[
        # DOC-001 through DOC-013 — see Part 5 (document_analysis.py)
    ],
    
    workflow_tasks=["PMR", "CBR", "TAT_ESCALATION"],
    
    policy_alerts=[
        {
            "id": "PA-001",
            "effective": "2025-09-18",
            "description": "Surgical repair benefits now paid regardless of confinement. Outpatient surgery now covered.",
            "applies_to": ["hospital_indemnity"],
            "previous_rule": "Surgical repair only when confined to hospital",
            "new_rule": "Surgical repair paid for hospital or outpatient",
        }
    ],
    
    tools=[],           # populated at runtime from tool registration
    checklist_steps=[],  # see Part 8 (checklist.py)
    copilot_system_prompt="",  # see prompts_supplemental.py
    dossier_template="",       # see compile_dossier modifications
)

def get_domain_config(domain_id: str) -> DomainConfig:
    """Returns config for given domain. Currently supports two domains."""
    configs = {
        "prudential_supplemental_health": PRUDENTIAL_SUPPLEMENTAL_HEALTH,
        "provider_fraud": None,  # existing prototype — no config object needed yet
    }
    return configs.get(domain_id)
```

### 1.2 Claims Data Model

```python
# NEW FILE: claims-copilot/cases.py

"""
Unified case/claim data model. Supports both:
  - Provider fraud cases (from existing anomaly detection)
  - Supplemental health claims (new Prudential domain)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict
from datetime import datetime

class CaseType(str, Enum):
    PROVIDER_FRAUD = "provider_fraud"
    SUPPLEMENTAL_HEALTH = "supplemental_health"

class ClaimType(str, Enum):
    WELLNESS = "wellness"
    ACCIDENT = "accident"
    HOSPITAL_INDEMNITY = "hospital_indemnity"
    CRITICAL_ILLNESS = "critical_illness"

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
    case_id: str                       # e.g. "WC-247", "NET-6610"
    case_type: CaseType
    claim_type: Optional[ClaimType]    # None for provider fraud
    subject_id: str                    # member_id or provider_id
    subject_name: str
    priority: CasePriority
    risk_score: float                  # 0-100
    flag_reason: str                   # one-line reason for flagging
    rules_triggered: List[str]         # rule IDs that fired
    status: CaseStatus = CaseStatus.NEW
    created_at: datetime = field(default_factory=datetime.now)
    summary: Optional[str] = None
    key_metrics: Dict = field(default_factory=dict)
    workflow_tasks: List[Dict] = field(default_factory=list)  # open PMR/CBR/TAT
    document_flags: List[str] = field(default_factory=list)   # DOC check results
    checklist_state: Dict = field(default_factory=dict)       # step completion tracking
    investigation_history: List[Dict] = field(default_factory=list)
    dossier: Optional[str] = None
```

---

## PART 2: Synthetic Data Generation (Supplemental Health)

### 2.1 Data Models for Supplemental Health

```python
# NEW FILE: claims-copilot/data/generate_supplemental.py

"""
Generates the full Prudential supplemental health dataset:
  - 10 employers
  - 200 members
  - 300 dependents (one outlier with 35)
  - 40 providers
  - 15 facilities
  - 180 addresses (some shared for network detection)
  - 200 policies
  - 500 claims (with document metadata per claim)
  - Workflow tasks (PMR/CBR) on subset of claims
  - 10 embedded fraud scenarios
  - 5 false positive scenarios

All data synthetic. Document analysis is simulated via metadata flags.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random

# ---- Entity Models ----

@dataclass
class Employer:
    employer_id: str          # "EMP-001"
    name: str
    size: str                 # "large", "mid", "small"
    industry: str
    state: str

@dataclass
class Member:
    member_id: str            # "MBR-001"
    name: str
    dob: datetime
    age: int
    address_id: str
    employer_id: str
    policy_id: str
    suspicious_banner: bool   # existing Prudential flag
    
@dataclass
class Dependent:
    dependent_id: str         # "DEP-001"
    name: str
    dob: datetime
    age: int
    relationship: str         # "spouse", "child", "other"
    member_id: str
    address_id: str
    date_added: datetime      # when added to policy

@dataclass
class Provider:
    provider_id: str          # "PRV-001"
    name: str
    specialty: str
    facility_id: Optional[str]
    state: str
    npi: str                  # national provider identifier (synthetic)

@dataclass
class Facility:
    facility_id: str          # "FAC-001"
    name: str
    type: str                 # "hospital", "surgical_center", "clinic"
    state: str

@dataclass
class Address:
    address_id: str           # "ADR-001"
    street: str
    city: str
    state: str
    zip: str

@dataclass
class Policy:
    policy_id: str            # "POL-001"
    member_id: str
    policy_type: str          # maps to available claim types
    start_date: datetime
    end_date: Optional[datetime]  # None if active
    status: str               # "active", "lapsed", "terminated"
    coverage_amount: float
    premium: float
    owner_id: str             # usually same as member_id
    beneficiary_id: str
    owner_change_history: List[Dict]       # [{date, old_owner, new_owner}]
    beneficiary_change_history: List[Dict]
    dependent_ids: List[str]
    state: str                # governing state
    et_state: Optional[str]   # extra-territorial state if different

@dataclass 
class DocumentMetadata:
    """
    Simulates what a real document analysis engine would find.
    Each claim has one of these. For fraud scenarios, multiple flags trigger.
    For legitimate claims, occasionally one flag triggers (realistic false positives).
    """
    doc_id: str
    claim_id: str
    format: str                        # "pdf", "docx", "image", "handwritten_scan"
    submission_method: str             # "portal", "fax", "email"
    has_headers: bool
    header_types_present: List[str]   # ["OVN", "HCF"]
    color_mode: str                   # "color", "bw"
    font_consistency_score: float     # 0.0-1.0 (1.0 = perfectly consistent)
    font_sizes_detected: List[int]    # [10, 12] normal, [10, 12, 16, 8] inconsistent
    erasure_indicators: bool
    typed_over_handwritten: bool
    signature_confidence: float       # 0.0-1.0
    medical_spelling_errors: List[str]
    vitals_present: bool
    medication_list_present: bool
    provider_match: bool              # does provider match requesting provider
    creation_date_vs_visit_date_gap: int  # days; large gap = suspicious

@dataclass
class WorkflowTask:
    task_id: str
    claim_id: str
    task_type: str            # "PMR", "CBR", "TAT_ESCALATION"
    created_date: datetime
    due_date: Optional[datetime]
    status: str               # "open", "completed", "overdue"
    notes: List[Dict]         # [{date, author, text}]
    contact_history: List[Dict]  # for CBR: [{date, method, outcome}]

@dataclass
class Claim:
    claim_id: str             # "WC-247", "AC-103", "HI-089", "CI-051"
    claim_type: ClaimType
    member_id: str
    dependent_id: Optional[str]  # if claim is for a dependent
    provider_id: str
    facility_id: Optional[str]
    date_of_service: datetime
    date_filed: datetime
    amount: float
    benefit_max: float
    diagnosis_code: str
    diagnosis_description: str
    status: str               # "pending", "approved", "denied", "under_investigation"
    auto_adjudicated: bool
    document_metadata: DocumentMetadata
    workflow_tasks: List[WorkflowTask]
    
    # Populated by intelligence pipeline at startup:
    risk_score: float = 0.0
    rules_triggered: List[str] = field(default_factory=list)
    document_flags: List[str] = field(default_factory=list)
    network_flags: List[str] = field(default_factory=list)
```

### 2.2 Fraud Scenarios and False Positives

```python
# Still inside generate_supplemental.py

"""
10 FRAUD SCENARIOS — embedded in the 500 claims.
Each scenario may generate multiple claims.

The coding agent should generate these with enough detail that
every tool call returns meaningful, specific data.
"""

FRAUD_SCENARIOS = {
    1: {
        "name": "35 Dependents Added",
        "claim_type": "wellness",
        "target_risk_score": 94,
        "description": """
            Member M. Rivera adds 35 dependents over 14 days, 
            files wellness claims for each at exactly $100.
            All dependents share one address with 2 other members.
        """,
        "rules_triggered": ["R-001", "R-002", "R-009"],
        "claims_generated": 35,  # one per dependent
        "network_signals": ["shared_address", "dependent_count_outlier"],
        "document_flags": [],  # wellness claims have minimal docs
    },
    2: {
        "name": "Termination Rush",
        "claim_type": "wellness+accident",
        "target_risk_score": 85,
        "description": """
            Member files 8 claims in final 30 days before 
            coverage ends September 2025.
        """,
        "rules_triggered": ["R-004"],
        "claims_generated": 8,
        "network_signals": ["temporal_cluster"],
        "document_flags": [],
    },
    3: {
        "name": "Owner Change Before Critical Illness",
        "claim_type": "critical_illness",
        "target_risk_score": 88,
        "description": """
            Policy owner changed 45 days before $50K critical 
            illness claim filed. New owner is not a family member.
        """,
        "rules_triggered": ["R-006"],
        "claims_generated": 1,
        "network_signals": ["owner_change_proximity"],
        "document_flags": [],
    },
    4: {
        "name": "Fabricated Accident",
        "claim_type": "accident",
        "target_risk_score": 79,
        "description": """
            Accident details physically inconsistent. Medical records 
            show injury mechanism different from what was claimed.
        """,
        "rules_triggered": [],
        "claims_generated": 1,
        "network_signals": [],
        "document_flags": ["claim_to_coverage_mismatch"],
    },
    5: {
        "name": "Provider Mill",
        "claim_type": "hospital_indemnity",
        "target_risk_score": 82,
        "description": """
            One provider supports 15 hospital indemnity claims in one month,
            near-identical documentation across patients.
        """,
        "rules_triggered": ["R-005"],
        "claims_generated": 15,
        "network_signals": ["provider_cluster"],
        "document_flags": ["DOC-008"],  # font consistency across patients
    },
    6: {
        "name": "Tampered Medical Records",
        "claim_type": "accident",
        "target_risk_score": 76,
        "description": """
            Records have mixed fonts, erasures, typed dates over 
            handwritten originals, submitted as Word doc via email.
        """,
        "rules_triggered": ["R-013"],
        "claims_generated": 1,
        "network_signals": [],
        "document_flags": ["DOC-001", "DOC-002", "DOC-003", "DOC-007", "DOC-011"],
    },
    7: {
        "name": "Duplicate Resubmission",
        "claim_type": "accident",
        "target_risk_score": 71,
        "description": """
            Previously denied accident claim resubmitted 
            with date changed by one day.
        """,
        "rules_triggered": ["R-008", "R-010"],
        "claims_generated": 2,  # original + resubmission
        "network_signals": [],
        "document_flags": [],
    },
    8: {
        "name": "Dependent Ring",
        "claim_type": "wellness",
        "target_risk_score": 87,
        "description": """
            3 members from different employers share 8 "dependents" 
            at the same address, filing wellness claims.
        """,
        "rules_triggered": ["R-007"],
        "claims_generated": 8,
        "network_signals": ["shared_dependents", "shared_address", "cross_employer"],
        "document_flags": [],
    },
    9: {
        "name": "Surgical Repair Exploit",
        "claim_type": "hospital_indemnity",
        "target_risk_score": 65,
        "description": """
            4 claims filed day after policy change (PA-001) for 
            outpatient surgical repair, all from same employer group.
        """,
        "rules_triggered": ["R-014"],
        "claims_generated": 4,
        "network_signals": ["temporal_cluster", "employer_cluster"],
        "document_flags": [],
    },
    10: {
        "name": "Missing Headers / B&W Records",
        "claim_type": "critical_illness",
        "target_risk_score": 68,
        "description": """
            Critical illness claim with medical records missing 
            all standard headers, B&W photocopies, no vitals documented.
        """,
        "rules_triggered": [],
        "claims_generated": 1,
        "network_signals": [],
        "document_flags": ["DOC-005", "DOC-006", "DOC-012"],
    },
}

FALSE_POSITIVE_SCENARIOS = {
    "A": {
        "name": "New Employee Genuine Accident",
        "flag_triggered": "R-003",
        "why_legitimate": "Genuine accident, bad timing — 60 days after policy start",
    },
    "B": {
        "name": "Complex Claim Multiple Contacts",
        "flag_triggered": "R-011",
        "why_legitimate": "Complex claim, member genuinely needs updates, 4 contacts in 15 days",
    },
    "C": {
        "name": "Rural Clinic B&W Records",
        "flag_triggered": "DOC-006",
        "why_legitimate": "Small rural clinic with old scanner, records are legitimate",
    },
    "D": {
        "name": "Blended Family Dependents",
        "flag_triggered": "R-001",
        "why_legitimate": "Marriage + stepchildren, 6 dependents added in 30 days is legitimate",
    },
    "E": {
        "name": "Genuine High Hospital Bill",
        "flag_triggered": "R-009",
        "why_legitimate": "Hospital bill genuinely exceeded benefit maximum",
    },
}

def generate_supplemental_data() -> Dict:
    """
    Returns dict with all generated data:
    {
        "employers": List[Employer],
        "members": List[Member],
        "dependents": List[Dependent],
        "providers": List[Provider],
        "facilities": List[Facility],
        "addresses": List[Address],
        "policies": List[Policy],
        "claims": List[Claim],         # 500 claims
        "workflow_tasks": List[WorkflowTask],
        "policy_alerts": List[Dict],
    }
    
    Generation order:
      1. Employers (10) — mix of large/mid/small
      2. Addresses (180) — most unique, some shared for network detection
      3. Members (200) — distributed across employers
      4. Dependents (300) — realistic distribution + one outlier with 35
      5. Providers (40) — physicians, hospitals, clinics
      6. Facilities (15) — hospitals, surgical centers
      7. Policies (200) — one per member, varying coverage, with change histories
      8. Claims (500) — distribution:
           Wellness: 250 (most auto-adjudicated)
           Hospital Indemnity: 100
           Accident: 100
           Critical Illness: 50
         Embed 10 fraud scenarios + 5 false positive scenarios
      9. Document metadata — one per claim, flags set per fraud scenario
     10. Workflow tasks:
           15% of claims: open PMR (5% with no notes past 5-day TAT)
           10% of claims: open CBR (3% with prior CBR, no call made)
           8% of claims: approaching or past TAT
    
    Claim ID format by type:
      Wellness: "WC-XXX"
      Accident: "AC-XXX"
      Hospital Indemnity: "HI-XXX"
      Critical Illness: "CI-XXX"
    """
    pass
```

---

## PART 3: Intelligence Layer — Rules Engine

```python
# NEW FILE: claims-copilot/intelligence/rules_engine.py

"""
Layer 1: Deterministic rules. Fast, explainable, run on every claim.
Returns list of triggered rules with severity and explanation.

Rule severity:
  BLOCK — prevents auto-adjudication, requires analyst review
  FLAG  — surfaces in queue, analyst should investigate
  INFO  — informational, noted in checklist but doesn't force review
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class Severity(str, Enum):
    BLOCK = "BLOCK"
    FLAG = "FLAG"
    INFO = "INFO"

@dataclass
class Rule:
    rule_id: str
    name: str
    description: str
    condition_description: str   # human-readable condition
    severity: Severity
    explanation_template: str    # template with {placeholders} for specifics

@dataclass
class RuleResult:
    rule_id: str
    name: str
    severity: Severity
    triggered: bool
    explanation: str             # filled template with actual values
    evidence: Dict              # supporting data points

# ---- Rule Definitions ----

RULES = [
    Rule("R-001", "Dependent Spike",
         "Dependents added exceeds threshold in lookback window",
         "dependents_added > 5 in 30 days",
         Severity.BLOCK,
         "Member {member_name} added {count} dependents in {days} days (threshold: 5 in 30)"),
    
    Rule("R-002", "Claim Velocity",
         "Claims per member exceeds threshold per quarter",
         "claims > 10 per member per quarter",
         Severity.FLAG,
         "Member {member_name} has filed {count} claims this quarter (threshold: 10)"),
    
    Rule("R-003", "Early Filing",
         "Claim filed shortly after policy start",
         "claim filed < 90 days after policy start",
         Severity.FLAG,
         "Claim filed {days} days after policy start date of {start_date}"),
    
    Rule("R-004", "Termination Rush",
         "Claim spike near coverage end",
         "claim count spike within 60 days of coverage end",
         Severity.FLAG,
         "Member filed {count} claims within {days} days of coverage ending {end_date}"),
    
    Rule("R-005", "Provider Cluster",
         "Same provider with abnormal patient volume for same diagnosis",
         "same provider + same diagnosis + 5 patients in 30 days",
         Severity.FLAG,
         "Provider {provider_name} has {count} patients with {diagnosis} in 30 days"),
    
    Rule("R-006", "Policy Manipulation",
         "Owner or beneficiary change shortly before claim",
         "owner/beneficiary change < 180 days before claim",
         Severity.FLAG,
         "Policy owner/beneficiary changed {days} days before claim (changed {date})"),
    
    Rule("R-007", "Dependent Age Gap",
         "Suspicious age relationship between member and dependent",
         "member-dependent age gap > 25 AND dependent age > 25",
         Severity.FLAG,
         "Member age {member_age}, dependent {dep_name} age {dep_age} (gap: {gap} years)"),
    
    Rule("R-008", "Duplicate Submission",
         "Same member, same date of service, same amount",
         "duplicate (member, date_of_service, amount)",
         Severity.BLOCK,
         "Duplicate of claim {original_claim_id}: same member, same date ({date}), same amount (${amount})"),
    
    Rule("R-009", "Benefit Max Gaming",
         "Consecutive claims at exact benefit maximum",
         "claim amount = exact benefit max, 3+ consecutive",
         Severity.INFO,
         "Last {count} claims all at exact benefit maximum of ${max_amount}"),
    
    Rule("R-010", "Resubmission After Denial",
         "Previously denied claim resubmitted with minor changes",
         "denied claim resubmitted with < 3 field changes",
         Severity.FLAG,
         "Matches denied claim {denied_claim_id} with changes: {changes}"),
    
    Rule("R-011", "CBR Frequency",
         "Member contacted multiple times recently",
         "member contacted 3+ times in 15 days",
         Severity.INFO,
         "Member has contacted {count} times in last {days} days"),
    
    Rule("R-012", "PMR No Follow-up",
         "Open PMR with no notes past TAT",
         "PMR open with no notes beyond 5-day TAT",
         Severity.FLAG,
         "PMR opened {days_ago} days ago, last note {last_note_days} days ago, TAT is 5 days"),
    
    Rule("R-013", "Medical Records Via Email",
         "Records received through insecure channel",
         "submission_method = email",
         Severity.INFO,
         "Medical records submitted via email (not portal or fax)"),
    
    Rule("R-014", "Policy Change Impact",
         "Claim type matches recent policy change timing",
         "claim_type in policy_alert.applies_to AND claim_date near alert.effective",
         Severity.INFO,
         "Claim type '{claim_type}' matches policy change PA-001 effective {effective_date}"),
]

def run_rules_engine(claim: 'Claim', context: Dict) -> List[RuleResult]:
    """
    Evaluates all rules against a single claim.
    
    Args:
        claim: The claim to evaluate
        context: Dict containing:
            - member: Member object
            - dependents: List of member's dependents
            - policy: Policy object
            - all_claims: All claims for this member (for velocity/pattern checks)
            - all_claims_by_provider: Claims grouped by provider (for provider cluster)
            - workflow_tasks: Open tasks for this claim
            - policy_alerts: Active policy change alerts
    
    Returns:
        List of RuleResult objects (only triggered rules, plus INFO rules that match)
    
    Implementation note:
        Each rule is a function that takes (claim, context) and returns
        Optional[RuleResult]. The engine runs all rules and collects results.
        Keep it simple — these are if/then checks, not ML.
    """
    pass
```

---

## PART 4: Intelligence Layer — Risk Scoring

```python
# NEW FILE: claims-copilot/intelligence/risk_scoring.py

"""
Layer 2: Risk scoring. Assigns 0-100 score to every claim.
Phase 1 (this prototype): Weighted heuristic.
Phase 2 (future): ML model trained on analyst confirm/dismiss actions.

Score interpretation:
  0-29:  LOW    — likely clean, fast-track eligible
  30-64: MEDIUM — some flags, needs attention
  65-100: HIGH  — significant risk indicators, priority review
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class RiskBreakdown:
    total_score: float              # 0-100
    tier: str                       # "HIGH", "MEDIUM", "LOW"
    feature_contributions: List[Dict]  # [{feature, value, weight, contribution, explanation}]
    top_factors: List[str]          # top 3 human-readable explanations

def score_claim(claim: 'Claim', context: Dict) -> RiskBreakdown:
    """
    Computes risk score for a claim using weighted feature sum.
    
    Feature categories and their weights (sum to 1.0):
    
    POLICY features (weight: 0.15):
      - policy_age_at_claim: months between policy start and claim
        (younger policy = higher risk; < 6 months scores high)
      - recent_changes_count: owner/beneficiary changes in last 180 days
      - coverage_amount: higher coverage = higher potential loss
    
    MEMBER features (weight: 0.20):
      - dependent_count: raw count (outlier detection)
      - dependent_add_velocity: dependents added per month recently
      - prior_claim_count: total prior claims
      - claim_frequency: claims per month
      - claim_type_diversity: how many different claim types filed
    
    CLAIM features (weight: 0.20):
      - amount_relative_to_max: claim amount / benefit maximum (1.0 = exact max)
      - documentation_completeness: based on document metadata fields present
      - document_format_flags: count of DOC checks triggered
    
    PROVIDER features (weight: 0.15):
      - total_claims_supported: claims this provider has supported
      - patient_count: unique patients
      - approval_rate: approved / total
      - geographic_concentration: % of patients from one area
    
    NETWORK features (weight: 0.15):
      - shared_address_count: members at same address
      - shared_provider_with_flagged: shares provider with already-flagged members
      - family_claim_correlation: family members all filing simultaneously
    
    TEMPORAL features (weight: 0.10):
      - proximity_to_termination: days until coverage end
      - time_between_dependent_add_and_claim: short = suspicious
      - proximity_to_policy_change: claims right after policy changes
    
    RULES BOOST (weight: 0.05):
      - rules_triggered_count: number of rules fired
      - max_rule_severity: BLOCK=1.0, FLAG=0.6, INFO=0.2
    
    Each feature is normalized to 0.0-1.0 before weighting.
    Final score = sum(feature_normalized * feature_weight) * 100, capped at 100.
    
    Returns RiskBreakdown with full explanation of what contributed.
    """
    pass
```

---

## PART 5: Intelligence Layer — Document Analysis Engine

```python
# NEW FILE: claims-copilot/intelligence/document_analysis.py

"""
Simulated document analysis engine.
In the prototype, we check the DocumentMetadata flags attached to each claim.
In production, this would run actual document forensics (OCR, image analysis, etc.).

IMPORTANT: Be explicit in copilot responses that document analysis is 
"based on document metadata" — don't pretend we're running real forensics.
The framework shows WHAT we would check and HOW results would surface.
"""

from dataclasses import dataclass
from typing import List, Dict

@dataclass
class DocumentCheckResult:
    check_id: str       # "DOC-001" through "DOC-013"
    check_name: str
    passed: bool        # True = no issue found
    severity: str       # "high", "medium", "low" (if failed)
    finding: str        # human-readable description of what was found
    evidence: str       # specific data point

DOCUMENT_CHECKS = [
    {"id": "DOC-001", "name": "Font Inconsistency",
     "description": "Multiple font styles in same document",
     "check_field": "font_consistency_score",
     "threshold": 0.8,  # below this = flag
     "severity": "high"},
    
    {"id": "DOC-002", "name": "Erasure Indicators",
     "description": "Evidence of erased or whited-out content",
     "check_field": "erasure_indicators",
     "threshold": True,  # True = flag
     "severity": "high"},
    
    {"id": "DOC-003", "name": "Typed Over Handwritten",
     "description": "Typed text overlaying handwritten dates or notes",
     "check_field": "typed_over_handwritten",
     "threshold": True,
     "severity": "high"},
    
    {"id": "DOC-004", "name": "Handwritten Report",
     "description": "Entire report handwritten (unusual for modern facilities)",
     "check_field": "format",
     "threshold": "handwritten_scan",
     "severity": "medium"},
    
    {"id": "DOC-005", "name": "Missing Headers",
     "description": "No OVN, HCF, or standard medical record headers",
     "check_field": "has_headers",
     "threshold": False,
     "severity": "medium"},
    
    {"id": "DOC-006", "name": "Black and White Records",
     "description": "Records that should be color appear B&W (possible altered photocopy)",
     "check_field": "color_mode",
     "threshold": "bw",
     "severity": "low"},
    
    {"id": "DOC-007", "name": "Editable Word Document",
     "description": "Medical records submitted as .doc/.docx instead of PDF/image",
     "check_field": "format",
     "threshold": "docx",
     "severity": "high"},
    
    {"id": "DOC-008", "name": "Inconsistent Font Sizes",
     "description": "Multiple font sizes within uniform document",
     "check_field": "font_sizes_detected",
     "threshold": 3,  # more than 3 different sizes = flag
     "severity": "medium"},
    
    {"id": "DOC-009", "name": "Medical Misspellings",
     "description": "Medical terminology misspelled (suggests non-medical author)",
     "check_field": "medical_spelling_errors",
     "threshold": 1,  # any spelling errors = flag
     "severity": "medium"},
    
    {"id": "DOC-010", "name": "Suspicious Signature",
     "description": "Signature doesn't match known specimens or appears stamped",
     "check_field": "signature_confidence",
     "threshold": 0.6,  # below this = flag
     "severity": "high"},
    
    {"id": "DOC-011", "name": "Records Via Email",
     "description": "Records sent via email rather than secure portal or fax",
     "check_field": "submission_method",
     "threshold": "email",
     "severity": "low"},
    
    {"id": "DOC-012", "name": "Missing Vitals/Medication",
     "description": "Full medical records without routine vitals or medication list",
     "check_field": ["vitals_present", "medication_list_present"],
     "threshold": False,  # either missing = flag
     "severity": "medium"},
    
    {"id": "DOC-013", "name": "Non-Requesting Provider Records",
     "description": "Records from provider different than requesting provider",
     "check_field": "provider_match",
     "threshold": False,
     "severity": "low"},
]

def run_document_checks(doc_metadata: 'DocumentMetadata') -> List[DocumentCheckResult]:
    """
    Runs all 13 document checks against a claim's document metadata.
    Returns list of DocumentCheckResult for all checks (passed and failed).
    
    Implementation: straightforward field comparisons against thresholds.
    """
    pass
```

---

## PART 6: Intelligence Layer — Network/Link Analysis

```python
# MODIFY: Use existing NetworkX infrastructure but with new entity types.

"""
Layer 3: Entity graph for supplemental health.
Reuses existing data/graph.py infrastructure but builds a different graph
for the supplemental health domain.

For the prototype, this runs at startup and caches the graph.
The copilot tools query this graph on demand.
"""

# NEW FILE: claims-copilot/intelligence/entity_graph.py

import networkx as nx
from typing import Dict, List

def build_supplemental_health_graph(data: Dict) -> nx.DiGraph:
    """
    Builds entity graph from supplemental health data.
    
    Nodes (with attributes):
      - member: {name, age, employer_id, address_id, suspicious_banner}
      - dependent: {name, age, relationship, member_id, date_added}
      - provider: {name, specialty, npi}
      - facility: {name, type}
      - employer: {name, size}
      - address: {street, city, state, zip}
      - policy: {type, start_date, status, coverage_amount}
    
    Edges:
      - member → dependent (has_dependent)
      - member → provider (treated_by, with claim_count attribute)
      - member → employer (employed_by)
      - member → address (lives_at)
      - member → policy (has_policy)
      - dependent → provider (treated_by)
      - dependent → address (lives_at)
    
    Returns the graph. Fraud pattern detection happens in the tools
    that query this graph (find_related_claims, detect_dependent_anomalies).
    """
    pass

def detect_patterns(graph: nx.DiGraph) -> List[Dict]:
    """
    Runs pattern detection on the entity graph.
    Called at startup to pre-compute patterns for the dashboard.
    
    Patterns detected:
      - dependent_ring: "unrelated" members share dependents
        (find dependents connected to multiple members who aren't related)
      - address_cluster: many claimants at same address
        (addresses with > 3 unrelated members)
      - provider_mill: one provider, abnormal claim volume
        (providers with treated_by edges > 2 std dev above mean)
      - employer_collusion: claim spike from one group
        (employer with claim count spike in recent window)
      - cross_member_dependent_sharing: same dependent on multiple policies
        (dependents with has_dependent edges from multiple members)
    
    Returns list of detected patterns:
    [
        {
            "pattern_type": "dependent_ring",
            "entities_involved": ["MBR-012", "MBR-045", "MBR-089"],
            "description": "3 members from different employers share 8 dependents",
            "severity": "high",
            "claim_ids_affected": ["WC-247", "WC-248", ...]
        },
        ...
    ]
    """
    pass
```

---

## PART 7: Copilot Tools (Supplemental Health)

### 7.1 Fraud Investigation Tools

```python
# NEW FILE: claims-copilot/agents/tools_supplemental.py

"""
Tools for Prudential supplemental health claim investigation.
Organized into three categories:
  - Fraud tools (investigation-focused)
  - Workflow tools (daily examiner tasks)
  - Policy intelligence tools (coverage determination)

All tools access _context (DataContext) for claim and entity data.

IMPORTANT DESIGN PRINCIPLE:
These tools serve the EXAMINER WORKFLOW, not just fraud detection.
The eligibility check, policy matching, and state rules tools are 
used on every claim — not just suspicious ones. That's the value prop.
"""

from langchain_core.tools import tool
from typing import Annotated, Dict, List

_context = None

def set_context(ctx):
    global _context
    _context = ctx

# ================================================================
# FRAUD INVESTIGATION TOOLS
# ================================================================

@tool
def check_eligibility(
    claim_id: Annotated[str, "The claim ID, e.g. WC-247"]
) -> Dict:
    """
    Consolidated eligibility check. Replaces checking 3 separate systems.
    This is the single most valuable tool for daily workflow — examiners
    currently switch between multiple systems to verify eligibility.
    
    Output: {
        claim_id,
        member_name,
        policy_status: "active" | "lapsed" | "terminated",
        member_verified: bool,
        dob_verified: bool,
        benefit_type_covered: bool,
        coverage_active_on_service_date: bool,
        expiration_date,
        issues: [str],           # any eligibility problems found
        eligible: bool,          # overall determination
        explanation: str
    }
    
    Checks:
      - Policy status (active, lapsed, terminated)
      - Member identity and DOB
      - Coverage includes claimed benefit type
      - Service date falls within coverage period
      - DOB → expiration date chain is valid
    """
    pass

@tool
def check_family_claims(
    claim_id: Annotated[str, "The claim ID"]
) -> Dict:
    """
    Returns all claims from member + their dependents in last 100 days.
    This is "the 100-day family check" that examiners do manually.
    
    Output: {
        claim_id,
        member_name,
        lookback_days: 100,
        member_claims: [{claim_id, type, date, amount, status}],
        dependent_claims: [{dependent_name, claim_id, type, date, amount, status}],
        total_claims_count: int,
        total_amount: float,
        patterns_noted: [str],   # e.g. "All claims filed same week"
        normal_range: str        # what's typical for comparison
    }
    """
    pass

@tool
def analyze_medical_documents(
    claim_id: Annotated[str, "The claim ID"]
) -> Dict:
    """
    Runs all DOC-001 through DOC-013 checks on claim's document metadata.
    Returns detailed results per check.
    
    NOTE: In this prototype, analysis is based on simulated document metadata.
    In production, this would integrate with document forensics services.
    
    Output: {
        claim_id,
        document_format: str,
        submission_method: str,
        checks_run: 13,
        checks_passed: int,
        checks_failed: int,
        results: [
            {check_id, check_name, passed, severity, finding, evidence}
        ],
        high_severity_flags: [str],  # just the high-severity failures
        summary: str                  # plain-language summary
    }
    """
    pass

@tool
def detect_dependent_anomalies(
    claim_id: Annotated[str, "The claim ID"]
) -> Dict:
    """
    Analyzes dependent patterns for the member associated with this claim.
    Catches the 35-dependent case and similar abuse patterns.
    
    Output: {
        claim_id,
        member_name,
        dependent_count: int,
        dependents: [{name, age, relationship, date_added}],
        anomalies: [
            {
                type: str,      # "count_outlier", "add_velocity", "age_gap", 
                                # "cross_member_overlap", "shared_address"
                severity: str,
                description: str,
                evidence: str
            }
        ],
        add_velocity: float,     # dependents added per month (recent)
        cross_member_overlaps: [{other_member, shared_dependent, shared_address}],
        normal_range: str        # typical dependent count for comparison
    }
    """
    pass

@tool
def check_provider_patterns(
    claim_id: Annotated[str, "The claim ID"]
) -> Dict:
    """
    Analyzes the provider associated with this claim for suspicious patterns.
    Detects provider mills and templated documentation.
    
    Output: {
        claim_id,
        provider_name,
        provider_specialty,
        total_claims_this_month: int,
        unique_patients_this_month: int,
        approval_rate: float,
        documentation_similarity_score: float,  # across patients
        geographic_concentration: float,
        flags: [str],
        compared_to_peers: {
            avg_claims_per_month: float,
            avg_patients: float,
            this_provider_percentile: float
        }
    }
    """
    pass

@tool 
def flag_inconsistencies(
    claim_id: Annotated[str, "The claim ID"]
) -> Dict:
    """
    Cross-references ALL available data for contradictions.
    Also provides innocent explanations for each finding.
    
    Output: {
        claim_id,
        inconsistencies: [
            {
                type: str,
                severity: str,
                description: str,
                evidence: str
            }
        ],
        innocent_explanations: [str],
        overall_concern_level: str
    }
    
    Checks:
      1. Claim details vs medical records (diagnosis match)
      2. Timing patterns (dependent add → claim timing)
      3. Amount patterns (benefit max gaming)
      4. Document quality vs claim complexity
      5. Provider patterns vs peer norms
      6. Network signals (shared addresses, shared dependents)
    
    The innocent_explanations field is CRITICAL. For every red flag,
    generate at least one plausible legitimate explanation. This is
    what makes the copilot trustworthy — it doesn't just accuse.
    """
    pass

@tool
def find_related_claims(
    claim_id: Annotated[str, "The claim ID"]
) -> Dict:
    """
    Finds claims linked by provider, address, dependent, or pattern.
    Uses the entity graph for network-level discovery.
    
    Output: {
        claim_id,
        related_by_provider: [{claim_id, member, diagnosis, amount, status}],
        related_by_address: [{claim_id, member, relationship}],
        related_by_dependent: [{claim_id, member, shared_dependent}],
        related_by_pattern: [{claim_id, pattern_type, similarity_score}],
        network_risk_level: str,
        visualization_data: Dict  # for network graph rendering
    }
    """
    pass

# ================================================================
# WORKFLOW TOOLS (daily examiner tasks, not fraud-specific)
# ================================================================

@tool
def check_workflow_tasks(
    claim_id: Annotated[str, "The claim ID"]
) -> Dict:
    """
    Returns open PMR, CBR, and TAT status for a claim.
    This surfaces alongside fraud investigation — examiners need to see
    their workflow tasks regardless of fraud risk.
    
    Output: {
        claim_id,
        pmr: {
            open: bool,
            created_date: str,
            days_open: int,
            has_notes: bool,
            last_note_date: str,
            past_tat: bool,        # > 5 days without notes
            details: str
        } or None,
        cbr: {
            open: bool,
            prior_cbr_count: int,
            callback_made: bool,
            member_contact_count_15d: int,   # contacts in last 15 days
            wants_examiner: bool,
            details: str
        } or None,
        tat: {
            claim_age_days: int,
            tat_deadline_days: int,
            days_remaining: int,
            past_tat: bool,
            escalation_needed: bool
        },
        action_needed: [str]     # plain-language list of what examiner should do
    }
    """
    pass

@tool
def get_contact_history(
    claim_id: Annotated[str, "The claim ID"]
) -> Dict:
    """
    Member contact count and history. Feeds CBR logic.
    
    Output: {
        claim_id,
        member_name,
        contacts_last_15_days: int,
        contacts_last_30_days: int,
        history: [{date, method, direction, summary, resolution}],
        cbr_threshold_exceeded: bool,  # 3+ in 15 days
        frustration_risk: str          # "low", "medium", "high"
    }
    """
    pass

# ================================================================
# POLICY INTELLIGENCE TOOLS (coverage determination)
# ================================================================

@tool
def get_policy_details(
    claim_id: Annotated[str, "The claim ID"]
) -> Dict:
    """
    Returns policy terms and history. Used for both fraud review
    and daily coverage determination.
    
    Output: {
        claim_id,
        policy_id,
        member_name,
        policy_type,
        start_date,
        end_date,
        status,
        coverage_amount,
        premium,
        owner: {name, relationship, change_date},
        beneficiary: {name, relationship, change_date},
        owner_change_history: [{date, old, new}],
        beneficiary_change_history: [{date, old, new}],
        dependent_count: int,
        governing_state: str,
        et_state: str,
        policy_age_months: int,
        risk_flags: [str]
    }
    """
    pass

@tool
def check_state_rules(
    claim_id: Annotated[str, "The claim ID"]
) -> Dict:
    """
    Determines applicable state rules and ET resolution.
    ET (extra-territorial) rules are complex: most recent ET supersedes policy.
    
    Output: {
        claim_id,
        member_service_state: str,
        policy_governing_state: str,
        et_state: str,
        et_supersedes: bool,
        applicable_rules: [
            {state, rule_type, description, effective_date}
        ],
        exclusions: [str],          # e.g. "Florida intoxication exclusion"
        resolution_explanation: str  # plain-language ET hierarchy explanation
    }
    """
    pass

@tool
def check_policy_alerts(
    claim_id: Annotated[str, "The claim ID"]
) -> Dict:
    """
    Checks if any active policy changes affect this claim.
    Proactively surfaces changes the examiner needs to know about.
    
    Output: {
        claim_id,
        alerts_applicable: [
            {
                alert_id,
                effective_date,
                description,
                previous_rule,
                new_rule,
                applies_because: str,   # why this alert matters for this claim
                timing_note: str        # filed before/after effective date
            }
        ],
        exploitation_flag: bool,  # timing suggests gaming the change
        no_alerts: bool
    }
    """
    pass

@tool
def match_claim_to_coverage(
    claim_id: Annotated[str, "The claim ID"]
) -> Dict:
    """
    Compares claim details against policy terms. Returns coverage determination.
    This is the hard part of accident and hospital indemnity claims —
    matching what happened to what's covered.
    
    Output: {
        claim_id,
        claim_type,
        claimed_benefit,
        diagnosis,
        policy_terms_summary: str,
        coverage_matches: bool,
        match_details: str,       # specific term-by-term comparison
        exclusions_checked: [str],
        exclusions_applied: [str],
        amount_determination: {
            claimed: float,
            benefit_max: float,
            recommended: float,
            explanation: str
        }
    }
    """
    pass

# ================================================================
# UNIVERSAL TOOLS (work across all domains)
# ================================================================

@tool
def explain_risk_score(
    claim_id: Annotated[str, "The claim ID"]
) -> Dict:
    """
    Breaks down the risk score with feature contributions.
    
    Output: {
        claim_id,
        total_score: float,
        tier: str,
        top_factors: [{feature, contribution, explanation}],
        all_features: [{category, feature, value, weight, contribution}],
        rules_triggered: [{rule_id, name, severity, explanation}],
        document_flags: [{check_id, name, severity}]
    }
    """
    pass

@tool
def run_fraud_checklist(
    claim_id: Annotated[str, "The claim ID"],
    step: Annotated[int, "Specific step to run (1-7), or 0 for all"] = 0
) -> Dict:
    """
    Executes the 7-step investigation checklist.
    Can run a single step or all steps sequentially.
    See Part 8 (checklist.py) for step definitions.
    
    Output: {
        claim_id,
        steps_run: int,
        results: [
            {
                step: int,
                name: str,
                status: "pass" | "fail" | "review_needed",
                findings: [str],
                tools_used: [str],
                auto_pass: bool   # whether this step auto-passed
            }
        ],
        overall_status: str,
        next_recommended_step: int
    }
    """
    pass

# ---- Collect all tools by category ----

FRAUD_TOOLS = [
    check_eligibility,
    check_family_claims,
    analyze_medical_documents,
    detect_dependent_anomalies,
    check_provider_patterns,
    flag_inconsistencies,
    find_related_claims,
]

WORKFLOW_TOOLS = [
    check_workflow_tasks,
    get_contact_history,
]

POLICY_TOOLS = [
    get_policy_details,
    check_state_rules,
    check_policy_alerts,
    match_claim_to_coverage,
]

UNIVERSAL_TOOLS = [
    explain_risk_score,
    run_fraud_checklist,
]

ALL_SUPPLEMENTAL_TOOLS = FRAUD_TOOLS + WORKFLOW_TOOLS + POLICY_TOOLS + UNIVERSAL_TOOLS
```

### 7.2 Supplemental Health Copilot Prompt

```python
# NEW FILE: claims-copilot/agents/prompts_supplemental.py

SUPPLEMENTAL_COPILOT_PROMPT = """You are a Supplemental Health Claims Copilot 
assisting an experienced claims examiner at Prudential.

YOUR PRIMARY ROLE: Help the examiner work every claim faster and more 
accurately. You are a productivity tool first, fraud detector second.

For EVERY claim (not just suspicious ones):
- Check eligibility efficiently (one check instead of three systems)
- Surface relevant policy details and state rules
- Track workflow tasks (PMR, CBR, TAT compliance)
- Match claims to coverage terms
- Document everything for audit trail

For FLAGGED claims (risk score > 30 or rules triggered):
- Explain why the claim was flagged with specific data
- Run the investigation checklist
- Present red flags WITH innocent explanations
- Surface network connections and patterns
- Help build escalation packages when warranted

Key domain knowledge:
- Claim types: wellness (often auto-adjudicated), accident, hospital indemnity, critical illness
- Fraud patterns to watch: dependent abuse, auto-adjudication gaming, medical record 
  tampering, policy manipulation, provider mills
- Medical record red flags: altered fonts, erasures, typed over handwritten, missing 
  headers, editable formats, suspicious signatures, B&W records, misspellings, 
  records via email
- Workflow tasks: PMR (Payment Method Review), CBR (Callback Request), TAT compliance
- Policy change: Surgical repair benefits now paid regardless of hospital confinement 
  (effective 9/18/25, alert PA-001)
- ET rules: most recent ET supersedes policy; state-specific exclusions apply 
  (e.g., Florida intoxication exclusion)
- Auto-adjudication: wellness claims auto-pay in most cases; your job is to surface 
  patterns that individual auto-adjudication rules miss

Response style:
- Lead with the most actionable finding
- Use specific numbers, dates, and dollar amounts
- When presenting red flags, always include severity AND innocent explanations
- Proactively mention open workflow tasks (PMR/CBR)
- Proactively surface relevant policy alerts
- Never make final determinations — present evidence, let the examiner decide
- Keep responses focused — don't dump everything at once
- If asked "what am I missing?" — genuinely advocate for the member

Available tools:
- check_eligibility: Start here for any claim. One check replaces three systems.
- check_family_claims: All claims from member + dependents, last 100 days.
- analyze_medical_documents: Run DOC-001 through DOC-013 checks on documents.
- detect_dependent_anomalies: Dependent add patterns, age gaps, cross-member overlap.
- check_provider_patterns: Provider claim volume, patient patterns, documentation quality.
- flag_inconsistencies: Cross-reference all data for contradictions + innocent explanations.
- find_related_claims: Claims linked by provider, address, dependent, or pattern.
- check_workflow_tasks: Open PMR, CBR, TAT status for this claim.
- get_contact_history: Member contact count and history.
- get_policy_details: Policy terms, age, changes, owner/beneficiary history.
- check_state_rules: Applicable state rules, ET resolution, exclusions.
- check_policy_alerts: Active policy changes affecting this claim type.
- match_claim_to_coverage: Compare claim details against policy terms.
- explain_risk_score: Break down risk score with feature contributions.
- run_fraud_checklist: Execute 7-step investigation checklist (all or single step).
- compile_dossier: Generate investigation summary or escalation package.
"""
```

---

## PART 8: Checklist Framework

```python
# NEW FILE: claims-copilot/intelligence/checklist.py

"""
7-step investigation checklist for supplemental health claims.
Can be run step-by-step or all at once.
Each step has auto-pass criteria — if all pass, the step is green.

The checklist is both:
  1. An automation framework (runs tools, evaluates results)
  2. A progress tracker (UI shows which steps are complete)
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Callable

@dataclass
class ChecklistStep:
    step_number: int
    name: str
    description: str
    tools_used: List[str]    # tool names to call
    auto_pass_criteria: Dict  # conditions for automatic pass
    
SUPPLEMENTAL_HEALTH_CHECKLIST = [
    ChecklistStep(
        step_number=1,
        name="Initial Claim Review",
        description="Verify claim form completeness, claim type, submission channel",
        tools_used=["analyze_medical_documents"],  # format checks only
        auto_pass_criteria={
            "required_fields_present": True,
            "standard_format": True,
        },
    ),
    ChecklistStep(
        step_number=2,
        name="Eligibility Verification",
        description="Policy status, member identity, coverage confirmation, DOB chain",
        tools_used=["check_eligibility"],
        auto_pass_criteria={
            "policy_active": True,
            "member_verified": True,
            "benefit_covered": True,
        },
    ),
    ChecklistStep(
        step_number=3,
        name="Fraud Screening",
        description="Rules engine, risk score, document fraud checks",
        tools_used=["explain_risk_score", "analyze_medical_documents"],
        auto_pass_criteria={
            "no_rules_triggered": True,
            "risk_score_below": 30,
            "no_document_flags": True,
        },
    ),
    ChecklistStep(
        step_number=4,
        name="Family and Pattern Review",
        description="Family claims last 100 days, dependent legitimacy, cross-member patterns",
        tools_used=["check_family_claims", "detect_dependent_anomalies"],
        auto_pass_criteria={
            "family_claims_normal_range": True,
            "no_dependent_flags": True,
        },
    ),
    ChecklistStep(
        step_number=5,
        name="Medical Record Review",
        description="Full document analysis, provider legitimacy, diagnosis match",
        tools_used=["analyze_medical_documents", "check_provider_patterns"],
        auto_pass_criteria={
            "all_doc_checks_pass": True,
            "provider_legitimate": True,
            "diagnosis_matches_benefit": True,
        },
    ),
    ChecklistStep(
        step_number=6,
        name="Policy Terms Application",
        description="State rules, ET resolution, exclusions, policy alerts, coverage matching",
        tools_used=["get_policy_details", "check_state_rules", 
                     "check_policy_alerts", "match_claim_to_coverage"],
        auto_pass_criteria={
            "no_exclusions_apply": True,
            "claim_matches_coverage": True,
        },
    ),
    ChecklistStep(
        step_number=7,
        name="Determination",
        description="Approve/Deny/Pend/Escalate, document rationale, check open tasks",
        tools_used=["compile_dossier", "check_workflow_tasks"],
        auto_pass_criteria={},  # always requires human decision
    ),
]

def run_checklist_step(step_number: int, claim_id: str, context: Dict) -> Dict:
    """
    Executes a single checklist step by calling its tools and
    evaluating auto-pass criteria.
    
    Returns: {
        step: int,
        name: str,
        status: "pass" | "fail" | "review_needed",
        findings: [str],
        tools_used: [str],
        tool_results: Dict,
        auto_pass: bool
    }
    """
    pass

def run_full_checklist(claim_id: str, context: Dict) -> List[Dict]:
    """
    Runs all 7 steps sequentially. Short-circuits to "review_needed"
    if any BLOCK-severity issue is found.
    """
    pass
```

---

## PART 9: Copilot Agent (Chat Mode)

```python
# NEW FILE: claims-copilot/agents/copilot.py

"""
Conversational copilot agent. Domain-aware tool selection.
Same architecture as the v2 schematic but with domain routing
between provider fraud tools and supplemental health tools.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

@dataclass
class CopilotSession:
    session_id: str
    case_id: str
    case_type: str              # "provider_fraud" | "supplemental_health"
    messages: List = field(default_factory=list)
    tools_called: List[str] = field(default_factory=list)
    checklist_state: Dict = field(default_factory=dict)  # track checklist progress
    findings_cache: Dict = field(default_factory=dict)
    created_at: str = ""

_sessions: Dict[str, CopilotSession] = {}

def get_or_create_session(case_id: str, case_type: str) -> CopilotSession:
    if case_id not in _sessions:
        session = CopilotSession(
            session_id=f"sess-{case_id}",
            case_id=case_id,
            case_type=case_type,
        )
        if case_type == "provider_fraud":
            from agents.prompts import INVESTIGATION_PROMPT
            system_msg = SystemMessage(content=INVESTIGATION_PROMPT)
        elif case_type == "supplemental_health":
            from agents.prompts_supplemental import SUPPLEMENTAL_COPILOT_PROMPT
            system_msg = SystemMessage(content=SUPPLEMENTAL_COPILOT_PROMPT)
        
        session.messages = [system_msg]
        _sessions[case_id] = session
    return _sessions[case_id]

def get_tools_for_case_type(case_type: str) -> list:
    if case_type == "provider_fraud":
        from agents.tools_investigation import (
            profile_entity, compare_to_peers,
            get_claim_details, find_connections, find_ring, get_referral_history
        )
        from agents.tools_dossier import (
            search_billing_rules, find_similar_cases, estimate_recovery, compile_dossier
        )
        return [
            profile_entity, compare_to_peers, get_claim_details,
            find_connections, find_ring, get_referral_history,
            search_billing_rules, find_similar_cases,
            estimate_recovery, compile_dossier
        ]
    
    elif case_type == "supplemental_health":
        from agents.tools_supplemental import ALL_SUPPLEMENTAL_TOOLS
        from agents.tools_dossier import compile_dossier
        return ALL_SUPPLEMENTAL_TOOLS + [compile_dossier]

async def handle_analyst_message(
    case_id: str,
    case_type: str,
    analyst_message: str,
    ws=None
) -> str:
    """
    Process one analyst message and return the agent's response.
    Same flow as v2 schematic — session management, tool selection,
    message history for memory.
    """
    session = get_or_create_session(case_id, case_type)
    tools = get_tools_for_case_type(case_type)
    
    session.messages.append(HumanMessage(content=analyst_message))
    
    from agents.nodes import get_bedrock_llm
    llm = get_bedrock_llm(temperature=0.1, max_tokens=4096, agent_name="copilot")
    agent = create_react_agent(llm, tools)
    
    result = agent.invoke({"messages": session.messages})
    
    response_msg = None
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            response_msg = msg
            break
    
    response_text = response_msg.content if response_msg else "I couldn't generate a response."
    session.messages.append(AIMessage(content=response_text))
    
    for msg in result["messages"]:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                session.tools_called.append(tc["name"])
    
    return response_text
```

---

## PART 10: Case Queue Builder

```python
# NEW FILE: claims-copilot/case_queue.py

"""
Builds the unified case queue from both data sources.
"""

def build_case_queue(
    anomaly_scores_df,           # existing provider fraud data
    provider_features_df,        # existing provider features
    supplemental_claims: List,   # new supplemental health claims
) -> List['Case']:
    """
    Returns sorted list of Case objects for the frontend queue.
    
    Provider fraud cases (from existing prototype):
      - Filter anomaly_scores_df where anomaly_score > 0.6 AND entity_type == 'provider'
      - For each, create Case with:
        case_id = f"NET-{provider_id.split('-')[1]}"
        case_type = CaseType.PROVIDER_FRAUD
        risk_score = anomaly_score * 100
        priority = HIGH if anomaly_score > 0.75, MEDIUM if > 0.6
    
    Supplemental health cases (all 500 claims):
      - Create Case for every claim
      - risk_score, rules_triggered, document_flags already computed by intelligence pipeline
      - priority = HIGH if risk_score >= 65, MEDIUM if >= 30, LOW if < 30
      - Include workflow_tasks (PMR/CBR status)
    
    Sort: HIGH priority first, then by risk_score descending.
    
    Queue should show ~500 supplemental health claims + ~10-15 provider fraud cases.
    """
    pass
```

---

## PART 11: API Layer

```python
# MODIFY FILE: claims-copilot/api.py — add these endpoints

# ---- Claims Queue Endpoints ----

@app.get("/api/claims")
async def get_claims(
    case_type: Optional[str] = None,
    claim_type: Optional[str] = None,   # wellness, accident, etc.
    status: Optional[str] = None,
    priority: Optional[str] = None,
    risk_tier: Optional[str] = None,    # HIGH, MEDIUM, LOW
):
    """
    Returns claims for queue view.
    Response: {
        claims: [{
            case_id, case_type, claim_type, subject_name,
            priority, risk_score, flag_reason, rules_triggered,
            workflow_tasks_summary, status, created_at, key_metrics
        }],
        counts: {
            total,
            by_type: {wellness: N, accident: N, hospital_indemnity: N, critical_illness: N, provider_fraud: N},
            by_priority: {HIGH: N, MEDIUM: N, LOW: N},
            by_status: {new: N, in_review: N, ...}
        }
    }
    """
    pass

@app.get("/api/claims/{claim_id}")
async def get_claim_detail(claim_id: str):
    """Full claim detail including risk breakdown, rules, docs, tasks."""
    pass

@app.post("/api/claims/{claim_id}/status")
async def update_claim_status(claim_id: str, body: dict):
    pass

# ---- Intelligence Endpoints ----

@app.get("/api/claims/{claim_id}/risk")
async def get_risk_breakdown(claim_id: str):
    """Risk score breakdown with feature contributions."""
    pass

@app.get("/api/claims/{claim_id}/rules")
async def get_triggered_rules(claim_id: str):
    """Triggered rules with explanations."""
    pass

@app.get("/api/claims/{claim_id}/documents")
async def get_document_analysis(claim_id: str):
    """Document analysis results (all DOC checks)."""
    pass

@app.get("/api/claims/{claim_id}/network")
async def get_claim_network(claim_id: str):
    """Entity network for this claim's member/provider/dependents."""
    pass

@app.get("/api/claims/{claim_id}/checklist")
async def get_checklist_status(claim_id: str):
    """Checklist state with results per step."""
    pass

# ---- Workflow Endpoints ----

@app.get("/api/claims/{claim_id}/tasks")
async def get_workflow_tasks(claim_id: str):
    """Open PMR, CBR, TAT status."""
    pass

# ---- Dashboard Endpoint ----

@app.get("/api/claims/stats")
async def get_dashboard_stats():
    """
    Aggregate stats for Risk Dashboard:
    {
        intercepts: {count, total_held_amount},
        risk_distribution: {HIGH: N, MEDIUM: N, LOW: N},
        top_rules: [{rule_id, name, trigger_count}],
        patterns_detected: [{type, description, entities, severity}],
        workflow_health: {
            pmr_open: N, pmr_past_tat: N,
            cbr_pending: N, cbr_no_callback: N,
            claims_past_tat: N
        }
    }
    """
    pass

# ---- Policy Endpoints ----

@app.get("/api/policy-alerts")
async def get_policy_alerts():
    """Active policy changes."""
    pass

@app.get("/api/config")
async def get_config():
    """Current domain configuration."""
    pass

# ---- Chat WebSocket ----

@app.websocket("/ws/chat/{claim_id}")
async def chat_websocket(websocket: WebSocket, claim_id: str):
    """
    Same as v2 schematic but with supplemental_health case type support.
    
    On connect, sends:
    {
        type: "connected",
        claim_id,
        case_type,
        claim_type,        # wellness, accident, etc.
        risk_score,
        rules_triggered,
        open_tasks,        # PMR/CBR summary
        checklist_state    # which steps already completed
    }
    
    Incoming:
      { action: "message", text: "..." }
      { action: "run_checklist" }
      { action: "run_checklist_step", step: 3 }
      { action: "end_session" }
    
    Outgoing:
      { type: "thinking" }
      { type: "tool_call", tool, args }
      { type: "tool_result", tool, summary }
      { type: "response", text }
      { type: "checklist_update", step, status, result }
      { type: "policy_alert", alert }
      { type: "error", message }
    """
    pass
```

---

## PART 12: Frontend

### 12.1 Claims Queue

```jsx
// NEW FILE: claims-copilot/frontend/src/components/ClaimsQueue.jsx

/**
 * Claims queue — the examiner's landing page.
 * Shows ALL claims (500+), not just flagged ones.
 * This is the "morning view" — what the examiner sees when they start work.
 * 
 * Layout:
 *   ┌────────────────────────────────────────────────────────────────────────┐
 *   │ CLAIMS QUEUE                                      [Filter ▾] [↻]      │
 *   │                                                                        │
 *   │ [All (500)] [Wellness (250)] [Accident (100)] [HI (100)] [CI (50)]    │
 *   │ [Provider Fraud (12)]                                                  │
 *   │ Risk: [🔴 HIGH (12)] [🟡 MEDIUM (38)] [⚪ LOW (450)]                   │
 *   │                                                                        │
 *   ├────────┬──────────┬────────────┬─────────────────────┬──────┬──────────┤
 *   │ Claim# │ Type     │ Member     │ Flag / Task          │ Risk │ Status   │
 *   ├────────┼──────────┼────────────┼─────────────────────┼──────┼──────────┤
 *   │ WC-247 │ Wellness │ M. Rivera  │ 🚩 35 deps added    │ 🔴 94│ NEW      │
 *   │ CI-051 │ Crit Ill │ R. Torres  │ 🚩 Owner change 45d │ 🔴 88│ NEW      │
 *   │ WC-312 │ Wellness │ K. Adams   │ 🚩 Dep ring detect  │ 🔴 87│ NEW      │
 *   │ AC-103 │ Accident │ J. Park    │ 🚩 Tampered records │ 🟡 76│ NEW      │
 *   │ HI-089 │ Hosp Ind │ T. Chen    │ 📋 PMR open (2d)    │ 🟡 65│ IN_REVIEW│
 *   │ AC-107 │ Accident │ D. Williams│ ☎️ CBR pending       │ ⚪ 28│ NEW      │
 *   │ WL-401 │ Wellness │ S. Johnson │ ✓ Auto-adjudicated  │ ⚪ 5 │ APPROVED │
 *   └────────┴──────────┴────────────┴─────────────────────┴──────┴──────────┘
 * 
 * KEY DESIGN POINT: workflow tasks (PMR, CBR) visible alongside fraud flags.
 * Examiner sees everything in one view — fraud work and daily tasks together.
 * 
 * Fetch: GET /api/claims → populate table
 * Filter tabs: filter by claim_type and risk tier
 * Row click: onSelectCase(case) → navigate to copilot
 */
```

### 12.2 ChatPanel with Checklist

```jsx
// NEW FILE: claims-copilot/frontend/src/components/ChatPanel.jsx

/**
 * Chat interface with integrated checklist progress bar.
 * 
 * Layout:
 *   ┌──────────────────────────────────────────────────────────┐
 *   │ CLAIM WC-247 — M. Rivera               Risk: 🔴 94/100   │
 *   │ Wellness | Employer: Acme Corp | Coverage ends: Sept 2025 │
 *   │                                                          │
 *   │ ⚠️ 3 rules triggered | 📋 PMR open | ☎️ No active CBR    │
 *   ├──────────────────────────────────────────────────────────┤
 *   │                                                          │
 *   │ ┌─ Checklist Progress ─────────────────────────────────┐ │
 *   │ │ ✅ Initial  ⬜ Eligible  ⬜ Fraud  ⬜ Family         │ │
 *   │ │ ⬜ Medical  ⬜ Policy    ⬜ Determine                │ │
 *   │ └──────────────────────────────────────────────────────┘ │
 *   │                                                          │
 *   │ (chat messages with tool call indicators)                │
 *   │                                                          │
 *   ├──────────────────────────────────────────────────────────┤
 *   │ [Type your question...                          ] [Send] │
 *   ├──────────────────────────────────────────────────────────┤
 *   │ Quick actions (vary by claim type):                      │
 *   │                                                          │
 *   │ ALL CLAIMS:                                              │
 *   │ [▶ Run Full Checklist] [Check Eligibility]               │
 *   │ [Workflow Tasks] [Escalate]                              │
 *   │                                                          │
 *   │ WELLNESS:                                                │
 *   │ [Dependent Check] [Claim History] [Auto-Adj Review]      │
 *   │                                                          │
 *   │ ACCIDENT:                                                │
 *   │ [Match to Policy] [Accident Details] [State Rules]       │
 *   │                                                          │
 *   │ HOSPITAL INDEMNITY:                                      │
 *   │ [Admission/Discharge] [Provider Check] [Policy Terms]    │
 *   │                                                          │
 *   │ CRITICAL ILLNESS:                                        │
 *   │ [Medical Records] [Document Analysis] [Policy Check]     │
 *   │                                                          │
 *   │ PROVIDER FRAUD (existing):                               │
 *   │ [Profile] [Peer Compare] [Network] [Ring Detection]      │
 *   └──────────────────────────────────────────────────────────┘
 * 
 * Checklist progress updates via WebSocket "checklist_update" events.
 * Steps turn green (pass), red (fail), or yellow (review_needed).
 * 
 * WebSocket: /ws/chat/{claimId}
 * Quick action chips send pre-written prompts as messages.
 */
```

### 12.3 Risk Dashboard

```jsx
// NEW FILE: claims-copilot/frontend/src/components/RiskDashboard.jsx

/**
 * Aggregate risk view — the examiner's "morning briefing."
 * 
 * Layout:
 *   ┌─────────────────────────────────────────────────────────────┐
 *   │ RISK DASHBOARD                                    Today      │
 *   ├─────────────────────────────────────────────────────────────┤
 *   │                                                             │
 *   │ ┌─ Auto-Adjudication Intercepts ───────────────────────┐   │
 *   │ │  8 claims blocked    $12,400 held for review          │   │
 *   │ │  (would have auto-paid without platform)              │   │
 *   │ └───────────────────────────────────────────────────────┘   │
 *   │                                                             │
 *   │ ┌─ Risk Distribution ──┐  ┌─ Top Rules Triggered ────────┐ │
 *   │ │ 🔴 HIGH    12 (2%)    │  │ R-001 Dep spike        8x   │ │
 *   │ │ 🟡 MEDIUM  38 (8%)    │  │ R-002 Claim velocity  14x   │ │
 *   │ │ ⚪ LOW    450 (90%)   │  │ R-004 Term rush       11x   │ │
 *   │ └──────────────────────┘  └────────────────────────────┘ │
 *   │                                                             │
 *   │ ┌─ Patterns Detected ────────────────────────────────────┐ │
 *   │ │ 🕸️ 1 dependent ring (3 members, shared address)        │ │
 *   │ │ 🏥 1 provider cluster (Dr. X, 15 claims/mo)            │ │
 *   │ │ 📈 2 termination rush patterns                          │ │
 *   │ │ 📄 3 claims with document tampering indicators          │ │
 *   │ └────────────────────────────────────────────────────────┘ │
 *   │                                                             │
 *   │ ┌─ Workflow Health ──────────────────────────────────────┐  │
 *   │ │ PMR open: 12 (3 past TAT)                              │  │
 *   │ │ CBR pending: 8 (2 with no callback made)               │  │
 *   │ │ Claims past TAT: 5                                     │  │
 *   │ └────────────────────────────────────────────────────────┘  │
 *   └─────────────────────────────────────────────────────────────┘
 * 
 * Fetch: GET /api/claims/stats
 * Pattern items are clickable → navigate to relevant claim in queue
 */
```

### 12.4 Hook: useCopilotChat

```javascript
// NEW FILE: claims-copilot/frontend/src/hooks/useCopilotChat.js

/**
 * Same as v2 schematic but with additional event types:
 * 
 * Returns:
 *   messages: [{role, text, timestamp, tool?, toolArgs?}]
 *   isThinking: bool
 *   isConnected: bool
 *   checklistState: [{step, name, status}]  // NEW: checklist progress
 *   policyAlerts: [alert]                    // NEW: proactive alerts
 *   sendMessage: (text) => void
 *   runChecklist: () => void                 // NEW: sends run_checklist action
 *   runChecklistStep: (step) => void         // NEW: sends single step
 *   clearMessages: () => void
 * 
 * Event handling:
 *   "connected"         → set isConnected, store initial claim info
 *   "thinking"          → set isThinking = true
 *   "tool_call"         → add tool message to chat
 *   "tool_result"       → update tool message with result
 *   "response"          → add assistant message, set isThinking = false
 *   "checklist_update"  → update checklistState for the step    // NEW
 *   "policy_alert"      → add to policyAlerts, show notification // NEW
 *   "error"             → add error message
 */
```

### 12.5 Modified App.jsx

```jsx
// MODIFY FILE: claims-copilot/frontend/src/App.jsx

/**
 * Navigation:
 * 
 * const NAV = [
 *   { id: 'queue',     label: 'Claims Queue',    Icon: ... },  // NEW — landing page
 *   { id: 'copilot',   label: 'Copilot',         Icon: ... },  // NEW — chat
 *   { id: 'dashboard', label: 'Risk Dashboard',  Icon: ... },  // NEW
 *   { id: 'network',   label: 'Network',         Icon: ... },  // KEEP
 *   { id: 'dossier',   label: 'Dossier',         Icon: ... },  // KEEP
 *   { id: 'auto',      label: 'Auto Scan',       Icon: ... },  // existing autonomous
 *   { id: 'activity',  label: 'Activity',        Icon: ... },  // KEEP
 * ]
 * 
 * State:
 *   selectedCase: null | Case object
 *   view: 'queue' (default)
 * 
 * Flow:
 *   1. App loads → ClaimsQueue (default)
 *   2. Click a claim → setSelectedCase, setView('copilot')
 *   3. ChatPanel opens with checklist + quick actions
 *   4. Can switch to Network, Dashboard, Dossier while case is selected
 *   5. "Back to Queue" returns to queue view
 *   6. Dashboard always accessible regardless of selected case
 */
```

---

## PART 13: Data Flow on Startup

```python
# MODIFY FILE: claims-copilot/main.py

"""
Startup sequence — order matters.
"""

@dataclass
class DataContext:
    # EXISTING fields (provider fraud):
    claims_df: pd.DataFrame
    providers_df: pd.DataFrame
    members_df: pd.DataFrame
    facilities_df: pd.DataFrame
    provider_features_df: pd.DataFrame
    member_features_df: pd.DataFrame
    peer_stats_df: pd.DataFrame
    z_scores_df: pd.DataFrame
    anomaly_scores_df: pd.DataFrame
    graph: nx.DiGraph
    
    # NEW fields (supplemental health):
    supplemental_data: Dict = field(default_factory=dict)  # all generated entities
    supplemental_claims: List = field(default_factory=list)
    supplemental_graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    detected_patterns: List = field(default_factory=list)
    case_queue: List = field(default_factory=list)
    domain_config: Optional['DomainConfig'] = None

def initialize_data(force_regenerate: bool = False) -> DataContext:
    """
    Full startup sequence:
    
    1. Generate existing provider fraud data (unchanged)
    2. Generate supplemental health entities and claims (NEW)
    3. Run Rules Engine on all 500 claims → tag with rule triggers (NEW)
    4. Run Risk Scoring on all 500 claims → assign 0-100 scores (NEW)
    5. Run Document Analysis on all 500 claims → tag with DOC flags (NEW)
    6. Build Entity Graph → create network relationships (NEW)
    7. Run Pattern Detection on entity graph (NEW)
    8. Build unified Case Queue from both data sources (NEW)
    9. Cache everything
    """
    # ... existing provider fraud data generation ...
    
    # NEW: Supplemental health pipeline
    from data.generate_supplemental import generate_supplemental_data
    from intelligence.rules_engine import run_rules_engine
    from intelligence.risk_scoring import score_claim
    from intelligence.document_analysis import run_document_checks
    from intelligence.entity_graph import build_supplemental_health_graph, detect_patterns
    from case_queue import build_case_queue
    
    supplemental_data = generate_supplemental_data()
    
    # Run intelligence pipeline on each claim
    for claim in supplemental_data["claims"]:
        context = _build_claim_context(claim, supplemental_data)
        claim.rules_triggered = [r.rule_id for r in run_rules_engine(claim, context) if r.triggered]
        risk = score_claim(claim, context)
        claim.risk_score = risk.total_score
        claim.document_flags = [r.check_id for r in run_document_checks(claim.document_metadata) if not r.passed]
    
    supplemental_graph = build_supplemental_health_graph(supplemental_data)
    detected_patterns = detect_patterns(supplemental_graph)
    
    case_queue = build_case_queue(
        anomaly_scores_df=anomaly_scores_df,
        provider_features_df=provider_features_df,
        supplemental_claims=supplemental_data["claims"],
    )
    
    return DataContext(
        # ... existing ...
        supplemental_data=supplemental_data,
        supplemental_claims=supplemental_data["claims"],
        supplemental_graph=supplemental_graph,
        detected_patterns=detected_patterns,
        case_queue=case_queue,
    )
```

---

## PART 14: File Change Summary

### New Files:

| File | Purpose | Estimate |
|------|---------|----------|
| `domain_config.py` | Domain configuration model + Prudential config | ~100 lines |
| `cases.py` | Case/Claim data models, enums | ~80 lines |
| `data/generate_supplemental.py` | 500 claims + all entities + 10 fraud + 5 FP | ~500 lines |
| `intelligence/rules_engine.py` | 14 rules, deterministic evaluation | ~250 lines |
| `intelligence/risk_scoring.py` | Weighted heuristic scoring, 0-100 | ~200 lines |
| `intelligence/document_analysis.py` | 13 DOC checks on metadata | ~150 lines |
| `intelligence/entity_graph.py` | Entity graph + pattern detection | ~200 lines |
| `intelligence/checklist.py` | 7-step checklist framework | ~150 lines |
| `agents/tools_supplemental.py` | 16 tools (fraud + workflow + policy + universal) | ~500 lines |
| `agents/prompts_supplemental.py` | Examiner copilot system prompt | ~60 lines |
| `agents/copilot.py` | Chat agent with session management | ~120 lines |
| `case_queue.py` | Unified queue builder | ~120 lines |
| `frontend/src/components/ClaimsQueue.jsx` | Claims queue table | ~200 lines |
| `frontend/src/components/ChatPanel.jsx` | Chat + checklist UI | ~300 lines |
| `frontend/src/components/RiskDashboard.jsx` | Dashboard component | ~200 lines |
| `frontend/src/hooks/useCopilotChat.js` | Chat WebSocket hook | ~120 lines |

### Modified Files:

| File | Changes |
|------|---------|
| `main.py` | Add supplemental data to DataContext, run intelligence pipeline at startup |
| `api.py` | Add all new endpoints + chat WebSocket |
| `agents/tools_dossier.py` | Add supplemental health dossier template |
| `frontend/src/App.jsx` | New nav items, selectedCase state, view routing |
| `frontend/package.json` | Add `react-markdown` |

### Unchanged Files:

All existing provider fraud files remain untouched (same list as v2 schematic).

---

## PART 15: Build Order

```
Phase A — Data & Intelligence Foundation (no UI dependencies)
  1. domain_config.py              — Configuration model
  2. cases.py                      — Data models  
  3. data/generate_supplemental.py — 500 claims + all entities
  4. intelligence/rules_engine.py  — 14 rules
  5. intelligence/risk_scoring.py  — Weighted heuristic
  6. intelligence/document_analysis.py — 13 DOC checks
  7. intelligence/entity_graph.py  — Graph + pattern detection
  8. intelligence/checklist.py     — 7-step framework
  9. main.py modifications         — Wire everything, run pipeline at startup

Phase B — Copilot Agent & Tools (depends on Phase A)
  10. agents/tools_supplemental.py  — All 16 tools
  11. agents/prompts_supplemental.py — System prompt
  12. agents/copilot.py             — Chat agent + sessions
  13. agents/tools_dossier.py mods  — Supplemental health template
  14. case_queue.py                 — Unified queue builder

Phase C — API Layer (depends on Phase B)
  15. api.py modifications          — All new endpoints + chat WS

Phase D — Frontend (depends on Phase C)
  16. useCopilotChat.js            — Chat hook
  17. ClaimsQueue.jsx              — Queue component
  18. ChatPanel.jsx                — Chat + checklist component
  19. RiskDashboard.jsx            — Dashboard component
  20. App.jsx modifications        — Nav + routing

Phase E — Integration Testing
  21. Verify 500 claims generated with correct risk scores
  22. Verify 10 fraud scenarios flagged correctly
  23. Verify 5 false positives flag but have innocent explanations
  24. Test chat WS end-to-end (open claim → ask question → get answer)
  25. Test checklist run (all 7 steps)
  26. Test provider fraud path still works unchanged
  27. Test dashboard stats aggregate correctly
```

---

## PART 16: Demo Script (Reframed — Examiner Workflow First)

```
DEMO FLOW (7 minutes):

[0:00] THE MORNING VIEW
  Open app → Claims Queue visible. 500 claims.
  "This is the examiner's morning. 500 claims, scored and ranked.
   The examiner doesn't start in a fraud tool — they start here,
   where they'd start anyway."
  
  Point out: risk tiers, claim type tabs, PMR/CBR badges alongside 
  fraud flags. "Everything in one view."

[0:30] ROUTINE CLAIM — WORKFLOW VALUE
  Click a LOW-risk accident claim (risk score 22).
  "Let's start with a normal claim. No fraud here."
  
  Click "Check Eligibility" chip.
  "One check instead of three systems. Eligible, coverage confirmed."
  
  Click "Match to Policy" chip.
  "Accident details matched to policy terms. Coverage determination done."
  
  Click "State Rules" chip.
  "ET resolution handled. Florida policy, service in Georgia — 
   here's which rules apply and why."
  
  Note the PMR badge: "Also has an open PMR, 2 days old. 
  The examiner sees their workflow tasks without switching screens."
  
  "That claim took 2 minutes instead of 10. Now multiply by 20 claims a day."

[2:00] POLICY INTELLIGENCE
  Click a hospital indemnity claim for outpatient surgery.
  Copilot proactively surfaces: "Note: as of 9/18/25, surgical repair 
  benefits are paid regardless of hospital confinement."
  "The system knows about policy changes before the examiner does."

[2:30] THE FLAGGED CLAIM
  Back to queue. Click WC-247 (35 dependents, risk 94).
  "Now let's look at what the platform caught."
  
  Ask: "Why was this flagged?"
  Copilot: 35 dependents in 14 days, 47 claims this quarter, 
  all at exactly $100. Rules R-001, R-002, R-009 triggered.

[3:00] THE CHECKLIST
  Click "Run Full Checklist."
  Watch 7 steps execute. Step 4 (Family Claims) goes red.
  "The examiner's checklist, automated. Every step documented."

[3:45] DOCUMENT FRAUD
  Back to queue. Click AC-103 (tampered records, risk 76).
  Click "Document Analysis."
  "5 flags: mixed fonts, erasures, typed over handwritten, 
   Word doc format, submitted via email."
  "These are the exact red flags from the fraud detection checklist.
   Checked automatically on every claim."

[4:15] THE NETWORK
  Click "View Network" on the dependent ring case.
  Graph shows: 3 members → shared dependents → shared address.
  "It's not one bad actor. It's a ring. The examiner wouldn't 
   see this looking at claims one at a time."

[4:45] FALSE POSITIVE — WHAT AM I MISSING?
  Click the blended family case (flagged R-001, 6 dependents).
  Ask: "What am I missing? Could this be legitimate?"
  Copilot: "Marriage certificate on file dated 30 days ago. 
  6 dependents is consistent with blended family. Recommend 
  verifying dependent documentation rather than escalating."
  "The system doesn't just accuse. It challenges assumptions."

[5:15] ESCALATION
  Back to WC-247. Click "Escalate."
  Dossier generates: timeline, evidence, network diagram, 
  dollar exposure, rule triggers, recommended action.
  "SIU gets a complete package. No manual write-up."

[5:45] THE DASHBOARD
  Show Risk Dashboard.
  "8 claims intercepted. $12,400 held. 1 dependent ring.
   1 provider cluster. 3 past-TAT claims need attention.
   This is the morning briefing."

[6:15] DOMAIN AGNOSTIC
  Switch to provider fraud domain (existing prototype).
  "Same platform, different tools underneath. 
   Configure a new domain and it works for any line of business."

[6:45] CLOSE
  "This isn't a fraud detection system that examiners use sometimes.
   It's a workflow platform they use on every claim that happens 
   to catch fraud. That's why it gets adopted — it makes Tuesday 
   morning faster. And the next time someone adds 35 dependents,
   you find out before the client does."
```