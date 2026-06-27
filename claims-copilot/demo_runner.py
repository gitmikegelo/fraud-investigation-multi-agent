"""
Deterministic Demo Runner for Zurich Travel Guard Investigation
===============================================================
Replays a fixed baggage-padding fraud scenario over WebSocket.
No LLM / Bedrock calls are made.

Scenario (claim BL-303 — Donna Walker / TRV-0003, baggage_loss)
---------------------------------------------------------------
1.  Orchestrator routes to Investigation (Phase: investigate)
2.  Investigation scans entities, profiles traveler TRV-0003
3.  Orchestrator routes to Dossier (Phase: compile)
4.  Dossier REJECTS — insufficient evidence (missing photo/document forensics)
5.  Investigation reviews the luggage-photo vision findings
6.  Orchestrator routes to Dossier (Phase: compile)
7.  Dossier REJECTS AGAIN — missing regulatory citations
8.  Investigation gathers TG regulatory rules + peer comparison
9.  Orchestrator routes to Dossier (Phase: compile)
10. Dossier ACCEPTS — evidence sufficient → produces final dossier
"""

import asyncio
import time
import os
from datetime import datetime

DEMO_FINAL_DOSSIER = r"""# TRAVEL INSURANCE FRAUD INVESTIGATION DOSSIER

**Hypothesis**: Baggage value-padding with staged damage — luxury-item baggage_loss claim 6.6x peer average, exceeding policy limit, supported by a manipulated luggage photo
**Case Type**: Baggage Padding / Value Inflation
**Generated**: {date}
**Status**: Evidence Sufficient - Ready for Action

---

## EXECUTIVE SUMMARY

Investigation identified suspected **baggage value-padding** on claim **BL-303** filed by traveler **TRV-0003 (Donna Walker)**. The $15,200 baggage_loss claim is **6.6x the peer average** ($2,312) and **exceeds the $2,500 policy baggage limit by $12,700 (508%)**. The submitted luggage photo shows **staged, deliberately created damage** (vision check DOC-002, CRITICAL), and the claimant's identity could not be confirmed from the baggage tag (DOC-005). The traveler is a **serial claimer** with 6 claims on file. Risk score **99.0 (HIGH)**. 8 independent evidence points with quantitative and regulatory basis established.

---

## ENTITIES INVOLVED

### Entity 1: TRV-0003 (Donna Walker)
- **Type**: Traveler (Primary Subject)
- **Risk Score**: 99
- **Total Claims**: 6 (serial claimer — threshold 3)
- **Current Claim**: BL-303 — $15,200.00 baggage_loss
- **Loyalty Tier**: standard

### Entity 2: BL-303 (Claim)
- **Type**: Baggage Loss Claim
- **Amount**: $15,200.00 (6.6x peer average of $2,312.40)
- **Policy Limit**: $2,500.00 — exceeded by $12,700.00 (508%)
- **Items**: Rolex Submariner, Louis Vuitton carry-on, MacBook Pro 16", Bose headphones, Prada sunglasses, cashmere sweater, gold jewelry — no purchase receipts

---

## EVIDENCE

1. BL-303 risk score 99.0 — highest in the active queue, 3 rules triggered (R-004, R-007, R-011)
2. Claim amount $15,200 is 6.6x the baggage_loss peer average of $2,312 (z-score 5.09)
3. Claim exceeds the $2,500 policy baggage coverage limit by $12,700 (508% over)
4. Luggage photo vision review [DOC-002 CRITICAL]: concentrated jagged hole appears deliberately created, inconsistent with carousel/transport damage
5. [DOC-005 WARNING]: baggage tag illegible — claimant identity (Donna Walker) cannot be confirmed; routing LHR→JFK visible but ownership unverified
6. All claimed items are high-value luxury goods (Rolex, LV, MacBook) with NO purchase receipts provided
7. Traveler TRV-0003 is a serial claimer — 6 claims on file vs peer norm (z-score elevated)
8. R-011 BLOCK: photo evidence held for forensic image review (staged-damage / value-padding risk)

---

## DOCUMENT & PHOTO FORENSICS

- **Evidence image**: images/bl303.png (damaged-luggage photo)
- **DOC-002 (CRITICAL)** Staged or Inconsistent Damage — large jagged hole concentrated in one localized area; deliberate-appearing rather than transport damage
- **DOC-005 (WARNING)** Missing Identifying Detail — baggage tag not legible enough to confirm claimant identity
- **Vision assessment**: significant red flags regarding damage authenticity; damage pattern suggests potential claim fraud

---

## REGULATORY VIOLATIONS

### TG-004: Baggage Valuation — Outlier and Receipt Verification
Claim is 6.6x the peer average, comprises exclusively luxury items with no receipts, and exceeds the policy baggage limit. Submitted photo shows staged/inconsistent damage.

### TG-007: Serial Claimer — Benefit Harvesting
Traveler TRV-0003 has 6 claims on file (threshold 3), indicating a benefit-harvesting pattern.

### TG-009: Document & Evidence Integrity
The luggage photo shows manipulated/staged damage and the baggage tag cannot substantiate ownership — fails evidence-integrity checks.

---

## PRECEDENT CASES

- **SIU-TG-2025-0207**: Baggage Padding — luxury-item claim 6x peer average, no receipts, staged damage photo. Claim reduced to documented items, $11K prevented.
- **SIU-TG-2025-0064**: Serial Claimer — 8 claims in 14 months, frequency 4.8σ above peers. Policy non-renewed, $47K under recovery review.

---

## FINANCIAL IMPACT

- **Total Claimed (BL-303)**: $15,200.00
- **Amount Within Policy Limit**: $2,500.00
- **Excess Over Limit**: $12,700.00
- **Collectability Factor**: 61%
- **Net Expected Prevention/Recovery**: **$12,700.00** (deny amount over limit; full denial if fraud substantiated)
- **Recommended Action**: DENY amount exceeding limit; HOLD pending receipts — escalate for staged-damage fraud

---

## RECOMMENDATIONS

1. **DENY** the portion of BL-303 exceeding the $2,500 policy baggage limit ($12,700)
2. **PLACE ON HOLD** pending original purchase receipts and proof of ownership for all luxury items
3. **REFER TO SIU** for staged-damage fraud — the luggage photo shows deliberately created damage
4. **REQUEST** legible baggage tag / airline baggage-handling records for flight LHR→JFK (2026-01-25)
5. **REVIEW** all 6 prior claims by TRV-0003 for similar value-padding patterns
6. **FLAG** TRV-0003 for enhanced monitoring on future claims

---
*Generated by ARIA - Zurich Travel Guard Investigation Copilot*
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
    """Replay a scripted baggage-padding (BL-303) investigation. Called from a thread."""

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
    log("tool", "tool:scan_suspicious_entities -> Found 7 high-risk entities; top: BL-303 (99.0), BL-040 (93.6) (0.3s)")

    log("tool", "tool:profile_entity -> Profiling TRV-0003 (Donna Walker)...")
    time.sleep(0.8)
    log("tool", "tool:profile_entity -> Traveler, 6 claims, current claim BL-303 $15.2K baggage_loss, loyalty=standard")

    log("tool", "tool:get_claim_details -> Fetching claim BL-303...")
    time.sleep(0.5)
    log("tool", "tool:get_claim_details -> baggage_loss $15,200; 7 luxury items, no receipts; rules R-004, R-007, R-011")

    log("tool", "tool:compare_to_peers -> Comparing TRV-0003 baggage_value vs traveler peers...")
    time.sleep(0.5)
    log("tool", "tool:compare_to_peers -> Value: $15,200, peer_avg: $2,312, z-score: 5.09")

    log("Investigation", "Sub-agent finished in 8.2s | Tool calls made: 4")
    log("Investigation", "Summary: BL-303 is an extreme baggage_loss outlier (6.6x peer avg) by serial claimer TRV-0003...")

    s("node_exit", {"node": "investigation", "elapsed": 10.0,
       "findings_preview": "BL-303 risk 99.0, $15,200 baggage_loss (6.6x peer avg, z=5.09), 7 luxury items no receipts, traveler TRV-0003 has 6 claims. Exceeds $2,500 policy limit..."})

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

    log("tool", "tool:assess_evidence -> Assessing 'baggage_padding' (3 evidence points)...")
    time.sleep(0.8)
    log("tool", "tool:assess_evidence -> INSUFFICIENT (2 passed, 2 failed)")
    log("tool", "tool:assess_evidence -> Missing: document_evidence, regulatory_citation")

    log("Dossier", "Evidence assessed as INSUFFICIENT - looping back to investigation")
    s("dossier_rejected", {
        "message": "Dossier rejected — evidence INSUFFICIENT. 2 of 6 critical checks failed.",
        "evidence_gaps": """CASE WRITER DENIAL NOTE — Iteration 1
