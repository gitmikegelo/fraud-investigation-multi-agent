# Claims Investigation Copilot — Build Schema

## Stack
- Python 3.11+
- LangGraph + LangChain for agent orchestration
- Claude 3.5 Sonnet via AWS Bedrock for LLM
- Pandas for data (synthetic, in-memory)
- NetworkX for graph analysis
- scikit-learn Isolation Forest for anomaly detection
- FAISS for billing rules RAG
- PyVis for ring visualization

## Requirements

```txt
langgraph>=0.2.0
langchain-aws>=0.2.0
langchain-core>=0.3.0
boto3>=1.34.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
networkx>=3.0
faiss-cpu>=1.7.0
sentence-transformers>=2.2.0
pyvis>=0.3.0
```

---

## File Structure

```
claims-copilot/
├── data/
│   ├── generate_synthetic.py    # creates source DataFrames + injects fraud
│   ├── features.py              # computes provider_features_df, member_features_df
│   ├── anomaly.py               # trains Isolation Forest, produces anomaly_scores_df
│   ├── graph.py                 # builds NetworkX DiGraph from claims
│   └── past_cases.py            # creates past_cases_df for similar case lookup
├── billing_rules/
│   ├── rules.json               # CMS/OIG billing rules corpus
│   └── index.py                 # builds FAISS index, provides search function
├── agents/
│   ├── prompts.py               # all 3 agent system prompts
│   ├── tools_investigation.py   # 7 tools for Investigation Agent
│   ├── tools_dossier.py         # 5 tools for Dossier Agent
│   ├── nodes.py                 # 3 node functions for LangGraph
│   ├── routing.py               # routing functions for conditional edges
│   └── workflow.py              # LangGraph StateGraph assembly + compile
├── viz/
│   └── ring_viz.py              # PyVis ring visualization
├── app.py                       # global data loader + entry point
└── requirements.txt
```

---

## Data Layer

### Global Data (loaded once in app.py, passed to tools)

```python
# app.py loads all data at startup into a DataStore dataclass
@dataclass
class DataStore:
    claims_df: pd.DataFrame
    providers_df: pd.DataFrame
    members_df: pd.DataFrame
    provider_features_df: pd.DataFrame
    member_features_df: pd.DataFrame
    anomaly_scores_df: pd.DataFrame
    graph: nx.DiGraph
    past_cases_df: pd.DataFrame
    faiss_index: Any           # FAISS index object
    billing_rules: list[dict]  # raw rules for retrieval
    embedder: Any              # sentence-transformers model

# All tool functions receive `data: DataStore` as first argument
```

### Source Tables

```python
# claims_df — ~50K rows
{
    "claim_id": str,              # PK, format "CLM-XXXX"
    "member_id": str,             # FK, format "M-XXXX"
    "provider_id": str,           # FK, format "P-XXXX"
    "referring_provider_id": str,  # FK nullable, format "P-XXXX"
    "facility_id": str,           # FK, format "F-XXX"
    "cpt_code": str,              # e.g. "27447", "99213"
    "icd_code": str,              # e.g. "M17.11"
    "billed_amount": float,
    "paid_amount": float,
    "service_date": datetime,
    "place_of_service": str,      # "office", "hospital_inpatient", "er"
    "claim_type": str,            # "professional", "institutional", "pharmacy"
}

# providers_df — ~500 rows
{
    "provider_id": str,   # PK
    "specialty": str,     # "orthopedic_surgery", "family_medicine", "cardiology", etc.
    "region": str,        # "region_1" through "region_5"
    "peer_group": str,    # "{specialty}_{region}"
}

# members_df — ~5K rows
{
    "member_id": str,  # PK
    "age": int,        # 18-90
    "gender": str,     # "M", "F"
    "region": str,     # "region_1" through "region_5"
}
```

### Feature Engineering (data/features.py)

Compute from claims_df. One row per provider.

```python
def compute_provider_features(claims_df, providers_df) -> pd.DataFrame:
    """
    For each provider, compute:

    claims_per_month:
        total claims / months active

    unique_patients_per_month:
        count distinct member_id / months active

    claims_per_patient:
        total claims / distinct members

    pct_high_complexity:
        count(cpt_code in ["99214","99215","99223","99232","99233"])
        / total claims for that provider

    avg_billed_per_claim:
        mean(billed_amount)

    top_cpt_concentration:
        count of most frequent cpt_code / total claims

    weekend_billing_rate:
        count(service_date is Saturday or Sunday) / total claims

    avg_patients_per_day:
        on days they billed, mean(distinct member_id per day)

    duplicate_claim_rate:
        count of claims where (member_id, cpt_code, service_date) appears >1
        / total claims

    same_patient_same_day_rate:
        count of (member_id, service_date) pairs with >1 claim
        / total claims

    referral_concentration:
        For providers who RECEIVE referrals:
        sum of top 3 referring_provider_id counts / total referrals received

    referral_source_count:
        count distinct referring_provider_id

    out_of_specialty_rate:
        Requires a mapping of specialty -> expected CPT code prefixes.
        count(cpt_code not in expected set) / total claims.
        Simplified: can hardcode a dict of specialty -> common CPT prefixes.
    """
```

