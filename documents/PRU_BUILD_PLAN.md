# Claims Copilot — Prudential Supplemental Health: End-to-End Build Plan

## Executive Summary

Remake the existing life insurance fraud detection prototype into a **Prudential Supplemental Health Examiner Workflow Copilot**. The current codebase handles contestable claims, STOLI, AML, and agent misconduct for life insurance. We are **replacing** the domain entirely with supplemental health (wellness, accident, hospital indemnity, critical illness) while preserving the LangGraph agent architecture and React+FastAPI stack.

**Graph view (NetworkGraph.jsx, GraphView.jsx) is cut from this iteration.**

---

## Alignment Adjustments (from KT review)

The following adjustments were incorporated after reviewing the alignment check against original KT notes. These fix gaps between what was captured from the Prudential examiner walkthrough and what the initial plan specified.

1. **Daily volume realism** — Queue defaults to "Today" view (~23 claims), not all 500. Claims distributed across ~20 business days.
2. **R-015 Family Claim Cluster** — New rule: 3+ family members filed in 100-day window -> FLAG.
3. **Claim source tracking** — `claim_source` field added (company_site, telephonic, web, disability_portal).
4. **Expanded workflow tasks** — Added MEDICAL_RECORD_REQUEST and INITIAL_REVIEW task types. Every claim gets an INITIAL_REVIEW task.
5. **Banner-based checklist branching** — Step 3 (Fraud Screening) branches: banner=True -> full fraud review regardless of score; banner=False -> standard scoring path.
6. **System name realism** — Copilot prompt references Prudential 360, Power BI, FIS/PAS, Compass by name.
7. **Proactive vs. Reactive framing** — Copilot prompt and demo explicitly distinguish proactive (per-claim checklist) from reactive (cross-claim pattern detection) modes.

---

## What Stays, What Goes, What's New

### DELETE (files to remove)
| File | Why |
|------|-----|
| `agents/prompts_disability.py` | Disability domain removed |
| `agents/tools_contestable.py` | Contestable domain removed |
| `agents/prompts_contestable.py` | Contestable domain removed |
| `data/generate_contestable.py` | Contestable data removed |
| `frontend/src/components/NetworkGraph.jsx` | Cut this iteration |
| `frontend/src/components/GraphView.jsx` | Cut this iteration |
| `viz/ring_viz.py` | No graph viz this iteration |

### HEAVY REWRITE (keep file, gut + replace contents)
| File | What Changes |
|------|-------------|
| `cases.py` | New enums (CaseType → SUPPLEMENTAL_HEALTH instead of CONTESTABLE/STOLI/AML/AGENT_MISCONDUCT), new Case fields (risk_score, claim_type, workflow_tasks, document_flags, checklist_state) |
| `case_queue.py` | Build queue from supplemental health claims + risk scores instead of anomaly_scores + contestable |
| `main.py` | New DataContext fields, new startup pipeline (generate → rules → risk → docs → graph → patterns → queue) |
| `api.py` | Replace current endpoints with claims-oriented ones. Add `/api/claims`, `/api/claims/{id}`, `/api/claims/{id}/risk`, `/api/claims/stats`, `/api/policy-alerts`. Modify `/ws/chat/{case_id}` |
| `agents/copilot.py` | Route to supplemental health tools instead of contestable/provider tools |
| `agents/prompts.py` | Replace orchestrator/investigation/dossier prompts with supplemental health framing |
| `agents/nodes.py` | Keep LLM setup + ReAct pattern. Update tool lists and system prompts |
| `agents/graph.py` | Simplify — may not need the 3-phase orchestrator→investigation→dossier loop for chat-first copilot |
| `agents/tools_dossier.py` | New dossier template for supplemental health escalation packages |
| `agents/tools_investigation.py` | Replace provider fraud tools with supplemental health investigation tools, OR migrate to `tools_supplemental.py` and deprecate this file |
| `agents/__init__.py` | Update exports |
| `data/__init__.py` | Update exports |
| `data/generate_synthetic.py` | Replace: no more agents/policyholders/transactions. Now: employers, members, dependents, providers, facilities, addresses, policies, 500 claims |
| `data/features.py` | Replace agent/policy features with claim risk features |
| `data/anomaly.py` | Remove Isolation Forest. Risk scoring is now rules + weighted heuristic |
| `data/graph.py` | New entity types (member→dependent→provider→address→employer) instead of (agent→policyholder→policy) |
| `billing_rules/rules.json` | Replace insurance fraud rules with supplemental health rules (R-001 through R-015) |
| `billing_rules/index.py` | Same search infrastructure, new rule corpus |
| `frontend/src/App.jsx` | New nav (Queue, Copilot, Dashboard, Dossier, Activity). Remove Network/Auto Scan. New routing |
| `frontend/src/components/CaseQueue.jsx` | New columns (Risk score, Claim type tabs, PMR/CBR badges). 500 claims instead of ~15 |
| `frontend/src/components/ChatPanel.jsx` | Add checklist progress bar, claim-type-specific chips, risk score header, policy alert banner |
| `frontend/src/hooks/useCopilotChat.js` | Add checklist_update and policy_alert event types |
| `frontend/src/hooks/useInvestigation.js` | May remove or heavily simplify — the autonomous loop is secondary now |
| `frontend/src/components/DossierPanel.jsx` | Update template to show supplemental health escalation package |
| `frontend/src/components/EventTimeline.jsx` | Keep but update event types |

