# Claims Copilot v2 — Detailed Build Schematic

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                      │
│                                                                     │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ CaseQueue │  │  ChatPanel   │  │ DossierP │  │  NetworkGraph │  │
│  │ (NEW)     │  │  (NEW)       │  │ (MODIFY) │  │  (KEEP)       │  │
│  └─────┬────┘  └──────┬───────┘  └──────────┘  └───────────────┘  │
│        │               │                                            │
│        │  ┌────────────┴──────────────┐                             │
│        └──┤  useInvestigation.js      │  (MODIFY — add chat mode)  │
│           │  useCopilotChat.js (NEW)  │                             │
│           └────────────┬──────────────┘                             │
│                        │ WebSocket                                   │
└────────────────────────┼────────────────────────────────────────────┘
                         │
┌────────────────────────┼────────────────────────────────────────────┐
│                    API LAYER (FastAPI)                               │
│                                                                     │
│  EXISTING (KEEP):                    NEW:                           │
│  ├─ GET /api/health                  ├─ GET /api/cases              │
│  ├─ GET /api/graph-schema            ├─ POST /api/cases/{id}/start  │
│  ├─ GET /api/anomaly-summary         ├─ WS /ws/chat/{case_id}      │
│  ├─ GET /api/fraud-network           └─ GET /api/cases/{id}/status  │
│  └─ WS /ws/investigate                                              │
│                                                                     │
└────────────────────────┼────────────────────────────────────────────┘
                         │
┌────────────────────────┼────────────────────────────────────────────┐
│                   AGENT LAYER                                       │
│                                                                     │
│  EXISTING (KEEP):                    NEW:                           │
│  ├─ graph.py (autonomous loop)       ├─ copilot.py (chat agent)    │
│  ├─ nodes.py                         ├─ tools_disability.py        │
│  ├─ prompts.py                       └─ prompts_disability.py      │
│  ├─ tools_investigation.py                                          │
│  └─ tools_dossier.py                                                │
│                                                                     │
└────────────────────────┼────────────────────────────────────────────┘
                         │
┌────────────────────────┼────────────────────────────────────────────┐
│                    DATA LAYER                                       │
│                                                                     │
│  EXISTING (KEEP):                    NEW:                           │
│  ├─ generate_synthetic.py            ├─ generate_disability.py     │
│  ├─ features.py                      └─ disability_cache.pkl       │
│  ├─ anomaly.py                                                      │
│  ├─ graph.py                                                        │
│  └─ data_cache.pkl                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## PART 1: Case Queue & Multi-Investigation Types

### 1.1 Case Data Model

```python
# NEW FILE: claims-copilot/cases.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict
from datetime import datetime

class CaseType(str, Enum):
    PROVIDER_FRAUD   = "provider_fraud"
    DISABILITY_CLAIM = "disability_claim"
    # Future: LIFE_CLAIM = "life_claim"
    # Future: AGENT_FRAUD = "agent_fraud"

class CasePriority(str, Enum):
    HIGH   = "HIGH"
    MEDIUM = "MEDIUM"
    LOW    = "LOW"

class CaseStatus(str, Enum):
    NEW          = "new"
    IN_REVIEW    = "in_review"
    ESCALATED    = "escalated"
    DISMISSED    = "dismissed"
    CLOSED       = "closed"

@dataclass
class Case:
    case_id: str                       # e.g. "NET-6610", "DIS-2401"
    case_type: CaseType
    subject_id: str                    # provider_id or claimant_id
    subject_name: str                  # display name
    priority: CasePriority
    flag_reason: str                   # one-line reason for flagging
    status: CaseStatus = CaseStatus.NEW
    created_at: datetime = field(default_factory=datetime.now)
    summary: Optional[str] = None      # short description
    key_metrics: Dict = field(default_factory=dict)  # type-specific metrics
    investigation_history: List[Dict] = field(default_factory=list)
    dossier: Optional[str] = None       # final dossier markdown if generated
```

### 1.2 Case Queue Generator

```python
# NEW FILE: claims-copilot/case_queue.py

"""
Builds the case queue from both data sources:
  - Provider fraud cases from anomaly_scores_df (existing)
  - Disability cases from disability data (new)
"""

def build_case_queue(
    anomaly_scores_df: pd.DataFrame,
    provider_features_df: pd.DataFrame,
    disability_claims: List[Dict],
) -> List[Case]:
    """
    Returns sorted list of Case objects for the frontend queue.
    
    Provider fraud cases:
      - Filter anomaly_scores_df where anomaly_score > 0.6 AND entity_type == 'provider'
      - For each, create Case with:
        case_id = f"NET-{provider_id.split('-')[1]}"
        flag_reason = top anomaly feature description
        key_metrics = {anomaly_score, total_billed, top_z_score, specialty}
        priority = HIGH if anomaly_score > 0.75, MEDIUM if > 0.6
    
    Disability cases:
      - For each flagged disability claim, create Case with:
        case_id = f"DIS-{sequential}"
        flag_reason = from disability red flags
        key_metrics = {policy_age_months, claim_amount, red_flag_count, treating_providers}
        priority = based on red_flag_score
    
    Sort by: priority (HIGH first), then by key risk metric descending.
    """
    pass
```

### 1.3 API Endpoints for Case Queue

