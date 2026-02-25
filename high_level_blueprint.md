# Claims Investigation Copilot — Build Schema

## Stack
- LangGraph + Claude (Bedrock) + Python
- Data: Pandas DataFrames (synthetic, in-memory)
- Graph: NetworkX
- Anomaly: scikit-learn Isolation Forest
- RAG: FAISS (small billing rules corpus)
- Viz: PyVis

## Data Schema

### Source Tables (Pandas DataFrames)

```python
# claims_df — 50K rows
columns = [
    "claim_id",              # str PK
    "member_id",             # str FK
    "provider_id",           # str FK
    "referring_provider_id", # str FK, nullable
    "facility_id",           # str FK
    "cpt_code",              # str (e.g. "27447")
    "icd_code",              # str (e.g. "M17.11")
    "billed_amount",         # float
    "paid_amount",           # float
    "service_date",          # datetime
    "place_of_service",      # str
    "claim_type",            # str: professional/institutional/pharmacy
]

# providers_df — 500 rows
columns = [
    "provider_id",  # str PK
    "specialty",    # str
    "region",       # str
    "peer_group",   # str (specialty + region)
]

# members_df — 5K rows
columns = [
    "member_id",  # str PK
    "age",        # int
    "gender",     # str
    "region",     # str
]
```

### Derived Tables (compute at startup)

```python
# provider_features_df — one row per provider
columns = [
    "provider_id",
    "claims_per_month",
    "unique_patients_per_month",
    "claims_per_patient",
    "pct_high_complexity",       # % E&M codes at 99214/99215
    "avg_billed_per_claim",
    "top_cpt_concentration",     # % claims using most common CPT
    "weekend_billing_rate",
    "avg_patients_per_day",
    "duplicate_claim_rate",
    "same_patient_same_day_rate",
    "referral_concentration",    # % referrals from top 3 sources
    "referral_source_count",
    "out_of_specialty_rate",
]

# anomaly_scores_df — one row per entity
columns = [
    "entity_id",
    "entity_type",        # provider/member
    "anomaly_score",      # 0.0-1.0
    "top_features",       # list[dict] with feature_name, value, peer_avg, z_score
    "total_billed",
]

# graph built as NetworkX DiGraph
# nodes: providers, members, facilities (with anomaly_score attr)
# edges derived from claims:
#   provider->member  (BILLED_FOR, weight=claim_count, total_amount)
#   provider->provider (REFERRED_TO, weight=referral_count)
#   provider->facility (OPERATES_AT, weight=claim_count)
```

## Synthetic Data Generation

Generate 95% normal, 5% fraud. Inject 3 scenarios:

```python
# HERO CASE (demo focus)
upcoding_ring = {
    "providers": ["P-4482", "P-1190", "P-3387", "P-5521"],  # 1 primary + 3 referring
    "members": 12,   # shared patients
    "claims": 47,
    "pattern": "P-4482 bills CPT 27447 at 89% (peers 23%). "
               "3 referrers shifted 78% of referrals to P-4482 ~8 months ago.",
    "total_billed": 2_300_000,
    "recoverable": 252_600,
}

# Secondary cases
phantom_billing = {"providers": 1, "members": 8, "total": 89_000}
doctor_shopping = {"members": 5, "providers": 8, "total": 67_000}
```

## 3 Agents (LangGraph)

### Architecture

```
Orchestrator (no tools, delegates only)
├── routes to → Investigation Agent (7 tools)
├── routes to → Dossier Agent (5 tools)
└── END when done

Flow:
  orchestrator → investigation → orchestrator → dossier
       ↑              │                            │
       │              │ always returns             │ if insufficient
       └──────────────┘                            │ goes back to
       └───────────────────────────────────────────┘ orchestrator
```

### State

```python
class InvestigationState(TypedDict):
    messages: Annotated[list, operator.add]
    current_phase: str        # scan/investigate/compile/done
    findings: dict
    dossier: str
    evidence_sufficient: bool
    loop_count: int
```

### Orchestrator — "Lead Investigator"

No tools. Reasons about what to do, delegates to other agents.

Key behaviors:
1. Asks Investigation Agent to scan claims
2. Reviews findings, decides what to dig into
3. Sends to Dossier Agent when ready
4. If Dossier says INSUFFICIENT → sends Investigation back
5. Stops when evidence sufficient or pattern is legitimate

### Investigation Agent — "Detective"

7 tools:

