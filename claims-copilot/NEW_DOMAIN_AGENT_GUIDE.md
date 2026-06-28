# New Domain Integration Guide (Coding Agent)

## Context

You are integrating a new insurance/claims domain into the Claims Copilot platform.
The platform is a plugin system: the core never changes. You only create files inside
`domains/<your_domain>/` and add one line to `domains/__init__.py`.

**Do not modify** `core/`, `api.py`, `main.py`, or anything in `frontend/`.

---

## Files You Will Create

```
domains/<domain_name>/
    __init__.py                    ← PLUGIN assembly + register_plugin() call

<domain_name>_config.py           ← DomainConfig instance
data/generate_<domain_name>.py    ← synthetic data generator
intelligence/rules_<domain_name>.py
intelligence/scoring_<domain_name>.py
intelligence/checklist_<domain_name>.py
agents/prompts_<domain_name>.py
agents/tools_<domain_name>.py         ← copilot tools
agents/tools_<domain_name>_inv.py     ← investigation tools
agents/tools_<domain_name>_dossier.py ← dossier tools
```

Then edit **one existing file**:
```
domains/__init__.py    ← add: import domains.<domain_name>  # noqa: F401
```

And edit **one existing file** if your domain adds new claim types:
```
cases.py    ← add new values to ClaimType and/or CaseType enums
```

---

## Step 1 — DomainConfig

**File:** `<domain_name>_config.py`

```python
from core.contracts import DomainConfig

MY_CONFIG = DomainConfig(
    name="<domain_name>",                    # must match DOMAIN_MODE env var exactly
    display_name="<Human Readable Title>",
    claim_types=["type_a", "type_b"],        # drives frontend tabs; lowercase_snake
    claim_id_prefixes={"type_a": "TA", "type_b": "TB"},
    claim_sources=["online_portal", "call_center"],
    claim_source_weights={"online_portal": 0.7, "call_center": 0.3},  # must sum to 1.0
    risk_tiers={"HIGH": (60, 100), "MEDIUM": (30, 59), "LOW": (0, 29)},
    workflow_task_types=["INITIAL_REVIEW", "DOCUMENT_REQUEST"],
    checklist_steps=["Step One Name", "Step Two Name", "Step Three Name"],
    system_references={},                    # optional: {"system_name": "Display Label"}
    rules_prefix="R",
    doc_checks_prefix="DOC",
    entity_types=["claimant", "vendor"],     # drives case-queue column headers
)
```

**Rules:**
- `claim_types` values must be valid Python identifiers (used as dict keys throughout).
- `checklist_steps` names must exactly match the `Step.name` values you define in Step 6.
- `entity_types` values appear in `/api/config` as column header keys; the frontend reads `entity_labels[key]`.

---

## Step 2 — Data Generator

**File:** `data/generate_<domain_name>.py`

```python
def generate_<domain_name>_data() -> dict:
    """Return a dict. Top-level keys must match context_keys in PLUGIN exactly."""
    claims    = _build_claims()
    claimants = _build_claimants()
    vendors   = _build_vendors()
    return {
        "claims":    claims,
        "claimants": claimants,
        "vendors":   vendors,
        # add every key you list in context_keys
    }
```

Each claim object must have at minimum:
- `.claim_id` (str, unique)
- `.claim_type` (str, must be a value in `MY_CONFIG.claim_types`)
- `.claim_amount` (float)

Use `@dataclass` for all objects. The conformance test calls `generate_fn()` and checks every `context_keys` entry is present.

---

## Step 3 — Rules Engine

**File:** `intelligence/rules_<domain_name>.py`

