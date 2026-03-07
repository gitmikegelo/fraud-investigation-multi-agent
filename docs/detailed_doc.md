

```markdown
# Claims Investigation Copilot
### Multi-Agent Fraud Investigation System
### Architecture & Implementation Document

---

## 1. Overview

**What it does:**
Three AI agents collaborate to investigate healthcare claims fraud — discovering
coordinated fraud rings, challenging each other's evidence, and producing
complete investigation dossiers.

**One-liner:**
> "It found one suspicious bill, got curious, discovered 3 doctors secretly
> funneling patients to each other to overbill $2.3 million, drew a map of the
> whole scheme, wrote up the investigation report with billing rule citations,
> and told the fraud team exactly what to do — all in 90 seconds."

**What makes this an Agent project, not an ML project:**
- Agents **reason** about what to investigate next
- Agents **delegate** to each other
- Agents **loop back** when evidence is insufficient
- Agents **adapt** their investigation path based on what they find
- No fixed pipeline — the orchestrator decides the path dynamically

---

## 2. Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Framework | LangGraph (Python) |
| LLM | Claude 3.5 Haiku via AWS Bedrock |
| Data | Pandas DataFrames + Pickle cache |
| Graph Analysis | NetworkX |
| Anomaly Detection | scikit-learn (Isolation Forest) |
| RAG (Billing Rules) | FAISS local index |
| Ring Visualization | PyVis |
| Backend API | FastAPI + WebSocket |
| Frontend UI | React + Vite |
| Runtime | Local Python (single machine) |

**Design principle:** Zero infrastructure. Everything runs locally. The demo is
about agent behavior, not deployment architecture.

---

## 3. Three-Agent Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                  CLAIMS INVESTIGATION COPILOT                     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   ORCHESTRATOR AGENT                        │  │
│  │                 "The Lead Investigator"                     │  │
│  │                                                            │  │
│  │  • Decides what to investigate and how deep to go          │  │
│  │  • Delegates to specialist agents                          │  │
│  │  • Adapts investigation path based on findings             │  │
│  │  • Stops when evidence is sufficient OR pattern is legit   │  │
│  │  • HAS NO TOOLS — only delegates                          │  │
│  └──────────────┬─────────────────────────┬───────────────────┘  │
│                 │                         │                       │
│         ┌───────▼──────────┐    ┌─────────▼────────────┐         │
│         │  INVESTIGATION   │    │    DOSSIER            │         │
│         │  AGENT           │    │    AGENT              │         │
│         │  "The Detective" │    │    "The Case Writer"  │         │
│         │                  │    │                       │         │
│         │ • Scans claims   │    │ • Assesses evidence   │         │
│         │ • Profiles       │    │   sufficiency         │         │
│         │   entities       │◄──▶│ • Compiles dossier    │         │
│         │ • Maps networks  │    │ • Cites billing rules │         │
│         │ • Finds rings    │    │ • Estimates recovery   │         │
│         │ • Digs deeper    │    │ • Recommends actions  │         │
│         │   on request     │    │ • PUSHES BACK if      │         │
│         │                  │    │   evidence is weak     │         │
│         └──────────────────┘    └────────────────────────┘        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                      TOOL LAYER                             │  │
│  │                 (Plain Python Functions)                     │  │
│  │                                                             │  │
│  │  Pandas           │  sklearn pkl    │  FAISS        │  │       │
│  │  (query claims)   │  (anomaly       │  (billing     │  │       │
│  │                   │   scoring)      │   rules RAG)  │  │       │
│  │  NetworkX         │  Pickle cache   │               │  │       │
│  │  (ring detection) │  (data storage) │               │  │       │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    DATA LAYER                               │  │
│  │              (Synthetic, In-Memory)                         │  │
│  │                                                             │  │
│  │  claims (50K rows)  │  providers (500)  │  members (5K)    │  │
│  │                                                             │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### LangGraph Flow

```
                    ┌──────────────┐
          ┌────────│ Orchestrator  │────────┐
          │        │  (reasons,    │        │
          │        │   delegates)  │        │
          │        └──────┬───────┘        │
          │               │                │
          │          done? → END            │
          ▼                                ▼
  ┌───────────────┐               ┌──────────────┐
  │ Investigation │               │   Dossier    │
  │ Agent         │               │   Agent      │
  │ (scan, profile│               │ (assess,     │
  │  graph, ring) │               │  compile)    │
  └───────┬───────┘               └──────┬───────┘
          │                              │
          │ always returns to            │ sufficient → orchestrator finalizes
          │ orchestrator                 │ insufficient → orchestrator sends
          └──────────────────────────────┘   investigation agent back