======================================

CLAIM: Baggage padding on BL-303 — TRV-0003 (Donna Walker)
ASSESSMENT: INSUFFICIENT — Cannot proceed to formal dossier

FINDINGS SO FAR:
• BL-303 risk score 99.0 — highest in the active queue
• $15,200 baggage_loss claim = 6.6x peer average ($2,312), z-score 5.09
• 7 luxury items (Rolex, Louis Vuitton, MacBook) with no purchase receipts
• Claim exceeds the $2,500 policy baggage limit by $12,700

DEFICIENCIES:
1. PHOTO/DOCUMENT FORENSICS (CRITICAL): A damaged-luggage photo was submitted but the forensic vision findings have not been reviewed. Cannot confirm whether the damage is genuine or staged. Without this, the "value-padding with staged damage" hypothesis is unsupported.
   → Action: Review the BL-303 evidence-image vision checks (DOC-002 staged damage, DOC-005 identity).

2. REGULATORY CITATION (REQUIRED): No travel-insurance rules have been cited. A formal dossier requires specific TG rule references to support the denial recommendation.
   → Action: Run search_regulatory_rules(['baggage_loss'], 'baggage padding luxury no receipts staged photo').

NEXT STEPS: Investigation agent must review the photo forensics and gather regulatory basis before re-submission."""
    })
    s("node_exit", {"node": "dossier", "elapsed": 14.0, "evidence_sufficient": False})

    # ===== ITERATION 5: Orchestrator → Investigation (loop back) =====
    s("node_enter", {"node": "orchestrator", "iteration": 5})
    log("Orchestrator", "--- Iteration 3 | Current phase: investigate ---")
    log("Orchestrator", "Evidence INSUFFICIENT - looping back to investigation")
    log("Orchestrator", "Phase transition: investigate -> investigate")
    s("phase_change", {"phase": "investigate", "loop_count": 3})
    s("node_exit", {"node": "orchestrator", "elapsed": 15.5, "phase": "investigate", "loop_count": 3})

    # ===== ITERATION 6: Investigation — photo forensics =====
    s("node_enter", {"node": "investigation", "iteration": 6})
    log("Investigation", "Starting investigation sub-agent (addressing evidence gaps)...")
    log("Investigation", "Evidence gaps: need photo/document forensics on the luggage image")

    log("tool", "tool:get_claim_details -> Reviewing BL-303 evidence-image vision checks...")
    time.sleep(1.0)
    log("tool", "tool:get_claim_details -> DOC-002 CRITICAL: jagged hole appears deliberately created, inconsistent with transport damage")
    log("tool", "tool:get_claim_details -> DOC-005 WARNING: baggage tag illegible — claimant identity unconfirmed (routing LHR→JFK)")

    log("tool", "tool:find_ring -> Checking for related baggage/value-padding patterns (risk >= 50)...")
    time.sleep(0.9)
    log("tool", "tool:find_ring -> No coordinated ring; isolated high-value claimant TRV-0003")

    log("tool", "tool:compare_to_peers -> Comparing TRV-0003 claim_count vs travelers...")
    time.sleep(0.5)
    log("tool", "tool:compare_to_peers -> Value: 6, peer_avg: 1.4, z-score: 3.1 (serial claimer)")

    log("Investigation", "Sub-agent finished in 6.8s | Tool calls made: 3")
    s("node_exit", {"node": "investigation", "elapsed": 23.0,
       "findings_preview": "Photo forensics confirm staged damage (DOC-002 CRITICAL); identity unverified (DOC-005). Serial-claimer z-score 3.1. Awaiting TG regulatory citations..."})

    # ===== ITERATION 7: Orchestrator → Dossier =====
    s("node_enter", {"node": "orchestrator", "iteration": 7})
    log("Orchestrator", "--- Iteration 4 | Current phase: investigate ---")
    log("Orchestrator", "Phase transition: investigate -> compile")
    s("phase_change", {"phase": "compile", "loop_count": 4})
    s("node_exit", {"node": "orchestrator", "elapsed": 24.5, "phase": "compile", "loop_count": 4})

    # ===== ITERATION 8: Dossier REJECTS AGAIN =====
    s("node_enter", {"node": "dossier", "iteration": 8})
    log("Dossier", "Starting dossier sub-agent...")

    log("tool", "tool:assess_evidence -> Assessing 'baggage_padding' (6 evidence points)...")
    time.sleep(0.8)
    log("tool", "tool:assess_evidence -> INSUFFICIENT (4 passed, 1 failed)")
    log("tool", "tool:assess_evidence -> Missing: regulatory_citation — need TG rule references")

    log("Dossier", "Evidence INSUFFICIENT — missing regulatory citations")
    s("dossier_rejected", {
        "message": "Dossier rejected — still INSUFFICIENT. 1 of 6 critical checks failed.",
        "evidence_gaps": """CASE WRITER DENIAL NOTE — Iteration 2