### Anomaly Model (data/anomaly.py)

```python
def train_anomaly_model(provider_features_df, providers_df) -> pd.DataFrame:
    """
    1. Input features: all numeric columns from provider_features_df
    2. Normalize per peer_group (z-score within group):
       for each feature, compute (value - peer_mean) / peer_std
    3. Train sklearn IsolationForest(contamination=0.05, random_state=42)
       on the z-scored features
    4. Score all providers: anomaly_score = model.decision_function(),
       rescaled to 0.0-1.0 (0=normal, 1=most anomalous)
    5. For each scored entity, compute top_features:
       the 3 features with highest absolute z-score, as list of dicts:
       [{"feature_name": str, "feature_value": float, "peer_avg": float, "z_score": float}]

    Returns anomaly_scores_df with columns:
        entity_id, entity_type("provider"), anomaly_score, top_features, total_billed
    """
```

### Graph Construction (data/graph.py)

```python
def build_graph(claims_df, providers_df, members_df, anomaly_scores_df) -> nx.DiGraph:
    """
    Nodes:
        Every unique provider_id — attrs: entity_type="provider", anomaly_score, specialty, region
        Every unique member_id — attrs: entity_type="member", anomaly_score (if scored, else 0)
        Every unique facility_id — attrs: entity_type="facility"

    Edges (aggregated from claims):
        provider -> member (BILLED_FOR):
            weight = count of claims between them
            total_amount = sum(billed_amount)

        provider -> provider (REFERRED_TO):
            From rows where referring_provider_id is not null.
            Edge from referring_provider_id -> provider_id
            weight = count of such referrals
            total_amount = sum(billed_amount) of those claims

        provider -> facility (OPERATES_AT):
            weight = count of claims at that facility
            total_amount = sum(billed_amount)
    """
```

### Past Cases (data/past_cases.py)

```python
# past_cases_df — ~20 rows of fake resolved cases for find_similar_cases tool
{
    "case_id": str,           # "CASE-2024-XXX"
    "scheme_pattern": str,    # "upcoding", "phantom", "ring", "doctor_shopping"
    "specialty": str,
    "hypothesis": str,
    "status": str,            # "confirmed_fraud", "legitimate", "escalated"
    "decision": str,          # "confirmed", "legitimate", "escalated"
    "decision_reason": str,
    "estimated_recovery": float,
    "actual_recovery": float,
}
# Include 1-2 cases matching each fraud scenario for retrieval.
# Include at least 1 case for P-4482 that was previously closed as
# "legitimate" (high volume, not upcoding) — the dossier references this.
```

### Billing Rules Corpus (billing_rules/rules.json)

```json
[
    {
        "rule_id": "CMS-4.12",
        "section": "CMS Guidelines §4.12",
        "applicable_codes": ["27447", "27446"],
        "rule_text": "CPT 27447 (total knee arthroplasty) requires documentation of tricompartmental involvement. Without documentation confirming all three compartments are affected, the appropriate code is 27446 (unicompartmental).",
        "summary": "Total knee requires tricompartmental documentation, else use partial knee code."
    },
    {
        "rule_id": "OIG-AKS-2023",
        "section": "OIG Compliance Guidance (2023)",
        "applicable_codes": [],
        "context_keywords": ["referral", "concentration", "kickback"],
        "rule_text": "Referral patterns exceeding 50% concentration from any single source trigger Anti-Kickback Statute (AKS) review under 42 U.S.C. § 1320a-7b(b).",
        "summary": "Referral concentration >50% triggers anti-kickback review."
    },
    {
        "rule_id": "CMS-UPCODING-01",
        "section": "CMS Upcoding Guidance",
        "applicable_codes": ["99211", "99212", "99213", "99214", "99215"],
        "rule_text": "Consistent billing of higher-complexity E&M codes at rates exceeding 2 standard deviations above peer group warrants medical record audit.",
        "summary": "High-complexity E&M codes >2 std dev above peers triggers audit."
    },
    {
        "rule_id": "CMS-DUP-01",
        "section": "CMS Claims Processing Manual Ch.1 §80.3",
        "applicable_codes": [],
        "context_keywords": ["duplicate", "resubmission"],
        "rule_text": "Duplicate claims are defined as claims submitted for the same beneficiary, same date of service, same provider, and same procedure code. Such claims shall be denied.",
        "summary": "Same patient/date/provider/code = duplicate, must deny."
    },
    {
        "rule_id": "CMS-UNBUNDLE-01",
        "section": "NCCI Correct Coding Initiative",
        "applicable_codes": [],
        "context_keywords": ["unbundling", "bundled", "component"],
        "rule_text": "Component codes that are integral to a comprehensive code shall not be billed separately. See NCCI edit tables for code pair restrictions.",
        "summary": "Don't bill components separately when a bundled code exists."
    }
]
```

