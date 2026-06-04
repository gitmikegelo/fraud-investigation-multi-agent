"""
Deterministic Demo Runner for Prudential Supplemental Health Investigation
==========================================================================
Replays a fixed dependent fraud ring scenario over WebSocket.
No LLM / Bedrock calls are made.

Scenario
--------
1.  Orchestrator routes to Investigation (Phase: investigate)
2.  Investigation scans entities, profiles MBR-1042 cluster
3.  Orchestrator routes to Dossier (Phase: compile)
4.  Dossier REJECTS — insufficient evidence (missing network analysis)
5.  Investigation traces dependent ring connections
6.  Orchestrator routes to Dossier (Phase: compile)
7.  Dossier REJECTS AGAIN — missing regulatory citations
8.  Investigation gathers regulatory rules + peer comparisons
9.  Orchestrator routes to Dossier (Phase: compile)
10. Dossier ACCEPTS — evidence sufficient → produces final dossier
"""

import asyncio
import time
import os
from datetime import datetime

DEMO_FINAL_DOSSIER = r"""# SUPPLEMENTAL HEALTH FRAUD INVESTIGATION DOSSIER

**Hypothesis**: Coordinated dependent fraud ring filing fabricated accident and hospital indemnity claims through shared provider
**Case Type**: Dependent Fraud / Provider Mill
**Generated**: {date}
**Status**: Evidence Sufficient - Ready for Action

---

## EXECUTIVE SUMMARY

Investigation identified a suspected dependent fraud ring involving 4 members centered around MBR-1042, sharing address ADDR-2201 and routing claims through PRV-087 (Dr. Ramon Espinoza, Urgent Care). The ring filed 23 accident and hospital indemnity claims totaling **$187,450** within an 8-week window, predominantly for dependents (DEP-3042, DEP-3043, DEP-3044). Risk scores range from 72 to 89. 8 independent evidence points with quantitative significance and regulatory basis established.

---

## ENTITIES INVOLVED

### Entity 1: MBR-1042 (Jacob Taylor)
- **Type**: Member (Primary Subject)
- **Risk Score**: 89
- **Employer**: EMP-015 (Meridian Logistics Corp)
- **Total Claims**: $78,200 (12 claims)
- **Dependents**: 3 (DEP-3042, DEP-3043, DEP-3044)
- **Address**: ADDR-2201

### Entity 2: MBR-1038 (Sarah Chen)
- **Type**: Member (Ring Member)
- **Risk Score**: 76
- **Total Claims**: $42,600 (6 claims)
- **Address**: ADDR-2201 (same as MBR-1042)

### Entity 3: PRV-087 (Dr. Ramon Espinoza)
- **Type**: Provider (Suspected Mill)
- **Specialty**: Urgent Care
- **Total Claims Processed**: 89 claims / quarter
- **Unique Members**: 8 (top member MBR-1042 at 34%)
- **Avg Claim Amount**: $4,250 (peer avg: $1,800)

### Entity 4: DEP-3042 (Emma Taylor)
- **Type**: Dependent (Minor)
- **Claims Filed**: 5 accident claims in 6 weeks
- **Total Amount**: $28,750

### Entity 5: DEP-3043 (Liam Taylor)
- **Type**: Dependent (Minor)
- **Claims Filed**: 4 hospital indemnity claims in 5 weeks
- **Total Amount**: $22,400

---

## EVIDENCE

1. MBR-1042 risk score 89 — 3.4 standard deviations above employer peer average for claim frequency
2. Cluster of 4 members at shared address ADDR-2201 filing through same provider PRV-087
3. 23 claims in 8-week window vs peer average of 1.2 claims/quarter (z-score: 4.8)
4. Dependent claim ratio 78% — DEP-3042/3043/3044 account for majority of filed claims
5. PRV-087 member concentration: 34% of volume from single member vs expected < 5%
6. Temporal clustering: 85% of claims filed Mon-Wed, suggesting coordinated submission
7. Network density 4.2 among ring members at ADDR-2201 — highly interconnected
8. Document inconsistencies: 3 claims show mismatched service dates between provider notes and facility records

---

## NETWORK ANALYSIS

- **Connected Entities**: 9
- **Connection Density**: 4.2
- **Ring Members**: MBR-1042, MBR-1038, MBR-1055, MBR-1061
- **Shared Address**: ADDR-2201 (1847 Oakmont Dr, Unit B)
- **Common Provider**: PRV-087 (Dr. Ramon Espinoza)
- **Relationship Map**: MBR-1042 → DEPENDENT_OF → DEP-3042/3043/3044; MBR-1042 → LIVES_AT → ADDR-2201; MBR-1038 → LIVES_AT → ADDR-2201; all → TREATED_BY → PRV-087

---

## REGULATORY VIOLATIONS

### SH-001: Dependent Eligibility Verification
Multiple dependents filing high-frequency claims without independent verification of dependent status. DEP-3042/3043/3044 eligibility documentation incomplete.

### SH-003: Provider Volume Threshold Exceeded
PRV-087 exceeds 75th percentile for claim volume with single-source member concentration > 25%. Pattern consistent with provider mill arrangement.

### SH-004: Document Integrity — Temporal Mismatch
3 claims show service date discrepancies between provider notes and facility admission records. Indicates potential document fabrication.

### SH-010: Shared Address Cluster
4 members sharing ADDR-2201 with correlated claim timing. Exceeds threshold of 3+ members at same address with concurrent claims.

---

## PRECEDENT CASES

- **SIU-2025-0847**: Dependent Ring — 6 members, shared address, 34 fabricated accident claims, $245K denied. Provider contract terminated.
- **SIU-2024-1203**: Provider Mill — Urgent care facility, 78% single-source referrals, $890K in fraudulent billing. License revoked, $620K recovered.

---

## FINANCIAL IMPACT

- **Total Claims Filed**: $187,450.00
- **Gross Exposure**: $187,450.00
- **Collectability Factor**: 85%
- **Litigation Discount**: 80%
- **Net Expected Recovery**: **$127,466.00**
- **Recommended Action**: DENY CLAIMS — Fabricated dependent claims through coordinated ring

---

## RECOMMENDATIONS

1. **DENY** all pending claims from MBR-1042, MBR-1038, and associated dependents filed through PRV-087
2. **REFER TO SIU** for formal investigation of dependent eligibility fraud across ADDR-2201 cluster
3. **TERMINATE PROVIDER** contract with PRV-087 pending review of billing practices
4. **FLAG EMPLOYER** EMP-015 for enrollment audit — verify dependent eligibility documentation
5. **RECOVER** overpayments on 12 previously paid claims totaling $68,400
6. Report to state Department of Insurance for coordinated fraud scheme

---
*Generated by ARIA - Prudential Supplemental Health Investigation Copilot*
"""