```

---

## 4. Healthcare Claims Fraud — Domain Primer

### The Four Core Entities

```
Who got treated?      → Member (patient)
Who provided care?    → Provider (doctor/clinic)
Where?                → Facility
What was done/billed? → Claim (the transaction)
```

Every fraud scheme is an abuse of the relationships between these four.

### The Claim — The Core Transaction

```
Claim
├── WHO was the patient (member_id)
├── WHO provided the service (provider_id)
├── WHO referred the patient (referring_provider_id)
├── WHERE it happened (facility_id, place_of_service)
├── WHAT was done (CPT codes — procedure codes)
├── WHY it was done (ICD codes — diagnosis codes)
├── HOW MUCH was billed (billed_amount)
├── HOW MUCH was paid (paid_amount)
├── WHEN (service_date)
└── claim_type (professional / institutional / pharmacy)
```

**CPT codes** = what was done (e.g., 27447 = total knee replacement,
99213 = office visit moderate complexity)

**ICD codes** = the diagnosis justifying it (e.g., M17.11 = primary
osteoarthritis, right knee)

Fraud is almost always in the **relationship between these fields**.

### Six Fraud Patterns

#### 1. Upcoding
Billing for a more expensive version of what was actually done.

```
Reality: Office visit, low complexity (CPT 99212, ~$45)
Billed:  Office visit, high complexity (CPT 99215, ~$210)

Reality: Partial knee replacement (CPT 27446, ~$25K)
Billed:  Total knee replacement (CPT 27447, ~$47K)
```

**Detection signals:**
- Provider's CPT code distribution vs peers in same specialty
- Ratio of high-complexity to low-complexity codes
- If 90% of a doctor's visits are "high complexity" and peers average 25%

#### 2. Unbundling
Billing separately for things that should be billed as one package.

```
A surgery includes: anesthesia, the procedure, post-op care
Correct: Bill one bundled code
Fraud:   Bill each component separately to get paid more
```

**Detection signals:**
- Multiple CPT codes on same date for same patient that are known bundles
- Total billed per encounter vs peers

#### 3. Phantom Billing
Billing for services that never happened.

```
Patient wasn't seen that day
Patient doesn't exist
Service wasn't performed
```

**Detection signals:**
- Services on dates the member was elsewhere (hospitalized, different state)
- Impossibly high volume (80 patients/day when peers do 25)
- Services after member death or disenrollment

#### 4. Duplicate Billing
Submitting the same claim twice (or slightly modified).

```
Same patient, same provider, same date, same codes
Submitted once → paid → submitted again slightly modified → paid again
```

**Detection signals:**
- Exact or near-exact claim matches (same member + provider + date + codes)
- Claims within days of each other for procedures that can't repeat that fast

#### 5. Kickbacks / Referral Schemes
Providers referring patients to each other for money, not medical need.

```
Dr. A refers all knee patients to Dr. B (who pays Dr. A per referral)
Dr. B upcodes the procedures
Both profit, insurer pays inflated claims
```

**Detection signals:**
- Referral concentration (80% to one provider, peers distribute across many)
- Sudden shift in referral patterns
- Synchronized changes across multiple referring providers
- **This is the ring detection part of the project**

#### 6. Doctor Shopping (Member-Side)
Patients visiting multiple providers for controlled substances.

```
Patient visits 8 different doctors in 3 months
Gets opioid prescriptions from each
Fills at different pharmacies
```

**Detection signals:**
- Number of unique providers per member
- Number of unique pharmacies per member
- Geographic spread of visits
- Overlapping prescriptions for same drug class

### What Fields Detect What

```
                        Claim Fields That Matter
                        ───────────────────────
Pattern          │ CPT │ ICD │ $Amt │ Date │ Provider │ Member │ Referrer │ Facility
─────────────────┼─────┼─────┼──────┼──────┼──────────┼────────┼──────────┼─────────
Upcoding         │  ✅ │  ✅ │  ✅  │      │    ✅    │        │          │
Unbundling       │  ✅ │     │  ✅  │  ✅  │    ✅    │   ✅   │          │
Phantom billing  │     │     │  ✅  │  ✅  │    ✅    │   ✅   │          │    ✅
Duplicates       │  ✅ │  ✅ │  ✅  │  ✅  │    ✅    │   ✅   │          │
Kickbacks/Rings  │     │     │  ✅  │      │    ✅    │   ✅   │    ✅    │
Doctor shopping  │  ✅ │     │      │  ✅  │    ✅    │   ✅   │          │    ✅
```

### The Key Insight: Peer Comparison

Every feature is meaningless in isolation. A surgeon billing $50K per claim
isn't suspicious — surgeons are expensive. A family doctor billing $50K per
claim is very suspicious.

```
Z-score = (this_provider_value - peer_group_average) / peer_group_std_dev

z > 2.0  → unusual
z > 3.0  → very suspicious
z > 4.0  → almost certainly anomalous
```

Peer group = same specialty + same region.

---

## 5. Data Schema

### Three Source Tables (Minimum Viable)

```
claims
├── claim_id          (string, PK)
├── member_id         (string, FK)
├── provider_id       (string, FK)
├── referring_provider_id  (string, FK, nullable — enables ring detection)
├── facility_id       (string, FK)
├── cpt_code          (string — primary procedure code)
├── icd_code          (string — primary diagnosis code)
├── billed_amount     (float)
├── paid_amount       (float)
├── service_date      (date)
├── place_of_service  (string)
└── claim_type        (string — professional / institutional / pharmacy)