```python
# MODIFY FILE: claims-copilot/api.py — add these endpoints

# ---- NEW: Case Queue Endpoints ----

@app.get("/api/cases")
async def get_cases(
    case_type: Optional[str] = None,    # filter by type
    status: Optional[str] = None,       # filter by status
    priority: Optional[str] = None,     # filter by priority
):
    """
    Returns list of cases for the queue view.
    Response: {
        cases: [
            {
                case_id, case_type, subject_id, subject_name,
                priority, flag_reason, status, created_at,
                key_metrics: {...}
            }
        ],
        counts: {
            total, by_type: {provider_fraud: N, disability_claim: N},
            by_priority: {HIGH: N, MEDIUM: N, LOW: N}
        }
    }
    """
    pass

@app.post("/api/cases/{case_id}/status")
async def update_case_status(case_id: str, body: dict):
    """
    Update case status. Body: { status: "in_review"|"escalated"|"dismissed"|"closed" }
    Persists to in-memory store (or simple JSON file for demo).
    """
    pass

@app.get("/api/cases/{case_id}")
async def get_case_detail(case_id: str):
    """
    Returns full case details including investigation_history and dossier.
    This is what loads when analyst clicks a case in the queue.
    """
    pass
```

---

## PART 2: Disability Claims Data Generation

### 2.1 Synthetic Disability Data

```python
# NEW FILE: claims-copilot/data/generate_disability.py

"""
Generates 50 synthetic disability claims:
  - 45 legitimate claims
  - 5 suspicious claims with distinct fraud patterns
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random

# ---- Data Models ----

@dataclass
class DisabilityPolicy:
    policy_id: str               # "POL-XXXX"
    claimant_id: str             # "CLM-XXXX"
    claimant_name: str
    claimant_age: int
    occupation: str
    employer: str
    policy_purchase_date: datetime
    monthly_benefit: float       # e.g. $4,500/month
    elimination_period_days: int  # waiting period before benefits start (typically 90)
    benefit_period_months: int    # how long benefits last (24, 60, or to age 65)
    annual_premium: float

@dataclass
class DisabilityClaim:
    claim_id: str                # "DC-XXXX"
    policy: DisabilityPolicy
    claim_filed_date: datetime
    alleged_disability_date: datetime   # when claimant says disability started
    disability_type: str               # "musculoskeletal", "mental_health", "neurological", etc.
    icd_codes: List[str]               # diagnosis codes
    described_limitations: List[str]    # what claimant says they can't do
    treating_providers: List[Dict]      # [{provider_name, specialty, relationship_months}]
    medical_records: List[Dict]         # [{date, provider, summary, supports_disability: bool}]
    ime_results: Optional[Dict]        # independent medical exam (if ordered)
    surveillance_notes: Optional[List[Dict]]  # SIU surveillance (if ordered)
    employer_statement: Optional[Dict] # employer's description of job duties
    prior_claims: List[Dict]           # previous claims with this or other carriers
    social_media_flags: List[Dict]     # flagged social media posts
    financial_records: Optional[Dict]  # income changes, new business activity
    red_flags: List[str]               # computed red flags
    red_flag_score: float              # 0-1 composite risk score
    status: str                        # "pending", "approved", "denied", "under_investigation"

# ---- The 5 Suspicious Cases ----

SUSPICIOUS_PATTERNS = {
    "early_filer": {
        # Policy purchased 4 months ago, claim filed claiming back injury
        # Medical records thin — only one visit to treating physician
        # No prior imaging or conservative treatment documented
        "pattern_name": "Early Filing / Thin Documentation",
        "policy_age_months": 4,
        "treating_provider_count": 1,
        "medical_record_count": 2,
        "red_flags": [
            "Policy purchased less than 6 months before claim",
            "Single treating physician with brief relationship",
            "No conservative treatment history documented",
            "Claimed disability onset within elimination period",
        ],
    },
    "activity_inconsistent": {
        # Claims severe back injury preventing desk work
        # Social media shows recent hiking/skiing photos
        # Employer says claimant was already on performance improvement plan
        "pattern_name": "Activity Inconsistent with Claimed Limitations",
        "social_media_posts": [
            {"date": "2026-01-15", "platform": "Instagram", "content": "Summit trail completed! 8 miles 🏔"},
            {"date": "2026-02-02", "platform": "Facebook", "content": "Great day at the slopes with family"},
        ],
        "employer_notes": "Claimant was placed on PIP 2 weeks before disability claim filed",
        "red_flags": [
            "Social media activity inconsistent with claimed limitations",
            "Performance improvement plan preceded claim filing",
            "Claimed limitations (no sitting >30min) contradict documented activities",
        ],
    },
    "friendly_doctor": {
        # 3 other claimants with same treating physician all have open disability claims
        # Doctor's documentation is nearly identical across patients
        # Doctor's notes support maximum disability for routine conditions
        "pattern_name": "Enabling Provider / Templated Documentation",
        "shared_provider": "Dr. R. Martinez",
        "other_claimants_with_same_doc": 3,
        "note_similarity_score": 0.94,  # cosine similarity across patient notes
        "red_flags": [
            "Treating physician supports 3 other active disability claims",
            "Clinical notes 94% similar across different patients",
            "Documentation supports maximum disability for mild-moderate condition",
            "No referral to specialist despite 8+ month disability duration",
        ],
    },
    "serial_claimant": {
        # Claimant has filed 3 prior disability claims with 2 different carriers
        # Each claim lasted until benefit exhaustion then returned to work
        # Current claim uses different diagnosis but similar timeline
        "pattern_name": "Serial / Repeat Claimant",
        "prior_claims": [
            {"carrier": "MetLife", "year": 2019, "duration_months": 24, "diagnosis": "Depression", "outcome": "Benefits exhausted"},
            {"carrier": "Prudential", "year": 2021, "duration_months": 12, "diagnosis": "Anxiety", "outcome": "Returned to work at max benefit"},
            {"carrier": "Lincoln", "year": 2023, "duration_months": 18, "diagnosis": "Chronic fatigue", "outcome": "Benefits exhausted"},
        ],
        "red_flags": [
            "3 prior disability claims across 2 carriers in 7 years",
            "Each prior claim lasted until benefit period exhaustion",
            "Current diagnosis (fibromyalgia) is new but follows same pattern",
            "Returned to work within 30 days of each benefit exhaustion",
        ],
    },
    "financial_motive": {
        # Claimant's business recently failed (LLC dissolved 2 months ago)
        # Filed disability claim 3 weeks after business closure
        # High benefit amount ($8,200/month) relative to prior income
        # Medical documentation is legitimate but disability severity is questionable
        "pattern_name": "Financial Motive / Timing Suspicious",
        "business_closure_date": "2025-12-01",
        "claim_filed_date": "2025-12-22",
        "monthly_benefit": 8200,
        "red_flags": [
            "Business (LLC) dissolved 3 weeks before claim filed",
            "Monthly benefit exceeds most recent documented income",
            "Disability timing coincides with financial hardship",
            "IME physician rates functional capacity higher than treating physician",
        ],
    },
}

def generate_disability_data() -> List[DisabilityClaim]:
    """
    Returns list of 50 DisabilityClaim objects.
    
    Normal claims (45):
      - Realistic mix of musculoskeletal (40%), mental health (25%),
        neurological (15%), cardiovascular (10%), other (10%)
      - 2-4 treating providers each
      - 3-8 medical records each
      - 0-1 red flags (false positives happen)
      - red_flag_score: 0.0 - 0.3
    
    Suspicious claims (5):
      - One per SUSPICIOUS_PATTERNS above
      - 3-5 red flags each
      - red_flag_score: 0.6 - 0.95
      - Rich detail in medical_records, social_media_flags, financial_records
    """
    pass
```

