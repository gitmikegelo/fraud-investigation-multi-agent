

# Claims Copilot
## Intelligent Workflow Platform for Supplemental Health Claims

---

**Prepared for:** Prudential Financial
**Version:** Prototype v2
**Classification:** Confidential

---

## Executive Summary

Claims Copilot is an AI-powered workflow platform designed for supplemental health claims examiners. It consolidates eligibility verification, fraud detection, policy intelligence, and workflow management into a single interface — replacing the need to toggle between multiple systems for every claim.

The platform scores and ranks all incoming claims using a three-layer intelligence pipeline, surfaces fraud patterns that would be invisible when reviewing claims individually, and provides an AI copilot that assists the examiner through every step of the investigation process.

**The core value proposition is simple:** examiners process claims faster, catch more fraud, and document everything automatically.

---

## What the Platform Does

### For Every Claim (Daily Workflow Value)

| Today (Without Platform) | With Claims Copilot |
|---|---|
| Check eligibility across 3 separate systems | One-click eligibility check returns a consolidated result |
| Manually cross-reference policy terms, state rules, and ET resolution | Copilot surfaces applicable rules, exclusions, and coverage determination automatically |
| Track PMR, CBR, and TAT deadlines across different screens | Workflow tasks appear alongside the claim in a single view |
| Manually check if policy changes affect the claim | Proactive alerts surface relevant policy changes (e.g., PA-001 surgical repair update) |
| Write up case notes and escalation packages from scratch | Dossier generated automatically with timeline, evidence, and recommended actions |

### For Flagged Claims (Fraud Intelligence)

| Capability | How It Works |
|---|---|
| **Risk Scoring** | Every claim receives a 0–100 risk score based on 30+ weighted features across policy, member, claim, provider, network, and temporal dimensions |
| **Rules Engine** | 14 deterministic rules run on every claim (e.g., dependent spike, claim velocity, policy manipulation, duplicate submissions) |
| **Document Analysis** | 13 automated checks on medical record metadata — font consistency, erasure indicators, missing headers, editable formats, and more |
| **Network Detection** | Entity graph connects members, dependents, providers, addresses, and employers to reveal rings, clusters, and coordinated patterns |
| **Investigation Checklist** | Structured 7-step process that can run automatically or step-by-step, with pass/fail tracking |

---

## Platform Views

### 1. Claims Queue — The Morning View

The examiner's landing page. All 500 claims displayed in a sortable, filterable queue.

```
┌────────────────────────────────────────────────────────────────────────┐
│ CLAIMS QUEUE                                        [Filter ▾] [↻]    │
│                                                                        │
│ [All (500)] [Wellness (250)] [Accident (100)] [HI (100)] [CI (50)]    │
│ Risk: [🔴 HIGH (12)] [🟡 MEDIUM (38)] [⚪ LOW (450)]                   │
│                                                                        │
├────────┬──────────┬────────────┬──────────────────────┬──────┬─────────┤
│ Claim# │ Type     │ Member     │ Flag / Task           │ Risk │ Status  │
├────────┼──────────┼────────────┼──────────────────────┼──────┼─────────┤
│ WC-247 │ Wellness │ M. Rivera  │ 🚩 35 deps added     │ 🔴 94│ NEW     │
│ CI-051 │ Crit Ill │ R. Torres  │ 🚩 Owner change 45d  │ 🔴 88│ NEW     │
│ AC-103 │ Accident │ J. Park    │ 🚩 Tampered records  │ 🟡 76│ NEW     │
│ HI-089 │ Hosp Ind │ T. Chen    │ 📋 PMR open (2d)     │ 🟡 65│ REVIEW  │
│ AC-107 │ Accident │ D. Williams│ ☎️ CBR pending        │ ⚪ 28│ NEW     │
│ WL-401 │ Wellness │ S. Johnson │ ✓ Auto-adjudicated   │ ⚪  5│ APPROVED│
└────────┴──────────┴────────────┴──────────────────────┴──────┴─────────┘
```

**Key design principle:** Fraud flags and workflow tasks (PMR, CBR, TAT) appear side by side. The examiner sees their full workload — not just the suspicious claims.

Claims are filterable by:
- **Claim type:** Wellness, Accident, Hospital Indemnity, Critical Illness
- **Risk tier:** High (65–100), Medium (30–64), Low (0–29)
- **Status:** New, In Review, Escalated, Approved, Denied, Closed
- **Workflow state:** Open PMR, Pending CBR, Past TAT