FAISS index builder:

```python
# billing_rules/index.py
def build_billing_rules_index(rules_path="billing_rules/rules.json"):
    """
    1. Load rules from JSON
    2. For each rule, create search text = rule_text + summary + applicable_codes joined
    3. Embed using sentence-transformers (model: "all-MiniLM-L6-v2")
    4. Build FAISS IndexFlatL2
    5. Return (index, rules_list, embedder)

    Search function:
    def search_rules(query: str, index, rules, embedder, k=5) -> list[dict]:
        query_vec = embedder.encode([query])
        D, I = index.search(query_vec, k)
        return [rules[i] for i in I[0] if i < len(rules)]
    """
```

---

## Synthetic Data Generation (data/generate_synthetic.py)

```python
def generate_all():
    """
    1. Generate providers_df (500 rows)
       - 10 specialties: orthopedic_surgery, family_medicine, cardiology,
         dermatology, neurology, oncology, psychiatry, radiology,
         emergency_medicine, internal_medicine
       - 5 regions: region_1 through region_5
       - ~10 providers per specialty per region = 500
       - peer_group = f"{specialty}_{region}"

    2. Generate members_df (5000 rows)
       - age: normal distribution mean=55, std=15, clipped 18-90
       - gender: 50/50 M/F
       - region: uniform across 5 regions

    3. Generate claims_df (50000 rows) — NORMAL baseline
       - For each claim, pick random provider, random member (same region weighted higher)
       - cpt_code: weighted by specialty (e.g. orthopedic → knee/hip codes more common)
       - icd_code: paired with cpt_code (logical medical pairing)
       - billed_amount: based on cpt_code with normal noise
       - paid_amount: billed * random(0.7, 0.95)
       - service_date: uniform over last 18 months
       - referring_provider_id: 30% of claims have one, distributed across multiple providers
       - facility_id: 20 facilities, provider affiliated with 1-2

    4. INJECT FRAUD — upcoding_ring (hero case)
       Provider P-4482 (orthopedic_surgery, region_4):
       - 89% of knee claims use CPT 27447 (peers avg 23%)
       - billed_amount ~$47K per knee claim (peers ~$31K)
       - 12 specific members (M-2847, M-3102, M-4455, M-5501, + 8 more)
       - 47 fraudulent claims over last 8 months

       3 referring providers (P-1190, P-3387, P-5521):
       - Before 8 months ago: referrals distributed across 6-8 ortho surgeons
       - After: 78% of knee referrals go to P-4482
       - The shift happens at the same month for all 3 (synchronized)

    5. INJECT FRAUD — phantom_billing
       1 provider, 8 members, ~20 claims
       - Bills on weekends at >50% rate (peers <5%)
       - avg_patients_per_day = 60+ (peers ~25)
       - Some claims on dates where member has conflicting claims elsewhere

    6. INJECT FRAUD — doctor_shopping
       5 members visiting 8+ providers each in 3 months
       - All for pain management / opioid-related CPT codes
       - Geographically spread visits

    Return claims_df, providers_df, members_df
    """
```

### CPT/ICD Reference Data (for realistic generation)

```python
# Simplified mapping for synthetic data
CPT_BY_SPECIALTY = {
    "orthopedic_surgery": {
        "27447": {"desc": "total knee arthroplasty", "avg_billed": 47000, "weight": 0.23},
        "27446": {"desc": "partial knee arthroplasty", "avg_billed": 31000, "weight": 0.15},
        "27130": {"desc": "total hip arthroplasty", "avg_billed": 45000, "weight": 0.12},
        "29881": {"desc": "knee arthroscopy", "avg_billed": 8500, "weight": 0.25},
        "20610": {"desc": "joint injection", "avg_billed": 350, "weight": 0.25},
    },
    "family_medicine": {
        "99211": {"desc": "office visit minimal", "avg_billed": 25, "weight": 0.10},
        "99212": {"desc": "office visit low", "avg_billed": 45, "weight": 0.20},
        "99213": {"desc": "office visit moderate", "avg_billed": 110, "weight": 0.40},
        "99214": {"desc": "office visit mod-high", "avg_billed": 175, "weight": 0.20},
        "99215": {"desc": "office visit high", "avg_billed": 250, "weight": 0.10},
    },
    # ... add more specialties as needed
}

CPT_TO_ICD = {
    "27447": ["M17.11", "M17.12", "M17.0"],  # knee osteoarthritis
    "27446": ["M17.11", "M17.12"],
    "99213": ["J06.9", "M54.5", "E11.9", "I10"],  # common diagnoses
    # ...
}
```