providers
├── provider_id       (string, PK)
├── specialty         (string)
├── region            (string)
└── peer_group        (string — derived: specialty + region)

members
├── member_id         (string, PK)
├── age               (int)
├── gender            (string)
└── region            (string)
```

**Everything else is derived from these three tables.**

### Derived: Provider Features

Computed from claims, used for anomaly detection:

```python
provider_features (computed per provider)
├── provider_id
│
├── # Volume
├── claims_per_month
├── unique_patients_per_month
├── claims_per_patient
│
├── # Coding patterns (UPCODING signal)
├── pct_high_complexity          # % of E&M codes at 99214/99215
├── avg_billed_per_claim
├── top_cpt_concentration        # % of claims using most common CPT
│
├── # Timing (PHANTOM signal)
├── weekend_billing_rate
├── avg_patients_per_day
│
├── # Duplicates
├── duplicate_claim_rate         # % of near-identical claims
├── same_patient_same_day_rate
│
├── # Referrals (KICKBACK signal)
├── referral_concentration       # % of referrals from top 3 sources
├── referral_source_count
├── referral_pattern_change      # did concentration spike recently?
│
├── # Specialty appropriateness
├── out_of_specialty_rate        # % of codes outside specialty norms
│
└── computed_at
```

### Derived: Member Features

```python
member_features (computed per member)
├── member_id
├── unique_providers_per_month
├── unique_pharmacies_per_month
├── er_visit_rate
├── avg_distance_to_provider
├── procedures_within_90_days
├── overlapping_prescriptions
└── computed_at
```

### Derived: Anomaly Scores

Output of Isolation Forest model:

```python
anomaly_scores
├── entity_id
├── entity_type            # provider / member
├── anomaly_score          # 0.0 – 1.0
├── top_contributing_features
│   ├── feature_name
│   ├── feature_value
│   ├── peer_avg
│   └── z_score
├── total_billed
└── scored_at
```

### Derived: Graph (For Ring Detection)

```python
graph_nodes
├── id                     # entity_id
├── entity_type            # provider / member / facility
├── anomaly_score
└── attributes             # specialty, region, etc.

graph_edges
├── src                    # source entity_id
├── dst                    # destination entity_id
├── relationship           # BILLED_FOR / REFERRED_TO / OPERATES_AT
├── weight                 # claim count
├── total_amount
└── first_seen             # date
```

**Edge derivation from claims:**

```
Provider ──[BILLED_FOR]──▶ Member
    weight = count of claims between them
    total_amount = sum of billed_amount

Provider ──[REFERRED_TO]──▶ Provider
    weight = count of referrals
    (from referring_provider_id → provider_id)

Provider ──[OPERATES_AT]──▶ Facility
    weight = count of claims at that facility

Member ──[VISITED]──▶ Facility
    weight = count of visits
