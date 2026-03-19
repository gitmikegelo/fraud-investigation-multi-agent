## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                           │
│  Claims Queue | Copilot | Risk Dashboard | Network | Dossier    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                      API LAYER (FastAPI)                          │
└──────────────────────────┼──────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                  INTELLIGENCE LAYER                               │
│                                                                  │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Rules Engine   │  │ Risk Scoring │  │ Network Analysis     │  │
│  │ (Layer 1)      │  │ (Layer 2)    │  │ (Layer 3)            │  │
│  └───────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│          │                 │                      │              │
│  ┌───────▼─────────────────▼──────────────────────▼───────────┐  │
│  │                  Composite Risk Score + Route               │  │
│  └────────────────────────┬───────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────────────────▼───────────────────────────────────┐  │
│  │              COPILOT AGENT (LangGraph)                      │  │
│  │  ┌──────────────┐ ┌───────────────┐ ┌───────────────────┐  │  │
│  │  │ Fraud Tools   │ │ Workflow Tools│ │ Policy Intel Tools│  │  │
│  │  │ (doc analysis │ │ (PMR, CBR,   │ │ (state rules, ET, │  │  │
│  │  │  tampering,   │ │  TAT, escal) │ │  benefit changes) │  │  │
│  │  │  patterns)    │ │              │ │                   │  │  │
│  │  └──────────────┘ └───────────────┘ └───────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              DOCUMENT ANALYSIS ENGINE                       │  │
│  │  Medical record tampering detection (from checklist)        │  │
│  │  Metadata analysis, font consistency, format validation     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────┼──────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                      DATA LAYER                                  │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────┐ ┌────────────┐  │
│  │ Domain Config │ │ Synthetic    │ │ Entity   │ │ Policy     │  │
│  │ (rules, tools │ │ Claims +     │ │ Graph    │ │ Rules DB   │  │
│  │  per LOB)     │ │ Documents    │ │(NetworkX)│ │ (state/ET/ │  │
│  │               │ │              │ │          │ │  changes)  │  │
│  └──────────────┘ └──────────────┘ └──────────┘ └────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Domain Configuration (Agnostic Core)

### 1.1 Configuration Model

Each line of business registers a configuration that the platform reads at startup. No LOB-specific logic is hardcoded.

```
Domain Configuration:
  ├─ domain_id
  ├─ domain_label (e.g., "Supplemental Health")
  ├─ claim_types []
  ├─ entity_types []
  ├─ fraud_rules []
  ├─ risk_features []
  ├─ relationship_types [] (for network graph)
  ├─ document_checks [] (what to look for in attached docs)
  ├─ workflow_tasks [] (PMR, CBR, etc.)
  ├─ policy_alerts [] (active policy changes to apply)
  ├─ tools []
  ├─ checklist_steps []
  ├─ copilot_prompts {}
  └─ dossier_template
```

### 1.2 Prudential Supplemental Health Config

```
domain_id: "prudential_supplemental_health"
domain_label: "Supplemental Health"

claim_types:
  - wellness
  - accident
  - hospital_indemnity
  - critical_illness

entity_types:
  - member
  - dependent
  - provider
  - facility
  - employer
  - policy

workflow_tasks:
  - PMR (Payment Method Review)
  - CBR (Callback Request)
  - TAT Escalation

policy_alerts:
  - { id: "PA-001", 
      effective: "2025-09-18",
      description: "Surgical repair benefits now paid regardless 
                    of confinement. Outpatient surgery now covered.",
      applies_to: ["hospital_indemnity"],
      previous_rule: "Surgical repair only when confined to hospital",
      new_rule: "Surgical repair paid for hospital or outpatient" }

document_checks:
  (see Part 3 below — full medical record fraud checklist)
```

### 1.3 What Stays from Current Prototype

| Component | Status | Notes |
|-----------|--------|-------|
| Case Queue UI | KEEP, MODIFY | Rename to Claims Queue, add risk score + workflow task columns |
| Chat Copilot UI | KEEP, MODIFY | Add checklist progress bar, document analysis panel |
| Chat WebSocket | KEEP | No changes |
| Network Graph UI | KEEP, MODIFY | New entity types (member/dependent/provider/address) |
| Dossier Panel | KEEP, MODIFY | New templates per domain |
| LangGraph Agent | KEEP, MODIFY | Domain-aware tool selection |
| Autonomous Loop | KEEP | Available as "deep scan" |
| useCopilotChat hook | KEEP | No changes |

---

## Part 2: Intelligence Pipeline (Three Layers)

### 2.1 Layer 1 — Rules Engine

Deterministic rules, fast, explainable, run on every claim before auto-adjudication.

**Rule Format (Domain-Agnostic):**

```
Rule:
  id: string
  name: string
  description: string
  domain: string (or "universal")
  condition: structured expression
  lookback_window: duration
  aggregation: optional
  severity: BLOCK | FLAG | INFO
  explanation_template: string with placeholders
```