### 2.2 Disability Data Integration into DataContext

```python
# MODIFY FILE: claims-copilot/main.py

# Add to DataContext:
@dataclass
class DataContext:
    # ... existing fields ...
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
    
    # NEW fields:
    disability_claims: List[DisabilityClaim] = field(default_factory=list)
    case_queue: List[Case] = field(default_factory=list)

# Modify initialize_data():
def initialize_data(force_regenerate: bool = False) -> DataContext:
    # ... existing data generation code ...
    
    # NEW: Generate disability data
    from data.generate_disability import generate_disability_data
    disability_claims = generate_disability_data()
    
    # NEW: Build case queue from both sources
    from case_queue import build_case_queue
    case_queue = build_case_queue(
        anomaly_scores_df=anomaly_scores_df,
        provider_features_df=provider_features_df,
        disability_claims=disability_claims,
    )
    
    ctx = DataContext(
        # ... existing ...
        disability_claims=disability_claims,
        case_queue=case_queue,
    )
    return ctx
```

---

## PART 3: Disability Investigation Tools

### 3.1 Disability-Specific Tools

```python
# NEW FILE: claims-copilot/agents/tools_disability.py

"""
Tools for disability claim investigation.
All tools access _context (DataContext) which holds disability_claims list.
"""

from langchain_core.tools import tool
from typing import Annotated, Dict, List

_context = None

def set_context(ctx):
    global _context
    _context = ctx

# ---- Tool 1: Get Claim Timeline ----

@tool
def get_claim_timeline(
    claim_id: Annotated[str, "The disability claim ID, e.g. DC-2401"]
) -> Dict:
    """
    Returns chronological timeline of key events for a disability claim.
    
    Output: {
        claim_id,
        claimant_name,
        timeline: [
            {date, event_type, description}
        ]
    }
    
    Event types and sources:
      - "policy_purchase":     from policy.policy_purchase_date
      - "alleged_onset":       from claim.alleged_disability_date
      - "medical_visit":       from each medical_records entry
      - "claim_filed":         from claim.claim_filed_date
      - "ime_ordered":         from claim.ime_results.date (if exists)
      - "surveillance":        from claim.surveillance_notes (if exists)
      - "social_media_flag":   from claim.social_media_flags (if exists)
      - "prior_claim":         from claim.prior_claims (if exists)
      - "business_event":      from claim.financial_records (if exists)
    
    Sorted chronologically. This is the primary tool for understanding
    the sequence of events — analysts always start here.
    """
    pass

# ---- Tool 2: Summarize Medical Records ----

@tool
def summarize_medical_records(
    claim_id: Annotated[str, "The disability claim ID"]
) -> Dict:
    """
    Returns analysis of medical documentation for the claim.
    
    Output: {
        claim_id,
        treating_providers: [{name, specialty, relationship_months, visit_count}],
        diagnosis_codes: [str],
        documentation_summary: str,  # plain-language summary of what records show
        consistency_flags: [str],    # any inconsistencies across records
        documentation_gaps: [str],   # missing expected documentation
        supports_claimed_disability: bool,
        confidence: str  # "strong", "moderate", "weak"
    }
    
    Logic:
      - Count medical records. <3 records for >90 day claim = "thin documentation" flag
      - Check if records from multiple providers or single source
      - Check if conservative treatment documented before disability claim
      - Check if IME agrees with treating physician
      - Flag if note_similarity_score > 0.85 across patients (if available)
    """
    pass

# ---- Tool 3: Check Claimant History ----

@tool
def check_claimant_history(
    claim_id: Annotated[str, "The disability claim ID"]
) -> Dict:
    """
    Returns claimant's history across carriers and prior claims.
    
    Output: {
        claim_id,
        claimant_name,
        prior_claims: [{carrier, year, diagnosis, duration_months, outcome}],
        pattern_flags: [str],      # e.g. "Serial claimant", "Benefit exhaustion pattern"
        total_prior_claims: int,
        total_prior_benefit_received: float,
        days_between_claims: int   # gap between last claim end and current
    }
    
    Logic:
      - If prior_claims >= 2: flag "Multiple prior disability claims"
      - If any prior claim ended at benefit exhaustion: flag "Benefit exhaustion pattern"
      - If returned to work within 30 days of benefit end: flag "Quick recovery after benefits end"
      - If different diagnosis each time: flag "Rotating diagnoses"
    """
    pass

# ---- Tool 4: Get Policy Details ----

@tool
def get_policy_details(
    claim_id: Annotated[str, "The disability claim ID"]
) -> Dict:
    """
    Returns policy information and calculates risk indicators.
    
    Output: {
        claim_id,
        policy_id,
        claimant_name,
        occupation,
        employer,
        policy_purchase_date,
        policy_age_months: int,
        monthly_benefit: float,
        annual_premium: float,
        benefit_to_premium_ratio: float,
        elimination_period_days: int,
        benefit_period_months: int,
        risk_flags: [str]
    }
    
    Logic:
      - If policy_age_months < 12: flag "Policy less than 1 year old at claim"
      - If policy_age_months < 6: flag "Policy less than 6 months old at claim"  
      - If monthly_benefit > 70% of estimated income: flag "High benefit relative to income"
      - Calculate benefit_to_premium_ratio: total potential payout / total premiums paid
    """
    pass

# ---- Tool 5: Flag Inconsistencies ----

@tool
def flag_inconsistencies(
    claim_id: Annotated[str, "The disability claim ID"]
) -> Dict:
    """
    Cross-references all available data to find contradictions.
    
    Output: {
        claim_id,
        inconsistencies: [
            {
                type: str,      # "activity_vs_limitation", "financial_motive",
                                # "documentation_vs_ime", "employer_context"
                severity: str,  # "high", "medium", "low"
                description: str,
                evidence: str   # specific data point
            }
        ],
        overall_concern_level: str,  # "high", "moderate", "low"
        innocent_explanations: [str] # possible legitimate reasons
    }
    
    Checks performed:
      1. Social media activity vs claimed limitations
      2. IME findings vs treating physician opinion
      3. Employer context (PIP, termination, layoff) vs claim timing
      4. Financial events (business closure, bankruptcy) vs claim timing
      5. Medical documentation quality vs disability duration
      6. Job physical demands vs claimed disability type
    
    The innocent_explanations field is critical — this is the
    "what am I missing?" feature. For each inconsistency found,
    generate at least one plausible innocent explanation.
    """
    pass

# ---- Tool 6: Find Related Claims (Provider Pattern) ----

@tool
def find_related_claims(
    claim_id: Annotated[str, "The disability claim ID"]
) -> Dict:
    """
    Checks if the treating provider(s) appear in other suspicious claims.
    
    Output: {
        claim_id,
        treating_providers: [
            {
                provider_name,
                total_disability_claims_supported: int,
                other_active_claims: [{claim_id, claimant_name, diagnosis, status}],
                note_similarity_score: float,  # if available
                flags: [str]
            }
        ],
        pattern_detected: bool,
        pattern_description: str
    }
    
    This is the disability equivalent of "ring detection" — finding
    a doctor who's supporting multiple questionable disability claims.
    """
    pass

# ---- Collect all tools ----

DISABILITY_TOOLS = [
    get_claim_timeline,
    summarize_medical_records,
    check_claimant_history,
    get_policy_details,
    flag_inconsistencies,
    find_related_claims,
]
```

