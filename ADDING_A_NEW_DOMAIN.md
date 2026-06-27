# Adding a New Insurance Domain (e.g. Car Insurance)

This guide explains how the Claims Copilot codebase is organized by *domain* and gives a
step-by-step recipe for adding a brand-new line of business (e.g. **car insurance**) by
cloning the existing **Zurich Travel Guard** ("travel") implementation.

It is written for the `claims-copilot/` directory. All paths below are relative to it
unless noted otherwise.

---

## 1. How domains work today

The system currently ships **two** domains, selected at runtime by the `DOMAIN_MODE`
environment variable:

| `DOMAIN_MODE` | Domain | Claim ID prefixes | Data size |
|---|---|---|---|
| `supplemental` | Prudential Supplemental Health | WC / AC / HI / CI | 500 claims |
| `travel` (default) | Zurich Travel Guard | TC / TI / ME / BL / TD | 200 claims |

`DOMAIN_MODE` is read in **[main.py](claims-copilot/main.py)**:

```python
DOMAIN_MODE = os.getenv("DOMAIN_MODE", "travel")   # main.py:32
```

It is set by the launch scripts (`set DOMAIN_MODE=travel` in
[start_travel.bat](claims-copilot/start_travel.bat) / [start.bat](claims-copilot/start.bat))
and also defaulted in `.env` (`DOMAIN_MODE=travel`). `load_dotenv(..., override=False)` means
**an OS env var wins over `.env`**, and an unset value falls back to the `"travel"` default.

> ⚠️ **The single biggest gotcha:** almost every domain switch in the code is a **binary
> `if DOMAIN_MODE == "travel": ... else: ...`** — and the `else` branch always means
> *supplemental*. So if you add `DOMAIN_MODE=car` without editing those branches, the app
> will silently fall through to **supplemental** (you'll see HI-xxx / AC-xxx claims and the
> medical checklist). Adding a domain is mostly a matter of converting every one of these
> binary branches into a 3-way dispatch. See §4 for the full list.

### The data flow (same for every domain)

```
generate_<domain>.py        →  synthetic claims + entities (fixed random seed)
        ↓
rules_engine_<domain>.py    →  deterministic BLOCK/FLAG/INFO rules per claim
        ↓
risk_scoring_<domain>.py    →  0–100 score + HIGH/MEDIUM/LOW tier (features 40% + rules 60%)
        ↓
case_queue_<domain>.py      →  ranked examiner queue (priority tier, then risk desc)
        ↓
DataContext  (pickled to data_cache_*.pkl)   ← built in main.initialize_<domain>_data()
        ↓
api.py  (FastAPI)  →  /api/config, /api/claims, /api/claims/{id}/checklist, /ws/chat, ...
        ↓
frontend/  (React, data-driven off /api/config + /api/claims)
        ↓
agents/  (LangGraph copilot: prompts_<domain>.py + tools_<domain>.py)
```

Everything downstream of `DataContext` is **data-driven**: the frontend, the queue, and the
dossier all read whatever the loaded context contains. The domain-specific work is therefore
concentrated in the generator / rules / scoring / checklist / queue / prompts / tools files,
plus the handful of `DOMAIN_MODE` dispatch sites.

---

## 2. The contract every domain must satisfy