**Prudential Supplemental Health Rules:**

| Rule ID | Name | Condition | Severity | Catches |
|---------|------|-----------|----------|---------|
| R-001 | Dependent spike | Dependents added > 5 in 30 days | BLOCK | 35-dependent case |
| R-002 | Claim velocity | Claims > 10 per member per quarter | FLAG | Volume abuse |
| R-003 | Early filing | Claim filed < 90 days after policy start | FLAG | Quick-hit fraud |
| R-004 | Termination rush | Claim spike within 60 days of coverage end | FLAG | Exit fraud |
| R-005 | Provider cluster | Same provider + same diagnosis + 5 patients in 30 days | FLAG | Provider mill |
| R-006 | Policy manipulation | Owner/beneficiary change < 180 days before claim | FLAG | Policy gaming |
| R-007 | Dependent age gap | Member-dependent age gap > 25 AND dependent > 25 | FLAG | Fake dependents |
| R-008 | Duplicate submission | Same member, same date of service, same amount | BLOCK | Double billing |
| R-009 | Benefit max gaming | Claim amount = exact benefit maximum (>3 consecutive) | INFO | Systematic gaming |
| R-010 | Resubmission | Previously denied claim resubmitted with minor changes | FLAG | Denial circumvention |
| R-011 | CBR frequency | Member contacted 3+ times in 15 days | INFO | From OneNote CBR rules |
| R-012 | PMR no follow-up | Previous PMR on claim with no notes beyond 5-day TAT | FLAG | From OneNote PMR rules |
| R-013 | Medical record email | Records received via email (not portal/fax) | INFO | From OneNote fraud list |
| R-014 | Policy change impact | Claim type matches recent policy change | INFO | Surgical repair change exploitation |

### 2.2 Layer 2 — Risk Scoring

Score every claim 0-100. Start with weighted heuristic. Upgrade to ML when labeled data exists.

**Feature Categories:**

| Category | Features |
|----------|----------|
| Policy | Policy age at claim, premium history, recent changes count, coverage amount |
| Member | Dependent count, dependent add velocity, prior claim count, claim frequency, days since last claim, claim type diversity |
| Claim | Amount relative to benefit max, timing relative to policy events, documentation completeness, document format flags |
| Provider | Total claims supported at Prudential, patient count, approval rate, geographic concentration |
| Network | Shared address count, shared provider with flagged members, family claim correlation |
| Temporal | Proximity to termination, proximity to benefit period end, time between dependent add and claim, day of week |
| Document | Number of document flags triggered (from Layer 1 document checks) |

**Scoring Phases:**

- Phase 1 (prototype): Weighted sum, weights from domain expert input
- Phase 2 (with feedback): Supervised model trained on analyst confirm/dismiss actions, retrained quarterly

### 2.3 Layer 3 — Network/Link Analysis

Entity graph built from claims data. Reuses existing NetworkX infrastructure.

**Prudential Supplemental Health Graph:**

```
Entities and Relationships:
  Member ── has_dependent ──→ Dependent
  Member ── treated_by ────→ Provider
  Member ── employed_by ───→ Employer
  Member ── lives_at ──────→ Address
  Member ── has_policy ────→ Policy
  Dependent ── treated_by ─→ Provider
  Dependent ── lives_at ───→ Address

Detectable Fraud Patterns:
  - Dependent ring: "unrelated" members share dependents
  - Address cluster: many claimants at same address
  - Provider mill: one provider, abnormal claim volume
  - Employer collusion: claim spike from one group
  - Cross-member dependent sharing: same dependent on multiple policies
```

---

## Part 3: Document Analysis Engine (From OneNote Checklist)

This is the most specific and actionable part of the OneNote. The checklist gives us an explicit list of what to detect.

### 3.1 Medical Record Fraud Detection Framework

**Check Categories (directly from OneNote):**

| Check ID | Category | What to Detect | Detection Method |
|----------|----------|----------------|------------------|
| DOC-001 | Font inconsistency | Larger font, different style font in same document | Font metadata extraction, visual analysis |
| DOC-002 | Erasures | Evidence of erased or whited-out content | Image analysis for correction artifacts |
| DOC-003 | Typed over handwritten | Typed text overlaying handwritten dates or notes | Layer analysis, inconsistent baseline detection |
| DOC-004 | Handwritten reports | Entire report is handwritten (unusual for modern facilities) | Document format classification |
| DOC-005 | Missing headers | No OVN (Office Visit Notes), HCF (Healthcare Facility) or standard headers | Template matching, header detection |
| DOC-006 | Black and white records | Records that should be color appear B&W (possible photocopy of altered doc) | Color space analysis |
| DOC-007 | Editable Word documents | Medical records submitted as .doc/.docx instead of PDF or image | File format check |
| DOC-008 | Inconsistent font size | Multiple font sizes within what should be uniform document | Font size variance analysis |
| DOC-009 | Misspellings | Medical terminology misspelled (suggests non-medical author) | Medical terminology spell check |
| DOC-010 | Suspicious physician signature | Signature doesn't match known specimens, or appears stamped/copied | Signature analysis |
| DOC-011 | Records via email | Records sent via email rather than secure portal or fax | Submission channel check |
| DOC-012 | Missing vitals/medication list | Full medical records without routine data points | Required field completeness check |
| DOC-013 | Non-RP records | Full medical non-RPs (records from non-requesting providers — unusual) | Source provider validation |