```

### Derived: Investigation Cases

Output of agent system:

```python
investigation_cases
├── case_id
├── case_type              # individual / ring
├── primary_entity_id
├── all_entity_ids
├── priority_tier          # P1 / P2 / P3
├── scheme_pattern         # upcoding / phantom / ring / etc.
├── hypothesis
├── dossier_markdown       # the full generated dossier
├── estimated_recovery
├── claim_count
├── total_billed
├── status                 # new / in_review / confirmed / legitimate
├── created_at
└── updated_at
```

---

## 6. Agent Definitions

### 6.1 Orchestrator Agent — "The Lead Investigator"

**Role:** Decides what to investigate, delegates to specialists, adapts the
investigation path, determines when a case is ready.

**This agent has NO tools.** It only delegates to the Investigation Agent
and Dossier Agent.

```python
ORCHESTRATOR_PROMPT = """
You are the lead investigator for a healthcare fraud investigation unit.
You have two specialist agents:

1. INVESTIGATION AGENT ("The Detective")
   - Can scan claims for anomalies
   - Can profile providers and members
   - Can map connections between entities
   - Can discover fraud rings
   - Can dig deeper into specific entities on request

2. DOSSIER AGENT ("The Case Writer")
   - Can compile evidence into a structured case file
   - Can estimate dollar recovery amounts
   - Can cite relevant billing rules
   - Can recommend investigation actions
   - Can assess whether evidence is SUFFICIENT or INSUFFICIENT
   - Will PUSH BACK and request more investigation if evidence is weak

Your job:
1. Ask Investigation Agent to scan for anomalies in new claims
2. REVIEW the findings — decide which ones warrant deeper investigation
3. For promising leads, ask Investigation Agent to map connections
4. DECIDE: is this an individual case or a coordinated ring?
5. When you have enough findings, ask Dossier Agent to compile the case
6. IF Dossier Agent says evidence is insufficient — send Investigation
   Agent back to gather what's missing (THIS IS CRITICAL)
7. When Dossier Agent confirms sufficient evidence — finalize the case
8. STOP investigating patterns that are clearly legitimate

IMPORTANT RULES:
- Think out loud before every decision. Explain your reasoning.
- You may loop back as many times as needed.
- You MUST stop if the pattern is clearly normal behavior.
- Always consider: "Is this worth investigating further or am I
  chasing noise?"
- When a ring is discovered, treat it as HIGHER priority than
  individual anomalies.
"""
```

### 6.2 Investigation Agent — "The Detective"

**Role:** Does the actual investigative work. Scans claims, profiles entities,
maps connections, discovers rings.

```python
INVESTIGATION_AGENT_PROMPT = """
You are a healthcare fraud detective. You investigate claims data to find
anomalies, suspicious patterns, and connections between entities.

You have access to these tools:
- scan_new_claims: Scan recent claims for anomalies
- profile_entity: Get detailed behavioral profile of a provider or member
- compare_to_peers: Compare an entity's metrics to their peer group
- get_claim_details: Pull full details for specific claims
- find_connections: Map relationships between entities
- find_ring: Detect clusters of interconnected suspicious entities
- get_referral_history: Pull historical referral patterns over time

When investigating:
1. Start broad (scan), then go narrow (profile specific entities)
2. Always check for connections — individual anomalies may be part of rings
3. When asked to dig deeper, be thorough
4. Report findings clearly with specific numbers
5. Flag if a pattern looks normal vs genuinely suspicious

You are called by the Orchestrator. Return your findings and let the
Orchestrator decide next steps.
"""
```

**Tools:**

```python
def scan_new_claims(since_days: int = 30) -> list:
    """
    Scan claims for anomalies using the pre-trained Isolation Forest model.
    Returns flagged entities with anomaly scores and top contributing features.
    """
    # Load pre-scored anomaly results
    flagged = anomaly_scores_df[
        anomaly_scores_df["anomaly_score"] > 0.5
    ].sort_values("anomaly_score", ascending=False)

    return flagged.to_dict("records")


def profile_entity(entity_id: str) -> dict:
    """
    Get complete behavioral profile of a provider or member.
    Includes billing patterns, volumes, code distributions, and peer comparison.
    """
    features = provider_features_df[
        provider_features_df["provider_id"] == entity_id
    ]
    provider_info = providers_df[
        providers_df["provider_id"] == entity_id
    ]
    return {**provider_info.iloc[0].to_dict(), **features.iloc[0].to_dict()}


def compare_to_peers(entity_id: str, metric: str) -> dict:
    """
    Compare a specific metric for an entity against their peer group.
    Returns entity value, peer average, z-score.
    """
    entity = provider_features_df[
        provider_features_df["provider_id"] == entity_id
    ].iloc[0]

    peer_group = providers_df[
        providers_df["provider_id"] == entity_id
    ]["peer_group"].iloc[0]

    peers = provider_features_df.merge(providers_df, on="provider_id")
    peers = peers[peers["peer_group"] == peer_group]

    peer_avg = peers[metric].mean()
    peer_std = peers[metric].std()
    entity_value = entity[metric]
    z_score = (entity_value - peer_avg) / peer_std if peer_std > 0 else 0

    return {
        "entity_value": entity_value,
        "peer_avg": peer_avg,
        "z_score": z_score,
        "peer_count": len(peers)
    }


def get_claim_details(entity_id: str, limit: int = 20) -> list:
    """
    Pull full claim details for a provider or member.
    """
    matches = claims_df[
        (claims_df["provider_id"] == entity_id) |
        (claims_df["member_id"] == entity_id)
    ].sort_values("service_date", ascending=False).head(limit)

    return matches.to_dict("records")


def find_connections(entity_id: str, depth: int = 2) -> dict:
    """
    Map all entities connected to the given entity within N hops.
    Uses NetworkX graph analysis.
    """
    import networkx as nx

    G = build_graph()  # builds NetworkX graph from graph_nodes/edges

    # BFS within depth
    paths = dict(
        nx.single_source_shortest_path(G, entity_id, cutoff=depth)
    )

    connected = []
    for target, path in paths.items():
        if target != entity_id:
            node_data = G.nodes[target]
            connected.append({
                "id": target,
                "entity_type": node_data.get("entity_type"),
                "anomaly_score": node_data.get("anomaly_score", 0),
                "hops": len(path) - 1
            })

    subgraph = G.subgraph(list(paths.keys()))
    density = nx.density(subgraph)

    return {
        "connected_entities": connected,
        "connection_density": density,
        "total_entities": len(connected)
    }


