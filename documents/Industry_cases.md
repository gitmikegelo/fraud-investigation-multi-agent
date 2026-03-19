Reasoning: The user wants real-world fraud detection pipelines from known companies that actually worked, and lessons applicable to their Prudential Life claims adjudication + fraud detection use case.

Let me share what's publicly known about fraud detection systems that actually work in insurance and adjacent industries.



# Fraud Detection Pipelines That Actually Worked

## 1. Shift Technology (Used by 70+ Insurers Including Top 10 Global)

```
What they do:
  Every claim scored at FNOL (First Notice of Loss)
  before any human touches it.

Pipeline:
  Claim submitted
       │
       ▼
  Feature extraction (300+ features per claim)
       │
       ▼
  ML scoring (0-100 fraud probability)
       │
       ▼
  Top 3% → routed to SIU with explanation
  Middle 7% → flagged for adjuster awareness  
  Bottom 90% → process normally

What actually made it work:
  - Scored EVERY claim, not just flagged ones
  - Explanable output ("scored high BECAUSE: 
    policy age 3 months + provider has 12 other 
    claims this quarter + diagnosis inconsistent 
    with reported accident")
  - Feedback loop: SIU confirms/denies fraud → 
    model retrains quarterly
  
Results (public):
  - 75% of confirmed fraud cases were in top 3% scores
  - Reduced false positives by 50% vs rules-based system
```

**Lesson for Prudential:** Score every claim at intake, including wellness. The 35-dependent case would score extremely high before auto-adjudication ever runs. You don't need to block auto-adjudication — you need a scoring layer *before* it.

---

## 2. FICO Insurance Fraud Manager (Used by 200+ Carriers)

```
Pipeline:
  Claim intake
       │
       ▼
  Rules engine (deterministic) ──→ hard flags
       │                           "policy < 60 days"
       ▼                           "known fraudster"  
  Network/link analysis ─────→ relationship flags
       │                        "claimant linked to 
       ▼                         3 other open claims 
  Anomaly detection ─────────→   via shared address"
       │                        
       ▼                        
  Composite score + priority
       │
       ▼
  Adjuster sees score IN their existing workflow
  (not a separate tool — embedded in claims system)

Key architectural decision:
  THREE LAYERS, not one:
  
  Layer 1: Rules (catches obvious stuff, fast, explainable)
    "If dependents_added > 10 in 30 days → FLAG"
    "If claim filed < 90 days after policy start → FLAG"
    
  Layer 2: Network (catches collusion)
    "Claimant shares address with 4 other claimants"
    "Treating provider supports 15 open disability claims"
    
  Layer 3: ML anomaly (catches novel patterns)
    "This claim doesn't match any known fraud type 
     but is statistically unusual in 7 dimensions"
```

**Lesson for Prudential:** Don't rely on one method. Their current system has weak Layer 1 (banner system), no Layer 2 (no network analysis), and no Layer 3. Even just a strong Layer 1 with better rules would have caught the 35-dependent case.

---

## 3. Coalition Against Insurance Fraud / NICB (Industry Databases)

```
What exists across the industry:

  NICB (National Insurance Crime Bureau):
    - Shared database across carriers
    - "If claimant filed suspicious claims at MetLife 
       AND Prudential, both carriers can see it"
    - ISO ClaimSearch: 1.5 billion claims indexed
    
  MIB (Medical Information Bureau):
    - Shares medical history flags across life/disability carriers
    - "Claimant applied for disability at 3 carriers 
       in 18 months with different diagnoses"

Pipeline that works:
  Claim intake → query NICB/ISO/MIB → enrich claim 
  with cross-carrier history BEFORE adjudication

Most carriers underuse these databases.
Queries are manual or only triggered after suspicion.
```

**Lesson for Prudential:** Ask in follow-up: "Do you query ISO ClaimSearch or MIB on every claim or only flagged ones?" If only flagged → there's a gap. Auto-querying on every claim (or every claim above a threshold) is standard at mature carriers.

---

## 4. Anthem (Now Elevance) — Healthcare Fraud

```
Different domain (health not life) but their pipeline 
is the gold standard and directly applicable:

Pre-pay review:
  Claim submitted
       │
       ▼
  Real-time scoring (before payment)
  ├─ Provider profiling (billing patterns vs peers)
  ├─ Member profiling (utilization patterns)  
  ├─ Claim-level rules (impossible combinations,
  │   duplicate billing, unbundling)
  └─ Network analysis (provider rings)
       │
       ▼
  Pay / Pend / Deny

Post-pay review:
  Monthly batch analysis
  ├─ Provider outlier detection
  ├─ Geographic anomalies  
  ├─ Temporal pattern shifts
  └─ New scheme detection (unsupervised ML)
       │
       ▼
  SIU case generation

What made it work:
  PRE-PAY stopped money going out the door
  POST-PAY caught slow-burn schemes
  BOTH required, neither alone sufficient
```