### 3.2 Document Analysis in Prototype

For the prototype, we simulate document analysis since we won't have real medical records:

**Synthetic Document Metadata:**

Each synthetic claim includes a document metadata object describing what a real document analysis would find. The tools report on these metadata flags as if they scanned the actual document.

```
For each claim's medical records:
  document_metadata:
    format: "pdf" | "docx" | "image" | "handwritten_scan"
    submission_method: "portal" | "fax" | "email"
    has_headers: true | false
    header_types_present: ["OVN", "HCF", ...]
    color_mode: "color" | "bw"
    font_consistency_score: 0.0-1.0 (1.0 = perfectly consistent)
    font_sizes_detected: [10, 12] or [10, 12, 16, 8] (inconsistent)
    erasure_indicators: true | false
    typed_over_handwritten: true | false
    signature_confidence: 0.0-1.0
    medical_spelling_errors: []
    vitals_present: true | false
    medication_list_present: true | false
    provider_match: true | false (does provider match requesting provider)
    creation_date_vs_visit_date_gap: days (large gap = suspicious)
```

For fraud scenarios, these metadata flags are set to trigger multiple DOC checks. For legitimate claims, occasionally one flag triggers (realistic false positives).

---

## Part 4: Workflow Task Management (From OneNote PMR/CBR)

### 4.1 PMR (Payment Method Review)

From OneNote, PMR involves:
- Additional provider/facility being added
- Payment method being updated
- Replaced Stop Pay Tracker effective 10/7/2024
- Additional notes on claim details (new benefits needing to be claimed, member confirming no police report filed)
- Member provided documents and no notes beyond 5-day TAT
- Escalations for claims out of TAT

### 4.2 CBR (Callback Request)

From OneNote, CBR involves:
- Member had a previous CBR set and no call out has been made
- Member had a previous PMR set and no additional notes to address it
- Member has contacted 3+ times in last 15 days
- Member wants to speak to claim examiner

### 4.3 How This Fits the Platform

The copilot tracks workflow tasks alongside fraud investigation:

```
When analyst opens a claim, copilot checks:
  1. Does this claim have an open PMR? → Surface it
  2. Does this claim have an open CBR? → Surface it  
  3. Is this claim out of TAT? → Surface escalation need
  4. Has the member contacted 3+ times? → Surface and note frustration risk

These aren't fraud signals but they're part of the analyst's 
daily workflow. Including them means the analyst uses the platform 
for EVERYTHING, not just fraud cases.
```

**Workflow Tools:**

| Tool | Purpose |
|------|---------|
| `check_workflow_tasks` | Return open PMR, CBR, TAT status for a claim |
| `update_task_status` | Mark PMR addressed, CBR completed, notes added |
| `check_tat_compliance` | Flag claims approaching or past TAT deadline |
| `get_contact_history` | Member contact count and history (feeds CBR logic) |

---

## Part 5: Policy Intelligence (From OneNote Alerts)

### 5.1 Policy Change Tracking

The OneNote includes a policy change alert about surgical repair benefits. This tells us policy rules change over time and analysts need to stay current.

**Policy Intelligence Framework:**

```
Policy Alert:
  id: string
  effective_date: date
  description: string
  applies_to: [claim_types]
  previous_rule: string
  new_rule: string
  training_required: bool
  
The copilot knows about active policy changes and:
  1. When adjudicating a claim that falls under a changed policy,
     proactively surfaces the change
  2. If claim was filed before effective date but processed after,
     notes which rule applies
  3. Checks if the claim type + timing suggests exploitation
     of the policy change (R-014)
```

### 5.2 State and Extra-Territorial Rules

From first KT session: ET rules are complex, the most recent ET supersedes the policy, state-specific exclusions apply (e.g., Florida intoxication exclusion).

**State Rules Framework:**

```
State Rule:
  state: string
  claim_type: string
  rule_type: "exclusion" | "inclusion" | "modification"
  description: string
  effective_date: date
  
ET Resolution Logic:
  1. Determine member's service state
  2. Determine policy's governing state
  3. Apply ET hierarchy (most recent ET supersedes)
  4. Return applicable rules with explanation
```

---

## Part 6: Copilot Agent

### 6.1 Tool Sets

**Universal Tools (all domains):**

| Tool | Purpose |
|------|---------|
| `run_fraud_checklist` | Execute domain-specific checklist, return pass/fail per step |
| `explain_risk_score` | Break down risk score with feature contributions |
| `get_entity_network` | Return entity network for graph visualization |
| `search_similar_cases` | Find similar historical cases and outcomes |
| `compile_dossier` | Generate investigation summary or escalation package |