def find_ring(min_anomaly_score: float = 0.5, min_entities: int = 3) -> list:
    """
    Detect clusters of interconnected suspicious entities.
    Returns ring candidates with entity details and total billed amounts.
    """
    import networkx as nx

    G = build_graph()
    components = list(nx.connected_components(G.to_undirected()))

    rings = []
    for comp in components:
        subgraph = G.subgraph(comp)
        entities = []
        total_anomaly = 0

        for node in comp:
            data = G.nodes[node]
            score = data.get("anomaly_score", 0)
            total_anomaly += score
            entities.append({
                "id": node,
                "entity_type": data.get("entity_type"),
                "anomaly_score": score
            })

        avg_anomaly = total_anomaly / len(comp) if comp else 0

        if len(comp) >= min_entities and avg_anomaly > min_anomaly_score:
            rings.append({
                "entity_count": len(comp),
                "avg_anomaly": avg_anomaly,
                "entities": entities,
                "density": nx.density(subgraph)
            })

    return sorted(rings, key=lambda r: r["avg_anomaly"], reverse=True)


def get_referral_history(provider_id: str, months: int = 18) -> list:
    """
    Pull historical referral patterns for a provider over time.
    Shows how referral distribution changed month-over-month.
    """
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(days=months * 30)

    referrals = claims_df[
        (claims_df["provider_id"] == provider_id) &
        (claims_df["referring_provider_id"].notna()) &
        (claims_df["service_date"] >= cutoff)
    ].copy()

    referrals["month"] = referrals["service_date"].dt.to_period("M")

    monthly = (
        referrals.groupby(["month", "referring_provider_id"])
        .size()
        .reset_index(name="referral_count")
    )

    # Calculate percentage per month
    monthly_totals = monthly.groupby("month")["referral_count"].transform("sum")
    monthly["referral_pct"] = monthly["referral_count"] / monthly_totals

    return monthly.to_dict("records")
```

### 6.3 Dossier Agent — "The Case Writer"

**Role:** Compiles evidence into investigation dossiers. **Critically: assesses
evidence sufficiency and pushes back when more investigation is needed.**

```python
DOSSIER_AGENT_PROMPT = """
You are a senior healthcare fraud investigation analyst who writes
formal case files. You receive investigation findings and compile them
into structured, actionable dossiers.

You have access to these tools:
- assess_evidence: Evaluate if gathered evidence is sufficient
- search_billing_rules: Search CMS/OIG guidelines relevant to CPT/ICD codes
- find_similar_cases: Find historically resolved cases with similar patterns
- estimate_recovery: Calculate estimated recoverable dollar amounts
- compile_dossier: Generate the formatted investigation dossier

CRITICAL BEHAVIOR:
Before compiling ANY dossier, you MUST call assess_evidence first.
If evidence is INSUFFICIENT, you must:
1. Clearly state what's missing
2. Explain why it matters
3. Request the specific additional investigation needed
4. DO NOT generate a dossier with weak evidence

You would rather delay a dossier than produce one that falls apart
under scrutiny. Your reputation depends on case quality.

When evidence IS sufficient:
1. Search for applicable billing rules
2. Find similar past cases for precedent
3. Estimate recovery amounts conservatively
4. Recommend specific, sequenced actions
5. Generate the complete dossier
"""
```

**Tools:**

```python
def assess_evidence(hypothesis: str, evidence: dict, scheme_pattern: str) -> dict:
    """
    Evaluate whether gathered evidence is sufficient to support the hypothesis.
    Returns SUFFICIENT or INSUFFICIENT with reasoning about what's missing.
    """
    checks = {
        "statistical_significance": all(
            f.get("z_score", 0) > 2.0
            for f in evidence.get("anomaly_features", [])
        ),
        "multiple_evidence_points": len(
            evidence.get("supporting_facts", [])
        ) >= 3,
        "temporal_pattern": evidence.get(
            "historical_comparison", None
        ) is not None,
        "ring_evidence": (
            evidence.get("connection_density", 0) > 2.0
            if scheme_pattern == "ring" else True
        ),
        "referral_history": (
            evidence.get("referral_shift_confirmed", False)
            if "referral" in scheme_pattern else True
        )
    }

    missing = [k for k, v in checks.items() if not v]

    evidence_requirements = {
        "statistical_significance": "Need z-scores > 2.0 on anomaly features",
        "multiple_evidence_points": "Need at least 3 independent evidence points",
        "temporal_pattern": "Need historical comparison showing behavior change",
        "ring_evidence": "Need connection density > 2.0 for ring claims",
        "referral_history": "Need confirmed referral pattern shift for referral schemes"
    }

    return {
        "assessment": "SUFFICIENT" if not missing else "INSUFFICIENT",
        "checks_passed": {k: v for k, v in checks.items() if v},
        "checks_failed": missing,
        "missing_evidence": [evidence_requirements[m] for m in missing]
    }


def search_billing_rules(cpt_codes: list, context: str) -> list:
    """
    Search CMS/OIG billing guidelines relevant to the given CPT codes.
    Uses FAISS vector search over embedded guidelines.
    """
    import faiss
    import numpy as np

    # query_embedding = embed(f"Billing rules for CPT {', '.join(cpt_codes)}. {context}")
    # D, I = faiss_index.search(np.array([query_embedding]), k=5)
    # return [guidelines[i] for i in I[0]]

    # For demo, return from pre-loaded rules
    relevant = []
    for rule in billing_rules:
        if any(code in rule["applicable_codes"] for code in cpt_codes):
            relevant.append(rule)
    return relevant[:5]