---

## Agent Prompts (agents/prompts.py)

```python
ORCHESTRATOR_PROMPT = """
You are the lead investigator for a healthcare fraud investigation unit.
You have two specialist agents you delegate to:

1. INVESTIGATION AGENT ("The Detective")
   - scan_new_claims: scan for anomalies
   - profile_entity: behavioral profile of a provider/member
   - compare_to_peers: z-score comparison against peer group
   - get_claim_details: raw claim data
   - find_connections: graph BFS from an entity
   - find_ring: detect suspicious clusters
   - get_referral_history: monthly referral patterns over time

2. DOSSIER AGENT ("The Case Writer")
   - assess_evidence: check if evidence is SUFFICIENT or INSUFFICIENT
   - search_billing_rules: find relevant CMS/OIG rules
   - find_similar_cases: find past resolved cases with similar patterns
   - estimate_recovery: calculate recoverable amounts
   - compile_dossier: generate full investigation report

YOUR PROCESS:
1. Delegate to Investigation Agent to scan claims for anomalies
2. Review findings — decide which warrant deeper investigation
3. For promising leads, delegate to Investigation Agent to map connections
4. Decide: individual case or coordinated ring?
5. When ready, delegate to Dossier Agent to compile case
6. IF Dossier Agent says INSUFFICIENT → delegate back to Investigation
   Agent for the specific missing evidence
7. When Dossier Agent says SUFFICIENT → finalize case
8. Stop if pattern is clearly legitimate

RULES:
- Think out loud before every decision
- You have NO tools yourself — only delegate
- Max 5 loops before forcing a decision
- When a ring is discovered, prioritize it over individual anomalies
- Always explain your reasoning before delegating

OUTPUT FORMAT for each turn:
REASONING: [your thinking]
ACTION: delegate_to_investigation | delegate_to_dossier | finalize | stop
REQUEST: [specific request to the agent]
"""

INVESTIGATION_AGENT_PROMPT = """
You are a healthcare fraud detective. You use tools to investigate claims
data for anomalies, suspicious patterns, and entity connections.

Available tools:
- scan_new_claims(since_days): scan for anomalies, returns scored entities
- profile_entity(entity_id): full behavioral profile
- compare_to_peers(entity_id, metric): z-score against peer group
- get_claim_details(entity_id, limit): raw claim rows
- find_connections(entity_id, depth): graph BFS, connection density
- find_ring(min_anomaly_score, min_entities): detect suspicious clusters
- get_referral_history(provider_id, months): monthly referral distribution

Investigation approach:
1. Start broad (scan), then narrow (profile specific entities)
2. Always check connections — individuals may be part of rings
3. Report findings with specific numbers and entity IDs
4. State whether pattern looks suspicious or potentially legitimate
5. When asked to dig deeper, use multiple tools

Return findings in structured format with specific numbers.
"""

DOSSIER_AGENT_PROMPT = """
You are a senior healthcare fraud analyst who writes formal case files.

Available tools:
- assess_evidence(hypothesis, evidence, scheme_pattern): checks sufficiency
- search_billing_rules(cpt_codes, context): CMS/OIG rule search
- find_similar_cases(scheme_pattern, specialty): past case lookup
- estimate_recovery(flagged_claims, peer_benchmarks): calculate recovery
- compile_dossier(case_data): generate markdown investigation report

CRITICAL RULE:
You MUST call assess_evidence FIRST before compile_dossier.
If assessment is INSUFFICIENT:
- State exactly what evidence is missing
- Explain why it matters for the case
- Request specific additional investigation
- Do NOT compile a dossier with weak evidence

If assessment is SUFFICIENT:
1. search_billing_rules for applicable regulations
2. find_similar_cases for precedent
3. estimate_recovery for dollar amounts
4. compile_dossier with all gathered data

Dossier structure:
1. Executive Summary (2-3 sentences)
2. Entities Involved (table)
3. Evidence Table (flagged claims)
4. Statistical Comparison (vs peers, z-scores)
5. Network Analysis (ring structure if applicable)
6. Applicable Billing Rules (cite CMS sections)
7. Similar Past Cases (table)
8. Recommended Actions (numbered, sequenced, with timelines)
9. Recovery Estimate (table with gross, collectability, net)
"""
```

---

## Tool Implementations

### Investigation Tools (agents/tools_investigation.py)

All tools take `data: DataStore` as first arg (bound via closure or partial).