---

### 2. Copilot — AI-Assisted Claim Review

Selecting any claim opens the Copilot — a conversational AI assistant with full access to the claim's data, related entities, and investigation tools.

```
┌──────────────────────────────────────────────────────────┐
│ CLAIM WC-247 — M. Rivera                  Risk: 🔴 94    │
│ Wellness | Acme Corp | Coverage ends: Sept 2025          │
│ ⚠️ 3 rules triggered | 📋 PMR open | ☎️ No active CBR   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ ┌─ Checklist Progress ─────────────────────────────────┐ │
│ │ ✅ Initial  ✅ Eligible  🔴 Fraud  ⬜ Family         │ │
│ │ ⬜ Medical  ⬜ Policy    ⬜ Determine                │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│  Examiner: Why was this flagged?                         │
│                                                          │
│  Copilot: This claim was flagged for three reasons:      │
│                                                          │
│  1. Dependent Spike (R-001, BLOCK): M. Rivera added 35   │
│     dependents in 14 days. Threshold is 5 in 30 days.   │
│  2. Claim Velocity (R-002, FLAG): 47 claims this quarter │
│     across member and dependents. Threshold is 10.       │
│  3. Benefit Max Gaming (R-009, INFO): All 35 wellness    │
│     claims filed at exactly $100.00 — the benefit max.   │
│                                                          │
│  Risk score breakdown: policy age (low risk), member     │
│  features (very high — dependent count is 8σ above mean),│
│  network signals (shared address with 2 other members).  │
│                                                          │
│  Shall I run the full investigation checklist, or would  │
│  you like to start with the dependent analysis?          │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ [Type your question...                          ] [Send] │
├──────────────────────────────────────────────────────────┤
│ [▶ Run Full Checklist] [Dependent Check] [Claim History] │
│ [Document Analysis] [View Network] [Escalate]            │
└──────────────────────────────────────────────────────────┘
```

**The Copilot can:**
- Answer natural language questions about any aspect of the claim
- Call investigation tools on demand (eligibility, documents, family claims, provider patterns)
- Run the 7-step checklist automatically or one step at a time
- Proactively surface relevant policy alerts and workflow tasks
- Present red flags alongside innocent explanations — it doesn't just accuse
- Generate escalation packages for SIU referral

**Quick action chips** adapt to the claim type:
- **Wellness:** Dependent Check, Claim History, Auto-Adjudication Review
- **Accident:** Match to Policy, Accident Details, State Rules
- **Hospital Indemnity:** Admission/Discharge, Provider Check, Policy Terms
- **Critical Illness:** Medical Records, Document Analysis, Policy Check

---

### 3. Risk Dashboard — The Morning Briefing

Aggregate intelligence view showing the examiner what matters most today.

```
┌─────────────────────────────────────────────────────────────┐
│ RISK DASHBOARD                                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌─ Auto-Adjudication Intercepts ──────────────────────────┐ │
│ │  8 claims blocked       $12,400 held for review          │ │
│ │  (would have auto-paid without platform)                 │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─ Risk Distribution ───┐  ┌─ Top Rules Triggered ───────┐  │
│ │ 🔴 HIGH     12  (2%)   │  │ R-001 Dep spike       8x    │  │
│ │ 🟡 MEDIUM   38  (8%)   │  │ R-002 Claim velocity 14x    │  │
│ │ ⚪ LOW     450 (90%)   │  │ R-004 Term rush      11x    │  │
│ └────────────────────────┘  └──────────────────────────────┘ │
│                                                              │
│ ┌─ Patterns Detected ─────────────────────────────────────┐  │
│ │ 🕸️ 1 dependent ring (3 members, shared address)         │  │
│ │ 🏥 1 provider cluster (15 claims/month, 1 provider)     │  │
│ │ 📈 2 termination rush patterns                           │  │
│ │ 📄 3 claims with document tampering indicators           │  │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─ Workflow Health ───────────────────────────────────────┐   │
│ │ PMR open: 12 (3 past TAT ⚠️)                           │   │
│ │ CBR pending: 8 (2 with no callback made ⚠️)            │   │
│ │ Claims approaching TAT: 5                               │   │
│ └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**Auto-Adjudication Intercepts** shows the direct financial impact — claims that would have auto-paid without the platform's intervention.

**Patterns Detected** surfaces network-level intelligence that is invisible when reviewing claims individually. Each pattern is clickable, navigating directly to the relevant claims.

**Workflow Health** ensures TAT compliance and follow-up accountability.

---

### 4. Network Graph — Relationship Visualization

Interactive entity graph showing connections between members, dependents, providers, addresses, and employers.

```
        ┌─────────┐
        │ ADR-042 │ (shared address)
        └────┬────┘
       ┌─────┼──────────────┐
  ┌────▼───┐ │         ┌────▼───┐
  │MBR-012 │ │         │MBR-045 │
  │(Acme)  │ │         │(Beta)  │
  └───┬────┘ │         └───┬────┘
      │      │             │
  ┌───▼────┐ │        ┌───▼────┐
  │DEP-101 │◄┘        │DEP-101 │  ← same dependent on
  │DEP-102 │           │DEP-103 │    two unrelated members
  │DEP-103 │           └────────┘
  └────┬───┘
       │
  ┌────▼────┐
  │ PRV-007 │ (all claims through same provider)
  └─────────┘