def find_similar_cases(scheme_pattern: str, specialty: str = None) -> list:
    """
    Find historically resolved cases with similar fraud patterns.
    Returns case details, decisions, and recovery amounts.
    """
    matches = cases_df[cases_df["scheme_pattern"] == scheme_pattern]
    if specialty:
        matches = matches[matches["specialty"] == specialty]
    return matches.head(5).to_dict("records")


def estimate_recovery(flagged_claims: list, peer_benchmarks: dict) -> dict:
    """
    Calculate estimated recoverable dollar amounts.
    """
    recovery = 0
    claim_details = []

    for claim in flagged_claims:
        if claim.get("flag") == "upcoding":
            expected = peer_benchmarks.get(
                claim.get("expected_cpt"), {}
            ).get("avg_paid", 0)
            delta = claim["paid_amount"] - expected
            recovery += delta
            claim_details.append({
                "claim_id": claim["claim_id"],
                "flag": "upcoding",
                "paid": claim["paid_amount"],
                "expected": expected,
                "recoverable": delta
            })
        elif claim.get("flag") in ("duplicate", "phantom"):
            recovery += claim["paid_amount"]
            claim_details.append({
                "claim_id": claim["claim_id"],
                "flag": claim["flag"],
                "recoverable": claim["paid_amount"]
            })

    return {
        "gross_recoverable": recovery,
        "collectability_score": 0.78,
        "net_expected_recovery": recovery * 0.78,
        "claim_breakdown": claim_details
    }


def compile_dossier(case_data: dict) -> str:
    """
    Generate the final formatted investigation dossier.
    Calls Claude to synthesize evidence into a professional report.
    """
    prompt = f"""
    Generate a formal healthcare fraud investigation dossier using
    ONLY the following data. Do not fabricate any numbers or claim IDs.

    CASE DATA:
    {json.dumps(case_data, indent=2)}

    Structure:
    # Investigation Dossier — Case {{case_id}}
    ## Priority: {{tier}} | Est. Recovery: ${{amount}}
    ### 1. Executive Summary
    ### 2. Entities Involved (table)
    ### 3. Evidence Table (claim details)
    ### 4. Statistical Comparison (vs peers)
    ### 5. Network Analysis (ring structure)
    ### 6. Applicable Billing Rules (cite specific CMS sections)
    ### 7. Similar Past Cases (table)
    ### 8. Recommended Actions (numbered, sequenced)
    ### 9. Recovery Estimate (table with amounts)

    RULES:
    - Every number must come from the provided data
    - Cite specific claim IDs and dates
    - Be conservative on recovery estimates
    """

    response = llm.invoke(prompt)
    return response.content
```

---

## 7. LangGraph Implementation

```python
from langgraph.graph import StateGraph, END
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, AIMessage
from typing import TypedDict, Annotated
import operator

# --- State ---
class InvestigationState(TypedDict):
    messages: Annotated[list, operator.add]
    current_phase: str       # scan / investigate / compile / review / done
    findings: dict
    dossier: str
    evidence_sufficient: bool
    loop_count: int

# --- LLM ---
llm = ChatBedrockConverse(
    model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    temperature=0,
    max_tokens=4096
)

# --- Agent Nodes ---

def orchestrator_node(state: InvestigationState) -> InvestigationState:
    """Reasons about what to do next. Delegates to agents."""
    response = llm.invoke([
        {"role": "system", "content": ORCHESTRATOR_PROMPT},
        *state["messages"],
        {"role": "user", "content": f"""
            Current phase: {state['current_phase']}
            Evidence sufficient: {state['evidence_sufficient']}
            Loop count: {state['loop_count']}
            What should we do next? Think step by step.
        """}
    ])
    return {
        "messages": [AIMessage(content=f"🤖 ORCHESTRATOR: {response.content}")],
    }


def investigation_node(state: InvestigationState) -> InvestigationState:
    """Runs investigation tools based on orchestrator's request."""
    investigation_agent = llm.bind_tools([
        scan_new_claims,
        profile_entity,
        compare_to_peers,
        get_claim_details,
        find_connections,
        find_ring,
        get_referral_history,
    ])
    response = investigation_agent.invoke([
        {"role": "system", "content": INVESTIGATION_AGENT_PROMPT},
        *state["messages"]
    ])
    # Execute tool calls, collect results
    return {
        "messages": [AIMessage(content=f"🔍 INVESTIGATION: {response.content}")],
        "findings": {**state.get("findings", {}), **new_findings}
    }