```python
from core.engine import RuleSpec, run_rules

# One pair of functions per rule ─────────────────────────────────────────────

def _r001_pred(claim, ctx: dict) -> bool:
    # Return True to trigger the rule (flag this claim as suspicious)
    return claim.claim_amount > 50_000

def _r001_explain(claim, ctx: dict, triggered: bool) -> str:
    if triggered:
        return f"Claim ${claim.claim_amount:,.2f} exceeds threshold"
    return "Amount within normal range"

# Rule list ─────────────────────────────────────────────────────────────────

RULE_SPECS = [
    RuleSpec(
        id="R-001",
        name="High Value Claim",
        severity="FLAG",       # "BLOCK" = score floor 70+; "FLAG" = additive boost; "INFO" = display only
        predicate=_r001_pred,
        explain=_r001_explain,
        details_fn=None,       # optional: (claim, ctx) -> dict
    ),
    # ... more rules
]

def run_rules_fn(claim, context_dict: dict) -> list:
    return run_rules(claim, context_dict, RULE_SPECS)
```

---

## Step 4 — Scoring

**File:** `intelligence/scoring_<domain_name>.py`

```python
from core.engine import FeatureSpec, score_claim

# One extractor (+ optional factor label) per feature ───────────────────────

def _amount_extractor(claim, ctx: dict) -> float:
    return claim.claim_amount / 10_000.0   # raw value; bounds will normalise to [0,1]

def _amount_factor(claim, ctx: dict, raw: float):
    if raw > 5.0:
        return f"Claim is very high value: ${claim.claim_amount:,.0f}"
    return None

# Feature list ───────────────────────────────────────────────────────────────

FEATURE_SPECS = [
    FeatureSpec(
        category="financial",
        name="Claim Amount",
        weight=0.5,                        # all weights must sum to 1.0
        extractor=_amount_extractor,
        normalizer_bounds=(0.0, 5.0),      # raw min → 0, raw max → 1
        factor_fn=_amount_factor,
    ),
    # ... more features; weights must sum to 1.0
]

def score_fn(claim, context_dict: dict, rules_results: list):
    from <domain_name>_config import MY_CONFIG
    return score_claim(
        claim, context_dict, rules_results,
        feature_specs=FEATURE_SPECS,
        risk_tiers=MY_CONFIG.risk_tiers,
    )
```

`score_claim` scoring formula: `(feature_score * 0.40 + rules_boost * 0.60) * 100`.
BLOCK rules floor the score at 70+. Weights for `FeatureSpec` are within the feature side only — they do not interact with the rules boost.

---

## Step 5 — Case Queue Builder

**File:** `case_queue_<domain_name>.py`

```python
from cases import Case, CaseType, ClaimType, CasePriority

def build_queue_fn(claims, risk_scores: dict, rules: dict, data: dict) -> list:
    queue = []
    claimant_map = {c.claimant_id: c for c in data.get("claimants", [])}

    for claim in claims:
        score = risk_scores.get(claim.claim_id)
        if not score:
            continue
        claimant = claimant_map.get(getattr(claim, "claimant_id", ""))
        queue.append(Case(
            case_id=claim.claim_id,
            case_type=CaseType.<YOUR_ENUM_VALUE>,    # add to cases.py CaseType if needed
            claim_type=ClaimType(claim.claim_type),  # add to cases.py ClaimType if needed
            subject_id=getattr(claim, "claimant_id", ""),
            subject_name=claimant.name if claimant else "",
            asset_description=getattr(claim, "asset_description", ""),
            counterparty_name=getattr(claim, "vendor_name", ""),
            risk_score=score.total_score,
            priority=CasePriority[score.tier],
            flag_reason="; ".join(
                r.explanation for r in rules.get(claim.claim_id, []) if r.triggered
            ),
            claim_amount=claim.claim_amount,
        ))

    return sorted(queue, key=lambda c: c.risk_score, reverse=True)
```

**NEVER add these fields to Case:** `member_id`, `employer_name`, `provider_name`.
Map domain entities to the neutral names: `subject_id`, `subject_name`, `asset_description`, `counterparty_name`.

---

## Step 6 — Checklist Module

**File:** `intelligence/checklist_<domain_name>.py`

The module **must** expose three names at module level: `CHECKLIST_STEPS`, `run_checklist_step`, `run_full_checklist`.