### NEW FILES
| File | Purpose | Est. Lines |
|------|---------|-----------|
| `domain_config.py` | Domain configuration model + Prudential supplemental health config | ~120 |
| `data/generate_supplemental.py` | 500 claims + all entities + 10 fraud scenarios + 5 false positives | ~600 |
| `intelligence/__init__.py` | Package init | ~10 |
| `intelligence/rules_engine.py` | 15 deterministic rules (R-001 to R-015 incl. Family Claim Cluster), BLOCK/FLAG/INFO severity | ~320 |
| `intelligence/risk_scoring.py` | Weighted heuristic 0-100 score with feature breakdown | ~250 |
| `intelligence/document_analysis.py` | 13 DOC checks on simulated metadata | ~200 |
| `intelligence/entity_graph.py` | Entity graph (member/dep/provider/address) + pattern detection | ~250 |
| `intelligence/checklist.py` | 7-step investigation checklist framework | ~200 |
| `agents/tools_supplemental.py` | 16 tools: 7 fraud + 2 workflow + 4 policy + 3 universal | ~600 |
| `agents/prompts_supplemental.py` | Examiner copilot system prompt | ~80 |
| `frontend/src/components/RiskDashboard.jsx` | Aggregate risk view — intercepts, distribution, patterns, workflow health | ~250 |
| `frontend/src/components/ChecklistBar.jsx` | 7-step progress bar component (extracted for reuse) | ~80 |

---

## Phased Build Order

### Phase 1: Data Foundation (no UI, no agent — just data)

**Goal:** Generate 500 realistic supplemental health claims with embedded fraud and false positives, run the full intelligence pipeline, and be able to inspect results via a simple API.

#### Step 1.1 — Domain config & data models
- Create `domain_config.py` with `DomainConfig` dataclass and `PRUDENTIAL_SUPPLEMENTAL_HEALTH` config
- Rewrite `cases.py` with new enums:
  - `CaseType`: `SUPPLEMENTAL_HEALTH` (drop CONTESTABLE, STOLI, AML, AGENT_MISCONDUCT)
  - Add `ClaimType` enum: wellness, accident, hospital_indemnity, critical_illness
  - `CasePriority`: HIGH/MEDIUM/LOW (keep)
  - `CaseStatus`: new/in_review/escalated/dismissed/approved/denied/closed
  - `Case` dataclass with: risk_score, claim_type, claim_source, rules_triggered, workflow_tasks, document_flags, checklist_state

#### Step 1.2 — Synthetic data generation
- Create `data/generate_supplemental.py` with entity dataclasses:
  - `Employer` (10), `Member` (200), `Dependent` (300, one member with 35), `Provider` (40), `Facility` (15), `Address` (180, some shared), `Policy` (200), `DocumentMetadata` (one per claim), `WorkflowTask`, `Claim` (500)