def dossier_node(state: InvestigationState) -> InvestigationState:
    """Assesses evidence and compiles dossier if sufficient."""
    dossier_agent = llm.bind_tools([
        assess_evidence,
        search_billing_rules,
        find_similar_cases,
        estimate_recovery,
        compile_dossier,
    ])
    response = dossier_agent.invoke([
        {"role": "system", "content": DOSSIER_AGENT_PROMPT},
        *state["messages"]
    ])
    return {
        "messages": [AIMessage(content=f"📋 DOSSIER: {response.content}")],
        "evidence_sufficient": evidence_check_result,
        "dossier": dossier_if_generated
    }

# --- Routing ---

def route_after_orchestrator(state: InvestigationState) -> str:
    if state["current_phase"] in ("scan", "investigate"):
        return "investigation"
    elif state["current_phase"] == "compile":
        return "dossier"
    elif state["current_phase"] == "done":
        return "end"
    return "investigation"  # default


def route_after_dossier(state: InvestigationState) -> str:
    if state["evidence_sufficient"]:
        return "orchestrator"   # finalize
    else:
        return "orchestrator"   # replan — will send back to investigation


# --- Build Graph ---

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

graph.add_edge("investigation", "orchestrator")  # always report back

graph.add_conditional_edges("dossier", route_after_dossier, {
    "orchestrator": "orchestrator"
})

# --- Compile and Run ---
app = graph.compile()

result = app.invoke({
    "messages": [HumanMessage(content="Investigate latest claims batch")],
    "current_phase": "scan",
    "findings": {},
    "dossier": "",
    "evidence_sufficient": False,
    "loop_count": 0
})
```

---

## 8. Graph Helper

```python
import networkx as nx

def build_graph() -> nx.DiGraph:
    """Build NetworkX graph from nodes and edges DataFrames."""
    G = nx.DiGraph()

    for _, row in graph_nodes_df.iterrows():
        G.add_node(
            row["id"],
            entity_type=row["entity_type"],
            anomaly_score=row.get("anomaly_score", 0),
            **row.get("attributes", {})
        )

    for _, row in graph_edges_df.iterrows():
        G.add_edge(
            row["src"],
            row["dst"],
            relationship=row["relationship"],
            weight=row["weight"],
            total_amount=row.get("total_amount", 0)
        )

    return G
```

---

## 9. Ring Visualization

```python
from pyvis.network import Network

def visualize_ring(ring_data: dict, output_path: str = "ring.html"):
    net = Network(
        height="600px", width="100%",
        bgcolor="#0a0a0a", font_color="white",
        directed=True
    )

    colors = {
        "provider": "#e74c3c",   # red
        "member": "#3498db",     # blue
        "facility": "#2ecc71",   # green
    }

    for entity in ring_data["entities"]:
        net.add_node(
            entity["id"],
            label=f"{entity['id']}\n({entity['entity_type']})\nScore: {entity['anomaly_score']:.2f}",
            color=colors.get(entity["entity_type"], "#95a5a6"),
            size=20 + (entity["anomaly_score"] * 30),
        )

    for edge in ring_data["edges"]:
        net.add_edge(
            edge["src"], edge["dst"],
            label=f"${edge['total_amount']:,.0f}",
            title=f"{edge['relationship']}: {edge['weight']} claims",
            width=max(1, edge["weight"] / 5),
            color="#ffffff55"
        )

    net.save_graph(output_path)
    return output_path
```

---

## 10. Synthetic Data Requirements

### Scale

| Table | Row Count |
|-------|-----------|
| providers | ~500 |
| members | ~5,000 |
| facilities | ~100 |
| claims | ~50,000 |

95% normal data. 5% injected fraud patterns.

### Fraud Scenarios to Inject

```python
fraud_scenarios = {
    "upcoding_ring": {
        "providers": 4,          # 1 primary + 3 referring
        "members": 12,
        "pattern": "CPT upcoding + concentrated referrals, "
                   "synchronized shift 8 months ago",
        "total_suspicious": 2_300_000,
        "recoverable": 252_600,
        "description": "HERO CASE for demo"
    },
    "phantom_billing": {
        "providers": 1,
        "members": 8,
        "pattern": "Bills for services on dates member wasn't seen",
        "total_suspicious": 89_000,
        "description": "Secondary case — different agent path"
    },
    "doctor_shopping": {
        "members": 5,
        "providers": 8,
        "pattern": "Members visiting multiple providers for opioids",
        "total_suspicious": 67_000,
        "description": "Non-ring case — agent handles differently"
    }
}
```

### Public Data Sources for Realistic Baselines

- CMS Medicare Provider Utilization & Payment Data
- CMS Synthetic Medicare Claims (SynPUF)
- NPPES NPI Registry
- CMS CPT/ICD reference tables

---

## 11. Example Agent Trace

This is what the demo shows — the reasoning trace:

```
🤖 ORCHESTRATOR: New claims batch received. Let me ask the Investigation
   Agent to scan for anomalies.
   → Delegating to Investigation Agent: "Scan latest claims for anomalies"

🔍 INVESTIGATION AGENT: [scans claims]
   Found 23 anomalous claims. Top finding: Provider P-4482, anomaly
   score 0.92, upcoding signal on knee procedures.