```python
from typing import Dict, List
from core.engine import Step, ChecklistStepResult, run_checklist, run_checklist_step_spec


def _step_one(claim, context: Dict) -> ChecklistStepResult:
    findings = []
    ok = True
    if not getattr(claim, "claimant_id", None):
        findings.append("MISSING: claimant_id"); ok = False
    else:
        findings.append("claimant_id present")
    return ChecklistStepResult(
        step_number=1,
        step_name="Step One Name",          # must match checklist_steps[0] in DomainConfig
        status="pass" if ok else "needs_review",
        auto_passed=ok,
        findings=findings,
    )

# ... more step functions

CHECKLIST: List[Step] = [
    Step(id="step_one", name="Step One Name", check=_step_one),
    Step(id="step_two", name="Step Two Name", check=_step_two),
    # names must match DomainConfig.checklist_steps in order
]

CHECKLIST_STEPS = [(i + 1, s.name) for i, s in enumerate(CHECKLIST)]  # DO NOT hardcode this


def run_checklist_step(step_number: int, claim_id: str, context: Dict) -> ChecklistStepResult:
    claim = next((c for c in context.get("claims", []) if c.claim_id == claim_id), None)
    if not claim:
        name = CHECKLIST[step_number - 1].name if 0 < step_number <= len(CHECKLIST) else "Unknown"
        return ChecklistStepResult(step_number, name, "error", False, ["Claim not found"])
    result = run_checklist_step_spec(CHECKLIST[step_number - 1], claim, context)
    result.step_number = step_number
    return result


def run_full_checklist(claim_id: str, context: Dict) -> List[ChecklistStepResult]:
    results = run_checklist(CHECKLIST, claim_id, context)
    for i, r in enumerate(results):
        r.step_number = i + 1
    return results
```

---

## Step 7 — Agent Tools (three modules)

Each tool module follows the same pattern. The `set_context` function is called at startup with the live `DataContext`.

**File:** `agents/tools_<domain_name>.py` (copilot tools)

```python
from langchain_core.tools import tool

_ctx = None

def set_context(data_ctx):
    global _ctx
    _ctx = data_ctx

@tool
def get_claim_details(claim_id: str) -> str:
    """Return full details for a specific claim by ID."""
    if not _ctx:
        return "Context not initialised"
    claim = next((c for c in _ctx.claims if c.claim_id == claim_id), None)
    return str(claim) if claim else f"Claim {claim_id} not found"

# ... more @tool functions

ALL_TOOLS = [get_claim_details, ...]
```

Repeat the same structure for `tools_<domain_name>_inv.py` (investigation tools) and `tools_<domain_name>_dossier.py` (dossier tools). Export `ALL_TOOLS` / `INVESTIGATION_TOOLS` / `DOSSIER_TOOLS` and `set_context` from each.

---

## Step 8 — Agent Prompts

**File:** `agents/prompts_<domain_name>.py`

```python
COPILOT_PROMPT = """\
You are an AI claims examiner assistant for <Domain Name>.
Available tools let you look up claims, <entity1>, and <entity2>.
Always cite the claim ID when referring to specific claims.
"""

ORCHESTRATOR_PROMPT = """\
You are an orchestrator. Route the examiner's question to either the
INVESTIGATION agent (fact-finding, data lookup) or the DOSSIER agent
(produce a written summary report). Output exactly one word: INVESTIGATION or DOSSIER.
"""

INVESTIGATION_PROMPT = """\
You are a claims investigation agent for <Domain Name>.
Use your tools to find facts. Return structured findings.
"""

DOSSIER_PROMPT = """\
You are a dossier-writing agent. Given investigation findings, write a
professional claims examiner dossier in markdown. Include risk summary,
triggered rules, and recommended action.
"""
```

---

## Step 9 — Vision Prompt

Add a `VISION_PROMPT` string to your prompts file or a dedicated constant. Must request a JSON response:

```python
VISION_PROMPT = """\
You are a claims document analyst. Examine the submitted evidence image.

DOC-001: Image is clear and unaltered
DOC-002: Date/time is consistent with claim date
DOC-003: Asset matches claim description
...

Respond with ONLY valid JSON, no markdown fences:
{
  "checks": [{"id": "DOC-001", "result": "pass|fail|unclear", "note": "..."}],
  "overall_assessment": "pass|fail|needs_review",
  "confidence": 0.85
}
"""
```

