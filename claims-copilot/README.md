# Prudential Supplemental Health Examiner Workflow Copilot

An AI-powered examiner workflow tool for Prudential supplemental health claims. Uses LangGraph agents, deterministic rules engine, entity graph analysis, and a 7-step examiner checklist to surface risk signals, automate routine checks, and guide examiners through claim review — with fraud detection as a secondary benefit.

## Overview

The system processes supplemental health claims across four product types:
- **Wellness** — Preventive care visits, routine exams
- **Accident** — Injury-related claims with facility verification
- **Hospital Indemnity** — Per-day hospital admission payouts
- **Critical Illness** — Lump-sum cancer, heart attack, stroke payouts

### Intelligence Pipeline

- **15 deterministic rules** (R-001 to R-015): Excessive dependents, termination rush, provider mills, document tampering, etc.
- **Hybrid risk scoring**: Feature-based anomaly detection (40%) + rules-driven signals (60%) → HIGH/MEDIUM/LOW tiers
- **13 document analysis checks**: Metadata, template matching, facility verification
- **Entity graph** (NetworkX): Detects shared-address clusters, provider volume patterns, dependent rings
- **7-step examiner checklist**: Eligibility → Medical records → Policy limits → Provider check → Document review → Family context → Final assessment

### 500 Synthetic Claims

10 fraud scenarios embedded in realistic data:
- WC-247: 35 fabricated dependents (hero case)
- Termination rush filing, owner change manipulation
- Provider mill (55 claims from one provider)
- Document tampering, duplicate resubmission
- Dependent ring, surgical repair exploit

5 false positives included to demonstrate examiner judgment.

## Architecture

```
Frontend (React 19 + Vite 7 + Tailwind 4)
├── CaseQueue — Date tabs, type filters, priority chips
├── ChatPanel — Claim-aware copilot with checklist bar
├── RiskDashboard — Stats, risk distribution, top rules, patterns
└── DossierPanel — Auto-generated claim dossier with PDF export

Backend (FastAPI + WebSocket)
├── 13 REST endpoints + 1 WebSocket
├── DataContext (pickle-cached) — Claims, intelligence, graph
└── Supplemental Health API — Stats, risk, rules, documents, checklist

Agent Layer (LangGraph + AWS Bedrock Claude)
├── 16 tools (7 fraud, 2 workflow, 4 policy, 3 universal)
├── ReAct agent with supplemental health system prompt
└── Session management with checklist state tracking

Intelligence Layer
├── rules_engine.py — 15 deterministic rules
├── risk_scoring.py — Hybrid scoring model
├── document_analysis.py — 13 document checks
├── entity_graph.py — NetworkX graph + pattern detection
└── checklist.py — 7-step examiner workflow
```

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- AWS CLI configured with Bedrock access

### Installation

```bash
cd claims-copilot

# Python backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt

# React frontend
cd frontend
npm install
```

### Environment

Create `.env` in the `claims-copilot` directory:
```
AWS_PROFILE=your-profile-name
AWS_REGION=us-east-1
```

## Running

### Backend

```bash
cd claims-copilot
python api.py
```

First run generates 500 claims and caches to `data_cache_v2_supplemental.pkl` (~2-3 seconds). Subsequent runs load instantly.

The API runs on `http://localhost:8000`. See `/docs` for full OpenAPI spec.

### Frontend

```bash
cd claims-copilot/frontend
npm run dev
```

Opens on `http://localhost:5173`.

## Demo Flow

1. **Queue** — Review claims sorted by risk. Filter by date, type, priority.
2. **Select a claim** — Click any row to load it into the Copilot.
3. **Copilot** — Chat about the claim. Use quick action chips: "Run Full Checklist", "Check Eligibility", "Why Flagged?"
4. **Dashboard** — View risk distribution, top rules triggered, patterns detected, workflow health.
5. **Dossier** — Auto-generated claim summary with rules, documents, checklist results. Download as PDF.

### Hero Case: WC-247

Member with 35 dependents, R-001 (Excessive Dependents) and R-002 (Rapid Dependent Filing) triggered. Risk score: HIGH. The copilot walks the examiner through the full checklist and surfaces the dependent abuse pattern.

## Key Files

| File | Purpose |
|------|---------|
| `api.py` | FastAPI backend, 13 endpoints + WebSocket |
| `main.py` | DataContext initialization, cache management |
| `cases.py` | Case/Claim dataclasses, enums |
| `domain_config.py` | Prudential supplemental health config |
| `case_queue.py` | Builds Case objects, sorts by risk |
| `agents/copilot.py` | LangGraph ReAct agent, session management |
| `agents/tools_supplemental.py` | 16 examiner workflow tools |
| `agents/prompts_supplemental.py` | Supplemental health system prompt |
| `intelligence/rules_engine.py` | 15 deterministic rules |
| `intelligence/risk_scoring.py` | Hybrid scoring model |
| `intelligence/checklist.py` | 7-step examiner checklist |
| `data/generate_supplemental.py` | 500 synthetic claims generator |
| `billing_rules/rules.json` | R-001 through R-015 rule definitions |

**To Run**: `python run_agents.py` (requires AWS Bedrock access)

## Testing

Run individual modules:

```bash
# Test data generation only
python data/generate_synthetic.py

# Test feature computation
python data/features.py

# Test anomaly detection
python data/anomaly.py

# Test graph building
python data/graph.py

# Test billing rules search
python billing_rules/index.py

# Test visualization
python viz/ring_viz.py
```

## Technologies

- **LangGraph** - Multi-agent orchestration
- **Pandas** - Data manipulation
- **NumPy** - Numerical operations
- **Scikit-learn** - Machine learning (Isolation Forest)
- **NetworkX** - Graph analysis
- **FAISS** - Vector similarity search
- **PyVis** - Network visualization
- **AWS Bedrock** - Claude LLM (planned)

## License

Hackathon project - Internal use

## Authors

Built for healthcare fraud detection hackathon 2026