- **Temporal distribution:** Distribute 500 claims across ~20 business days (~25 claims/day). Each claim gets a `date_filed` spanning from ~4 weeks ago to today. This makes the "Today" queue view realistic.
- Claim distribution: ~250 wellness, ~100 accident, ~100 hospital_indemnity, ~50 critical_illness
- Claim ID format: WC-XXX, AC-XXX, HI-XXX, CI-XXX
- **Claim source:** Each claim gets a `claim_source` field -- one of: `company_site`, `telephonic`, `web`, `disability_portal`. Distribution weighted toward company_site (~50%) and web (~30%).
- Embed 10 fraud scenarios (from schematic: 35 deps, termination rush, owner change, fabricated accident, provider mill, tampered records, duplicate resubmission, dependent ring, surgical repair exploit, missing headers)
- Embed 5 false positives (new employee genuine accident, complex claim multiple contacts, rural clinic B&W, blended family, genuine high hospital bill)
- Generate `WorkflowTask` objects:
  - **Every claim** gets an `INITIAL_REVIEW` task (reflects real flow: claim created -> task assigned)
  - Claims requiring medical records get `MEDICAL_RECORD_REQUEST` task (with requested/received status and days_waiting)
  - 15% of claims get `PMR`, 10% get `CBR`, 8% approaching/past TAT
- `generate_supplemental_data()` → returns dict of all entity lists

#### Step 1.3 — Intelligence pipeline
- Create `intelligence/__init__.py`
- Create `intelligence/rules_engine.py`:
  - 15 `Rule` definitions (R-001 through R-015) with severity (BLOCK/FLAG/INFO)
  - **R-015 (NEW):** "Family Claim Cluster" -- 3+ family members filed claims in 100-day window -> FLAG severity. Explanation template: "{count} family members filed claims in last 100 days (threshold: 3)"
  - `run_rules_engine(claim, context)` → evaluates all rules, returns triggered results with explanations
  - Each rule is a simple if/then function, not ML
- Create `intelligence/risk_scoring.py`:
  - 7 feature categories: policy (0.15), member (0.20), claim (0.20), provider (0.15), network (0.15), temporal (0.10), rules_boost (0.05)
  - `score_claim(claim, context)` → returns `RiskBreakdown` (total 0-100, tier, feature_contributions, top_factors)
  - Normalize each feature to 0-1, multiply by weight, sum, cap at 100
- Create `intelligence/document_analysis.py`:
  - 13 `DocumentCheck` definitions (DOC-001 through DOC-013)
  - `run_document_checks(doc_metadata)` → returns results for all 13 checks
  - Simple field comparisons against metadata flags
- Create `intelligence/entity_graph.py`:
  - `build_supplemental_health_graph(data)` → NetworkX DiGraph with member/dependent/provider/facility/address/employer/policy nodes
  - `detect_patterns(graph)` → pre-compute dependent rings, provider clusters, shared address groups

#### Step 1.4 — Wire startup pipeline
- Rewrite `main.py`:
  - New `DataContext` fields: supplemental_data, supplemental_claims, supplemental_graph, detected_patterns, case_queue, domain_config
  - `initialize_data()`:
    1. `generate_supplemental_data()` → entities + 500 claims
    2. For each claim: `run_rules_engine()` → tag rules_triggered
    3. For each claim: `score_claim()` → assign risk_score + tier
    4. For each claim: `run_document_checks()` → tag document_flags
    5. `build_supplemental_health_graph()` → entity graph
    6. `detect_patterns()` → network patterns
    7. `build_case_queue()` → sorted case list
    8. Pickle cache
  - Remove existing provider fraud data generation (or keep behind a flag — recommend removing for clean rebuild)
- Rewrite `case_queue.py`:
  - `build_case_queue(supplemental_claims)` → creates `Case` objects from all 500 claims
  - Sort: HIGH first, then risk_score descending

#### Step 1.5 — Verify data foundation
- Run `main.py` startup, confirm:
  - 500 claims generated
  - 10 fraud scenarios score HIGH (>65)
  - 5 false positives score MEDIUM (30-64) with legitimate explanations
  - ~450 claims score LOW (<30)
  - Rules trigger correctly on fraud scenarios
  - Document flags trigger on scenarios 5, 6, 10
  - Entity graph has ~900+ nodes, patterns detected
- Add a simple smoke test or print validation

---

### Phase 2: API Layer

**Goal:** Expose all data through REST endpoints. Frontend can fetch claims queue, claim details, risk breakdowns, and dashboard stats.

#### Step 2.1 — Core claims endpoints
- Rewrite `api.py`:
  - `GET /api/claims` -- returns claims with filtering (claim_type, priority, risk_tier, status, **date_range**). Supports `date_range=today|this_week|all` (default: today). Includes counts for all tab groupings (date, type, risk tier).
  - `GET /api/claims/{claim_id}` — full claim detail (risk breakdown, rules, docs, tasks, checklist state)
  - `POST /api/claims/{claim_id}/status` — update claim status (approve, deny, escalate, dismiss)
  - `GET /api/health` — keep