**Prudential Supplemental Health — Fraud Tools:**

| Tool | Purpose | Maps to Analyst Task |
|------|---------|---------------------|
| `check_eligibility` | Consolidated eligibility check (replaces 3 systems) | Eligibility verification |
| `check_family_claims` | All claims from member + dependents in configurable window | The 100-day family check |
| `analyze_medical_documents` | Run all DOC-001 through DOC-013 checks on claim documents | Medical record fraud detection |
| `detect_dependent_anomalies` | Dependent add patterns, age distributions, cross-member overlap | Catches 35-dependent case |
| `check_provider_patterns` | Provider claim volume, patient patterns, documentation quality | Provider mill detection |
| `flag_inconsistencies` | Cross-reference all data for contradictions + innocent explanations | Comprehensive red flag review |
| `find_related_claims` | Find claims linked by provider, address, dependent, or pattern | Network-level fraud |

**Prudential Supplemental Health — Workflow Tools:**

| Tool | Purpose | Maps to Analyst Task |
|------|---------|---------------------|
| `check_workflow_tasks` | Return open PMR, CBR, TAT status | Daily task management |
| `get_contact_history` | Member contact count and history | CBR threshold check |
| `check_tat_compliance` | Flag claims approaching or past TAT | Escalation management |

**Prudential Supplemental Health — Policy Intelligence Tools:**

| Tool | Purpose | Maps to Analyst Task |
|------|---------|---------------------|
| `get_policy_details` | Policy terms, age, changes, owner/beneficiary history | Policy review |
| `check_state_rules` | Applicable state rules, ET resolution, exclusions | ET determination |
| `check_policy_alerts` | Active policy changes affecting this claim type | Staying current (surgical repair change) |
| `match_claim_to_coverage` | Compare claim details against policy terms, return coverage determination | The hard part of accident claims |

**Provider Fraud Tools (from original prototype, available when domain = provider_fraud):**

| Tool | Purpose |
|------|---------|
| `profile_entity` | Provider billing profile and anomaly summary |
| `compare_to_peers` | Z-score comparison against specialty peers |
| `find_connections` | Graph traversal for provider relationships |
| `find_ring` | Ring detection algorithm |
| `get_referral_history` | Referral pattern analysis |

### 6.2 Checklist Automation

**Prudential Supplemental Health Checklist (7 steps):**

```
Step 1: Initial Claim Review
  Actions:
    - Verify claim form completeness
    - Check claim type and benefit requested
    - Identify submission channel
  Tools: analyze_medical_documents (format checks only)
  Auto-pass criteria: all required fields present, standard format

Step 2: Eligibility Verification
  Actions:
    - Check policy status (active, lapsed, terminated)
    - Verify member identity and date of birth
    - Confirm coverage includes claimed benefit type
    - Check date of birth → expiration date chain
  Tools: check_eligibility
  Auto-pass criteria: policy active, member verified, benefit covered

Step 3: Fraud Screening
  Actions:
    - Check suspicious banner status
    - Run rules engine (all applicable rules)
    - Calculate risk score
    - Run document fraud checks (DOC-001 through DOC-013)
  Tools: explain_risk_score, analyze_medical_documents
  Auto-pass criteria: no rules triggered, risk score < 30, no document flags
  
Step 4: Family and Pattern Review
  Actions:
    - Pull family claims last 100 days
    - Check dependent legitimacy
    - Check for cross-member patterns
  Tools: check_family_claims, detect_dependent_anomalies
  Auto-pass criteria: family claims within normal range, no dependent flags

Step 5: Medical Record Review (if applicable)
  Actions:
    - Full document fraud analysis
    - Verify provider legitimacy
    - Match diagnosis to claimed benefit
    - Check for provider patterns
  Tools: analyze_medical_documents, check_provider_patterns
  Auto-pass criteria: all DOC checks pass, provider legitimate, diagnosis matches

Step 6: Policy Terms Application
  Actions:
    - Determine governing state (ET resolution)
    - Check exclusions (e.g., intoxication)
    - Check for active policy change alerts
    - Match claim to coverage terms
  Tools: get_policy_details, check_state_rules, check_policy_alerts, 
         match_claim_to_coverage
  Auto-pass criteria: no exclusions apply, claim matches coverage terms

Step 7: Determination
  Actions:
    - Approve / Deny / Pend / Escalate
    - Document rationale
    - Generate summary or escalation package
    - Check for open PMR/CBR tasks
  Tools: compile_dossier, check_workflow_tasks
  Output: determination with full audit trail
```

### 6.3 Copilot System Prompt