```python
def scan_new_claims(data: DataStore, since_days: int = 30) -> list[dict]:
    """Return entities with anomaly_score > 0.5, sorted desc."""
    cutoff = datetime.now() - timedelta(days=since_days)
    flagged = data.anomaly_scores_df[
        data.anomaly_scores_df["anomaly_score"] > 0.5
    ].sort_values("anomaly_score", ascending=False)
    return flagged.head(20).to_dict("records")


def profile_entity(data: DataStore, entity_id: str) -> dict:
    """Merge provider info + features into single dict."""
    provider = data.providers_df[data.providers_df["provider_id"] == entity_id]
    features = data.provider_features_df[
        data.provider_features_df["provider_id"] == entity_id
    ]
    if provider.empty:
        return {"error": f"Entity {entity_id} not found"}
    result = {**provider.iloc[0].to_dict()}
    if not features.empty:
        result.update(features.iloc[0].to_dict())
    return result


def compare_to_peers(data: DataStore, entity_id: str, metric: str) -> dict:
    """Z-score of entity's metric vs peer group."""
    entity_row = data.provider_features_df[
        data.provider_features_df["provider_id"] == entity_id
    ]
    if entity_row.empty:
        return {"error": f"Entity {entity_id} not found"}

    peer_group = data.providers_df[
        data.providers_df["provider_id"] == entity_id
    ]["peer_group"].iloc[0]

    peers = data.provider_features_df.merge(
        data.providers_df[["provider_id", "peer_group"]], on="provider_id"
    )
    peers = peers[peers["peer_group"] == peer_group]

    entity_value = entity_row.iloc[0][metric]
    peer_avg = peers[metric].mean()
    peer_std = peers[metric].std()
    z_score = (entity_value - peer_avg) / peer_std if peer_std > 0 else 0

    return {
        "entity_id": entity_id,
        "metric": metric,
        "entity_value": round(float(entity_value), 4),
        "peer_avg": round(float(peer_avg), 4),
        "z_score": round(float(z_score), 2),
        "peer_count": len(peers),
    }


def get_claim_details(data: DataStore, entity_id: str, limit: int = 20) -> list[dict]:
    """Raw claims for a provider or member."""
    mask = (data.claims_df["provider_id"] == entity_id) | \
           (data.claims_df["member_id"] == entity_id)
    result = data.claims_df[mask].sort_values("service_date", ascending=False).head(limit)
    return result.to_dict("records")


def find_connections(data: DataStore, entity_id: str, depth: int = 2) -> dict:
    """NetworkX BFS from entity. Returns connected entities + density."""
    G = data.graph
    if entity_id not in G:
        return {"error": f"Entity {entity_id} not in graph"}

    paths = dict(nx.single_source_shortest_path(G, entity_id, cutoff=depth))

    connected = []
    for target, path in paths.items():
        if target != entity_id:
            node_data = G.nodes[target]
            connected.append({
                "id": target,
                "entity_type": node_data.get("entity_type"),
                "anomaly_score": node_data.get("anomaly_score", 0),
                "hops": len(path) - 1,
            })

    subgraph = G.subgraph(list(paths.keys()))
    density = nx.density(subgraph)

    return {
        "entity_id": entity_id,
        "connected_entities": sorted(connected, key=lambda x: x["anomaly_score"], reverse=True),
        "connection_density": round(density, 3),
        "total_entities": len(connected),
    }


def find_ring(
    data: DataStore,
    min_anomaly_score: float = 0.5,
    min_entities: int = 3
) -> list[dict]:
    """Connected components filtered by avg anomaly score."""
    G = data.graph
    components = list(nx.connected_components(G.to_undirected()))

    rings = []
    for comp in components:
        entities = []
        total_anomaly = 0
        total_billed = 0

        for node in comp:
            nd = G.nodes[node]
            score = nd.get("anomaly_score", 0)
            total_anomaly += score
            entities.append({
                "id": node,
                "entity_type": nd.get("entity_type"),
                "anomaly_score": round(score, 3),
            })

        avg_anomaly = total_anomaly / len(comp) if comp else 0

        if len(comp) >= min_entities and avg_anomaly > min_anomaly_score:
            # sum billed from edges
            sub = G.subgraph(comp)
            total_billed = sum(
                d.get("total_amount", 0) for _, _, d in sub.edges(data=True)
            )
            rings.append({
                "entity_count": len(comp),
                "avg_anomaly": round(avg_anomaly, 3),
                "total_billed": round(total_billed, 2),
                "density": round(nx.density(sub), 3),
                "entities": sorted(entities, key=lambda x: x["anomaly_score"], reverse=True),
            })

    return sorted(rings, key=lambda r: r["avg_anomaly"], reverse=True)


def get_referral_history(
    data: DataStore, provider_id: str, months: int = 18
) -> list[dict]:
    """Monthly referral breakdown. Shows concentration changes over time."""
    cutoff = datetime.now() - timedelta(days=months * 30)
    ref = data.claims_df[
        (data.claims_df["provider_id"] == provider_id)
        & (data.claims_df["referring_provider_id"].notna())
        & (data.claims_df["service_date"] >= cutoff)
    ].copy()

    if ref.empty:
        return []

    ref["month"] = ref["service_date"].dt.to_period("M").astype(str)
    monthly = (
        ref.groupby(["month", "referring_provider_id"])
        .size()
        .reset_index(name="referral_count")
    )
    totals = monthly.groupby("month")["referral_count"].transform("sum")
    monthly["referral_pct"] = (monthly["referral_count"] / totals).round(3)

    return monthly.sort_values(["month", "referral_pct"], ascending=[True, False]).to_dict("records")
```