#### Step 2.2 — Intelligence endpoints
  - `GET /api/claims/{claim_id}/risk` — risk score breakdown with feature contributions
  - `GET /api/claims/{claim_id}/rules` — triggered rules with explanations
  - `GET /api/claims/{claim_id}/documents` — document analysis results (all 13 DOC checks)
  - `GET /api/claims/{claim_id}/checklist` — checklist state with results per step

#### Step 2.3 — Workflow & policy endpoints
  - `GET /api/claims/{claim_id}/tasks` — open PMR, CBR, TAT status
  - `GET /api/policy-alerts` — active policy changes
  - `GET /api/config` — current domain configuration

#### Step 2.4 — Dashboard endpoint
  - `GET /api/claims/stats` — aggregate stats:
    - intercepts (count + held amount)
    - risk_distribution (HIGH/MEDIUM/LOW counts)
    - top_rules_triggered (rule_id + count)
    - patterns_detected (from entity graph)
    - workflow_health (open PMR, pending CBR, past TAT)

#### Step 2.5 — Verify API
- Start server, hit each endpoint with curl/httpie
- Confirm claims queue returns 500 with correct filters
- Confirm risk breakdown has meaningful feature contributions

---

### Phase 3: Copilot Agent & Tools

**Goal:** Chat with the copilot about any claim. The copilot calls tools to retrieve claim data, run checks, and provide analysis.

#### Step 3.1 — Supplemental health tools
- Create `agents/tools_supplemental.py` with 16 tools:
  - **Fraud tools (7):** `check_eligibility`, `check_family_claims`, `analyze_medical_documents`, `detect_dependent_anomalies`, `check_provider_patterns`, `flag_inconsistencies`, `find_related_claims`
  - **Workflow tools (2):** `check_workflow_tasks` (includes INITIAL_REVIEW, MEDICAL_RECORD_REQUEST, PMR, CBR, TAT status + medical_record_status with requested/received/days_waiting), `get_contact_history`
  - **Policy tools (4):** `get_policy_details`, `check_state_rules`, `check_policy_alerts`, `match_claim_to_coverage`
  - **Universal tools (3):** `explain_risk_score`, `run_fraud_checklist`, `compile_dossier`
- Each tool takes `claim_id`, looks up data via `_context` global, returns structured dict
- `set_context(ctx)` to inject DataContext

#### Step 3.2 — Copilot system prompt
- Create `agents/prompts_supplemental.py`:
  - `SUPPLEMENTAL_COPILOT_PROMPT` — framed as examiner workflow assistant
  - Productivity first, fraud detection second
  - All 16 tools documented with when to use each
  - Response style guidance (lead with actionable, specific numbers, innocent explanations for red flags)
  - **System name realism:** Reference Prudential 360, Power BI, FIS/PAS, Compass by name. Example: "The check_eligibility tool consolidates what you'd find across Prudential 360, Power BI, and FIS/PAS into one response."
  - **Proactive vs. Reactive framing:** Include in prompt:
    - PROACTIVE mode: Every claim triggers the checklist. Most auto-pass. Flagged claims get examiner review. Catches issues BEFORE payment.
    - REACTIVE mode: Patterns detected across claims after the fact. Dashboard surfaces dependent rings, provider mills, termination rushes. Catches what individual claim review misses.
  - **Medical record request awareness:** When discussing claims still awaiting medical records, note the MEDICAL_RECORD_REQUEST status and days waiting.
#### Step 3.3 — Copilot agent
- Rewrite `agents/copilot.py`:
  - `CopilotSession` dataclass with session_id, case_id, messages, tools_called, checklist_state
  - `get_or_create_session(case_id)` → session management
  - `get_tools_for_case_type("supplemental_health")` → returns ALL_SUPPLEMENTAL_TOOLS
  - `handle_analyst_message(case_id, analyst_message, ws)` → ReAct agent invocation with message history
  - Use `create_react_agent(llm, tools)` from LangGraph (same pattern as current codebase)