def _send(ws, loop, event_type, data):
    from api import ws_send
    asyncio.run_coroutine_threadsafe(ws_send(ws, event_type, data), loop)
    time.sleep(0.05)


def _log_and_send(ws, loop, agent, message, delay=0.3):
    _send(ws, loop, "log", {"agent": agent, "message": message})
    # Write to demo log file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, f"investigation_demo_{timestamp}.txt")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{agent}\n{message}\n")
    except Exception:
        pass
    time.sleep(delay)


def run_demo_investigation_sync(ws, loop):
    """Replay a scripted dependent fraud ring investigation. Called from a thread."""

    s = lambda et, d: _send(ws, loop, et, d)
    log = lambda a, m, delay=0.3: _log_and_send(ws, loop, a, m, delay)

    s("status", {"message": "Investigation starting (demo mode)..."})
    time.sleep(0.5)

    # ===== ITERATION 1: Orchestrator → Investigation =====
    s("node_enter", {"node": "orchestrator", "iteration": 1})
    log("Orchestrator", "--- Iteration 1 | Current phase: start ---")
    log("Orchestrator", "Calling LLM for routing decision...")
    time.sleep(0.8)
    log("Orchestrator", "LLM responded in 1.2s")
    log("Orchestrator", "Phase transition: start -> investigate")
    s("phase_change", {"phase": "investigate", "loop_count": 1})
    s("node_exit", {"node": "orchestrator", "elapsed": 1.5, "phase": "investigate", "loop_count": 1})

    # ===== ITERATION 2: Investigation — initial scan =====
    s("node_enter", {"node": "investigation", "iteration": 2})
    log("Investigation", "Starting investigation sub-agent (7 tools available)...")
    log("Investigation", "Invoking LLM + tool loop...")

    log("tool", "tool:scan_suspicious_entities -> Scanning entities (risk > 40)...")
    time.sleep(1.0)
    log("tool", "tool:scan_suspicious_entities -> Found 6 high-risk entities (0.3s)")

    log("tool", "tool:profile_entity -> Profiling MBR-1042 (Jacob Taylor)...")
    time.sleep(0.8)
    log("tool", "tool:profile_entity -> Risk: 89, 12 claims, $78.2K total, 3 dependents, employer EMP-015")

    log("tool", "tool:profile_entity -> Profiling PRV-087 (Dr. Ramon Espinoza)...")
    time.sleep(0.6)
    log("tool", "tool:profile_entity -> 89 claims/qtr, 8 unique members, top member MBR-1042 at 34%")

    log("tool", "tool:get_claim_details -> Fetching claims for MBR-1042...")
    time.sleep(0.5)
    log("tool", "tool:get_claim_details -> 12 claims returned — 9 accident, 3 hospital indemnity, avg $6,517")

    log("tool", "tool:compare_to_peers -> Comparing MBR-1042 claim_count vs EMP-015 peers...")
    time.sleep(0.5)
    log("tool", "tool:compare_to_peers -> Value: 12, peer_avg: 2.1, z-score: 3.4")

    log("Investigation", "Sub-agent finished in 8.2s | Tool calls made: 5")
    log("Investigation", "Summary: Identified high-risk member MBR-1042 with elevated claim frequency and dependent claim concentration through PRV-087...")

    s("node_exit", {"node": "investigation", "elapsed": 10.0,
       "findings_preview": "MBR-1042 risk score 89, 12 claims ($78.2K), 3 dependents filing through PRV-087 (34% member concentration). Claim frequency z-score 3.4 vs employer peers..."})

    # ===== ITERATION 3: Orchestrator → Dossier =====
    s("node_enter", {"node": "orchestrator", "iteration": 3})
    log("Orchestrator", "--- Iteration 2 | Current phase: investigate ---")
    log("Orchestrator", "Phase transition: investigate -> compile")
    s("phase_change", {"phase": "compile", "loop_count": 2})
    s("node_exit", {"node": "orchestrator", "elapsed": 11.5, "phase": "compile", "loop_count": 2})

    # ===== ITERATION 4: Dossier REJECTS =====
    s("node_enter", {"node": "dossier", "iteration": 4})
    log("Dossier", "Starting dossier sub-agent (5 tools available)...")
    log("Dossier", "Invoking LLM + tool loop (evidence assessment)...")

    log("tool", "tool:assess_evidence -> Assessing 'dependent_ring' (3 evidence points)...")
    time.sleep(0.8)
    log("tool", "tool:assess_evidence -> INSUFFICIENT (2 passed, 2 failed)")
    log("tool", "tool:assess_evidence -> Missing: network_evidence, document_evidence")

    log("Dossier", "Evidence assessed as INSUFFICIENT - looping back to investigation")
    s("dossier_rejected", {
        "message": "Dossier rejected \u2014 evidence INSUFFICIENT. 2 of 6 critical checks failed.",
        "evidence_gaps": """CASE WRITER DENIAL NOTE \u2014 Iteration 1
======================================

CLAIM: Dependent fraud ring involving MBR-1042 (Jacob Taylor)
ASSESSMENT: INSUFFICIENT \u2014 Cannot proceed to formal dossier

FINDINGS SO FAR:
\u2022 Member MBR-1042 flagged with risk score 89 (3.4\u03c3 above employer peer group)
\u2022 12 claims totaling $78,200 through single provider PRV-087
\u2022 3 dependents (DEP-3042, DEP-3043, DEP-3044) account for 78% of claim volume
\u2022 Provider PRV-087 shows 34% member concentration (expected < 5%)

DEFICIENCIES:
1. NETWORK ANALYSIS (CRITICAL): No graph traversal performed to establish shared address connections. Cannot confirm whether MBR-1042, MBR-1038, MBR-1055, MBR-1061 share ADDR-2201 or if the address cluster is coincidental. Without this, the \"coordinated ring\" hypothesis is unsupported.
   \u2192 Action: Run find_connections(MBR-1042, depth=2) and find_ring(min_risk_score=50)

2. DOCUMENT INTEGRITY (CRITICAL): No document-level checks performed. Claims may have service date mismatches between provider notes and facility records. Document tampering indicators have not been examined.
   \u2192 Action: Run get_claim_details(MBR-1042) with document flag analysis

NEXT STEPS: Investigation agent must gather network topology and document evidence before re-submission."""
    })
    s("node_exit", {"node": "dossier", "elapsed": 14.0, "evidence_sufficient": False})

    # ===== ITERATION 5: Orchestrator → Investigation (loop back) =====
    s("node_enter", {"node": "orchestrator", "iteration": 5})
    log("Orchestrator", "--- Iteration 3 | Current phase: investigate ---")
    log("Orchestrator", "Evidence INSUFFICIENT - looping back to investigation")
    log("Orchestrator", "Phase transition: investigate -> investigate")
    s("phase_change", {"phase": "investigate", "loop_count": 3})
    s("node_exit", {"node": "orchestrator", "elapsed": 15.5, "phase": "investigate", "loop_count": 3})

    # ===== ITERATION 6: Investigation — network + ring analysis =====
    s("node_enter", {"node": "investigation", "iteration": 6})
    log("Investigation", "Starting investigation sub-agent (addressing evidence gaps)...")
    log("Investigation", "Evidence gaps: need network analysis + document integrity checks")

    log("tool", "tool:find_connections -> Traversing graph from MBR-1042 (depth=2)...")
    time.sleep(1.0)
    log("tool", "tool:find_connections -> 9 connected entities, density=4.2, shared address ADDR-2201")

    log("tool", "tool:find_ring -> Searching detected patterns (risk >= 50)...")
    time.sleep(1.2)
    log("tool", "tool:find_ring -> Found dependent_ring: 4 members at ADDR-2201, avg risk 78.5")

    log("tool", "tool:compare_to_peers -> Comparing MBR-1042 dependent_claims vs peers...")
    time.sleep(0.6)
    log("tool", "tool:compare_to_peers -> Value: 9, peer_avg: 0.8, z-score: 4.8")

    log("tool", "tool:get_referral_history -> Pulling 6-month history for PRV-087...")
    time.sleep(0.5)
    log("tool", "tool:get_referral_history -> 6 months, avg 15 claims/month, MBR-1042 concentration increasing")

    log("Investigation", "Sub-agent finished in 6.8s | Tool calls made: 4")
    s("node_exit", {"node": "investigation", "elapsed": 23.0,
       "findings_preview": "Dependent ring confirmed: 4 members at ADDR-2201, density 4.2. Dependent claims z-score 4.8. PRV-087 shows increasing MBR-1042 concentration..."})

    # ===== ITERATION 7: Orchestrator → Dossier =====
    s("node_enter", {"node": "orchestrator", "iteration": 7})
    log("Orchestrator", "--- Iteration 4 | Current phase: investigate ---")
    log("Orchestrator", "Phase transition: investigate -> compile")
    s("phase_change", {"phase": "compile", "loop_count": 4})
    s("node_exit", {"node": "orchestrator", "elapsed": 24.5, "phase": "compile", "loop_count": 4})

    # ===== ITERATION 8: Dossier REJECTS AGAIN =====
    s("node_enter", {"node": "dossier", "iteration": 8})
    log("Dossier", "Starting dossier sub-agent...")

    log("tool", "tool:assess_evidence -> Assessing 'dependent_ring' (6 evidence points)...")
    time.sleep(0.8)
    log("tool", "tool:assess_evidence -> INSUFFICIENT (4 passed, 1 failed)")
    log("tool", "tool:assess_evidence -> Missing: regulatory_citation \u2014 need SH rule references")

    log("Dossier", "Evidence INSUFFICIENT \u2014 missing regulatory citations")
    s("dossier_rejected", {
        "message": "Dossier rejected \u2014 still INSUFFICIENT. 1 of 6 critical checks failed.",
        "evidence_gaps": """CASE WRITER DENIAL NOTE \u2014 Iteration 2
======================================

CLAIM: Dependent fraud ring involving MBR-1042 (Jacob Taylor)
ASSESSMENT: INSUFFICIENT \u2014 Strong quantitative case but lacks regulatory grounding

EVIDENCE ESTABLISHED (4 of 5 checks passed):
\u2713 Multiple evidence points: 6 independent data points collected
\u2713 Statistical significance: Claim frequency z-score 3.4, dependent claims z-score 4.8 (both > 2.0 threshold)
\u2713 Network evidence: Dependent ring confirmed \u2014 4 members at ADDR-2201, graph density 4.2, all routing through PRV-087
\u2713 Temporal pattern: 85% of claims filed Mon-Wed within 8-week window, indicating coordinated submission

REMAINING DEFICIENCY:
1. REGULATORY CITATION (REQUIRED): No supplemental health regulatory rules have been cited. A formal dossier requires specific rule references to support denial recommendations and withstand appeals. The following rules are likely applicable but have not been formally searched:
   \u2022 SH-001 (Dependent Eligibility Verification) \u2014 DEP-3042/3043/3044 eligibility docs incomplete
   \u2022 SH-003 (Provider Volume Threshold) \u2014 PRV-087 exceeds 75th percentile with 34% single-source concentration
   \u2022 SH-010 (Shared Address Cluster) \u2014 4 members at ADDR-2201 with concurrent claims
   \u2022 SH-004 (Document Integrity) \u2014 Potential service date mismatches in 3 claims
   \u2192 Action: Run search_regulatory_rules(['accident', 'hospital_indemnity'], 'dependent ring shared address')

NOTE: Once regulatory basis is established, this case is ready for final dossier compilation with estimated recovery of $127K-$160K."""
    })
    s("node_exit", {"node": "dossier", "elapsed": 27.0, "evidence_sufficient": False})

    # ===== ITERATION 9: Orchestrator → Investigation =====
    s("node_enter", {"node": "orchestrator", "iteration": 9})
    log("Orchestrator", "--- Iteration 5 | Current phase: investigate ---")
    log("Orchestrator", "Phase transition: investigate -> investigate")
    s("phase_change", {"phase": "investigate", "loop_count": 5})
    s("node_exit", {"node": "orchestrator", "elapsed": 28.5, "phase": "investigate", "loop_count": 5})

    # ===== ITERATION 10: Investigation — document checks =====
    s("node_enter", {"node": "investigation", "iteration": 10})
    log("Investigation", "Gathering document evidence and temporal patterns...")

    log("tool", "tool:get_claim_details -> Checking document flags for MBR-1042 claims...")
    time.sleep(0.8)
    log("tool", "tool:get_claim_details -> 3 claims with document anomalies: date mismatches between provider and facility records")

    log("Investigation", "Sub-agent finished in 2.5s | Tool calls made: 1")
    s("node_exit", {"node": "investigation", "elapsed": 31.5,
       "findings_preview": "Document integrity issues found: 3 claims with service date mismatches. Combined with network and statistical evidence, regulatory rules SH-001, SH-003, SH-004, SH-010 applicable..."})

    # ===== ITERATION 11: Orchestrator → Dossier (final) =====
    s("node_enter", {"node": "orchestrator", "iteration": 11})
    log("Orchestrator", "--- Iteration 6 | Current phase: investigate ---")
    log("Orchestrator", "Phase transition: investigate -> compile")
    s("phase_change", {"phase": "compile", "loop_count": 6})
    s("node_exit", {"node": "orchestrator", "elapsed": 33.0, "phase": "compile", "loop_count": 6})

    # ===== ITERATION 12: Dossier ACCEPTS =====
    s("node_enter", {"node": "dossier", "iteration": 12})
    log("Dossier", "Starting dossier sub-agent...")

    log("tool", "tool:assess_evidence -> Assessing 'dependent_ring' (8 evidence points)...")
    time.sleep(0.8)
    log("tool", "tool:assess_evidence -> SUFFICIENT (5 passed, 0 failed)")

    log("tool", "tool:search_regulatory_rules -> Searching rules for accident, hospital_indemnity...")
    time.sleep(0.6)
    log("tool", "tool:search_regulatory_rules -> Found 4 applicable rules: SH-001, SH-003, SH-004, SH-010")

    log("tool", "tool:find_similar_cases -> Looking up precedents for dependent_ring...")
    time.sleep(0.5)
    log("tool", "tool:find_similar_cases -> Found 2 precedent cases")

    log("tool", "tool:estimate_recovery -> Dependent ring: $187K exposure, risk=0.89...")
    time.sleep(0.5)
    log("tool", "tool:estimate_recovery -> Gross: $187,450, net recovery: $127,466")

    log("tool", "tool:compile_dossier -> Generating supplemental health fraud dossier...")
    time.sleep(1.0)
    log("tool", "tool:compile_dossier -> Dossier generated (3,412 chars)")

    log("Dossier", "Evidence assessed as SUFFICIENT")
    s("dossier_accepted", {"message": "Evidence SUFFICIENT \u2014 dossier compiled."})
    s("node_exit", {"node": "dossier", "elapsed": 38.0, "evidence_sufficient": True})

    # ===== Final orchestrator → done =====
    s("node_enter", {"node": "orchestrator", "iteration": 13})
    log("Orchestrator", "Phase transition: compile -> done")
    s("phase_change", {"phase": "done", "loop_count": 7})
    s("node_exit", {"node": "orchestrator", "elapsed": 39.0, "phase": "done", "loop_count": 7})

    # ===== Complete =====
    dossier_text = DEMO_FINAL_DOSSIER.format(date=datetime.now().strftime("%Y-%m-%d %H:%M"))

    s("investigation_complete", {
        "iterations": 13,
        "total_time": 39.0,
        "phase": "done",
        "loop_count": 7,
        "evidence_sufficient": True,
        "dossier": dossier_text,
        "findings": {
            "last_investigation": "Dependent fraud ring confirmed: MBR-1042 cluster, 4 members at ADDR-2201, PRV-087 provider mill. Z-scores: claim frequency 3.4, dependent claims 4.8. Rules: SH-001, SH-003, SH-004, SH-010.",
        },
    })

    return dossier_text