### Dossier Tools (agents/tools_dossier.py)

```python
def assess_evidence(
    data: DataStore,
    hypothesis: str,
    evidence: dict,
    scheme_pattern: str
) -> dict:
    """
    evidence dict expected keys:
        anomaly_features: list[dict] each with "z_score"
        supporting_facts: list[str]
        historical_comparison: any truthy value or None
        connection_density: float (for ring patterns)
        referral_shift_confirmed: bool (for referral patterns)
    """
    checks = {
        "statistical_significance": all(
            f.get("z_score", 0) > 2.0
            for f in evidence.get("anomaly_features", [])
        ),
        "multiple_evidence_points": len(evidence.get("supporting_facts", [])) >= 3,
        "temporal_pattern": evidence.get("historical_comparison") is not None,
        "ring_evidence": (
            evidence.get("connection_density", 0) > 2.0
            if "ring" in scheme_pattern else True
        ),
        "referral_history": (
            evidence.get("referral_shift_confirmed", False)
            if "referral" in scheme_pattern else True
        ),
    }

    missing = [k for k, v in checks.items() if not v]
    requirements = {
        "statistical_significance": "Need z-scores > 2.0 on anomaly features",
        "multiple_evidence_points": "Need at least 3 independent supporting facts",
        "temporal_pattern": "Need historical comparison showing behavior changed over time",
        "ring_evidence": "Need connection density > 2.0 to confirm ring structure",
        "referral_history": "Need confirmed referral pattern shift with timeline",
    }

    return {
        "assessment": "SUFFICIENT" if not missing else "INSUFFICIENT",
        "checks_passed": [k for k, v in checks.items() if v],
        "checks_failed": missing,
        "missing_evidence": [requirements[m] for m in missing],
    }


def search_billing_rules(
    data: DataStore, cpt_codes: list[str], context: str
) -> list[dict]:
    """FAISS similarity search over billing rules corpus."""
    query = f"Billing rules for CPT codes {', '.join(cpt_codes)}. Context: {context}"
    query_vec = data.embedder.encode([query])
    D, I = data.faiss_index.search(np.array(query_vec).astype("float32"), k=5)
    results = []
    for idx in I[0]:
        if 0 <= idx < len(data.billing_rules):
            results.append(data.billing_rules[idx])
    return results


def find_similar_cases(
    data: DataStore, scheme_pattern: str, specialty: str = None
) -> list[dict]:
    """Lookup past resolved cases."""
    matches = data.past_cases_df[data.past_cases_df["scheme_pattern"] == scheme_pattern]
    if specialty:
        matches = matches[matches["specialty"] == specialty]
    return matches.head(5).to_dict("records")


def estimate_recovery(
    data: DataStore, flagged_claims: list[dict], peer_benchmarks: dict
) -> dict:
    """
    flagged_claims: list of dicts with keys: claim_id, flag, paid_amount, expected_cpt (if upcoding)
    peer_benchmarks: dict of {cpt_code: {"avg_paid": float}}
    """
    recovery = 0
    breakdown = []

    for claim in flagged_claims:
        flag = claim.get("flag", "")
        if flag == "upcoding":
            expected = peer_benchmarks.get(claim.get("expected_cpt", ""), {}).get("avg_paid", 0)
            delta = claim["paid_amount"] - expected
            if delta > 0:
                recovery += delta
                breakdown.append({
                    "claim_id": claim["claim_id"],
                    "flag": "upcoding",
                    "paid": claim["paid_amount"],
                    "expected": expected,
                    "recoverable": round(delta, 2),
                })
        elif flag in ("duplicate", "phantom"):
            recovery += claim["paid_amount"]
            breakdown.append({
                "claim_id": claim["claim_id"],
                "flag": flag,
                "recoverable": claim["paid_amount"],
            })

    collectability = 0.78
    return {
        "gross_recoverable": round(recovery, 2),
        "collectability_score": collectability,
        "net_expected_recovery": round(recovery * collectability, 2),
        "claim_breakdown": breakdown,
    }


def compile_dossier(data: DataStore, case_data: dict, llm) -> str:
    """
    Calls Claude to generate markdown dossier.
    case_data should contain all evidence, rules, similar cases, recovery estimate.
    """
    prompt = f"""Generate a formal healthcare fraud investigation dossier using
ONLY the following data. Do not fabricate any numbers, claim IDs, or statistics.

CASE DATA:
{json.dumps(case_data, indent=2, default=str)}

Follow this exact structure:

# Investigation Dossier — Case {{case_id}}
## Priority: {{tier}} | Est. Recovery: ${{amount}}

### 1. Executive Summary
(2-3 sentences. What is happening and how much money.)

### 2. Entities Involved
(Table: Entity | Type | Role | Anomaly Score | Key Flag)

### 3. Evidence Table
(Table: Claim ID | Date | CPT | Billed | Paid | Flag)

### 4. Statistical Comparison
(Table: Metric | This Provider | Peer Average | Z-Score)

### 5. Network Analysis
(Ring structure and referral patterns if applicable)

### 6. Applicable Billing Rules
(Cite specific CMS/OIG sections from provided rules)

### 7. Similar Past Cases
(Table: Past Case | Pattern | Resolution | Recovery)

### 8. Recommended Actions
(Numbered, sequenced, with timelines)

### 9. Recovery Estimate
(Table: Category | Amount. Include collectability.)

RULES:
- Every number must come from the provided data
- Cite specific claim IDs and dates
- Be conservative on recovery estimates"""

    response = llm.invoke(prompt)
    return response.content
```