#### Step 3.4 — Checklist framework
- Create `intelligence/checklist.py`:
  - 7 `ChecklistStep` definitions:
    1. Initial Review (auto: check claim exists, basic data complete, INITIAL_REVIEW task exists)
    2. Eligibility Verification (auto: policy active, coverage matches)
    3. Fraud Screening -- **BRANCHES ON SUSPICIOUS BANNER:**
       - `member.suspicious_banner == True` -> run ALL fraud checks regardless of risk score, flag for senior examiner, check for existing Prudential review
       - `member.suspicious_banner == False` -> standard rules engine + risk scoring, only escalate if risk > threshold or BLOCK rules trigger
       - Auto-pass: risk score < 30 AND no BLOCK rules AND no suspicious banner
    4. Family & Network Check (auto: no dependent anomalies, no network flags, R-015 family cluster not triggered)
    5. Medical Documentation Review (auto: all DOC checks pass, medical records received per MEDICAL_RECORD_REQUEST task)
    6. Policy & Coverage Determination (auto: coverage matches, no state conflicts)
    7. Final Determination (always manual — approve/deny/escalate)
  - `run_checklist_step(step_number, claim_id, context)` → calls tools, evaluates auto-pass
  - `run_full_checklist(claim_id, context)` → runs all 7 steps

#### Step 3.5 — Dossier modifications
- Update `agents/tools_dossier.py`:
  - New `compile_dossier()` template for supplemental health escalation packages
  - Sections: Claim Summary, Risk Assessment, Rules Triggered, Document Analysis, Network Analysis, Checklist Results, Recommended Action
  - Keep `assess_evidence()` logic adapted to supplemental health

#### Step 3.6 — Update graph.py and nodes.py
- Simplify `agents/graph.py`:
  - For chat mode, the copilot is a single ReAct agent (no orchestrator→investigation→dossier loop needed)
  - Keep the autonomous investigation path available but secondary
- Update `agents/nodes.py`:
  - Keep `get_bedrock_llm()` and LLM setup
  - Update system prompts to supplemental health
  - Remove contestable/STOLI/AML-specific logic

#### Step 3.7 — Chat WebSocket
- Update `api.py` WebSocket `/ws/chat/{claim_id}`:
  - On connect: send case summary, risk score, rules triggered, open workflow tasks, checklist state
  - Message handling: pass to `handle_analyst_message()`, stream tool calls and responses
  - Add `checklist_update` event type (step completed/failed)
  - Add `policy_alert` event type (proactive alert when claim affected by PA-001)

#### Step 3.8 — Verify copilot
- Open WebSocket to a HIGH risk claim (WC-247, 35 dependents)
- Send: "Why was this flagged?" — should call `explain_risk_score` and return specific data
- Send: "Run the full checklist" — should execute 7 steps and report results
- Send: "What am I missing?" — should provide innocent explanations
- Test on a LOW risk claim — should be fast eligibility/coverage check

---

### Phase 4: Frontend

**Goal:** Complete examiner UI with claims queue as landing page, chat copilot, risk dashboard, and dossier view.

#### Step 4.1 — App shell & navigation
- Rewrite `App.jsx`:
  - Navigation: Queue (default), Copilot, Dashboard, Dossier, Activity
  - Remove: Network, Auto Scan
  - State: `selectedCase`, `view` ('queue' default)
  - Flow: Queue → click claim → Copilot → can switch to Dashboard/Dossier → Back to Queue

