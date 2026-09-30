

"""
Deterministic Demo Runner for Car Insurance Investigation
=========================================================
Replays a fixed inflated-estimate / repair-shop-ring fraud scenario over
WebSocket. No LLM / Bedrock calls are made.

Scenario (claim COL-107 — Matthew Garcia / INS-0001, collision)
---------------------------------------------------------------
1.  Orchestrator routes to Investigation (Phase: investigate)
2.  Investigation scans entities, profiles insured INS-0001
3.  Orchestrator routes to Dossier (Phase: compile)
4.  Dossier REJECTS — insufficient evidence (missing estimate forensics)
5.  Investigation reviews DECREE line-items + watchlisted shop history
6.  Orchestrator routes to Dossier (Phase: compile)
7.  Dossier REJECTS AGAIN — missing regulatory citations
8.  Investigation gathers AU regulatory rules + peer comparison
9.  Orchestrator routes to Dossier (Phase: compile)
10. Dossier ACCEPTS — evidence sufficient → produces final dossier
"""

import asyncio
import time
import os
from datetime import datetime

DEMO_FINAL_DOSSIER = r"""# AUTO INSURANCE FRAUD INVESTIGATION DOSSIER

**Hypothesis**: Inflated repair estimate with repair-shop ring — collision claim 1.4x the vehicle ACV and 2.4x the independent DECREE damage estimate, routed through a watchlisted body shop by a serial claimer
**Case Type**: Inflated Estimate / Repair-Shop Ring
**Case Reference**: COL-107 · INS-0001 · SHP-007
**Generated**: {date}
**Risk Score**: 98.4 / 100 (HIGH)
**Confidence Level**: 92%
**Status**: Evidence Sufficient — Ready for Action

---

## EXECUTIVE SUMMARY

Investigation identified suspected **inflated-estimate / repair-shop-ring fraud** on claim **COL-107** filed by insured **INS-0001 (Matthew Garcia)**. The **$25,877.85** collision claim is **1.4x the vehicle ACV** ($18,484) and **2.4x the independent DECREE damage estimate** (midpoint $10,750, 88% confidence). The repair estimate originates from **SHP-007 (Discount Fender Fix)**, a shop on the **fraud watchlist** (BLOCK rule R-004), which is linked to a cluster of high-value estimates consistent with an organised repair-shop ring. The insured is a **serial claimer** with **6 claims** on file (2x the flagging threshold).

The combination of (a) a claim exceeding the vehicle's own value, (b) an estimate 2.4x an independent expert assessment, (c) a watchlisted shop with clustered high-value estimates, and (d) a serial-claimer history establishes a coherent, multi-factor fraud pattern. **8 independent evidence points** with quantitative, forensic, and regulatory basis have been established across three investigation cycles (two dossier rejections resolved). The case mirrors two SIU precedents that resulted in claim denial, shop blacklisting, and demand recovery.

**Bottom line**: DENY the amount exceeding the substantiated repair value (~$15,128 over-estimate exposure; **$9,225 net expected recovery**), place the claim on hold pending independent re-inspection, and refer SHP-007 to the SIU for ring analysis.

---

## ENTITIES INVOLVED

### Entity 1: INS-0001 — Matthew Garcia (Primary Subject)
- **Type**: Insured
- **Risk Score**: 98.4 / 100 (HIGH — highest in the active queue)
- **Total Claims**: 6 (serial claimer — threshold 3; ~4.3x peer average of 1.4)
- **Current Claim**: COL-107 — $25,877.85 collision
- **Vehicle**: 2018 Ford F-150 (ACV $18,484)
- **Policy**: Active; incident 2025-11-24 within coverage period (2025-05-15 → 2026-05-15)
- **Behavioural Flags**: Repeated use of a watchlisted shop; claim amounts trending above vehicle values

### Entity 2: SHP-007 — Discount Fender Fix (Repair Shop)
- **Type**: Repair Shop
- **Status**: **WATCHLISTED** (fraud watchlist)
- **Linked Claim**: COL-107 — repair estimate $25,877.85
- **Network Status**: Out-of-network / unverified
- **Risk Contribution**: BLOCK rule R-004 triggered
- **Pattern**: Concentration of high-value estimates above comparable repairs for the documented damage

### Entity 3: COL-107 — Collision Claim
- **Type**: Collision Claim
- **Amount**: $25,877.85 (1.4x vehicle ACV; 2.4x DECREE estimate)
- **Independent DECREE Estimate**: $8,950–$12,550 (midpoint $10,750, confidence 88%)
- **Excess Over ACV**: $7,393.85
- **Excess Over Independent Estimate**: $15,127.85
- **Rules Triggered**: R-004 (watchlist BLOCK), R-005 (amount exceeds ACV), serial-claimer FLAG

### Entity 4: VEH — 2018 Ford F-150
- **ACV**: $18,484
- **Damage**: Front-end collision (documented via submitted photo)
- **Assessment**: Damage authentic but **inconsistent in scope** with the $25,877.85 estimate

---

## EVIDENCE LEDGER

| # | Evidence | Severity | Source |
|---|----------|----------|--------|
| 1 | COL-107 risk score 98.4 — highest in the active queue, 3 rules triggered | CRITICAL | Risk engine |
| 2 | Claim $25,877.85 is 1.4x the vehicle ACV of $18,484 (excess $7,393.85) | HIGH | ACV comparison |
| 3 | Claim is 2.4x the independent DECREE estimate (midpoint $10,750, 88% conf.) | CRITICAL | DECREE assessment |
| 4 | Repair estimate from SHP-007 (Discount Fender Fix) — on the fraud watchlist | CRITICAL | R-004 BLOCK |
| 5 | DECREE line-item review: padded panels/operations beyond documented damage | HIGH | Line-item forensics |
| 6 | Insured INS-0001 is a serial claimer — 6 claims (threshold 3; ~4.3x peer avg) | HIGH | Claim history |
| 7 | Damage photo submitted — flagged for priority forensic image review | MEDIUM | Vision/DOC review |
| 8 | SHP-007 linked to a cluster of high-value estimates — potential ring | HIGH | Ring detection |

---

## STATISTICAL ANALYSIS

| Metric | Claim Value | Benchmark | Deviation |
|--------|-------------|-----------|-----------|
| Claim amount vs vehicle ACV | $25,877.85 | $18,484 | **1.40x** (+$7,393.85) |
| Claim amount vs independent estimate | $25,877.85 | $10,750 | **2.41x** (+$15,127.85) |
| Insured claim count | 6 | 1.4 (peer avg) | **~4.3x** (serial claimer) |
| Composite risk score | 98.4 | 40 (queue threshold) | **+58.4 pts** |

**Interpretation**: Every headline metric sits far outside legitimate-claim norms. The single most decisive figure is the **2.41x gap versus an 88%-confidence independent estimate** — legitimate collision repairs rarely exceed an expert estimate by more than 10–15%.

---

## ESTIMATE & DOCUMENT FORENSICS

- **Independent estimate (DECREE)**: $8,950–$12,550 (midpoint $10,750), confidence 88% (HIGH)
- **Submitted estimate (SHP-007)**: $25,877.85 — **2.4x** the DECREE midpoint
- **Line-item variance**: padded operations/panels beyond the visible front-end collision damage; labour hours and parts inconsistent with the documented impact
- **Photo review**: front-end damage is authentic (no digital manipulation detected) but its **scope does not support** the estimate magnitude — classic "real damage, inflated repair" pattern
- **Shop status**: SHP-007 (Discount Fender Fix) on the fraud watchlist; out-of-network with a concentration of high-value estimates

---

## NETWORK ANALYSIS

- **Repair-shop ring**: POTENTIAL (MODERATE confidence)
- **Anchor entity**: SHP-007 (Discount Fender Fix) — watchlisted
- **Connection**: SHP-007 → COL-107 (INS-0001) inflated estimate
- **Ring indicators**: single shop linked to multiple high-value estimates; out-of-network routing; estimates above comparable repairs
- **Expansion recommended**: full 24-month scan of SHP-007-linked claims and insureds to size the ring and identify co-conspirators

```
INS-0001 (Matthew Garcia, 98.4) ──filed──> COL-107 ($25,877.85)
                                              │
                                        estimate by
                                              ▼
                                   SHP-007 (Discount Fender Fix) [WATCHLISTED]
                                              │
                                   linked to cluster of
                                   high-value estimates ──> potential ring
```

---

## TIMELINE / CHRONOLOGY

| Date | Event |
|------|-------|
| 2025-05-15 | Policy coverage begins |
| 2025-11-24 | Reported collision incident (within coverage) |
| 2025-11-25 | Damage photo submitted; front-end damage documented |
| 2025-11-26 | Repair estimate $25,877.85 received from SHP-007 (watchlisted) |
| 2025-11-27 | DECREE independent assessment returns $10,750 midpoint (88% conf.) |
| — | Risk engine scores COL-107 at 98.4; R-004 BLOCK holds the claim |

---

## REGULATORY VIOLATIONS

### AU-003: Repair-Shop Watchlist & Ring Detection — **CRITICAL**
Estimate originates from watchlisted shop SHP-007, linked to a high-value claim 1.4x ACV and 2.4x the independent estimate.
- Red flags matched: shop on fraud watchlist; single shop linked to multiple high-value claims; estimate far above comparable repairs.

### AU-002: Repair Estimate Requirement — **HIGH**
Submitted estimate line items are inconsistent with the documented damage and exceed comparable repairs for the loss.
- Red flags matched: estimate from an unverifiable/out-of-network shop; line items inconsistent with reported damage.

### AU-005: Serial Claimer / Staged Collision — **HIGH**
Insured INS-0001 has 6 claims on file (threshold 3), indicating a serial-claimer pattern.
- Red flags matched: 3+ auto claims by the same insured in a short window; claim frequency well above peer group.

### AU-006: Document & Evidence Integrity — **MEDIUM**
Damage photo flagged for forensic review; estimate documentation from a watchlisted source requires authentication.

---

## PRECEDENT CASES

### SIU-AU-2025-0142 — Inflated Repair Estimate, Watchlisted Shop (2025)
- **Scheme**: Out-of-network body shop submitted estimates averaging 1.5x ACV across 11 collision claims, padding line items for undamaged panels.
- **Scale**: 3 entities, 11 claims, $142,000 paid.
- **Outcome**: Shop blacklisted, $142K demand issued, 2 insureds referred for review.
- **Relevance**: **DIRECT PARALLEL** to INS-0001 + SHP-007 (watchlisted shop, estimate above ACV).

### SIU-AU-2025-0064 — Serial Claimer, Staged Collisions (2025)
- **Scheme**: Insured filed 6 auto claims in 12 months, frequency 4.8σ above peers.
- **Scale**: 1 entity, 6 claims, $88,000 paid.
- **Outcome**: Open claims held, policy non-renewed, $88K under recovery review.
- **Relevance**: **DIRECT PARALLEL** to INS-0001's 6-claim serial pattern.

---

## FINANCIAL IMPACT

| Line | Amount |
|------|--------|
| Total Claimed (COL-107) | $25,877.85 |
| Independent Estimate (DECREE midpoint) | $10,750.00 |
| Excess Over Vehicle ACV | $7,393.85 |
| Excess Over Independent Estimate | $15,127.85 |
| Collectability Factor | 61% |
| **Net Expected Prevention / Recovery** | **$9,225.00** |

**Recommended financial action**: DENY the amount exceeding the substantiated repair value; HOLD pending independent re-inspection. If the ring is confirmed across SHP-007's 24-month history, aggregate exposure could materially exceed this single-claim figure (cf. $142K in SIU-AU-2025-0142).

---

## RISK ASSESSMENT

- **Overall Severity**: CRITICAL
- **Confidence Level**: 92%
- **Confidence Factors**:
  - Multiple independent evidence points (8) spanning quantitative, forensic, and regulatory domains
  - Statistical significance: 1.4x ACV and 2.4x an 88%-confidence independent estimate
  - Regulatory violations across AU-003, AU-002, AU-005 (plus AU-006 integrity flag)
  - Two SIU precedents with near-identical patterns and adverse outcomes
  - Watchlisted-shop involvement corroborated by ring-detection signals

---

## RECOMMENDATIONS

1. **DENY** the portion of COL-107 exceeding the substantiated DECREE repair value (~$15,128 over-estimate; deny at minimum the amount above ACV, $7,394).
2. **PLACE ON HOLD** pending an independent re-inspection and line-item breakdown from an in-network shop.
3. **REFER TO SIU** for repair-shop-ring review of SHP-007 (Discount Fender Fix) — cite AU-003.
4. **AUDIT** all estimates submitted by SHP-007 in the past 24 months; identify all linked insureds and claims to size the ring.
5. **REVIEW** all 6 prior claims by INS-0001 for similar estimate-padding patterns; assess for recovery on paid claims.
6. **FLAG** INS-0001 and SHP-007 for enhanced monitoring; consider policy non-renewal for INS-0001 pending SIU findings.
7. **ISSUE** formal denial correspondence citing AU-003 (watchlist), AU-002 (estimate integrity), and AU-005 (serial claimer).

---

## NEXT STEPS

- **Immediate**: Payment hold on COL-107; independent re-inspection ordered.
- **Verification**: Obtain original itemised estimate, police/incident report, and full-resolution damage photos.
- **Investigation**: Expand SHP-007 network scan; profile the other insureds linked to the shop.
- **Recovery**: Prepare demand letters for any identified overpayments across INS-0001's claim history.
- **Prevention**: Add SHP-007 to the blacklist candidate list; escalate to network management.

---
*Generated by ARIA — Car Insurance Examiner Workflow Copilot*
"""