---

## Step 10 — Context Bridge Functions

These two functions live in `domains/<domain_name>/__init__.py`. They translate the generic `DataContext` into the flat dicts your checklist and dossier code expect.

```python
def _build_checklist_ctx(data_ctx, claim_id: str) -> dict:
    return {
        "claims":            data_ctx.claims,
        "claimants":         data_ctx.entities.get("claimants", []),
        "vendors":           data_ctx.entities.get("vendors", []),
        "claim_rules":       data_ctx.claim_rules,
        "claim_risk_scores": data_ctx.claim_risk_scores,
        "claim_doc_results": data_ctx.claim_doc_results,
        "has_claim_images":  False,
    }

def _dossier_context_fn(data_ctx, claim_id: str) -> dict:
    claim = data_ctx.get_claim(claim_id)
    subject_id = getattr(claim, "claimant_id", "") if claim else ""
    return {
        "claim":       claim,
        "subject_id":  subject_id,
        "risk":        data_ctx.claim_risk_scores.get(claim_id),
        "rules":       data_ctx.claim_rules.get(claim_id, []),
        "doc_results": data_ctx.claim_doc_results.get(claim_id, []),
        "tasks":       data_ctx.get_claim_tasks(claim_id),
        "all_claims":  data_ctx.claims,
    }
```

Keys you return from `_build_checklist_ctx` are what your checklist step functions receive as `context`. Keys you return from `_dossier_context_fn` are what your dossier prompt sees.

---

## Step 11 — Assemble PLUGIN

**File:** `domains/<domain_name>/__init__.py`

```python
from core.contracts import DomainPlugin
from core.registry import register_plugin

from <domain_name>_config import MY_CONFIG
from data.generate_<domain_name> import generate_<domain_name>_data
from intelligence.rules_<domain_name> import run_rules_fn
from intelligence.scoring_<domain_name> import score_fn
import intelligence.checklist_<domain_name> as _checklist_mod
from case_queue_<domain_name> import build_queue_fn
from agents.prompts_<domain_name> import (
    COPILOT_PROMPT, ORCHESTRATOR_PROMPT, INVESTIGATION_PROMPT, DOSSIER_PROMPT, VISION_PROMPT,
)
from agents.tools_<domain_name> import ALL_TOOLS, set_context as _set_ctx
from agents.tools_<domain_name>_inv import INVESTIGATION_TOOLS, set_context as _set_inv_ctx
from agents.tools_<domain_name>_dossier import DOSSIER_TOOLS, set_context as _set_dos_ctx

from intelligence.checklist_<domain_name> import CHECKLIST

_CHECKLIST_DESCRIPTIONS = {
    i + 1: step.name for i, step in enumerate(CHECKLIST)
}

# Define _build_checklist_ctx and _dossier_context_fn here (see Step 10)

PLUGIN = DomainPlugin(
    name="<domain_name>",          # must match MY_CONFIG.name and DOMAIN_MODE env var
    config=MY_CONFIG,

    generate_fn=generate_<domain_name>_data,
    rules_fn=run_rules_fn,
    score_fn=score_fn,
    build_queue_fn=build_queue_fn,
    checklist_module=_checklist_mod,

    copilot_prompt=COPILOT_PROMPT,
    copilot_tools=ALL_TOOLS,

    investigation_prompts={
        "ORCHESTRATOR":  ORCHESTRATOR_PROMPT,
        "INVESTIGATION": INVESTIGATION_PROMPT,
        "DOSSIER":       DOSSIER_PROMPT,
    },
    investigation_tools=INVESTIGATION_TOOLS,
    dossier_tools=DOSSIER_TOOLS,

    vision_prompt=VISION_PROMPT,
    checklist_descriptions=_CHECKLIST_DESCRIPTIONS,

    context_keys=["claims", "claimants", "vendors"],   # must match generate_fn return keys
    build_checklist_ctx=_build_checklist_ctx,
    dossier_context_fn=_dossier_context_fn,
    set_tool_context_fns=[_set_ctx, _set_inv_ctx, _set_dos_ctx],
    entity_types=MY_CONFIG.entity_types,
)

register_plugin(PLUGIN)
```