======================================

CLAIM: Baggage padding on BL-303 — TRV-0003 (Donna Walker)
ASSESSMENT: INSUFFICIENT — Strong quantitative + forensic case but lacks regulatory grounding

EVIDENCE ESTABLISHED (4 of 5 checks passed):
✓ Multiple evidence points: 6 independent data points collected
✓ Statistical significance: baggage value z-score 5.09, serial-claimer z-score 3.1 (both > 2.0)
✓ Document evidence: luggage photo shows staged damage (DOC-002 CRITICAL), identity unverified (DOC-005)
✓ Temporal/amount pattern: claim 6.6x peer average, exceeds policy limit by 508%

REMAINING DEFICIENCY:
1. REGULATORY CITATION (REQUIRED): No travel-insurance regulatory rules have been cited. A formal dossier requires specific TG rule references to support the denial recommendation and withstand appeals. Likely applicable:
   • TG-004 (Baggage Valuation — Outlier & Receipt Verification) — 6.6x peer avg, no receipts, over policy limit
   • TG-007 (Serial Claimer — Benefit Harvesting) — 6 claims on file
   • TG-009 (Document & Evidence Integrity) — staged-damage photo, unverifiable baggage tag
   → Action: Run search_regulatory_rules(['baggage_loss'], 'baggage padding luxury no receipts staged photo').

