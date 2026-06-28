# Domain Registry Refactor — Design (for later)

## Why this exists

Today the Claims Copilot is **single-domain by construction**. The app currently runs one
domain (Car Insurance), but the *structure* still carries the original multi-domain cost model:
adding or swapping a client/industry means **copy-pasting ~12 files and editing ~6 dispatch
sites**, and a missed dispatch branch silently serves the wrong domain.

This document describes the target architecture that turns "add a new client" into **drop in one
folder + register one line**, with **zero edits** to `api.py`, `main.py`, `copilot.py`,
`nodes.py`, or `document_vision.py`.

> Status: **design only — not yet implemented.** The current Car Insurance build is the intended
> *first plugin* once this refactor lands.

---

## The problem today (concrete)

A domain is spread across two expensive shapes:

1. **Per-domain file set** (one of each, per domain):
   `data/generate_<d>.py`, `intelligence/rules_engine_<d>.py`, `risk_scoring_<d>.py`,
   `checklist_<d>.py`, `case_queue_<d>.py`, `agents/prompts_<d>.py`, `tools_<d>.py`,
   `prompts_investigation_<d>.py`, `tools_investigation_<d>.py`, `tools_dossier_<d>.py`.

2. **Hard-coded dispatch** keyed off `DOMAIN_MODE`:
   - `main.py` — which generator/rules/scoring/queue to import + `initialize_<d>_data()`
   - `api.py` — checklist import, `CHECKLIST_DESCRIPTIONS`, `_build_<d>_checklist_ctx`, `lifespan()`
     tool-context wiring, `_APP_TITLE`, the checklist endpoint, the dossier builder, `_patch_loggers`
   - `agents/copilot.py` — copilot prompt + tools selection
   - `agents/nodes.py` — investigation/dossier prompts + tools selection
   - `intelligence/document_vision.py` — the vision prompt
   - `cases.py` / `domain_config.py` — enums + a `DomainConfig`

The dossier function in `api.py` also reaches directly into domain-specific entity fields
(`get_member`, `get_insured`, etc.), which is the deepest coupling.

---

## Target architecture

### 1. A `DomainPlugin` contract

```python
# domains/base.py
from dataclasses import dataclass
from typing import Callable, List, Dict, Any

@dataclass(frozen=True)
class DomainPlugin:
    name: str                       # "car_insurance"
    config: "DomainConfig"          # the existing DomainConfig dataclass

    # data + intelligence
    generate_fn: Callable[[], Dict] # generate_car_data
    rules_fn: Callable              # run_car_rules_engine(claim, ctx) -> List[RuleResult]
    score_fn: Callable              # score_car_claim(claim, ctx, rules) -> RiskBreakdown
    build_queue_fn: Callable        # build_car_case_queue(...)
    checklist_module: Any           # exposes run_full_checklist / run_checklist_step / CHECKLIST_STEPS

    # presentation / agent
    copilot_prompt: str
    copilot_tools: List             # ALL_CAR_TOOLS
    investigation_prompts: Dict[str, str]   # ORCHESTRATOR/INVESTIGATION/DOSSIER
    investigation_tools: List
    dossier_tools: List
    vision_prompt: str
    checklist_descriptions: Dict[int, str]

    # the per-domain entity wiring that api.py currently hard-codes
    context_keys: List[str]                 # ["insureds","vehicles","repair_shops",...]
    build_checklist_ctx: Callable[["DataContext", str], dict]
    dossier_context_fn: Callable[["DataContext", str], dict]   # replaces the api.py branch
    set_tool_context_fns: List[Callable]    # [tools_car.set_context, tools_investigation_car.set_context, ...]
```

### 2. A `domains/` package — one subpackage per client

```
domains/
  base.py            # DomainPlugin + registry
  car/
    __init__.py      # exports PLUGIN = DomainPlugin(...)
    generate.py      # (today's data/generate_car.py)
    rules.py         # rules_engine_car.py
    scoring.py       # risk_scoring_car.py
    checklist.py     # checklist_car.py
    queue.py         # case_queue_car.py
    prompts.py       # prompts_car.py + prompts_investigation_car.py
    tools.py         # tools_car.py + investigation/dossier tools
    vision.py        # the _CAR_VISION_PROMPT
```

### 3. One registry, `DOMAIN_MODE` becomes a key

```python
# domains/__init__.py
from .car import PLUGIN as CAR
DOMAIN_REGISTRY = {p.name: p for p in (CAR,)}     # add NEW_CLIENT here — the only edit

def get_active_plugin() -> DomainPlugin:
    name = os.getenv("DOMAIN_MODE", "car_insurance")
    return DOMAIN_REGISTRY[name]
```

### 4. Core files read the plugin instead of branching

- `main.py`: `PLUGIN = get_active_plugin()`; one generic `initialize_data()` that calls
  `PLUGIN.generate_fn / rules_fn / score_fn / build_queue_fn` and pickles to
  `data_cache_{PLUGIN.name}.pkl` (a per-domain cache name — kills the stale-cache trap).
- `api.py`: `CHECKLIST_DESCRIPTIONS = PLUGIN.checklist_descriptions`;
  `_APP_TITLE = PLUGIN.config.display_name`; checklist endpoint calls
  `PLUGIN.build_checklist_ctx(data_ctx, claim_id)`; dossier calls `PLUGIN.dossier_context_fn(...)`;
  `lifespan()` loops `PLUGIN.set_tool_context_fns`. **No `if DOMAIN_MODE ==` anywhere.**
- `copilot.py`: `PLUGIN.copilot_prompt`, `PLUGIN.copilot_tools`.
- `nodes.py`: `PLUGIN.investigation_prompts`, `PLUGIN.investigation_tools`, `PLUGIN.dossier_tools`.
- `document_vision.py`: `_VISION_PROMPT = PLUGIN.vision_prompt`.

### 5. Cache safety (fixes a real bug we hit)

Each domain pickles to `data_cache_{name}.pkl` **and stamps the domain name inside the pickle**.
On load, assert the stamp matches the active plugin; mismatch → regenerate. This removes the
"server silently serves the wrong domain from a stale `.pkl`" failure mode entirely.

---

## Migration path

1. Add `domains/base.py` (`DomainPlugin` + registry) — no behavior change.
2. Move the current `*_car.py` files under `domains/car/` and build `domains/car/__init__.py:PLUGIN`.
   (Thin re-export shims can keep old import paths working during the move.)
3. Replace each `DOMAIN_MODE` branch in the core files with a `PLUGIN.<field>` read, one file at a
   time, re-running the verification steps in the implementation plan after each.
4. Delete the dead branches once all five core files read from the plugin.
5. Add the domain stamp to the cache and switch to `data_cache_{name}.pkl`.

**End state:** a new client = a new `domains/<client>/` package implementing the contract + one
line in `DOMAIN_REGISTRY`. The core files never change again.

---

## Net effect

| | Today | After refactor |
|---|---|---|
| New client | ~12 new files **+** ~6 edited dispatch sites | 1 new folder **+** 1 registry line |
| Missed-branch risk | silent wrong-domain fallthrough | impossible (no branches) |
| Stale-cache risk | serves wrong domain silently | caught by in-pickle domain stamp |