```

The graph reveals:
- **Dependent rings:** Unrelated members sharing the same dependents
- **Address clusters:** Multiple claimants at the same physical address
- **Provider mills:** Abnormal patient volume through a single provider
- **Employer-linked patterns:** Claim spikes from a single employer group

---

## Three-Layer Intelligence Pipeline

Every claim passes through three layers of analysis before an examiner sees it.

### Layer 1: Rules Engine (14 Deterministic Rules)

Fast, explainable business rules that fire on every claim. Each rule has a severity level:

| Severity | Meaning | Example Rules |
|---|---|---|
| **BLOCK** | Prevents auto-adjudication, requires examiner review | Dependent Spike (>5 in 30 days), Duplicate Submission |
| **FLAG** | Surfaces in queue for investigation | Claim Velocity, Termination Rush, Policy Manipulation, Provider Cluster, Resubmission After Denial |
| **INFO** | Noted in checklist, doesn't force review | Benefit Max Gaming, CBR Frequency, Medical Records Via Email, Policy Change Impact |

**Full rule set:**

| ID | Rule | Condition | Severity |
|---|---|---|---|
| R-001 | Dependent Spike | >5 dependents added in 30 days | BLOCK |
| R-002 | Claim Velocity | >10 claims per member per quarter | FLAG |
| R-003 | Early Filing | Claim <90 days after policy start | FLAG |
| R-004 | Termination Rush | Claim spike within 60 days of coverage end | FLAG |
| R-005 | Provider Cluster | Same provider + same diagnosis + 5 patients in 30 days | FLAG |
| R-006 | Policy Manipulation | Owner/beneficiary change <180 days before claim | FLAG |
| R-007 | Dependent Age Gap | Member-dependent age gap >25 AND dependent age >25 | FLAG |
| R-008 | Duplicate Submission | Same member, date of service, and amount | BLOCK |
| R-009 | Benefit Max Gaming | 3+ consecutive claims at exact benefit maximum | INFO |
| R-010 | Resubmission After Denial | Denied claim resubmitted with <3 field changes | FLAG |
| R-011 | CBR Frequency | Member contacted 3+ times in 15 days | INFO |
| R-012 | PMR No Follow-up | Open PMR with no notes past 5-day TAT | FLAG |
| R-013 | Medical Records Via Email | Records submitted via email (not portal or fax) | INFO |
| R-014 | Policy Change Impact | Claim type matches timing of recent policy change | INFO |

### Layer 2: Risk Scoring (Weighted Heuristic, 0–100)

Each claim is scored across seven feature categories:

| Category | Weight | Example Features |
|---|---|---|
| **Policy** | 15% | Policy age at claim, recent owner/beneficiary changes, coverage amount |
| **Member** | 20% | Dependent count, dependent add velocity, prior claim count, claim frequency |
| **Claim** | 20% | Amount relative to benefit max, documentation completeness, document format flags |
| **Provider** | 15% | Total claims supported, unique patient count, approval rate, geographic concentration |
| **Network** | 15% | Shared address count, shared provider with flagged members, family claim correlation |
| **Temporal** | 10% | Proximity to termination, time between dependent add and claim, proximity to policy change |
| **Rules Boost** | 5% | Number of rules triggered, maximum rule severity |

**Score interpretation:**

| Tier | Score Range | Queue Behavior |
|---|---|---|
| 🔴 HIGH | 65–100 | Priority review, top of queue |
| 🟡 MEDIUM | 30–64 | Examiner should investigate |
| ⚪ LOW | 0–29 | Likely clean, fast-track eligible |

The risk breakdown is fully transparent — the examiner can see exactly which features contributed to the score and by how much.

### Layer 3: Network/Link Analysis

An entity graph connects all members, dependents, providers, facilities, addresses, and employers. Pattern detection runs on this graph to find:

| Pattern | Detection Method |
|---|---|
| **Dependent Ring** | Dependents connected to multiple unrelated members |
| **Address Cluster** | >3 unrelated members at the same address |
| **Provider Mill** | Provider with claim volume >2 standard deviations above peer mean |
| **Employer Collusion** | Claim spike from a single employer group |
| **Cross-Member Dependent Sharing** | Same dependent on multiple unrelated policies |

---

## Document Analysis Framework

Every claim's supporting documentation is evaluated against 13 checks. In the prototype, analysis is performed on document metadata attributes. In production, this integrates with document forensics services (OCR, image analysis, signature verification).

| Check | What It Detects | Severity |
|---|---|---|
| DOC-001 | Font inconsistency — multiple font styles in same document | High |
| DOC-002 | Erasure indicators — evidence of erased or whited-out content | High |
| DOC-003 | Typed over handwritten — typed text overlaying handwritten dates | High |
| DOC-004 | Entirely handwritten report (unusual for modern facilities) | Medium |
| DOC-005 | Missing standard headers (OVN, HCF) | Medium |
| DOC-006 | Black & white records (possible altered photocopy) | Low |
| DOC-007 | Editable Word document format (instead of PDF/image) | High |
| DOC-008 | Inconsistent font sizes within a uniform document | Medium |
| DOC-009 | Medical terminology misspellings (suggests non-medical author) | Medium |
| DOC-010 | Suspicious or stamped-looking signature | High |
| DOC-011 | Records submitted via email (not portal or fax) | Low |
| DOC-012 | Missing vitals or medication list in full medical records | Medium |
| DOC-013 | Records from a different provider than the requesting provider | Low |

---

## 7-Step Investigation Checklist

A structured framework that can be run automatically or step by step. Each step has auto-pass criteria — if all criteria are met, the step passes without examiner intervention.

| Step | Name | What It Checks | Auto-Pass Criteria |
|---|---|---|---|
| 1 | **Initial Claim Review** | Claim form completeness, submission channel, format | Required fields present, standard format |
| 2 | **Eligibility Verification** | Policy status, member identity, coverage confirmation | Policy active, member verified, benefit covered |
| 3 | **Fraud Screening** | Rules engine results, risk score, document checks | No rules triggered, risk <30, no document flags |
| 4 | **Family & Pattern Review** | Family claims (100 days), dependent legitimacy, cross-member patterns | Family claims in normal range, no dependent flags |
| 5 | **Medical Record Review** | Full document analysis, provider legitimacy, diagnosis match | All DOC checks pass, provider legitimate, diagnosis matches |
| 6 | **Policy Terms Application** | State rules, ET resolution, exclusions, policy alerts, coverage match | No exclusions apply, claim matches coverage |
| 7 | **Determination** | Approve / Deny / Pend / Escalate with documented rationale | Always requires human decision |

The checklist serves two purposes:
1. **Automation** — tools run, results evaluated, clean claims fast-tracked
2. **Audit trail** — every step documented with findings, tools used, and outcome

### What "Run Full Checklist" Returns

When the examiner clicks **Run Full Checklist** on a flagged claim (e.g., WC-247 — 35 dependents), the Copilot runs all 7 steps and returns output like this:

```
┌────────────────────────────────────────────────────────────────────┐
│ INVESTIGATION CHECKLIST — WC-247 (M. Rivera)       Risk: 🔴 94   │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  🟢 Step 1 — Initial Review                          AUTO-PASSED  │
│     ✓ All required fields present                                  │
│     ✓ INITIAL_REVIEW task assigned                                 │
│                                                                    │
│  🟢 Step 2 — Eligibility Verification                AUTO-PASSED  │
│     ✓ Policy is active                                             │
│     ✓ Coverage type matches: wellness                              │
│                                                                    │
│  🔴 Step 3 — Fraud Screening                         FAILED       │
│     ⛔ BLOCK rules triggered: R-001, R-002                         │
│     R-001: Member has 35 dependents (threshold: 10)               │
│     R-002: 47 claims filed across member + dependents in 90       │
│            days (threshold: 5 in 30 days)                         │
│     Risk score: 94.0 (HIGH)                                       │
│     → Auto-adjudication blocked. Examiner review required.        │
│                                                                    │
│  🟡 Step 4 — Family & Network Check                  NEEDS REVIEW │
│     🚩 R-015: 35 family members filed claims in last 100 days     │
│     🚩 R-001: Dependent count (35) exceeds threshold (10)         │
│     ✓ Shared address: Normal                                       │
│                                                                    │
│  🟡 Step 5 — Medical Documentation Review            NEEDS REVIEW │
│     ⚠️  DOC-001: Font inconsistency detected in 3 documents       │
│     ⚠️  DOC-005: Missing standard medical record headers           │
│     ⏳ Medical record request pending — waiting 4 days             │
│                                                                    │
│  🟡 Step 6 — Policy & Coverage Determination         NEEDS REVIEW │
│     ✓ Coverage matches: wellness                                   │
│     ⚠️  PA-001: Policy alert active — surgical repair change       │
│            does not apply to this claim type (wellness)            │
│     ✓ No adverse state exclusions found                            │
│                                                                    │
│  ⬜ Step 7 — Final Determination                     AWAITING YOU │
│     Options: Approve / Deny / Pend / Escalate to SIU              │
│     The above findings have been captured for your records.        │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│  Summary: 2 passed  ·  3 needs review  ·  1 failed                │
│                                                                    │
│  Copilot: Steps 1–2 auto-passed. Step 3 failed — two BLOCK        │
│  rules triggered (R-001, R-002). Recommend escalating to SIU       │
│  given the 35-dependent pattern and claim velocity. Would you      │
│  like me to compile the escalation dossier?                        │
│                                                                    │
│  [Compile Dossier]  [Escalate to SIU]  [View Network]             │
└────────────────────────────────────────────────────────────────────┘
```

**Step status key:**
- 🟢 **PASS / AUTO-PASSED** — All criteria met; no examiner action needed
- 🟡 **NEEDS REVIEW** — Flags or open questions; examiner should review findings
- 🔴 **FAILED** — BLOCK rule triggered or critical failure; must be addressed
- ⬜ **AWAITING YOU** — Step 7 always requires a human decision

**Banner branching (Step 3):**  
If the member has a `suspicious_banner` active in Prudential 360, Step 3 overrides all scoring and routes directly to senior examiner review — regardless of risk score. This mirrors the existing banner-to-review workflow, but now every claim still passes through Steps 1–2 and 4–6 automatically.

**For a clean claim (risk score < 30, no rules triggered)**, the output looks like:

```
  🟢 Step 1 — Initial Review           AUTO-PASSED
  🟢 Step 2 — Eligibility Verification AUTO-PASSED
  🟢 Step 3 — Fraud Screening          AUTO-PASSED  (score: 12, LOW)
  🟢 Step 4 — Family & Network Check   AUTO-PASSED
  🟢 Step 5 — Medical Documentation    AUTO-PASSED  (all 13 checks passed)
  🟢 Step 6 — Policy & Coverage        AUTO-PASSED
  ⬜ Step 7 — Final Determination       → Fast-track eligible
  
  Summary: 6 passed · 0 needs review · 0 failed
