# Claims Copilot

AI-powered claims examiner workflow — a drop-in-folder plugin platform.
Swap domains without touching core code: one folder + one registry line = a new client domain.

---

## Quick start

### Prerequisites
- Python 3.11+
- Node.js 18+
- AWS account with Bedrock access (Claude Haiku 4.5 enabled in your region)

### 1. Backend

```bash
cd claims-copilot

# Install Python deps
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set AWS_REGION, BEDROCK_MODEL_ID, DOMAIN_MODE

# Run backend (port 8000)
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

### 2. Frontend

```bash
cd claims-copilot/frontend

npm install
npm run dev        # dev server on http://localhost:5173
```

The Vite dev server proxies `/api` and `/ws` to `localhost:8000` automatically.

---

## Architecture

```
claims-copilot/
  core/
    contracts.py      # DomainPlugin dataclass — the plugin contract
    registry.py       # DOMAIN_REGISTRY + get_active_plugin()
    engine.py         # generic rules runner, scorer, checklist runner
  domains/
    __init__.py       # bootstrap: imports all domain modules to register them
    car/
      __init__.py     # PLUGIN = DomainPlugin(...) — assembles the car domain
  intelligence/       # car-domain rules, scoring, checklist, vision
  agents/             # LangGraph copilot + investigation nodes + tools
  main.py             # initialize_data() — plugin-driven, per-domain cache
  api.py              # FastAPI — reads PLUGIN, no domain literals
  frontend/src/       # React UI — config-driven from /api/config
  tests/
    test_golden_baseline.py      # regression gate: hero-case scores must not drift
    test_rules_engine.py         # unit tests for car rules (R-001 to R-006)
    test_plugin_conformance.py   # every registered plugin satisfies the contract
    test_domain_swap.py          # smoke: init + queue with no AttributeError
```

**Principle:** `core/`, `api.py`, `main.py`, and the frontend contain zero domain literals.
A domain is a folder implementing `DomainPlugin`. The registry is the only edit point.

---

## Adding a new domain

1. Create `domains/<your_domain>/` with at minimum an `__init__.py` that assembles and registers a `DomainPlugin`:

```python
# domains/my_domain/__init__.py
from core.contracts import DomainPlugin, DomainConfig
from core.registry import register_plugin

PLUGIN = DomainPlugin(
    name="my_domain",
    config=DomainConfig(...),
    generate_fn=...,
    rules_fn=...,
    score_fn=...,
    build_queue_fn=...,
    checklist_module=...,
    copilot_prompt=...,
    copilot_tools=[...],
    investigation_prompts={"ORCHESTRATOR": ..., "INVESTIGATION": ..., "DOSSIER": ...},
    investigation_tools=[...],
    dossier_tools=[...],
    vision_prompt=...,
    checklist_descriptions={1: "...", ...},
    context_keys=["claims", ...],
    build_checklist_ctx=...,
    dossier_context_fn=...,
    set_tool_context_fns=[...],
    entity_types=[...],
)
register_plugin(PLUGIN)
```

2. Add one import to `domains/__init__.py`:

```python
import domains.my_domain  # noqa: F401
```

3. Set `DOMAIN_MODE=my_domain` in `.env` and restart the backend.

4. Run the conformance test to verify wiring:

```bash
pytest tests/test_plugin_conformance.py
```

No changes to `core/`, `api.py`, `main.py`, or the frontend are required.

---

## Tests

```bash
# Regression gate (hero-case scores must match golden baseline)
pytest tests/test_golden_baseline.py

# Rules engine unit tests
pytest tests/test_rules_engine.py

# Plugin contract conformance
pytest tests/test_plugin_conformance.py

# Domain swap smoke test
$env:DOMAIN_MODE="car_insurance"
pytest tests/test_domain_swap.py

# All tests
pytest tests/
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DOMAIN_MODE` | `car_insurance` | Active domain plugin name |
| `AWS_REGION` | `us-east-1` | Bedrock region |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Model for agents and vision |
| `BEDROCK_VISION_MODEL_ID` | *(same as BEDROCK_MODEL_ID)* | Override for vision checks only |
| `LLM_TEMPERATURE` | `0.1` | LLM temperature |

See `.env.example` for a ready-to-copy template.

---

## Cache

On startup `initialize_data()` writes `data_cache_{DOMAIN_MODE}.pkl` in the project root.
The pickle is stamped with the domain name; loading a stale cache from a different domain
triggers automatic regeneration. Delete any `data_cache_*.pkl` to force a full regeneration.