---

## LangGraph Wiring (agents/workflow.py)

### State

```python
class InvestigationState(TypedDict):
    messages: Annotated[list, operator.add]  # full conversation history
    current_phase: str        # scan | investigate | compile | done
    findings: dict            # accumulated investigation findings
    dossier: str              # final dossier markdown (empty until compiled)
    evidence_sufficient: bool # set by dossier agent
    loop_count: int           # increment each orchestrator turn, max 5
```

### Node Functions (agents/nodes.py)

```python
def orchestrator_node(state: InvestigationState, llm) -> dict:
    """
    1. Build prompt with ORCHESTRATOR_PROMPT + full message history
       + current state summary (phase, evidence_sufficient, loop_count)
    2. Call Claude
    3. Parse response for ACTION (delegate_to_investigation | delegate_to_dossier | finalize | stop)
    4. Update current_phase based on action:
       - delegate_to_investigation → "investigate"
       - delegate_to_dossier → "compile"
       - finalize or stop → "done"
    5. Increment loop_count
    6. If loop_count >= 5, force current_phase = "compile"
    7. Return updated state fields
    """


def investigation_node(state: InvestigationState, llm, data: DataStore) -> dict:
    """
    1. Build prompt with INVESTIGATION_AGENT_PROMPT + messages
    2. Bind investigation tools to LLM
    3. Run tool-calling loop:
       - LLM decides which tool(s) to call
       - Execute tool, append result to messages
       - Repeat until LLM returns final text response (no more tool calls)
    4. Add findings to state.findings dict
    5. Return updated state
    """


def dossier_node(state: InvestigationState, llm, data: DataStore) -> dict:
    """
    1. Build prompt with DOSSIER_AGENT_PROMPT + messages + all findings
    2. Bind dossier tools to LLM
    3. LLM MUST call assess_evidence first
    4. If INSUFFICIENT:
       - Set evidence_sufficient = False
       - Add message explaining what's missing
    5. If SUFFICIENT:
       - Call search_billing_rules, find_similar_cases, estimate_recovery
       - Call compile_dossier with all gathered data
       - Set evidence_sufficient = True
       - Set dossier = compiled markdown
    6. Return updated state
    """
```

### Routing (agents/routing.py)

```python
def route_after_orchestrator(state: InvestigationState) -> str:
    if state["current_phase"] == "done":
        return "end"
    elif state["current_phase"] == "compile":
        return "dossier"
    else:
        return "investigation"


def route_after_dossier(state: InvestigationState) -> str:
    # Always returns to orchestrator.
    # Orchestrator will check evidence_sufficient and decide:
    #   - if True → finalize (done)
    #   - if False → send back to investigation
    return "orchestrator"
```

### Graph Assembly

```python
graph = StateGraph(InvestigationState)

graph.add_node("orchestrator", orchestrator_node)
graph.add_node("investigation", investigation_node)
graph.add_node("dossier", dossier_node)

graph.set_entry_point("orchestrator")

graph.add_conditional_edges("orchestrator", route_after_orchestrator, {
    "investigation": "investigation",
    "dossier": "dossier",
    "end": END,
})

graph.add_edge("investigation", "orchestrator")

graph.add_conditional_edges("dossier", route_after_dossier, {
    "orchestrator": "orchestrator",
})

app = graph.compile()
```