**Lesson for Prudential:** Their auto-adjudication for wellness is **pre-pay with no fraud check**. Money goes out the door immediately. Even a simple rules layer pre-pay would help. The copilot we're building is post-pay (analyst reviews after). Ideally we propose both.

---

## 5. Lemonade (Insurtech) — AI Jim

```
Fully automated claims pipeline:

Claim filed (video + text)
       │
       ▼
  AI Jim (bot) processes claim
  ├─ Cross-references policy terms
  ├─ Checks 18 anti-fraud algorithms
  ├─ Behavioral analysis on video submission
  └─ Network/social graph check
       │
       ├─ Clean → auto-pay (30% of claims paid in <3 seconds)
       └─ Suspicious → route to human
       
Anti-fraud algorithms include:
  - Duplicate claim detection
  - Inconsistency in narrative vs documentation
  - Behavioral cues in video
  - Social network of claimant
  
Public result: 
  ~1% fraud rate (industry average ~10%)
  Because fraudsters learned to avoid Lemonade
  DETERRENCE > DETECTION
```

**Lesson for Prudential:** The deterrence effect matters. If claimants know every claim is scored, fraud attempts decrease. Currently wellness claims have zero scrutiny — word gets around.

---

## What We Can Actually Apply

```
REALISTIC FOR OUR PROTOTYPE (ranked by impact):

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#1  RULES ENGINE PRE-SCREEN (from FICO model)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Simple deterministic rules that run on EVERY 
    claim before auto-adjudication:
    
    IF dependents_added > 5 in 30_days → HOLD
    IF claim_filed < 90_days after policy_start → FLAG  
    IF wellness_claims > 10 per member per quarter → HOLD
    IF same_provider + same_diagnosis + 5_patients → FLAG
    IF coverage_termination < 60_days AND claim_spike → FLAG
    
    This alone catches Case 2 (35 dependents).
    
    Implementation: runs before auto-adjudicator,
    gates whether claim auto-pays or routes to human.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#2  CLAIM-LEVEL RISK SCORING (from Shift model)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Every claim gets a score. Features:
    
    - Policy age at claim
    - Claim type + amount
    - Member claim history (frequency, recency)
    - Family/dependent claim patterns  
    - Provider claim volume
    - Proximity to termination/lapse
    - Time between events (add dependent → file claim)
    
    Score feeds into:
    - The suspicious banner (enhanced)
    - Claims queue priority
    - Auto-adjudication gate

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#3  NETWORK/LINK ANALYSIS (from FICO + our existing prototype)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Connect entities:
    Member ←→ Dependents ←→ Providers ←→ Other Members
    
    Detect:
    - Shared addresses across "unrelated" claimants
    - Provider supporting abnormal claim volume
    - Dependent networks (are 35 "dependents" real people?)
    
    THIS IS WHERE OUR EXISTING NETWORK GRAPH APPLIES.
    Don't throw it away — repurpose it for member/dependent 
    networks instead of provider billing networks.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#4  COPILOT FOR INVESTIGATION (our chat agent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    When a claim IS flagged and a human reviews it:
    - Automate the OneNote checklist
    - Surface all relevant data in one place
    - Answer analyst questions conversationally
    - Generate escalation package
    
    This is the Shift model's "explainability" layer.
    Don't just flag — explain WHY and show EVIDENCE.
```

---

## Proposed Pipeline for Prudential

```
            Claim Submitted
                  │
                  ▼
         ┌───────────────┐
         │  RULES ENGINE  │ ← catches obvious (35 dependents)
         │  (Pre-screen)  │
         └───────┬───────┘
                 │
          Pass   │   Fail/Flag
          ┌──────┴──────┐
          │             │
          ▼             ▼
   ┌────────────┐  ┌──────────────┐
   │ RISK SCORE │  │ ROUTE TO     │
   │ (ML/Stats) │  │ HUMAN QUEUE  │
   └─────┬──────┘  └──────────────┘
         │                ▲
    Low  │  Med/High      │
    ┌────┴────┐           │
    │         │           │
    ▼         └───────────┘
┌──────────┐
│ AUTO-ADJ │ ← only clean + low-risk claims auto-pay
└──────────┘

Human review queue:
┌─────────────────────────────┐
│ COPILOT-ASSISTED REVIEW     │
│ ├─ Automated checklist      │
│ ├─ Risk explanation         │
│ ├─ Network visualization    │
│ ├─ Chat investigation       │
│ └─ Escalation package gen   │
└─────────────────────────────┘
```

This is the architecture that actually works across the industry. The question for session 2 follow-up: **which layer does Prudential want us to build first?**