### 3.2 Disability-Specific Prompts

```python
# NEW FILE: claims-copilot/agents/prompts_disability.py

DISABILITY_COPILOT_PROMPT = """You are a Disability Claims Investigation Copilot 
assisting an experienced SIU analyst.

Your role:
- Answer the analyst's questions about disability claims using available tools
- Present findings clearly with specific data points
- When asked, play devil's advocate and suggest innocent explanations
- Never make a determination — present evidence, let the analyst decide

Investigation context:
- Disability fraud involves claimants misrepresenting their inability to work
- Key factors: timing of claim vs policy purchase, medical documentation quality,
  activity inconsistencies, provider patterns, financial motive, prior claim history
- Not every red flag is fraud — people do get legitimately disabled

Available tools:
- get_claim_timeline: Start here. Shows chronological sequence of events.
- summarize_medical_records: What the medical documentation actually says.
- check_claimant_history: Prior claims across carriers.
- get_policy_details: Policy age, benefit amounts, risk indicators.
- flag_inconsistencies: Cross-reference all data for contradictions.
- find_related_claims: Check if treating provider has pattern of supporting suspicious claims.

Response style:
- Lead with the most important finding
- Use specific numbers and dates, not vague language
- When presenting red flags, always note severity
- If the analyst asks "what am I missing?" — genuinely try to find innocent explanations
- Keep responses focused — don't dump everything at once
"""
```

---

## PART 4: Conversational Copilot Agent (Chat Mode)

### 4.1 Chat Agent Architecture