```python
scan_new_claims(since_days=30) -> list[dict]
    # Returns entities with anomaly_score > 0.5, sorted desc

profile_entity(entity_id) -> dict
    # Provider features + info merged

compare_to_peers(entity_id, metric) -> dict
    # Returns {entity_value, peer_avg, z_score, peer_count}

get_claim_details(entity_id, limit=20) -> list[dict]
    # Raw claim rows for entity

find_connections(entity_id, depth=2) -> dict
    # NetworkX BFS. Returns {connected_entities, connection_density, total_entities}

find_ring(min_anomaly_score=0.5, min_entities=3) -> list[dict]
    # NetworkX connected_components filtered by anomaly. Returns ring candidates.

get_referral_history(provider_id, months=18) -> list[dict]
    # Monthly referral breakdown showing concentration changes over time
```

### Dossier Agent — "Case Writer"

5 tools. MUST call assess_evidence before compile_dossier.

```python
assess_evidence(hypothesis, evidence, scheme_pattern) -> dict
    # Checks: statistical_significance (z>2), multiple_evidence_points (>=3),
    #         temporal_pattern, ring_evidence (density>2), referral_history
    # Returns {assessment: "SUFFICIENT"/"INSUFFICIENT", checks_failed, missing_evidence}

search_billing_rules(cpt_codes, context) -> list[dict]
    # FAISS similarity search over CMS/OIG guidelines
    # Returns {section_id, rule_text, summary}

find_similar_cases(scheme_pattern, specialty=None) -> list[dict]
    # Lookup past resolved cases with same pattern

estimate_recovery(flagged_claims, peer_benchmarks) -> dict
    # Returns {gross_recoverable, collectability_score(0.78), net_expected, claim_breakdown}

compile_dossier(case_data) -> str
    # Claude call to generate markdown dossier with:
    # Executive Summary, Entities Table, Evidence Table, Statistical Comparison,
    # Network Analysis, Billing Rules, Similar Cases, Recommended Actions, Recovery Estimate
```

## LangGraph Wiring

```python
graph = StateGraph(InvestigationState)

graph.add_node("orchestrator", orchestrator_node)
graph.add_node("investigation", investigation_node)
graph.add_node("dossier", dossier_node)

graph.set_entry_point("orchestrator")

graph.add_conditional_edges("orchestrator", route_after_orchestrator, {
    "investigation": "investigation",
    "dossier": "dossier",
    "end": END
})

graph.add_edge("investigation", "orchestrator")

graph.add_conditional_edges("dossier", route_after_dossier, {
    "orchestrator": "orchestrator"
})

app = graph.compile()
```

Routing logic:
- After orchestrator: phase scan/investigate → investigation, compile → dossier, done → END
- After investigation: always → orchestrator
- After dossier: always → orchestrator (who decides to finalize or send back to investigation)

## Ring Visualization (PyVis)

```python
def visualize_ring(ring_data, output_path="ring.html"):
    # ring_data has "entities" (list of {id, entity_type, anomaly_score})
    # and "edges" (list of {src, dst, relationship, weight, total_amount})
    # Node color by type: provider=red, member=blue, facility=green
    # Node size by anomaly_score
    # Edge width by weight, label by dollar amount
    # Dark background (#0a0a0a)
```

## File Structure

```
claims-copilot/
├── data/
│   ├── generate_synthetic.py    # creates claims/providers/members DataFrames
│   ├── features.py              # computes provider_features, member_features
│   ├── anomaly.py               # trains Isolation Forest, produces anomaly_scores
│   └── graph.py                 # builds NetworkX graph from claims
├── agents/
│   ├── prompts.py               # ORCHESTRATOR_PROMPT, INVESTIGATION_PROMPT, DOSSIER_PROMPT
│   ├── tools_investigation.py   # 7 investigation tools
│   ├── tools_dossier.py         # 5 dossier tools
│   ├── nodes.py                 # orchestrator_node, investigation_node, dossier_node
│   └── graph.py                 # LangGraph StateGraph wiring
├── billing_rules/
│   ├── rules.json               # small corpus of CMS/OIG rules
│   └── index.py                 # FAISS index builder
├── viz/
│   └── ring_viz.py              # PyVis ring visualization
├── main.py                      # entry point — load data, run agent
└── requirements.txt
```

## Key Demo Moments

1. **Discovery**: Agent finds P-4482, anomaly 0.92, upcoding signal
2. **Ring**: Pulls thread → 4 providers, 12 members, $2.3M
3. **Pushback**: Dossier says INSUFFICIENT → orchestrator sends detective back → finds synchronized referral shift 8 months ago → NOW sufficient
4. **Dossier**: Complete case file with stats, citations, $252K recovery estimate