```
Universal Frame:
  - Claims investigation copilot assisting an experienced analyst
  - Use tools to answer questions with specific data
  - Never make final determinations
  - Present red flags with possible innocent explanations
  - Track checklist progress
  - Proactively suggest next steps

Prudential Supplemental Health Additions:
  - Supplemental health claims: wellness, accident, hospital indemnity, 
    critical illness
  - Key fraud types: dependent abuse, auto-adjudication gaming, medical 
    record tampering, policy manipulation, provider mills
  - Medical record red flags: altered fonts, erasures, typed over handwritten, 
    missing headers, editable formats, suspicious signatures, B&W records, 
    misspellings, records via email
  - Workflow awareness: check for open PMR/CBR tasks, TAT compliance
  - Policy awareness: surgical repair benefit change effective 9/18/25 — 
    now paid regardless of hospital confinement
  - ET rules: most recent ET supersedes policy; state-specific exclusions 
    (e.g., Florida intoxication)
  - Auto-adjudication: wellness claims auto-pay; surface patterns that 
    individual claims don't trigger
```

---

## Part 7: Data Layer

### 7.1 Synthetic Data Generation

**Entities:**

| Entity | Count | Notes |
|--------|-------|-------|
| Employers | 10 | Mix of large, mid, small |
| Members | 200 | Employees across employers |
| Dependents | 300 | Realistic distribution, one outlier with 35 |
| Providers | 40 | Physicians, hospitals, clinics |
| Facilities | 15 | Hospitals, surgical centers |
| Addresses | 180 | Most unique, some shared (for network detection) |
| Policies | 200 | One per member, varying coverage |
| Claims | 500 | Mix across all types |
| Documents | 500 | One metadata object per claim (simulated doc analysis) |

**Claim Type Distribution:**

| Type | Count | Auto-Adjudicated | Analyst Effort |
|------|-------|-------------------|----------------|
| Wellness | 250 | Yes (most) | Low (when clean) |
| Hospital Indemnity | 100 | No | Medium |
| Accident | 100 | No | High |
| Critical Illness | 50 | No | High |

**10 Embedded Fraud Scenarios:**

| # | Scenario | Claim Type | Risk | What Catches It |
|---|----------|------------|------|-----------------|
| 1 | **35 dependents added** — member adds 35 dependents over 14 days, files wellness claims for each at exactly $100 | Wellness | 94 | Rules R-001, R-002, R-009. Network: shared address |
| 2 | **Termination rush** — member files 8 claims in final 30 days before coverage ends Sept 2025 | Wellness + Accident | 85 | Rule R-004. Temporal pattern |
| 3 | **Owner change before critical illness** — policy owner changed 45 days before $50K critical illness claim | Critical Illness | 88 | Rule R-006. Policy history |
| 4 | **Fabricated accident** — accident details physically inconsistent, medical records show different injury mechanism | Accident | 79 | Document analysis, claim-to-coverage mismatch |
| 5 | **Provider mill** — one provider supports 15 hospital indemnity claims in one month, near-identical documentation across patients | Hospital Indemnity | 82 | Rule R-005. DOC-008 (font consistency). Provider pattern |
| 6 | **Tampered medical records** — records have mixed fonts, erasures, typed dates over handwritten originals, submitted as Word doc via email | Accident | 76 | DOC-001, DOC-002, DOC-003, DOC-007, DOC-011 |
| 7 | **Duplicate resubmission** — previously denied accident claim resubmitted with date changed by one day | Accident | 71 | Rules R-008, R-010 |
| 8 | **Dependent ring** — 3 members from different employers share 8 "dependents" at the same address, filing wellness claims | Wellness | 87 | Network: shared dependents + address. Rule R-007 |
| 9 | **Surgical repair exploit** — 4 claims filed day after policy change for outpatient surgical repair, all from same employer group | Hospital Indemnity | 65 | Rule R-014. Policy alert match. Temporal cluster |
| 10 | **Missing headers / B&W records** — critical illness claim with medical records missing all standard headers, B&W photocopies, no vitals documented | Critical Illness | 68 | DOC-005, DOC-006, DOC-012 |

**Legitimate Claims with False Positive Flags (important for demo):**

| # | Scenario | Flag Triggered | Why It's Legitimate |
|---|----------|----------------|---------------------|
| A | New employee files accident claim 60 days after policy start | R-003 (early filing) | Genuine accident, bad timing |
| B | Member contacts 4 times in 15 days | R-011 (CBR frequency) | Complex claim, genuinely needs updates |
| C | Medical records in B&W | DOC-006 | Small rural clinic with old scanner |
| D | 6 dependents added in 30 days | R-001 threshold (barely) | Blended family, marriage + stepchildren |
| E | Claim amount equals benefit max | R-009 | Hospital bill genuinely exceeded maximum |

### 7.2 Workflow Task Data

Generate realistic PMR and CBR tasks attached to claims:

```
For 15% of claims: open PMR task
  - 5% have no notes beyond 5-day TAT (flaggable)
  - 10% have proper notes

For 10% of claims: open CBR task  
  - 3% have prior CBR with no call made (flaggable)
  - 7% are new CBR requests

For 8% of claims: approaching or past TAT
```

### 7.3 Data Flow on Startup