NOTE: Once the regulatory basis is established, this case is ready for final compilation with ~$12.7K over-limit denial."""
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
    log("Investigation", "Gathering regulatory basis for baggage value-padding...")

    log("tool", "tool:get_claim_details -> Confirming BL-303 rule triggers and coverage limit...")
    time.sleep(0.8)
    log("tool", "tool:get_claim_details -> R-004 (outlier), R-007 (serial), R-011 (photo review BLOCK); limit $2,500 exceeded by $12,700")

    log("Investigation", "Sub-agent finished in 2.5s | Tool calls made: 1")
    s("node_exit", {"node": "investigation", "elapsed": 31.5,
       "findings_preview": "Confirmed rule triggers R-004/R-007/R-011 and $12,700 over-limit. Combined with forensics, TG-004/TG-007/TG-009 applicable..."})

    # ===== ITERATION 11: Orchestrator → Dossier (final) =====
    s("node_enter", {"node": "orchestrator", "iteration": 11})
    log("Orchestrator", "--- Iteration 6 | Current phase: investigate ---")
    log("Orchestrator", "Phase transition: investigate -> compile")
    s("phase_change", {"phase": "compile", "loop_count": 6})
    s("node_exit", {"node": "orchestrator", "elapsed": 33.0, "phase": "compile", "loop_count": 6})

    # ===== ITERATION 12: Dossier ACCEPTS =====
    s("node_enter", {"node": "dossier", "iteration": 12})
    log("Dossier", "Starting dossier sub-agent...")

    log("tool", "tool:assess_evidence -> Assessing 'baggage_padding' (8 evidence points)...")
    time.sleep(0.8)
    log("tool", "tool:assess_evidence -> SUFFICIENT (5 passed, 0 failed)")

    log("tool", "tool:search_regulatory_rules -> Searching rules for baggage_loss...")
    time.sleep(0.6)
    log("tool", "tool:search_regulatory_rules -> Found 3 applicable rules: TG-004, TG-007, TG-009")

    log("tool", "tool:find_similar_cases -> Looking up precedents for baggage_padding...")
    time.sleep(0.5)
    log("tool", "tool:find_similar_cases -> Found 2 precedent cases")

    log("tool", "tool:estimate_recovery -> Baggage padding: $15.2K claimed, $2.5K limit...")
    time.sleep(0.5)
    log("tool", "tool:estimate_recovery -> Over-limit exposure $12,700; net prevention $12,700")

    log("tool", "tool:compile_dossier -> Generating travel-insurance fraud dossier...")
    time.sleep(1.0)
    log("tool", "tool:compile_dossier -> Dossier generated (3,180 chars)")

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
            "last_investigation": "Baggage value-padding confirmed: BL-303 (TRV-0003), $15,200 = 6.6x peer avg (z=5.09), exceeds $2,500 policy limit by $12,700, staged-damage photo (DOC-002). Rules: R-004, R-007, R-011 / TG-004, TG-007, TG-009.",
        },
    })

    return dossier_text