### Entry Point (app.py)

```python
def main():
    # 1. Generate/load synthetic data
    claims_df, providers_df, members_df = generate_all()

    # 2. Compute features
    provider_features_df = compute_provider_features(claims_df, providers_df)
    member_features_df = compute_member_features(claims_df, members_df)

    # 3. Train anomaly model + score
    anomaly_scores_df = train_anomaly_model(provider_features_df, providers_df)

    # 4. Build graph
    graph = build_graph(claims_df, providers_df, members_df, anomaly_scores_df)

    # 5. Load billing rules + FAISS index
    faiss_index, billing_rules, embedder = build_billing_rules_index()

    # 6. Load past cases
    past_cases_df = generate_past_cases()

    # 7. Bundle into DataStore
    data = DataStore(...)

    # 8. Init LLM
    llm = ChatBedrock(model_id="anthropic.claude-3-5-sonnet-20241022-v2:0")

    # 9. Build + run agent workflow
    app = build_workflow(llm, data)
    result = app.invoke({
        "messages": [HumanMessage(content="Investigate latest claims batch")],
        "current_phase": "scan",
        "findings": {},
        "dossier": "",
        "evidence_sufficient": False,
        "loop_count": 0,
    })

    # 10. Print trace + dossier
    for msg in result["messages"]:
        print(msg.content)
    print(result["dossier"])
```

---

## Ring Visualization (viz/ring_viz.py)

```python
def visualize_ring(ring_data: dict, graph: nx.DiGraph, output_path: str = "ring.html") -> str:
    """
    ring_data: output from find_ring tool (one ring)
        - entities: list[{id, entity_type, anomaly_score}]
    graph: NetworkX DiGraph (to get edges between ring entities)

    Node colors: provider=#e74c3c, member=#3498db, facility=#2ecc71
    Node size: 20 + (anomaly_score * 30)
    Edge width: max(1, weight / 5)
    Edge label: ${total_amount:,.0f}
    Background: #0a0a0a, font: white
    """
    net = Network(height="600px", width="100%", bgcolor="#0a0a0a",
                  font_color="white", directed=True)

    colors = {"provider": "#e74c3c", "member": "#3498db", "facility": "#2ecc71"}
    ring_ids = {e["id"] for e in ring_data["entities"]}

    for entity in ring_data["entities"]:
        net.add_node(entity["id"],
                     label=f"{entity['id']}\n{entity['entity_type']}\n{entity['anomaly_score']:.2f}",
                     color=colors.get(entity["entity_type"], "#95a5a6"),
                     size=20 + (entity["anomaly_score"] * 30))

    sub = graph.subgraph(ring_ids)
    for src, dst, d in sub.edges(data=True):
        net.add_edge(src, dst,
                     label=f"${d.get('total_amount', 0):,.0f}",
                     title=f"{d.get('relationship','')}: {d.get('weight',0)} claims",
                     width=max(1, d.get("weight", 1) / 5),
                     color="#ffffff55")

    net.save_graph(output_path)
    return output_path
```

---

## Expected Demo Trace

```
🤖 ORCHESTRATOR: Scanning claims for anomalies.
   → Delegate to Investigation Agent

🔍 INVESTIGATION: Found 23 anomalous entities.
   Top: P-4482 (score 0.92, orthopedic_surgery, upcoding signal)

🤖 ORCHESTRATOR: P-4482 highest score. Checking connections.
   → Delegate to Investigation Agent

🔍 INVESTIGATION: P-4482 connected to P-1190, P-3387, P-5521 (referring).
   12 shared members. Referral concentration 78% (expected ~18%).
   Connection density 4.2x. Possible ring.

🤖 ORCHESTRATOR: Coordinated scheme. $2.3M suspicious. Sending to Dossier.
   → Delegate to Dossier Agent

📋 DOSSIER: assess_evidence → INSUFFICIENT.
   Missing: referral_history (need to confirm pattern CHANGED, not always concentrated)

🤖 ORCHESTRATOR: Need historical referral data. Sending Investigation back.
   → Delegate to Investigation Agent

🔍 INVESTIGATION: get_referral_history for P-1190, P-3387, P-5521.
   All three shifted to P-4482 ~8 months ago. Before: distributed. After: 78%.
   Shift synchronized across all three.

🤖 ORCHESTRATOR: Smoking gun. Updated evidence. Back to Dossier.
   → Delegate to Dossier Agent

📋 DOSSIER: assess_evidence → SUFFICIENT.
   Compiling dossier... search_billing_rules... estimate_recovery...
   Case CASE-2025-0342. P1 CRITICAL. Recovery: $252,600.

🤖 ORCHESTRATOR: Case finalized. Done.
```