```python
# NEW FILE: claims-copilot/agents/copilot.py

"""
Conversational copilot agent. Replaces the autonomous loop for
analyst-driven investigation. Uses same LLM, different interaction:
  - Analyst sends message
  - Agent picks tools based on the question
  - Agent responds with findings
  - Analyst asks follow-up
  - Repeat until analyst is done

State persists across the conversation — the agent remembers
what it already looked up.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

@dataclass
class CopilotSession:
    """Holds state for one analyst chat session."""
    session_id: str
    case_id: str
    case_type: str              # "provider_fraud" | "disability_claim"
    messages: List = field(default_factory=list)  # full message history
    tools_called: List[str] = field(default_factory=list)  # audit log
    findings_cache: Dict = field(default_factory=dict)  # tool results cache
    created_at: str = ""

# Global session store (in-memory for demo; production would use Redis/DB)
_sessions: Dict[str, CopilotSession] = {}

def get_or_create_session(case_id: str, case_type: str) -> CopilotSession:
    """Get existing session or create new one for a case."""
    if case_id not in _sessions:
        session = CopilotSession(
            session_id=f"sess-{case_id}",
            case_id=case_id,
            case_type=case_type,
        )
        # Set system prompt based on case type
        if case_type == "provider_fraud":
            from agents.prompts import INVESTIGATION_PROMPT
            system_msg = SystemMessage(content=INVESTIGATION_PROMPT)
        elif case_type == "disability_claim":
            from agents.prompts_disability import DISABILITY_COPILOT_PROMPT
            system_msg = SystemMessage(content=DISABILITY_COPILOT_PROMPT)
        
        session.messages = [system_msg]
        _sessions[case_id] = session
    return _sessions[case_id]

def get_tools_for_case_type(case_type: str) -> list:
    """Returns the tool list appropriate for the case type."""
    if case_type == "provider_fraud":
        from agents.tools_investigation import (
            scan_new_claims, profile_entity, compare_to_peers,
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
        # Note: scan_new_claims excluded — that's for the batch hotlist, not chat
    
    elif case_type == "disability_claim":
        from agents.tools_disability import DISABILITY_TOOLS
        from agents.tools_dossier import compile_dossier  # shared
        return DISABILITY_TOOLS + [compile_dossier]

async def handle_analyst_message(
    case_id: str,
    case_type: str,
    analyst_message: str,
    ws = None  # WebSocket for streaming tool calls
) -> str:
    """
    Process one analyst message and return the agent's response.
    
    Flow:
    1. Get or create session
    2. Append analyst message to history
    3. Invoke react agent with full message history + tools
    4. Stream tool calls to WebSocket (if connected)
    5. Append agent response to history
    6. Return agent response text
    
    The message history gives the agent memory of the full conversation.
    """
    session = get_or_create_session(case_id, case_type)
    tools = get_tools_for_case_type(case_type)
    
    # Add analyst message
    session.messages.append(HumanMessage(content=analyst_message))
    
    # Build react agent (stateless — state is in the message history)
    from agents.nodes import get_bedrock_llm
    llm = get_bedrock_llm(temperature=0.1, max_tokens=4096, agent_name="copilot")
    agent = create_react_agent(llm, tools)
    
    # Invoke with full message history
    result = agent.invoke({"messages": session.messages})
    
    # Extract final response (last non-tool-call message)
    response_msg = None
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            response_msg = msg
            break
    
    response_text = response_msg.content if response_msg else "I couldn't generate a response."
    
    # Append to session history
    session.messages.append(AIMessage(content=response_text))
    
    # Log tool usage
    for msg in result["messages"]:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                session.tools_called.append(tc["name"])
    
    return response_text
```

### 4.2 Chat WebSocket Endpoint

```python
# MODIFY FILE: claims-copilot/api.py — add chat WebSocket

@app.websocket("/ws/chat/{case_id}")
async def chat_websocket(websocket: WebSocket, case_id: str):
    """
    Persistent WebSocket for analyst conversation with copilot.
    
    Incoming messages:
      { "action": "message", "text": "Tell me about this claim" }
      { "action": "end_session" }
    
    Outgoing events:
      { "type": "thinking",     "timestamp": "..." }                     # agent is processing
      { "type": "tool_call",    "tool": "get_claim_timeline", "args": {...}, "timestamp": "..." }
      { "type": "tool_result",  "tool": "get_claim_timeline", "summary": "...", "timestamp": "..." }
      { "type": "response",     "text": "Based on the timeline...", "timestamp": "..." }
      { "type": "error",        "message": "...", "timestamp": "..." }
    """
    await websocket.accept()
    
    # Determine case type from case_queue
    case = next((c for c in _data_context.case_queue if c.case_id == case_id), None)
    if not case:
        await websocket.send_json({"type": "error", "message": f"Case {case_id} not found"})
        await websocket.close()
        return
    
    await websocket.send_json({"type": "connected", "case_id": case_id, "case_type": case.case_type})
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("action") == "end_session":
                break
            
            if data.get("action") == "message":
                analyst_text = data["text"]
                
                # Send "thinking" indicator
                await websocket.send_json({"type": "thinking"})
                
                # Process message (runs in thread to not block)
                response = await asyncio.to_thread(
                    handle_analyst_message_sync,
                    case_id=case_id,
                    case_type=case.case_type,
                    analyst_message=analyst_text,
                )
                
                await websocket.send_json({
                    "type": "response",
                    "text": response,
                    "timestamp": datetime.now().isoformat()
                })
    except WebSocketDisconnect:
        pass
```

---

## PART 5: Frontend Changes

### 5.1 New Component: CaseQueue