A domain is "complete" when it produces a `DataContext`
([main.py:38](claims-copilot/main.py#L38)) with these fields populated:

```python
@dataclass
class DataContext:
    domain_config: DomainConfig          # from domain_config.py
    supplemental_data: Dict              # the full generator output dict (named "supplemental_*"
    supplemental_claims: List            #   for legacy reasons — it holds whatever domain's data)
    supplemental_graph: nx.DiGraph       # entity graph (can be minimal)
    detected_patterns: List
    case_queue: List[Case]               # the ranked queue the UI shows
    claim_rules: Dict[str, List[RuleResult]]
    claim_risk_scores: Dict[str, RiskBreakdown]
    claim_doc_results: Dict[str, list]   # vision/document check results per claim
```

> 📝 The field names say `supplemental_*` even in travel mode — they are **domain-neutral
> containers**, not health-specific. Don't be misled; you reuse the same field names.

These are the shared shapes your new files must emit:

- **`RuleResult`** — `rule_id, rule_name, severity ("BLOCK"|"FLAG"|"INFO"), triggered: bool,
  explanation, details: dict`
- **`RiskBreakdown`** — `total_score (0–100), tier ("HIGH"|"MEDIUM"|"LOW"),
  feature_contributions, top_factors, rules_boost`
- **`ChecklistStepResult`** — `step_number, step_name, status
  ("pass"|"fail"|"needs_review"|"not_run"|"error"), auto_passed: bool, findings, details`
- **`Case`** — built by the queue builder; the API serializes it for the frontend.

---

## 3. Files to CREATE (clone the `*_travel.*` set)

For a `car` domain, create these by copying the travel file and renaming symbols:

| New file | Clone of | Key symbols to rename |
|---|---|---|
| `data/generate_car.py` | [data/generate_travel.py](claims-copilot/data/generate_travel.py) | `generate_car_data()`, `CarClaim`, entity dataclasses, `_inject_fraud_scenarios`, `_inject_false_positives` |
| `intelligence/rules_engine_car.py` | [intelligence/rules_engine_travel.py](claims-copilot/intelligence/rules_engine_travel.py) | `ALL_CAR_RULES`, `run_car_rules_engine()`, `r001_…` functions |
| `intelligence/risk_scoring_car.py` | [intelligence/risk_scoring_travel.py](claims-copilot/intelligence/risk_scoring_travel.py) | `score_car_claim()` |
| `intelligence/checklist_car.py` | [intelligence/checklist_travel.py](claims-copilot/intelligence/checklist_travel.py) | `CHECKLIST_STEPS`, `run_full_checklist()`, `run_checklist_step()`, `_step_*` |
| `case_queue_car.py` | [case_queue_travel.py](claims-copilot/case_queue_travel.py) | `build_car_case_queue()`, `CLAIM_TYPE_MAP` |
| `agents/prompts_car.py` | [agents/prompts_travel.py](claims-copilot/agents/prompts_travel.py) | `CAR_COPILOT_PROMPT` |
| `agents/tools_car.py` | [agents/tools_travel.py](claims-copilot/agents/tools_travel.py) | `ALL_CAR_TOOLS`, `set_context()`, individual `@tool` functions |
| `start_car.bat` | [start_travel.bat](claims-copilot/start_travel.bat) | `set DOMAIN_MODE=car` |

### 3a. Data generator (`data/generate_car.py`)

Mirror [generate_travel.py](claims-copilot/data/generate_travel.py):

- Fix the random seed (`random.seed(...)`) so the demo is deterministic.
- Define entity dataclasses. Car equivalents of the travel entities:
  - `Traveler` → `Insured` (driver/policyholder)
  - `Destination` → `Vehicle` (with `vin`, `make`, `model`, `year`, `acv`/blue-book value, `salvage_flag`)
  - `Hotel`/`MedicalProvider` → `RepairShop` (with `on_watchlist`, `verified`, `in_network`)
  - `TravelPolicy` → `CarPolicy` (collision/comprehensive/liability coverage limits, deductible)
  - `BookingRecord`/`FlightRecord` → `RepairEstimate` / `PoliceReport`
  - `TravelClaim` → `CarClaim` with `claim_type ∈ {collision, comprehensive, theft, liability, medical_payments}`
- Return a **dict** keyed by entity name (this becomes `DataContext.supplemental_data`). Travel returns:
  `claims, travelers, companions, destinations, airlines, hotels, providers, policies, bookings, flights, workflow_tasks, documents, travel_agents`.
  Car would return e.g.:
  `claims, insureds, vehicles, repair_shops, policies, estimates, police_reports, workflow_tasks, documents`.
- Inject 4–6 **hero fraud scenarios** with hardcoded claim IDs (so the demo always shows them)
  and 2–3 **false positives** (high-risk-looking claims that resolve clean — these teach examiner
  judgment). See `_inject_fraud_scenarios()` / `_inject_false_positives()` in travel for the pattern.
  Set `claim.fraud_scenario` / `claim.false_positive_scenario` markers.

### 3b. Rules engine (`intelligence/rules_engine_car.py`)

Each rule is `def rNNN_name(claim, context) -> RuleResult`. Register them in `ALL_CAR_RULES`
and expose `run_car_rules_engine(claim, context)`. Example car rules:

- R-001 Policy effective after incident date → **BLOCK**
- R-002 No repair estimate on file → **BLOCK**
- R-003 Duplicate / resubmission → **BLOCK**
- R-004 Repair shop on fraud watchlist → **BLOCK**
- R-005 Estimate > 3× comparable for vehicle ACV → **FLAG**
- R-006 Claim amount exceeds vehicle ACV (total-loss padding) → **FLAG**
- R-007 Insured has ≥ 5 claims in 12 months (serial claimer) → **FLAG**
- R-008 Major collision with no police report → **FLAG**
- R-009 Damage photo evidence submitted → **BLOCK** for forensic review *(see the R-011 pattern in travel)*

> **Severity drives the score.** In scoring, each triggered **BLOCK ≈ +20** points and each
> **FLAG ≈ +8** (capped at +60). Choose severities deliberately.

### 3c. Risk scoring (`intelligence/risk_scoring_car.py`)

Keep the travel formula: `total = (feature_score + rules_boost) × 100`, clamped 0–100, tiers
`HIGH ≥ 60 / MEDIUM 30–59 / LOW < 30`. Reweight the 40% feature block for car (e.g. claim amount
vs. ACV, repair-shop risk, insured claim frequency, photo-evidence presence). The travel file's
**R-011 photo-evidence floor** ([risk_scoring_travel.py](claims-copilot/intelligence/risk_scoring_travel.py))
is a worked example of forcing specific claims to the top of the queue.

### 3d. Checklist (`intelligence/checklist_car.py`)

Define `CHECKLIST_STEPS` (list of `(num, name)`), one `_step_*` function each returning a
`ChecklistStepResult`, and `run_checklist_step()` / `run_full_checklist()`. Steps read from the
`context` dict that `api.py` builds (see §4). If a step inspects evidence images, read
`context["claim_doc_results"][claim_id]` — see how travel Step 2 ("Trip Documentation") consumes
vision results.

### 3e. Case queue (`case_queue_car.py`)

`build_car_case_queue(claims, claim_risk_scores, claim_rules, data) -> List[Case]`. Map claim-type
strings to `ClaimType` enum via `CLAIM_TYPE_MAP`, assign `CasePriority` from the risk tier, and
sort by `(priority, -risk_score)`.

### 3f. Agent prompt & tools

- `agents/prompts_car.py`: define `CAR_COPILOT_PROMPT` describing the examiner role, the available
  tools, and car-specific fraud patterns.
- `agents/tools_car.py`: module-level `_context`, a `set_context(ctx)` setter, ~10–13 `@tool`
  functions, and an `ALL_CAR_TOOLS` list. Each tool reads `_context` and returns a dict.

---

## 4. Files to MODIFY (the dispatch sites)

These are the **binary branches** that must become 3-way. Search the repo for
`DOMAIN_MODE == "travel"` to find them all.

### 4.1 `cases.py` — add enum values
- `CaseType`: add `CAR_INSURANCE = "car_insurance"`.
- `ClaimType`: add `COLLISION`, `COMPREHENSIVE`, `THEFT`, `LIABILITY`, `MEDICAL_PAYMENTS`.

### 4.2 `domain_config.py` — add a `DomainConfig`
Add a `CAR_INSURANCE = DomainConfig(...)` block alongside `ZURICH_TRAVEL_GUARD`
([domain_config.py:81](claims-copilot/domain_config.py#L81)). Fill in `name`, `display_name`,
`claim_types`, `claim_id_prefixes`, `claim_sources` + weights, `risk_tiers`,
`workflow_task_types`, `checklist_steps`, `system_references`, `entity_types`. **`display_name`
and `claim_types` flow straight to the frontend via `/api/config`.**

### 4.3 `main.py` — add `initialize_car_data()`
Clone `initialize_travel_data()` ([main.py:247](claims-copilot/main.py#L247)):
- Cache file: `data_cache_v1_car.pkl` (each domain has its **own** cache file — they don't collide).
- Import `generate_car_data`, `run_car_rules_engine`, `score_car_claim`, `build_car_case_queue`.
- Build the `context_dict` with car entity keys, run rules, score, build the queue, populate
  `DataContext`, and `pickle.dump` it.
- The cache is loaded blindly if the file exists — **there is no domain stamp inside the pickle.**
  When you change generation/scoring, delete the stale `.pkl` or call with
  `force_regenerate=True`, or you'll keep loading old data. (This is exactly what causes "I still
  see the old claims" — see §6.)

### 4.4 `api.py` — convert every branch to 3-way
- Checklist import (top of file, ~L28): `if travel … elif car … else supplemental`.
- `CHECKLIST_DESCRIPTIONS` (~L79): add a car dict.
- Add `_build_car_checklist_ctx(claim_id)` mirroring `_build_travel_checklist_ctx`
  ([api.py:57](claims-copilot/api.py#L57)) with car entity keys; run vision via
  `run_vision_document_checks` when a claim image exists.
- `lifespan()` (~L101): add `elif DOMAIN_MODE == "car": data_ctx = initialize_car_data();
  set_car_context(data_ctx)`.
- App title `_APP_TITLE` (~L133): add the car title.
- The `/api/claims/{id}/checklist` endpoint (~L399): dispatch to `_build_car_checklist_ctx`.

### 4.5 `agents/copilot.py` — prompt & tools selection
Two binary branches to extend ([copilot.py:37](claims-copilot/agents/copilot.py#L37) and
[copilot.py:59](claims-copilot/agents/copilot.py#L59)):
```python
if DOMAIN_MODE == "travel":
    from agents.prompts_travel import TRAVEL_COPILOT_PROMPT as PROMPT
elif DOMAIN_MODE == "car":
    from agents.prompts_car import CAR_COPILOT_PROMPT as PROMPT
else:
    from agents.prompts_supplemental import SUPPLEMENTAL_COPILOT_PROMPT as PROMPT
```
Do the same for `get_tools_for_case_type()` → `ALL_CAR_TOOLS`.

### 4.6 `intelligence/document_vision.py` — vision prompt
Add a `_CAR_VISION_PROMPT` (forensic checks for vehicle-damage photos, repair estimates, police
reports) and extend the selection near the bottom of the file:
```python
_DOMAIN_MODE = os.getenv("DOMAIN_MODE", "travel")
if _DOMAIN_MODE == "supplemental":
    _VISION_PROMPT = _SUPPLEMENTAL_VISION_PROMPT
elif _DOMAIN_MODE == "car":
    _VISION_PROMPT = _CAR_VISION_PROMPT
else:
    _VISION_PROMPT = _TRAVEL_VISION_PROMPT
```
Evidence images live in the workspace-level **`images/`** folder and are matched to a claim by
ID: `claim_id` → lowercase-alphanumeric. So `COL-017` → `images/col017.png` (plus numbered
variants `col017_1.png`, …). No DB wiring needed — just name the file to match the claim ID.

### 4.7 `frontend/src/App.jsx` — (optional) dynamic title
The header text is hardcoded to "Zurich Travel Guard". The frontend already fetches `/api/config`;
render `config.display_name` instead of the literal string. The queue, claim-type chips, and
checklist are already data-driven and need **no** changes.

---

## 5. Quick checklist

**Create:** `data/generate_car.py`, `intelligence/rules_engine_car.py`,
`intelligence/risk_scoring_car.py`, `intelligence/checklist_car.py`, `case_queue_car.py`,
`agents/prompts_car.py`, `agents/tools_car.py`, `start_car.bat`.

**Modify:** `cases.py` (enums) · `domain_config.py` (config) · `main.py` (`initialize_car_data`) ·
`api.py` (3-way dispatch ×5) · `agents/copilot.py` (prompt + tools) ·
`intelligence/document_vision.py` (vision prompt) · `frontend/src/App.jsx` (optional title).

**Data/images:** add hero fraud + false-positive scenarios in the generator; drop evidence
images into `images/` named after the claim ID (`col017.png`).

---

## 6. Verify it works

```bash
# 1. Generate + cache the car data fresh (deletes any stale assumptions)
cd claims-copilot
DOMAIN_MODE=car python -c "from main import initialize_car_data; ctx=initialize_car_data(force_regenerate=True); \
  print('top:', [(c.case_id, c.risk_score) for c in ctx.case_queue[:5]])"

# 2. Boot the API in car mode and confirm the domain
DOMAIN_MODE=car python api.py        # then, in another shell:
curl -s http://localhost:8000/api/config        # → name should be "car_insurance"
curl -s http://localhost:8000/api/health         # → claims_count matches your generator
curl -s http://localhost:8000/api/claims | grep -oE '"claim_id":"[^"]+"' | head   # → COL-/COMP-/THEFT- prefixes
```

> 🔧 **If `/api/config` still says `prudential_supplemental_health` or `zurich_travel_guard`:**
> you missed a `DOMAIN_MODE` dispatch branch (it fell through the `else`), **or** an old
> `python api.py` process is still serving a stale cache on port 8000. Kill every `python api.py`
> process, delete `data_cache_v1_car.pkl`, and restart. Caches are loaded blindly with no domain
> check, so a stale `.pkl` will happily serve the wrong domain's claims.

**Done when:** `/api/config` reports the car domain, the queue shows car claim-type prefixes,
the checklist runs the car steps, the copilot answers with the car prompt/tools, and a claim with
an `images/<claimid>.png` triggers the car vision checks.