```

In this case the Copilot surfaces the result and recommends fast-track approval — the examiner confirms in one click.

---

## Copilot Tool Set

The Copilot has access to 16 purpose-built tools organized into four categories:

### Fraud Investigation Tools

| Tool | Purpose | Key Output |
|---|---|---|
| `check_eligibility` | One-check eligibility verification (replaces 3 systems) | Policy status, member verification, coverage confirmation, issues found |
| `check_family_claims` | All claims from member + dependents in last 100 days | Claim list, total amounts, pattern analysis, comparison to normal range |
| `analyze_medical_documents` | Run all 13 DOC checks on claim documentation | Pass/fail per check, high-severity flags, plain-language summary |
| `detect_dependent_anomalies` | Dependent add patterns, age gaps, cross-member overlap | Dependent list, anomalies detected, add velocity, cross-member overlaps |
| `check_provider_patterns` | Provider claim volume, patient patterns, documentation quality | Monthly volume, unique patients, approval rate, peer comparison |
| `flag_inconsistencies` | Cross-reference all data for contradictions | Inconsistencies found **plus innocent explanations** for each |
| `find_related_claims` | Claims linked by provider, address, dependent, or pattern | Related claims by connection type, network risk level |

### Workflow Tools

| Tool | Purpose | Key Output |
|---|---|---|
| `check_workflow_tasks` | Open PMR, CBR, and TAT status | Task details, days open, TAT compliance, action items |
| `get_contact_history` | Member contact count and history | Contact timeline, CBR threshold check, frustration risk |

### Policy Intelligence Tools

| Tool | Purpose | Key Output |
|---|---|---|
| `get_policy_details` | Policy terms, age, owner/beneficiary history | Full policy record, change history, risk flags |
| `check_state_rules` | Applicable state rules and ET resolution | Governing state, ET hierarchy, exclusions, explanation |
| `check_policy_alerts` | Active policy changes affecting this claim | Applicable alerts, timing analysis, exploitation flag |
| `match_claim_to_coverage` | Compare claim details against policy terms | Coverage match, term-by-term comparison, amount determination |

### Universal Tools

| Tool | Purpose | Key Output |
|---|---|---|
| `explain_risk_score` | Full risk score breakdown with feature contributions | Score, tier, top factors, all feature weights, rules triggered |
| `run_fraud_checklist` | Execute investigation checklist (all 7 steps or single step) | Step results, pass/fail/review status, next recommended step |
| `compile_dossier` | Generate investigation summary or escalation package | Timeline, evidence, network diagram, dollar exposure, recommendation |

---

## Prototype Dataset

The prototype operates on a fully synthetic dataset designed to demonstrate all platform capabilities:

| Entity | Count | Notes |
|---|---|---|
| Employers | 10 | Mix of large, mid-size, and small |
| Members | 200 | Distributed across employers |
| Dependents | 300 | Realistic distribution + one outlier with 35 |
| Providers | 40 | Physicians, hospitals, clinics |
| Facilities | 15 | Hospitals and surgical centers |
| Addresses | 180 | Most unique, some shared for network detection |
| Policies | 200 | Varying coverage, with change histories |
| **Claims** | **500** | Distribution below |

**Claim distribution:**

| Type | Count | Typical Behavior |
|---|---|---|
| Wellness | 250 | Most auto-adjudicated, high volume |
| Hospital Indemnity | 100 | Moderate complexity |
| Accident | 100 | Requires coverage matching |
| Critical Illness | 50 | High dollar, most scrutiny |

### Embedded Fraud Scenarios (10)

| # | Scenario | Claim Type | Target Risk | Key Signals |
|---|---|---|---|---|
| 1 | 35 Dependents Added | Wellness | 94 | Dependent spike, claim velocity, benefit max gaming |
| 2 | Termination Rush | Wellness + Accident | 85 | 8 claims in final 30 days of coverage |
| 3 | Owner Change Before Critical Illness | Critical Illness | 88 | Policy owner changed 45 days before $50K claim |
| 4 | Fabricated Accident | Accident | 79 | Injury mechanism inconsistent with medical records |
| 5 | Provider Mill | Hospital Indemnity | 82 | 15 near-identical claims through one provider |
| 6 | Tampered Medical Records | Accident | 76 | Mixed fonts, erasures, typed over handwritten, Word doc |
| 7 | Duplicate Resubmission | Accident | 71 | Denied claim resubmitted with date changed by one day |
| 8 | Dependent Ring | Wellness | 87 | 3 members from different employers share 8 dependents |
| 9 | Surgical Repair Exploit | Hospital Indemnity | 65 | 4 claims filed day after outpatient surgery policy change |
| 10 | Missing Headers / B&W Records | Critical Illness | 68 | No standard headers, B&W photocopies, no vitals |

### Embedded False Positives (5)

These scenarios trigger flags but represent legitimate claims — demonstrating that the platform helps examiners avoid false accusations:

| # | Scenario | Flag Triggered | Why It's Legitimate |
|---|---|---|---|
| A | New Employee Genuine Accident | R-003 (Early Filing) | Genuine accident, unfortunate timing — 60 days after policy start |
| B | Complex Claim Multiple Contacts | R-011 (CBR Frequency) | Complex claim, member genuinely needs updates |
| C | Rural Clinic B&W Records | DOC-006 (B&W Records) | Small rural clinic with old scanner |
| D | Blended Family Dependents | R-001 (Dependent Spike) | Marriage + stepchildren, 6 dependents added in 30 days |
| E | Genuine High Hospital Bill | R-009 (Benefit Max) | Hospital bill genuinely exceeded benefit maximum |

---

## Policy Intelligence

The platform tracks active policy changes and proactively surfaces them when relevant:

### Current Active Alert: PA-001

| Field | Detail |
|---|---|
| **Effective Date** | September 18, 2025 |
| **Change** | Surgical repair benefits now paid regardless of hospital confinement |
| **Previous Rule** | Surgical repair only when confined to hospital |
| **New Rule** | Surgical repair paid for hospital or outpatient |
| **Applies To** | Hospital Indemnity claims |
| **Platform Behavior** | Proactively alerts examiner when reviewing affected claims; flags claims filed suspiciously close to the effective date |

### Extra-Territorial (ET) Rules

The platform resolves ET hierarchy automatically:
- Most recent ET supersedes the policy's governing state
- State-specific exclusions are surfaced (e.g., Florida intoxication exclusion)
- Plain-language explanation of which rules apply and why

---

## Architecture & Design Principles

### Domain-Agnostic Platform

The platform is built on a configurable architecture. The supplemental health claims domain is one configuration — the same platform supports provider fraud investigation (included in the prototype) and can be extended to additional lines of business by registering a new domain configuration.

```
┌──────────────────────────────────────────────┐
│           Claims Copilot Platform             │
│                                               │
│  ┌─────────────┐   ┌──────────────────────┐  │
│  │  Provider    │   │  Supplemental Health │  │
│  │  Fraud       │   │  Claims              │  │
│  │  Domain      │   │  Domain              │  │
│  └─────────────┘   └──────────────────────┘  │
│                                               │
│  Same platform, different tools and rules     │
└──────────────────────────────────────────────┘
```

### Examiner-First Design

The platform is designed as a **daily-use workflow tool**, not a fraud alert system. The distinction matters:

- **Fraud alert system:** Examiners use it when something looks suspicious
- **Workflow platform:** Examiners use it on every claim; fraud detection is embedded

This approach drives adoption because the platform provides value on routine claims (faster eligibility checks, automated policy matching, workflow task tracking) — not just on the rare fraud case.

### Transparent AI

The Copilot never makes final determinations. It presents evidence, explains risk scores with full feature breakdowns, and always includes innocent explanations alongside red flags. The examiner decides.

### Prototype Scope

| Component | Prototype | Production |
|---|---|---|
| Claims data | 500 synthetic claims | Live claims feed |
| Document analysis | Metadata-based simulation | OCR, image forensics, signature verification |
| Risk scoring | Weighted heuristic | ML model trained on examiner confirm/dismiss actions |
| Entity graph | Pre-computed at startup | Real-time graph database |
| Policy rules | Single active alert (PA-001) | Full policy change feed |
| State rules | Simulated ET resolution | Complete state rule engine |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| API | FastAPI (Python) |
| AI Agent | LangGraph + Amazon Bedrock (Claude) |
| Graph | NetworkX |
| Communication | WebSocket (real-time chat) |
| Data | Synthetic generation, in-memory cache |

---

## Demonstration Walkthrough

The prototype supports a guided 7-minute demonstration:

1. **The Morning View** (0:30) — Claims Queue with 500 scored and ranked claims
2. **Routine Claim** (1:30) — Process a low-risk accident claim in 2 minutes: eligibility, coverage matching, state rules, workflow tasks
3. **Policy Intelligence** (0:30) — Proactive surgical repair policy alert
4. **Flagged Claim** (0:30) — 35-dependent case: risk score breakdown, rules triggered
5. **Automated Checklist** (0:45) — 7 steps execute, step 4 goes red
6. **Document Fraud** (0:30) — Tampered records: 5 DOC flags identified
7. **Network Discovery** (0:30) — Dependent ring visualized across 3 members
8. **False Positive** (0:30) — "What am I missing?" — blended family is legitimate
9. **Escalation** (0:30) — Auto-generated SIU referral package
10. **Dashboard** (0:30) — $12,400 held, patterns detected, workflow health
11. **Domain Agnostic** (0:30) — Switch to provider fraud domain, same platform

---

*This document describes a working prototype. All data is synthetic. Document analysis operates on simulated metadata. Risk scoring uses a weighted heuristic; production deployment would incorporate machine learning trained on examiner decisions.*