```
1. Generate synthetic entities (members, dependents, providers, employers, addresses)
2. Generate synthetic policies (with owner/beneficiary change history)
3. Generate synthetic claims (500, with 10 fraud + 5 false positive scenarios)
4. Generate synthetic document metadata (per claim)
5. Generate workflow tasks (PMR, CBR attached to subset of claims)
6. Register active policy alerts (surgical repair change)
7. Run Rules Engine → tag claims with rule triggers
8. Run Risk Scoring → assign 0-100 score per claim
9. Build Entity Graph → create network relationships
10. Build Claims Queue → sorted by risk score, filtered by status
11. Cache everything (pickle for demo, DB for production)
```

---

## Part 8: API Layer

### 8.1 Endpoints

**Claims Queue:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/claims` | List claims with filters (type, priority, status, risk tier) |
| GET | `/api/claims/{id}` | Full claim detail: risk score, rules triggered, document flags, workflow tasks |
| POST | `/api/claims/{id}/status` | Update claim status |
| GET | `/api/claims/stats` | Dashboard: counts by type, priority, status, intercepts |

**Intelligence:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/claims/{id}/risk` | Risk score breakdown with feature contributions |
| GET | `/api/claims/{id}/rules` | Triggered rules with explanations |
| GET | `/api/claims/{id}/documents` | Document analysis results (all DOC checks) |
| GET | `/api/claims/{id}/network` | Entity network for graph visualization |
| GET | `/api/claims/{id}/checklist` | Checklist status with results per step |

**Workflow:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/claims/{id}/tasks` | Open PMR, CBR, TAT status |
| POST | `/api/claims/{id}/tasks/{task_id}` | Update task status |

**Policy:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/policy-alerts` | Active policy changes |
| GET | `/api/state-rules/{state}` | State-specific rules and exclusions |

**Copilot:**

| Method | Path | Purpose |
|--------|------|---------|
| WS | `/ws/chat/{claim_id}` | Persistent chat WebSocket |

**Platform:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check |
| GET | `/api/config` | Current domain configuration |
| GET | `/api/domains` | Available domain configurations |

### 8.2 WebSocket Events

```
Incoming:
  { action: "message", text: "..." }
  { action: "run_checklist" }
  { action: "run_checklist_step", step: 3 }
  { action: "run_auto_scan" }
  { action: "end_session" }

Outgoing:
  { type: "connected", claim_id, claim_type, risk_score, open_tasks }
  { type: "thinking" }
  { type: "tool_call", tool, args }
  { type: "tool_result", tool, summary }
  { type: "response", text }
  { type: "checklist_update", step, status, result }
  { type: "policy_alert", alert }
  { type: "error", message }
```

---

## Part 9: Frontend

### 9.1 Navigation

```
[📋 Claims Queue]      ← landing page, 20-25 claims/day view
[💬 Copilot]           ← investigation chat with checklist
[📊 Risk Dashboard]    ← aggregate risk view, intercepts count
[🕸️ Network]           ← entity graph visualization
[📄 Dossier]           ← investigation output / escalation package
[📜 Activity]          ← event log / audit trail
```

### 9.2 Claims Queue

```
┌────────────────────────────────────────────────────────────────────────┐
│ CLAIMS QUEUE                                      [Filter ▾] [↻]      │
│                                                                        │
│ [All (500)] [Wellness (250)] [Accident (100)] [HI (100)] [CI (50)]    │
│ Risk: [🔴 HIGH (12)] [🟡 MEDIUM (38)] [⚪ LOW (450)]                   │
│                                                                        │
├────────┬──────────┬────────────┬─────────────────────┬──────┬──────────┤
│ Claim# │ Type     │ Member     │ Flag / Task          │ Risk │ Status   │
├────────┼──────────┼────────────┼─────────────────────┼──────┼──────────┤
│ WC-247 │ Wellness │ M. Rivera  │ 🚩 35 deps added    │ 🔴 94│ NEW      │
│ CI-051 │ Crit Ill │ R. Torres  │ 🚩 Owner change 45d │ 🔴 88│ NEW      │
│ WC-312 │ Wellness │ K. Adams   │ 🚩 Dep ring detect  │ 🔴 87│ NEW      │
│ AC-103 │ Accident │ J. Park    │ 🚩 Tampered records │ 🟡 76│ NEW      │
│ HI-089 │ Hosp Ind │ T. Chen    │ 📋 PMR open (2d)    │ 🟡 65│ IN_REVIEW│
│ AC-107 │ Accident │ D. Williams│ ☎️ CBR pending       │ ⚪ 28│ NEW      │
│ WL-401 │ Wellness │ S. Johnson │ ✓ Auto-adjudicated  │ ⚪ 5 │ APPROVED │
└────────┴──────────┴────────────┴─────────────────────┴──────┴──────────┘

Note: workflow tasks (PMR, CBR) visible alongside fraud flags.
Analyst sees everything in one view.
```

### 9.3 Copilot Chat