🤖 ORCHESTRATOR: P-4482 has the highest score. Could be isolated or
   part of something bigger. Let me check connections.
   → Delegating to Investigation Agent: "Map connections for P-4482"

🔍 INVESTIGATION AGENT: [maps graph]
   P-4482 connected to 3 referring providers (P-1190, P-3387, P-5521)
   and 12 shared members. Referral concentration 78% — 4.2x expected.
   This looks like a ring.

🤖 ORCHESTRATOR: Not an individual case — coordinated scheme. $2.3M
   suspicious billing. Critical priority. Sending to Dossier Agent.
   → Delegating to Dossier Agent: "Compile dossier for suspected ring"

📋 DOSSIER AGENT: I have billing data for P-4482 and ring structure.
   But referral pattern evidence is circumstantial. I need HISTORICAL
   referral data to confirm the concentration CHANGED.

   ⚠️ EVIDENCE ASSESSMENT: INSUFFICIENT
   REQUESTING: Historical referral patterns for referring providers.

🤖 ORCHESTRATOR: Fair point — we need to show the pattern CHANGED.
   Sending Investigation Agent back.
   → Delegating to Investigation Agent: "Pull 18-month referral
     history for P-1190, P-3387, P-5521"

🔍 INVESTIGATION AGENT: [queries historical data]
   Confirmed. All three shifted referral patterns ~8 months ago.
   Before: distributed across 6-8 surgeons.
   After: 78% concentrated on P-4482.
   Shift was sudden and synchronized.

🤖 ORCHESTRATOR: Smoking gun. Synchronized shift 8 months ago.
   → Delegating to Dossier Agent: "Updated evidence. Compile final dossier."

📋 DOSSIER AGENT:
   ✅ EVIDENCE ASSESSMENT: SUFFICIENT. Confidence: HIGH.
   Generating dossier...
   - Scheme: Upcoding + coordinated referral ring
   - Entities: 4 providers, 12 members, 47 claims
   - Estimated recovery: $252,600
   - Recommended actions: Request operative notes, issue pre-payment
     hold, refer to SIU for Anti-Kickback investigation

🤖 ORCHESTRATOR: Case CASE-2025-0342 created. Priority: P1 CRITICAL.
```

---

## 12. Build Plan

| Task | Hours |
|------|-------|
| Synthetic data generation (3 tables + fraud injection) | 3 hrs |
| Feature engineering (provider_features, member_features) | 2 hrs |
| Anomaly model (Isolation Forest, train + score) | 1 hr |
| Graph construction (NetworkX from claims) | 1 hr |
| FAISS index for billing rules (small corpus) | 1 hr |
| Investigation Agent (prompt + 7 tools) | 2 hrs |
| Dossier Agent (prompt + 5 tools) | 2 hrs |
| Orchestrator Agent (prompt + LangGraph wiring) | 2 hrs |
| PyVis ring visualization | 1 hr |
| Demo trace formatting + rehearsal | 2 hrs |
| **Total** | **~17 hrs** |

### Critical Path

```
Synthetic data ──→ Features ──→ Anomaly model ──┐
                        │                        ├──→ Investigation Agent ──┐
                        └──→ Graph (NetworkX) ───┘                         │
                                                                           ├──→ Orchestrator ──→ Demo
Billing rules FAISS index ──→ Dossier Agent ───────────────────────────────┘
```

---

## 13. Demo Script (5-7 Minutes)

### 0:00–0:30 — Problem
> "Healthcare fraud: $100B a year. Tools flag suspicious claims. But a flag
> is not an investigation. An analyst gets an alert, then spends 4 hours
> manually pulling data, checking connections, writing a case file.
> We built a team of AI agents that does the entire investigation."

### 0:30–1:00 — Architecture (30 sec max)
> "Three agents. An Orchestrator that decides what to investigate.
> A Detective that does the digging. A Case Writer that compiles the
> evidence — and pushes back if it's not enough."

### 1:00–3:30 — Watch the Agents Work
Show the reasoning trace. Three key beats:

**Beat 1 — Discovery:** Agent finds Provider P-4482, anomaly score 0.92.

**Beat 2 — The Ring:** Agent pulls the thread, finds 4 connected providers,
12 shared members, $2.3M suspicious billing. Show the PyVis ring visualization.

**Beat 3 — The Pushback:** ⭐ KEY MOMENT. Dossier Agent says "not enough
evidence." Orchestrator sends Detective back. Detective finds the synchronized
referral shift. NOW Dossier Agent compiles the case.

### 3:30–4:30 — The Dossier
Scroll through: executive summary, statistical comparison, billing rule
citations, recovery estimate ($252,600).

### 4:30–5:30 — Conversational Follow-Up
Analyst asks follow-up questions about the case.

### 5:30–6:30 — Close
> "We didn't build another fraud scorer. We built an investigation team —
> three agents that discover schemes, challenge each other's evidence,
> and produce court-ready case files.
> From suspicious bill to complete case file in 90 seconds."
```