#### Step 4.2 — Claims Queue
- Rewrite `CaseQueue.jsx`:
  - Fetch from `GET /api/claims`
  - **Date-based tabs (PRIMARY -- matches examiner's real daily volume):**
    - `[Today (23)] [This Week (112)] [All (500)]`
    - Default to "Today" -- the examiner's actual working view is ~20-25 claims/day
    - 500 total is the full dataset (~1 month). Dashboard and patterns use all 500. Queue defaults to today.
  - **Claim type sub-tabs:** Wellness, Accident, Hospital Ind., Critical Illness
  - Risk filter chips: HIGH (red), MEDIUM (yellow), LOW (gray)
  - Columns: Claim#, Type, Member, Flag/Task, Risk (with color dot + score), Status
  - Flag/Task column shows: fraud flags (🚩) alongside workflow tasks (📋 PMR, ☎️ CBR, 📄 Med Records Pending)
  - Row click → `onSelectCase(case)` → navigate to copilot
  - Refresh button

#### Step 4.3 — ChatPanel with checklist
- Rewrite `ChatPanel.jsx`:
  - **Header:** Claim ID, member name, risk score (color-coded), claim type badge, employer, coverage dates
  - **Alert banner:** Rules triggered count, open PMR/CBR status
  - **Checklist progress bar:** 7 steps, color-coded (green=pass, red=fail, yellow=needs review, gray=not run)
  - **Messages area:** Same as current but with tool call indicators
  - **Quick action chips by claim type:**
    - All: Run Full Checklist, Check Eligibility, Workflow Tasks, Escalate
    - Wellness: Dependent Check, Claim History, Auto-Adj Review
    - Accident: Match to Policy, Accident Details, State Rules
    - Hospital Indemnity: Admission/Discharge, Provider Check, Policy Terms
    - Critical Illness: Medical Records, Document Analysis, Policy Check
  - **Input bar:** Textarea + Send button (same as current)
  - WebSocket: `/ws/chat/{claimId}`

#### Step 4.4 — Risk Dashboard
- Create `RiskDashboard.jsx`:
  - Fetch from `GET /api/claims/stats`
  - Cards:
    - Auto-Adjudication Intercepts (count + held amount)
    - Risk Distribution (HIGH/MEDIUM/LOW with counts and percentages)
    - Top Rules Triggered (rule ID + name + count)
    - Patterns Detected (dependent ring, provider cluster, termination rush, doc tampering)
    - Workflow Health (open PMR, pending CBR, past TAT)
  - Pattern items clickable → navigate to relevant claim

#### Step 4.5 — Update useCopilotChat hook
- Add to `useCopilotChat.js`:
  - New state: `checklistState`, `policyAlerts`
  - New event handlers: `checklist_update` → update step status, `policy_alert` → add to alerts
  - New actions: `runChecklist()`, `runChecklistStep(step)`
  - Keep existing: messages, isThinking, isConnected, sendMessage

#### Step 4.6 — Update supporting components
- Update `DossierPanel.jsx`: New supplemental health dossier template rendering
- Update `EventTimeline.jsx`: New event types for supplemental health
- Keep `StatsBar.jsx` and `Header.jsx` with minor updates

#### Step 4.7 — Delete graph components
- Remove `NetworkGraph.jsx` and `GraphView.jsx`
- Remove nav entries and imports for Network

#### Step 4.8 — Verify frontend
- Start frontend dev server
- Claims Queue loads with 500 claims, tabs/filters work
- Click HIGH risk claim → ChatPanel opens with risk score + checklist
- Chat works end-to-end (type question → get answer with tool calls)
- Quick action chips send correct prompts
- Dashboard shows aggregate stats
- Dossier generates for escalated claim

---

### Phase 5: Cleanup & Polish

#### Step 5.1 — Remove old domain files
- Delete `agents/prompts_disability.py`
- Delete `agents/prompts_contestable.py`  
- Delete `agents/tools_contestable.py`
- Delete `data/generate_contestable.py`
- Delete `viz/ring_viz.py`
- Clean up any imports referencing deleted files
- Update `requirements.txt` if any packages are no longer needed (e.g., pyvis)

#### Step 5.2 — Update billing_rules
- Replace `billing_rules/rules.json` with supplemental health rules:
  - R-001 through R-015 rule definitions (R-015 = Family Claim Cluster)
  - Fraud patterns: DEPENDENT_ABUSE, AUTO_ADJ_GAMING, DOCUMENT_TAMPERING, POLICY_MANIPULATION, PROVIDER_MILL
  - Each rule with: fraud_indicators, related_rules, summary, rule_text

#### Step 5.3 — Update README.md
- Rewrite to describe Prudential Supplemental Health Copilot
- New architecture description, setup instructions, demo flow

#### Step 5.4 — Demo mode / demo_runner
- Update `demo_runner.py` for supplemental health demo scenario
- Hardcode the WC-247 (35 dependents) investigation as the showcase
- Or remove demo_runner if not needed — the ChatPanel IS the demo now

---

## File Dependency Graph (build order)

```
domain_config.py ─────────────────────┐
cases.py ─────────────────────────────┤
                                      │
data/generate_supplemental.py ────────┤
                                      │
intelligence/__init__.py              │
intelligence/rules_engine.py ─────────┤
intelligence/risk_scoring.py ─────────┤
intelligence/document_analysis.py ────┤
intelligence/entity_graph.py ─────────┤
intelligence/checklist.py ────────────┤
                                      │
main.py (rewrite) ◄───────────────────┘
case_queue.py (rewrite) ◄─────────────┘
                                      │
agents/tools_supplemental.py ─────────┤  (depends on data models + intelligence)
agents/prompts_supplemental.py        │
agents/copilot.py (rewrite) ──────────┤
agents/tools_dossier.py (update) ─────┤
agents/nodes.py (update) ─────────────┤
agents/graph.py (simplify) ───────────┤
agents/__init__.py (update) ──────────┤
                                      │
api.py (rewrite) ◄────────────────────┘  (depends on everything above)
                                      │
frontend/src/hooks/useCopilotChat.js ─┤  (depends on API contract)
frontend/src/App.jsx ─────────────────┤
frontend/src/components/CaseQueue.jsx ┤
frontend/src/components/ChatPanel.jsx ┤
frontend/src/components/RiskDashboard.jsx
frontend/src/components/DossierPanel.jsx
frontend/src/components/ChecklistBar.jsx
```

---

## Key Design Decisions

1. **Full replace, not additive.** The current codebase is life insurance fraud (contestable, STOLI, AML). We are not maintaining dual domains — we're replacing with supplemental health. Simpler, cleaner, faster to build.

2. **Graph view cut.** No NetworkGraph or GraphView components this iteration. Entity graph still exists in the backend for `find_related_claims` tool — just no dedicated visualization page.

3. **Autonomous investigation loop is secondary.** The LangGraph orchestrator→investigation→dossier loop exists but the primary UX is the chat copilot. The autonomous path can be triggered via "Run Full Checklist" but the examiner is in control.

4. **Intelligence pipeline runs at startup.** All 500 claims are pre-scored (rules + risk + docs + patterns). The copilot tools read pre-computed results. No runtime ML inference.

5. **Simulated document analysis.** DOC-001 through DOC-013 check metadata flags, not real documents. The framework demonstrates WHAT would be checked. Copilot responses explicitly say "based on document metadata."

6. **False positives are intentional.** 5 scenarios that trigger rules but are legitimate. The copilot's "What am I missing?" response surfaces innocent explanations. This is the trust differentiator.

7. **One WebSocket per claim.** `/ws/chat/{claim_id}` handles all copilot interaction for a claim. Checklist updates, tool calls, and policy alerts all flow through the same connection.

---

## Risk / Watch Items

- **Bedrock LLM availability:** The copilot depends on AWS Bedrock. If the model is slow or unavailable, chat will stall. Keep timeouts reasonable.
- **Daily queue view:** Default view is "Today" (~23 claims) so queue perf shouldn't be an issue. "All" tab loads 500 -- add pagination if needed.
- **Tool output size:** Some tools (e.g., `check_family_claims` on the 35-dependent case) could return large payloads. Cap tool output at 2000 chars (existing pattern in codebase).
- **Pickle cache invalidation:** When data generation logic changes, stale cache causes confusion. Add a version hash to cache filename.
- **Demo timing:** The 7-step checklist involves 7+ tool calls. Each tool call hits Bedrock. Budget 30-60 seconds for full checklist run. Pre-warm the model.
- **Unvalidated specifics:** DOC-001->DOC-013 checks and rule thresholds (e.g., >5 deps in 30 days, >10 claims/quarter) are reasonable inferences, not captured verbatim from Prudential's OneNote checklist. Be transparent in demos: "These checks are based on what we captured. We'd calibrate to your full checklist during implementation."

---

## Demo Talking Points (from alignment review)

These are specific callouts to hit during the demo based on KT gaps:

1. **"One check replaces three screens"** -- When showing `check_eligibility`, say: "This replaces checking Prudential 360, then Power BI, then falling back to FIS/PAS."
2. **"Two modes"** -- At some point in the demo, explicitly say: "Proactive: the checklist catches individual claim issues before payment. Reactive: the dashboard catches patterns across claims that no individual review would find. Today you have proactive (OneNote checklist) but no reactive. We give you both."
3. **"Daily queue, not a backlog"** -- When showing the Claims Queue, note: "This is today's 23 claims, sorted by risk. Not a wall of 500."
4. **"Banner-aware"** -- When showing a claim with suspicious_banner: "The system knows this member already has institutional suspicion. It runs the full fraud workup regardless of the computed risk score."