```
┌──────────────────────────────────────────────────────────┐
│ CLAIM WC-247 — M. Rivera               Risk: 🔴 94/100   │
│ Wellness | Employer: Acme Corp | Coverage ends: Sept 2025 │
│                                                          │
│ ⚠️ 3 rules triggered | 📋 PMR open | ☎️ No active CBR    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ ┌─ Checklist Progress ─────────────────────────────────┐ │
│ │ ✅ Initial  ⬜ Eligible  ⬜ Fraud  ⬜ Family         │ │
│ │ ⬜ Medical  ⬜ Policy    ⬜ Determine                │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ (chat messages here)                                     │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ [Type your question...                          ] [Send] │
├──────────────────────────────────────────────────────────┤
│ [▶ Run Full Checklist]  [Check Eligibility]              │
│ [Family Claims] [Document Analysis] [View Network]       │
│ [Policy & State Rules] [Workflow Tasks] [Escalate]       │
└──────────────────────────────────────────────────────────┘

Quick action chips change by claim type:
  Wellness:  [Dependent Check] [Claim History] [Auto-Adj Review]
  Accident:  [Match to Policy] [Accident Details] [State Rules]
  Hosp Ind:  [Admission/Discharge] [Provider Check] [Policy Terms]
  Crit Ill:  [Medical Records] [Document Analysis] [Policy Check]
```

### 9.4 Risk Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│ RISK DASHBOARD                                    Today      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─ Auto-Adjudication Intercepts ───────────────────────┐   │
│ │                                                       │   │
│ │  8 claims blocked    $12,400 held for review          │   │
│ │  (would have auto-paid without platform)              │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                             │
│ ┌─ Risk Distribution ──┐  ┌─ Top Rules Triggered ────────┐ │
│ │ 🔴 HIGH    12 (2%)    │  │ R-001 Dep spike        8x   │ │
│ │ 🟡 MEDIUM  38 (8%)    │  │ R-002 Claim velocity  14x   │ │
│ │ ⚪ LOW    450 (90%)   │  │ R-004 Term rush       11x   │ │
│ └──────────────────────┘  │ R-005 Provider mill    6x   │ │
│                            └────────────────────────────┘ │
│ ┌─ Patterns Detected ────────────────────────────────────┐ │
│ │ 🕸️ 1 dependent ring (3 members, shared address)        │ │
│ │ 🏥 1 provider cluster (Dr. X, 15 claims/mo)            │ │
│ │ 📈 2 termination rush patterns                          │ │
│ │ 📄 3 claims with document tampering indicators          │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─ Workflow Health ──────────────────────────────────────┐  │
│ │ PMR open: 12 (3 past TAT)                              │  │
│ │ CBR pending: 8 (2 with no callback made)               │  │
│ │ Claims past TAT: 5                                     │  │
│ └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 10: Build Phases

### Phase 1: Foundation — Data + Rules + Queue (Week 1)

```
Goal: Platform runs. Claims queue shows 500 claims scored and ranked.

Tasks:
  1. Domain configuration model
  2. Prudential supplemental health config
  3. Synthetic data generator (entities, policies, claims, documents, tasks)
  4. 10 fraud scenarios + 5 false positive scenarios embedded
  5. Rules engine (14 rules from checklist)
  6. Risk scoring (weighted heuristic)
  7. Claims queue API endpoints
  8. Claims Queue UI

Demo checkpoint:
  "500 claims scored. 12 flagged HIGH. The 35-dependent case 
   is blocked before auto-adjudication. The tampered medical 
   record case is flagged with specific DOC checks."
```

### Phase 2: Copilot + Document Analysis (Week 2)

```
Goal: Analyst can investigate any claim conversationally.

Tasks:
  9. Document analysis engine (DOC-001 through DOC-013 checks)
  10. Fraud tools (7 tools)
  11. Workflow tools (3 tools)
  12. Policy intelligence tools (4 tools)
  13. Checklist framework + 7-step Prudential checklist
  14. Copilot agent with domain-aware tool selection
  15. Chat WebSocket
  16. ChatPanel UI with checklist progress

Demo checkpoint:
  "Analyst clicks flagged claim. Asks 'why flagged?' 
   Copilot explains rules and risk score. Analyst clicks 
   'Run Full Checklist' — all 7 steps execute. Step 5 
   finds tampered medical records: mixed fonts, erasures, 
   Word doc format. Step 3 finds 35 dependents."
```

### Phase 3: Network + Dashboard + Dossier (Week 3)

```
Goal: Full investigation flow, pattern detection, escalation.

Tasks:
  17. Entity graph builder (member/dependent/provider/address)
  18. Network graph UI (repurposed from existing)
  19. Risk Dashboard UI
  20. Dossier / escalation package template
  21. Auto-scan integration
  22. Workflow task management in UI

Demo checkpoint:
  "Analyst sees dependent ring in network graph. Generates 
   escalation package. Dashboard shows 8 claims intercepted 
   today, $12,400 held. PMR/CBR tasks visible alongside 
   fraud work."
```