```jsx
// NEW FILE: claims-copilot/frontend/src/components/CaseQueue.jsx

/**
 * Case queue table that shows all pending investigations.
 * This is the landing screen — replaces the current "start investigation" button.
 * 
 * Props:
 *   onSelectCase: (case) => void  — callback when analyst clicks a row
 * 
 * State:
 *   cases: []         — fetched from GET /api/cases
 *   filters: {}       — active type/priority/status filters
 *   loading: bool
 * 
 * Layout:
 *   ┌──────────────────────────────────────────────────────────────────┐
 *   │ INVESTIGATION QUEUE                          [Filter] [Refresh] │
 *   ├──────────┬──────────────┬────────────┬─────────────┬───────────┤
 *   │ Case ID  │ Type         │ Subject    │ Flag Reason │ Priority  │
 *   ├──────────┼──────────────┼────────────┼─────────────┼───────────┤
 *   │ DIS-2401 │ Disability   │ J. Smith   │ Early claim │ ● HIGH    │
 *   │ DIS-2402 │ Disability   │ R. Chen    │ Single MD   │ ● MEDIUM  │
 *   │ NET-6610 │ Provider Net │ P-6610     │ 3.36σ bill  │ ● HIGH    │
 *   │ DIS-2403 │ Disability   │ T. Patel   │ Serial clm  │ ● HIGH    │
 *   │ NET-6640 │ Provider Net │ P-6640     │ 2.8σ bill   │ ● MEDIUM  │
 *   └──────────┴──────────────┴────────────┴─────────────┴───────────┘
 *   
 *   Tabs at top: [All (12)] [Disability (5)] [Provider Fraud (7)]
 *   
 *   Priority indicator: ● colored dot (red=HIGH, amber=MEDIUM, gray=LOW)
 *   
 *   Row click → onSelectCase(case) → parent navigates to investigation view
 * 
 * Fetch on mount: GET /api/cases → setCases(response.cases)
 */
```

### 5.2 New Component: ChatPanel

```jsx
// NEW FILE: claims-copilot/frontend/src/components/ChatPanel.jsx

/**
 * Conversational chat interface for analyst-driven investigation.
 * Connects via WebSocket to /ws/chat/{caseId}.
 * 
 * Props:
 *   caseId: string
 *   caseType: string
 *   caseSummary: object   — initial case info to display
 * 
 * State:
 *   messages: [
 *     { role: "system",    text: "Connected to case DIS-2401..." },
 *     { role: "analyst",   text: "Tell me about this claim" },
 *     { role: "assistant", text: "This is a disability claim filed by..." },
 *     { role: "tool",      tool: "get_claim_timeline", summary: "..." },
 *   ]
 *   isThinking: bool       — true while agent is processing
 *   ws: WebSocket          — persistent connection
 *   inputText: string      — current input field value
 * 
 * Layout:
 *   ┌──────────────────────────────────────────┐
 *   │ CASE DIS-2401 — J. Smith                 │  ← case header
 *   │ Disability Claim | Priority: HIGH         │
 *   ├──────────────────────────────────────────┤
 *   │                                          │
 *   │  ┌─ Assistant ─────────────────────────┐ │
 *   │  │ This is a disability claim filed by  │ │
 *   │  │ John Smith for back injury...        │ │
 *   │  └─────────────────────────────────────┘ │
 *   │                                          │
 *   │  ┌─ You ──────────────────────────────┐  │
 *   │  │ Show me the timeline               │  │
 *   │  └─────────────────────────────────────┘ │
 *   │                                          │
 *   │  ┌─ Tool: get_claim_timeline ──────────┐ │  ← collapsible
 *   │  │ [tool execution details]            │  │
 *   │  └─────────────────────────────────────┘ │
 *   │                                          │
 *   │  ┌─ Assistant ─────────────────────────┐ │
 *   │  │ Here's the timeline for this claim: │  │
 *   │  │ • 2025-08-15: Policy purchased      │  │
 *   │  │ • 2025-12-01: Alleged disability... │  │
 *   │  └─────────────────────────────────────┘ │
 *   │                                          │
 *   │  ● Agent is thinking...                  │  ← typing indicator
 *   │                                          │
 *   ├──────────────────────────────────────────┤
 *   │ [Type your question...          ] [Send] │  ← input bar
 *   ├──────────────────────────────────────────┤
 *   │ Quick actions:                           │  ← suggestion chips
 *   │ [Timeline] [Medical Records] [History]   │
 *   │ [Policy Details] [Red Flags] [Related]   │
 *   └──────────────────────────────────────────┘
 * 
 * Quick action chips:
 *   - Map to pre-written prompts:
 *     "Timeline"        → "Show me the chronological timeline for this claim"
 *     "Medical Records" → "Summarize the medical documentation"
 *     "History"         → "Check this claimant's prior claim history"
 *     "Policy Details"  → "What are the policy details and risk indicators?"
 *     "Red Flags"       → "What inconsistencies do you see in this claim?"
 *     "Related Claims"  → "Are there other claims with the same treating provider?"
 *   - For provider fraud cases, different chips:
 *     "Profile"         → "Tell me about this provider"
 *     "Peer Comparison" → "How does this provider compare to peers?"
 *     "Claims"          → "Show me the actual claims"
 *     "Network"         → "Who is this provider connected to?"
 *     "Referrals"       → "Show me the referral history"
 *     "Ring Detection"  → "Are there any fraud rings involving this provider?"
 * 
 * WebSocket connection:
 *   - Connect on mount: new WebSocket(`ws://localhost:8000/ws/chat/${caseId}`)
 *   - On "thinking" event: setIsThinking(true)
 *   - On "tool_call" event: add tool message to chat
 *   - On "response" event: add assistant message, setIsThinking(false)
 *   - Disconnect on unmount
 * 
 * Auto-scroll: scrollToBottom on new message
 * 
 * Markdown rendering: agent responses rendered as markdown (use react-markdown)
 */