---

## Step 12 — Register the Domain

Edit `domains/__init__.py` — add exactly one line:

```python
import domains.car          # noqa: F401
import domains.<domain_name>  # noqa: F401   ← ADD THIS
```

---

## Step 13 — cases.py Enum Extensions (if needed)

If your domain has claim or case types not already in `cases.py`, add them:

```python
class CaseType(str, Enum):
    CAR_INSURANCE = "car_insurance"
    MY_DOMAIN = "<domain_name>"       # ← add

class ClaimType(str, Enum):
    # Car Insurance
    COLLISION = "collision"
    # ...
    # My Domain
    TYPE_A = "type_a"                 # ← add
    TYPE_B = "type_b"                 # ← add
```

---

## Step 14 — Verify

```bash
# Set the domain
$env:DOMAIN_MODE = "<domain_name>"

# Run conformance test (checks all DomainPlugin fields + generate/rules/score/queue shapes)
pytest tests/test_plugin_conformance.py

# Run domain swap smoke test (initialize_data + queue + no phantom fields)
pytest tests/test_domain_swap.py
```

Both must pass with 0 failures before the domain is considered wired.

---

## Critical Rules (violations cause test failures or runtime errors)

| # | Rule |
|---|------|
| 1 | `PLUGIN.name` == `MY_CONFIG.name` == the value of `DOMAIN_MODE` env var |
| 2 | Every key in `context_keys` must appear as a top-level key in `generate_fn()` return value |
| 3 | `CHECKLIST_STEPS` must be derived from `CHECKLIST` — never hardcoded separately |
| 4 | `DomainConfig.checklist_steps` names must match `Step.name` in `CHECKLIST` exactly and in order |
| 5 | `FeatureSpec` weights must sum to `1.0` |
| 6 | `Case` must never have fields: `member_id`, `employer_name`, `provider_name` |
| 7 | Never call `get_active_plugin()` at module import time — only inside function bodies |
| 8 | `register_plugin(PLUGIN)` must be the last statement in `domains/<domain_name>/__init__.py` |
| 9 | Do not import from `domains/` inside `core/` — circular import will leave registry empty |
| 10 | `investigation_prompts` dict must have exactly the keys `ORCHESTRATOR`, `INVESTIGATION`, `DOSSIER` |

---

## DataContext API (available inside tool `set_context` callbacks)

`data_ctx` passed to `set_context(data_ctx)` is a `DataContext` instance with:

```python
data_ctx.claims                          # List — all domain claim objects
data_ctx.entities                        # Dict[str, List] — keyed by entity-type plural
data_ctx.case_queue                      # List[Case]
data_ctx.claim_rules                     # Dict[claim_id, List[RuleResult]]
data_ctx.claim_risk_scores               # Dict[claim_id, RiskBreakdown]
data_ctx.claim_doc_results               # Dict[claim_id, List]
data_ctx.graph                           # networkx.DiGraph — entity relationship graph
data_ctx.get_claim(claim_id)             # -> claim object or None
data_ctx.get_case(case_id)              # -> Case or None
data_ctx.get_claim_tasks(claim_id)      # -> List[Dict]
```

`data_ctx.entities` keys are whatever entity-type names your `generate_fn` returns minus `"claims"`, e.g. `"claimants"`, `"vendors"`.

---

## Engine Severity Reference

| `severity` | Effect on score |
|---|---|
| `"BLOCK"` | Floors total score at 70. Each additional BLOCK adds 10 more to the floor (up to 90). |
| `"FLAG"` | Adds 8 points per triggered flag to the rules-boost pool (capped at 60 total boost). |
| `"INFO"` | Recorded in results but no scoring effect. |