### Phase 4: Domain Agnostic + Polish (Week 4)

```
Goal: Demonstrate multi-domain capability. Demo-ready.

Tasks:
  23. Refactor all Prudential-specific code into domain config
  24. Create second domain config (provider fraud from original prototype)
  25. Domain switcher in UI
  26. End-to-end testing both domains
  27. False positive scenarios tested (analyst dismisses correctly)
  28. Demo script rehearsal

Demo checkpoint:
  "Switch from Prudential Supplemental Health to Provider Fraud. 
   Same platform, different rules, tools, data. One product, 
   any insurance line of business."
```

---

## Part 11: Demo Script (Prudential Sell)

```
[0:00] THE PROBLEM
  "Last month, a member added 35 dependents and filed 
   wellness claims for each at exactly $100. Auto-adjudication 
   paid every one. You found out when the client emailed you."

[0:30] THE QUEUE
  Show claims queue. 500 claims, 12 flagged HIGH.
  "Every claim scored before adjudication. The auto-adjudicator 
   still runs — but now there's a fraud layer in front of it."

  Point to WC-247: risk score 94, 3 rules triggered.
  "This one never makes it to auto-pay."

[1:00] THE INVESTIGATION
  Click WC-247. Copilot opens.
  "Why was this flagged?"
  Copilot: 35 dependents in 14 days, 47 claims this quarter,
  all at exactly $100.

[1:30] THE CHECKLIST
  Click "Run Full Checklist."
  Watch 7 steps execute. Step 4 (Family Claims) goes red.
  "Your OneNote checklist, automated. Every step documented 
   with evidence."

[2:30] THE NETWORK
  "Show me the network."
  Graph shows: member → 35 dependents → shared address with 
  2 other members who also have abnormal dependent counts.
  "It's not one bad actor. It's a ring."

[3:00] DOCUMENT FRAUD (different claim)
  Go back to queue. Click AC-103 (tampered records).
  Click "Document Analysis."
  Copilot: "5 document flags detected: mixed font sizes, 
  erasure indicators, typed text over handwritten dates, 
  submitted as Word document via email."
  
  "These are the exact red flags from your fraud checklist. 
   The system checks every one automatically."

[4:00] THE DAILY WORKFLOW
  Click a LOW-risk accident claim.
  "For clean claims, the copilot accelerates adjudication."
  Click "Check Eligibility" → one answer instead of 3 systems.
  Click "Match to Policy" → accident details matched to terms.
  Click "Check State Rules" → ET resolution with applicable state.
  
  Note the PMR badge: "You also have a PMR open on this one, 
  2 days old."

[5:00] POLICY INTELLIGENCE
  Process a hospital indemnity claim for outpatient surgery.
  Copilot proactively surfaces: "Note: as of 9/18/25, surgical 
  repair benefits are paid regardless of hospital confinement. 
  This outpatient claim is now covered."
  "The system knows about policy changes before your analyst does."

[5:30] THE ESCALATION
  Back to WC-247. Click "Escalate."
  Dossier generates: timeline, evidence, network diagram, 
  dollar exposure, rule triggers, document analysis, 
  recommended action.
  "SIU gets a complete package. No manual write-up."

[6:00] THE DASHBOARD
  Show Risk Dashboard.
  "8 claims intercepted today. $12,400 held for review. 
   3 past-TAT claims need attention. 1 provider cluster detected."
  "This is your morning briefing."

[6:30] DOMAIN AGNOSTIC
  Switch to provider fraud domain.
  Same platform, different everything underneath.
  "This isn't a Prudential-only tool. Configure a new domain 
   and it works for any line of business. That's the product."

[7:00] CLOSE
  "Your analysts already touch every claim. We make them faster 
   on clean ones and smarter on dirty ones. The auto-adjudicator 
   keeps running — it just has a brain now. And the next time 
   someone adds 35 dependents, you find out before the client does."
```

---

## Part 12: Open Items for Prudential

| Item | Priority | Why |
|------|----------|-----|
| OneNote checklist full document (we have partial) | HIGH | May contain additional checks we haven't captured |
| Sample claim screen from Prudential 360 | HIGH | Need actual field names for realistic synthetic data |
| Auto-adjudication rules for wellness | HIGH | Need to know exactly what passes through unchecked |
| Suspicious banner trigger logic | HIGH | Build our scoring to complement, not conflict |
| State/ET rules table or document | HIGH | Build state rules tool accurately |
| PMR/CBR process documentation | MEDIUM | Validate our workflow tool design |
| List of confirmed fraud cases (anonymized) | MEDIUM | Validate scenario realism |
| Claim volume by type (monthly) | MEDIUM | Calibrate synthetic data |
| SIU handoff requirements | MEDIUM | Shape escalation package format |
| System integration points (APIs, databases) | LOW (for prototype) | Production planning |
| Compliance/regulatory constraints | LOW (for prototype) | What can't be automated |