```

### 5.3 New Hook: useCopilotChat

```javascript
// NEW FILE: claims-copilot/frontend/src/hooks/useCopilotChat.js

/**
 * Custom hook for managing copilot chat WebSocket connection.
 * 
 * Usage:
 *   const { messages, isThinking, sendMessage, isConnected } = useCopilotChat(caseId)
 * 
 * Returns:
 *   messages: [{ role, text, timestamp, tool?, toolArgs? }]
 *   isThinking: bool
 *   isConnected: bool
 *   sendMessage: (text: string) => void
 *   clearMessages: () => void
 * 
 * Internal:
 *   - Manages WebSocket lifecycle (connect/disconnect)
 *   - Parses incoming events into message objects
 *   - Handles reconnection on disconnect
 *   - Truncates message display if conversation gets very long (keep last 100)
 */

export function useCopilotChat(caseId) {
    // WebSocket URL: `ws://${window.location.hostname}:8000/ws/chat/${caseId}`
    // 
    // Event handling:
    //   "connected"    → set isConnected = true, add system message
    //   "thinking"     → set isThinking = true
    //   "tool_call"    → add tool message { role: "tool", tool: name, toolArgs: args }
    //   "tool_result"  → update last tool message with result summary
    //   "response"     → add assistant message, set isThinking = false
    //   "error"        → add error message, set isThinking = false
    // 
    // sendMessage(text):
    //   1. Add { role: "analyst", text } to messages
    //   2. ws.send(JSON.stringify({ action: "message", text }))
}
```

### 5.4 Modified App.jsx — Navigation & Layout Changes

```jsx
// MODIFY FILE: claims-copilot/frontend/src/App.jsx

/**
 * New navigation structure:
 * 
 * const NAV = [
 *   { id: 'queue',     label: 'Case Queue',    Icon: IconGrid    },  // NEW — landing page
 *   { id: 'copilot',   label: 'Copilot',       Icon: IconChat    },  // NEW — chat investigation
 *   { id: 'auto',      label: 'Auto Scan',     Icon: IconScan    },  // RENAMED from 'overview'
 *   { id: 'dossier',   label: 'Dossier',       Icon: IconFile    },  // KEEP
 *   { id: 'network',   label: 'Fraud Network', Icon: IconHub     },  // KEEP
 *   { id: 'activity',  label: 'Activity',      Icon: IconActivity},  // KEEP
 * ]
 * 
 * New state:
 *   const [selectedCase, setSelectedCase] = useState(null)   // currently selected case
 *   const [view, setView] = useState('queue')                 // current view
 * 
 * View routing:
 *   'queue'   → <CaseQueue onSelectCase={handleSelectCase} />
 *   'copilot' → <ChatPanel caseId={selectedCase.case_id} caseType={selectedCase.case_type} />
 *   'auto'    → existing autonomous investigation view (GraphView + EventTimeline)
 *   'dossier' → <DossierPanel /> (works for both auto and copilot outputs)
 *   'network' → <NetworkGraph />
 *   'activity'→ <EventTimeline />
 * 
 * Flow:
 *   1. App loads → shows CaseQueue (default view)
 *   2. Analyst clicks a case → setSelectedCase(case), setView('copilot')
 *   3. ChatPanel opens, WebSocket connects, analyst starts investigating
 *   4. Analyst can switch to Network view (same data context)
 *   5. Analyst can trigger "Auto Scan" from copilot ("run the full autonomous investigation")
 *   6. Analyst can click "Compile Dossier" from copilot when ready
 */
```

---

## PART 6: Integration & Wiring

### 6.1 Context Setting for Disability Tools

```python
# MODIFY FILE: claims-copilot/api.py — context initialization

# In startup / data init:
from agents.tools_disability import set_context as set_disability_context

# After initialize_data():
set_disability_context(data_context)