def _send(ws, loop, event_type, data):
    from api import ws_send
    asyncio.run_coroutine_threadsafe(ws_send(ws, event_type, data), loop)
    time.sleep(0.05)


def _log_and_send(ws, loop, agent, message, delay=0.3, log_path=None):
    _send(ws, loop, "log", {"agent": agent, "message": message})
    # Append to the single per-run demo log file (log_path is fixed once per investigation).
    if log_path:
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{agent}\n{message}\n")
        except Exception:
            pass
    time.sleep(delay)


def run_demo_investigation_sync(ws, loop):
    """Replay a scripted inflated-estimate (COL-107) investigation. Called from a thread."""

    # One log file for the entire run (timestamp computed once, not per line).
    _run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    _logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(_logs_dir, exist_ok=True)
    _run_log_path = os.path.join(_logs_dir, f"investigation_demo_{_run_timestamp}.txt")

    s = lambda et, d: _send(ws, loop, et, d)
    log = lambda a, m, delay=0.3: _log_and_send(ws, loop, a, m, delay, log_path=_run_log_path)

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

    log("tool", "tool:scan_suspicious_entities -> Scanning case queue (risk > 40)...")
    time.sleep(1.0)
    log("tool", "tool:scan_suspicious_entities -> Found 4 high-risk entities; top: INS-0001 (98.4), INS-0040 (92.7) (0.3s)")

    log("tool", "tool:profile_entity -> Profiling INS-0001 (Matthew Garcia)...")
    time.sleep(0.8)
    log("tool", "tool:profile_entity -> Insured, 6 claims, current claim COL-107 $25.9K collision, vehicle 2018 Ford F-150 (ACV $18,484)")

    log("tool", "tool:get_claim_details -> Fetching claim COL-107...")
    time.sleep(0.5)
    log("tool", "tool:get_claim_details -> collision $25,877.85; shop SHP-007 (watchlisted); rules R-004, R-005, serial-claimer")

    log("tool", "tool:compare_to_peers -> Comparing INS-0001 claim_amount vs insured peers...")
    time.sleep(0.5)
    log("tool", "tool:compare_to_peers -> Value: $25,877.85, ACV: $18,484, ratio: 1.4x (excess $7,393.85)")

    log("Investigation", "Sub-agent finished in 8.2s | Tool calls made: 4")
    log("Investigation", "Summary: COL-107 is an inflated collision estimate (1.4x ACV) from watchlisted shop SHP-007 by serial claimer INS-0001...")

    s("node_exit", {"node": "investigation", "elapsed": 10.0,
       "findings_preview": "COL-107 risk 98.4, $25,877.85 collision (1.4x ACV $18,484), watchlisted shop SHP-007, insured INS-0001 has 6 claims. Estimate exceeds vehicle value..."})

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

    log("tool", "tool:assess_evidence -> Assessing 'inflated_estimate' (3 evidence points)...")
    time.sleep(0.8)
    log("tool", "tool:assess_evidence -> INSUFFICIENT (2 passed, 2 failed)")
    log("tool", "tool:assess_evidence -> Missing: document_evidence, regulatory_citation")

    log("Dossier", "Evidence assessed as INSUFFICIENT - looping back to investigation")
    s("dossier_rejected", {
        "message": "Dossier rejected — evidence INSUFFICIENT. 2 of 6 critical checks failed.",
        "evidence_gaps": """CASE WRITER DENIAL NOTE — Iteration 1
======================================

CLAIM: Inflated estimate on COL-107 — INS-0001 (Matthew Garcia)
ASSESSMENT: INSUFFICIENT — Cannot proceed to formal dossier

FINDINGS SO FAR:
• COL-107 risk score 98.4 — highest in the active queue
• $25,877.85 collision claim = 1.4x vehicle ACV ($18,484), excess $7,393.85
• Repair estimate from SHP-007 (Discount Fender Fix) — on the fraud watchlist
• Insured INS-0001 is a serial claimer — 6 claims on file

DEFICIENCIES:
1. ESTIMATE / DOCUMENT FORENSICS (CRITICAL): The submitted repair estimate has not been compared line-by-line against the independent DECREE damage assessment, and the watchlisted shop's estimate history has not been reviewed. Without this, the "inflated-estimate / ring" hypothesis is unsupported.
   → Action: Review the COL-107 DECREE line-items and pull SHP-007 shop history.

2. REGULATORY CITATION (REQUIRED): No auto-insurance rules have been cited. A formal dossier requires specific AU rule references to support the denial recommendation.
   → Action: Run search_regulatory_rules(['collision'], 'inflated estimate watchlisted shop serial claimer').

NEXT STEPS: Investigation agent must review the estimate forensics and gather regulatory basis before re-submission."""
    })
    s("node_exit", {"node": "dossier", "elapsed": 14.0, "evidence_sufficient": False})

    # ===== ITERATION 5: Orchestrator → Investigation (loop back) =====
    s("node_enter", {"node": "orchestrator", "iteration": 5})
    log("Orchestrator", "--- Iteration 3 | Current phase: investigate ---")
    log("Orchestrator", "Evidence INSUFFICIENT - looping back to investigation")
    log("Orchestrator", "Phase transition: investigate -> investigate")
    s("phase_change", {"phase": "investigate", "loop_count": 3})
    s("node_exit", {"node": "orchestrator", "elapsed": 15.5, "phase": "investigate", "loop_count": 3})

    # ===== ITERATION 6: Investigation — estimate forensics =====
    s("node_enter", {"node": "investigation", "iteration": 6})
    log("Investigation", "Starting investigation sub-agent (addressing evidence gaps)...")
    log("Investigation", "Evidence gaps: need estimate forensics on the COL-107 repair estimate")

    log("tool", "tool:get_claim_details -> Reviewing COL-107 DECREE line-items vs submitted estimate...")
    time.sleep(1.0)
    log("tool", "tool:get_claim_details -> DECREE estimate $8,950-$12,550 (midpoint $10,750, 88%); submitted $25,877.85 = 2.4x")
    log("tool", "tool:get_claim_details -> Line-items include panels/operations inconsistent with documented front-end damage")

    log("tool", "tool:get_shop_history -> Pulling SHP-007 (Discount Fender Fix) estimate history (24 months)...")
    time.sleep(0.9)
    log("tool", "tool:get_shop_history -> SHP-007 watchlisted; concentration of high-value estimates above comparable repairs")

    log("tool", "tool:find_ring -> Checking for repair-shop ring around SHP-007 (risk >= 50)...")
    time.sleep(0.5)
    log("tool", "tool:find_ring -> SHP-007 linked to multiple high-value claims — potential ring")

    log("Investigation", "Sub-agent finished in 6.8s | Tool calls made: 3")
    s("node_exit", {"node": "investigation", "elapsed": 23.0,
       "findings_preview": "Estimate forensics confirm 2.4x DECREE inflation with padded line-items; SHP-007 watchlisted with clustered high-value estimates. Awaiting AU regulatory citations..."})

    # ===== ITERATION 7: Orchestrator → Dossier =====
    s("node_enter", {"node": "orchestrator", "iteration": 7})
    log("Orchestrator", "--- Iteration 4 | Current phase: investigate ---")
    log("Orchestrator", "Phase transition: investigate -> compile")
    s("phase_change", {"phase": "compile", "loop_count": 4})
    s("node_exit", {"node": "orchestrator", "elapsed": 24.5, "phase": "compile", "loop_count": 4})

    # ===== ITERATION 8: Dossier REJECTS AGAIN =====
    s("node_enter", {"node": "dossier", "iteration": 8})
    log("Dossier", "Starting dossier sub-agent...")

    log("tool", "tool:assess_evidence -> Assessing 'inflated_estimate' (6 evidence points)...")
    time.sleep(0.8)
    log("tool", "tool:assess_evidence -> INSUFFICIENT (4 passed, 1 failed)")
    log("tool", "tool:assess_evidence -> Missing: regulatory_citation — need AU rule references")

    log("Dossier", "Evidence INSUFFICIENT — missing regulatory citations")
    s("dossier_rejected", {
        "message": "Dossier rejected — still INSUFFICIENT. 1 of 6 critical checks failed.",
        "evidence_gaps": """CASE WRITER DENIAL NOTE — Iteration 2
======================================

CLAIM: Inflated estimate on COL-107 — INS-0001 (Matthew Garcia)
ASSESSMENT: INSUFFICIENT — Strong quantitative + forensic case but lacks regulatory grounding

EVIDENCE ESTABLISHED (4 of 5 checks passed):
✓ Multiple evidence points: 6 independent data points collected
✓ Statistical significance: claim 1.4x ACV and 2.4x the independent DECREE estimate
✓ Document evidence: DECREE line-item variance; SHP-007 watchlisted estimate history
✓ Pattern: serial claimer (6 claims) routed through a watchlisted shop

REMAINING DEFICIENCY:
1. REGULATORY CITATION (REQUIRED): No auto-insurance regulatory rules have been cited. A formal dossier requires specific AU rule references to support the denial recommendation and withstand appeals. Likely applicable:
   • AU-003 (Repair-Shop Watchlist & Ring Detection) — estimate from watchlisted SHP-007
   • AU-002 (Repair Estimate Requirement) — line items inconsistent with the damage
   • AU-005 (Serial Claimer / Staged Collision) — 6 claims on file
   → Action: Run search_regulatory_rules(['collision'], 'inflated estimate watchlisted shop serial claimer').

NOTE: Once the regulatory basis is established, this case is ready for final compilation with ~$9.2K over-estimate denial."""
    })
    s("node_exit", {"node": "dossier", "elapsed": 27.0, "evidence_sufficient": False})

    # ===== ITERATION 9: Orchestrator → Investigation =====
    s("node_enter", {"node": "orchestrator", "iteration": 9})
    log("Orchestrator", "--- Iteration 5 | Current phase: investigate ---")
    log("Orchestrator", "Phase transition: investigate -> investigate")
    s("phase_change", {"phase": "investigate", "loop_count": 5})
    s("node_exit", {"node": "orchestrator", "elapsed": 28.5, "phase": "investigate", "loop_count": 5})

    # ===== ITERATION 10: Investigation — regulatory basis =====
    s("node_enter", {"node": "investigation", "iteration": 10})
    log("Investigation", "Gathering regulatory basis for inflated-estimate / repair-shop ring...")

    log("tool", "tool:get_claim_details -> Confirming COL-107 rule triggers and coverage...")
    time.sleep(0.8)
    log("tool", "tool:get_claim_details -> R-004 (watchlist BLOCK), R-005 (amount exceeds ACV), serial-claimer; ACV exceeded by $7,393.85")

    log("Investigation", "Sub-agent finished in 2.5s | Tool calls made: 1")
    s("node_exit", {"node": "investigation", "elapsed": 31.5,
       "findings_preview": "Confirmed rule triggers R-004/R-005/serial-claimer and $7,393.85 over-ACV. Combined with forensics, AU-003/AU-002/AU-005 applicable..."})

    # ===== ITERATION 11: Orchestrator → Dossier (final) =====
    s("node_enter", {"node": "orchestrator", "iteration": 11})
    log("Orchestrator", "--- Iteration 6 | Current phase: investigate ---")
    log("Orchestrator", "Phase transition: investigate -> compile")
    s("phase_change", {"phase": "compile", "loop_count": 6})
    s("node_exit", {"node": "orchestrator", "elapsed": 33.0, "phase": "compile", "loop_count": 6})

    # ===== ITERATION 12: Dossier ACCEPTS =====
    s("node_enter", {"node": "dossier", "iteration": 12})
    log("Dossier", "Starting dossier sub-agent...")

    log("tool", "tool:assess_evidence -> Assessing 'inflated_estimate' (8 evidence points)...")
    time.sleep(0.8)
    log("tool", "tool:assess_evidence -> SUFFICIENT (5 passed, 0 failed)")

    log("tool", "tool:search_regulatory_rules -> Searching rules for collision...")
    time.sleep(0.6)
    log("tool", "tool:search_regulatory_rules -> Found 3 applicable rules: AU-003, AU-002, AU-005")

    log("tool", "tool:find_similar_cases -> Looking up precedents for inflated_estimate...")
    time.sleep(0.5)
    log("tool", "tool:find_similar_cases -> Found 2 precedent cases")

    log("tool", "tool:estimate_recovery -> Inflated estimate: $25.9K claimed, $10.75K substantiated...")
    time.sleep(0.5)
    log("tool", "tool:estimate_recovery -> Over-estimate exposure $15,128; net prevention $9,225")

    log("tool", "tool:compile_dossier -> Generating auto-insurance fraud dossier...")
    time.sleep(1.0)
    log("tool", "tool:compile_dossier -> Dossier generated (3,240 chars)")

    log("Dossier", "Evidence assessed as SUFFICIENT")
    s("dossier_accepted", {"message": "Evidence SUFFICIENT — dossier compiled."})
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
            "last_investigation": "Inflated estimate confirmed: COL-107 (INS-0001), $25,877.85 = 1.4x ACV ($18,484) and 2.4x DECREE estimate ($10,750), watchlisted shop SHP-007, serial claimer (6 claims). Rules: R-004, R-005 / AU-003, AU-002, AU-005.",
        },
    })

    return dossier_text