# Also need to set context when handling chat:
# In chat_websocket handler, before processing messages,
# ensure the correct context is set based on case_type
```

### 6.2 Autonomous Loop Integration

```python
# The existing /ws/investigate endpoint stays as-is.
# 
# When an analyst clicks "Run Auto Scan" from the copilot chat,
# the frontend:
#   1. Sends { action: "run_auto" } to the chat WebSocket
#   2. Backend spawns the existing investigation graph
#   3. Streams events back through the same WebSocket
#   4. When complete, the dossier is available in the chat context
#
# The copilot agent can then reference the auto-generated dossier
# in conversation: "The auto scan found X. Do you want me to dig deeper into Y?"
```

### 6.3 Shared Dossier Compilation

```python
# The compile_dossier tool from tools_dossier.py works for both case types.
# For disability claims, the case_data dict will have different fields:
#
# Provider fraud case_data:
#   { subject: "P-6610", scheme: "upcoding_ring", evidence: [...],
#     billing_rules: [...], similar_cases: [...], recovery: {...} }
#
# Disability case_data:
#   { subject: "CLM-2401", scheme: "activity_inconsistent", evidence: [...],
#     timeline: [...], medical_summary: {...}, inconsistencies: [...],
#     prior_claims: [...], recommendation: "..." }
#
# The compile_dossier tool should detect case type from the data shape
# and use appropriate markdown template.
#
# MODIFY: tools_dossier.py compile_dossier to handle both templates.
```

---

## PART 7: File Change Summary

### New Files to Create:

| File | Purpose | Size Estimate |
|------|---------|---------------|
| `claims-copilot/cases.py` | Case data model (Case, CaseType, CaseStatus) | ~60 lines |
| `claims-copilot/case_queue.py` | Build case queue from both data sources | ~120 lines |
| `claims-copilot/data/generate_disability.py` | Synthetic disability claims (50 claims, 5 suspicious) | ~350 lines |
| `claims-copilot/agents/tools_disability.py` | 6 disability investigation tools | ~300 lines |
| `claims-copilot/agents/prompts_disability.py` | Disability copilot system prompt | ~40 lines |
| `claims-copilot/agents/copilot.py` | Chat agent with session management | ~120 lines |
| `frontend/src/components/CaseQueue.jsx` | Case queue table component | ~180 lines |
| `frontend/src/components/ChatPanel.jsx` | Chat interface component | ~250 lines |
| `frontend/src/hooks/useCopilotChat.js` | Chat WebSocket hook | ~100 lines |

### Files to Modify:

| File | Changes |
|------|---------|
| `claims-copilot/main.py` | Add disability_claims and case_queue to DataContext; generate both on init |
| `claims-copilot/api.py` | Add `/api/cases` endpoints + `/ws/chat/{case_id}` WebSocket |
| `claims-copilot/agents/tools_dossier.py` | Update `compile_dossier` to handle disability case template |
| `frontend/src/App.jsx` | Add queue/copilot views to nav, add selectedCase state, route views |
| `frontend/package.json` | Add `react-markdown` dependency for chat message rendering |

### Files Unchanged:

| File | Reason |
|------|--------|
| `agents/graph.py` | Autonomous loop stays as-is |
| `agents/nodes.py` | Autonomous node logic unchanged |
| `agents/prompts.py` | Provider fraud prompts unchanged |
| `agents/tools_investigation.py` | Provider fraud tools unchanged |
| `data/generate_synthetic.py` | Provider fraud data gen unchanged |
| `data/features.py` | Feature computation unchanged |
| `data/anomaly.py` | Anomaly detection unchanged |
| `data/graph.py` | Graph construction unchanged |
| `billing_rules/*` | Rules index unchanged |
| `demo_runner.py` | Demo mode unchanged (optional: add disability demo sequence) |
| `frontend/src/components/NetworkGraph.jsx` | Network visualization unchanged |
| `frontend/src/components/GraphView.jsx` | Auto-investigation view unchanged |
| `frontend/src/components/EventTimeline.jsx` | Event timeline unchanged |
| `frontend/src/components/StatsBar.jsx` | Stats display unchanged |
| `frontend/src/hooks/useInvestigation.js` | Auto-investigation hook unchanged |

---

## PART 8: Build Order (Implementation Sequence)

```
Phase A — Data & Models (do first, no UI dependencies)
  1. cases.py                        — Case data model
  2. data/generate_disability.py     — Synthetic disability data
  3. case_queue.py                   — Queue builder
  4. main.py modifications           — Wire into DataContext

Phase B — Backend Agent & Tools (depends on Phase A)
  5. agents/tools_disability.py      — 6 disability tools
  6. agents/prompts_disability.py    — System prompt
  7. agents/copilot.py               — Chat agent + session mgmt
  8. agents/tools_dossier.py mods    — Dual-template compile

Phase C — API Layer (depends on Phase B)
  9. api.py modifications            — Case endpoints + chat WebSocket

Phase D — Frontend (depends on Phase C)
  10. useCopilotChat.js              — Chat hook
  11. CaseQueue.jsx                  — Queue component
  12. ChatPanel.jsx                  — Chat component
  13. App.jsx modifications          — Nav + routing + state

Phase E — Integration Testing
  14. Test disability data generation
  15. Test chat WebSocket end-to-end
  16. Test case queue → chat → tool call → response flow
  17. Test auto investigation still works unchanged
  18. Test compile_dossier with both case types
```

---

## PART 9: Demo Script (What to Show)

```
DEMO FLOW (5 minutes):

1. [0:00] Open app → Case Queue visible
   "This is the analyst's morning view. Flagged cases 
    from overnight batch analysis — both provider fraud 
    and disability claims."

2. [0:30] Click DIS-2401 (Early Filer, HIGH priority)
   Chat opens. Quick action chips visible.
   "The analyst picks a disability case to investigate."

3. [0:45] Click "Timeline" chip
   Agent calls get_claim_timeline, responds with chronological events.
   "Policy purchased August 2025, disability claimed December 2025 — 
    four months later. That's a red flag."

4. [1:15] Type: "What do the medical records show?"
   Agent calls summarize_medical_records.
   "Only two medical visits documented. Single treating physician 
    with a 3-month relationship. No imaging, no conservative treatment."

5. [1:45] Type: "Has this person filed claims before?"
   Agent calls check_claimant_history.
   "No prior claims — this is their first. That's actually in their favor."

6. [2:15] Type: "What am I missing? Could this be legitimate?"
   Agent calls flag_inconsistencies with innocent_explanations.
   "Here's where AI adds real value — it challenges the analyst's 
    assumptions before they escalate."

7. [3:00] Click "Back to Queue" → Click NET-6610 (Provider Network, HIGH)
   "Same tool, different investigation type. Now it's provider fraud."
   
8. [3:15] Click "Profile" chip
   Agent calls profile_entity — shows billing anomalies.
   "Same conversational interface, different tools underneath.
    The analyst's workflow doesn't change."

9. [3:45] Type: "Run the full autonomous scan on this provider"
   Triggers existing autonomous investigation loop.
   Events stream in the Activity tab. Dossier generates.
   "When the analyst wants to see the AI's full analysis, 
    they can trigger it on demand. AI proposes, human disposes."

10. [4:30] Show final dossier in Dossier tab.
    "The autonomous scan produced this dossier. But the analyst 
     got here through conversation — they understand the evidence 
     because they drove the investigation."
```
