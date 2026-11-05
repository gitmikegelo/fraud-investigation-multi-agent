"""
Deterministic Demo Runner for the Marine Cargo Investigation
============================================================
Replays a fixed over-valuation / part-phantom cargo / colluding-surveyor scenario
over WebSocket. No LLM / Bedrock calls are made.

All names are fictional. Figures match data/generate_marine.py (seed 3107).

Scenario (claim MC-3107 — Luzon Premier Glass & Glazing Corp. / CNE-012, breakage)
----------------------------------------------------------------------------------
1.  Orchestrator routes to Investigation
2.  Investigation scans entities, profiles CNE-012, pulls claim details
3.  Orchestrator routes to Dossier
4.  Dossier REJECTS — shipping documents not reconciled, evidence images not checked
5.  Investigation reconciles B/L / invoice / VGM, benchmarks value, checks photo reuse
6.  Orchestrator routes to Dossier
7.  Dossier REJECTS AGAIN — no coverage basis, network not confirmed
8.  Investigation maps shared director/address, surveyor history, recovery position
9.  Dossier ACCEPTS → final dossier
"""

import asyncio
import time
import os
from datetime import datetime

DEMO_CLAIM_ID = "MC-3107"

DEMO_FINAL_DOSSIER = r"""# MARINE CARGO CLAIM INVESTIGATION DOSSIER

**Hypothesis**: Over-valued, part-phantom cargo supported by a non-independent survey — breakage claim on a shipment whose weighed container mass shows ~43% less cargo than invoiced, surveyed by a firm that shares a director and registered address with the claimant
**Case Type**: Over-valuation / Phantom Cargo / Colluding Surveyor
**Case Reference**: MC-3107 · CNE-012 · SVY-004 · FWD-002
**Generated**: {date}
**Risk Score**: 99.0 / 100 (HIGH)
**Confidence Level**: 91%
**Status**: Evidence Sufficient — Ready for Decision

---

## EXECUTIVE SUMMARY

Claim **MC-3107** from **Luzon Premier Glass & Glazing Corp.** seeks **US$204,493.29** — 71% of the insured value — for breakage of insulated glass units shipped Singapore → Manila on **MERIDIAN HARMONY 034N** (B/L MCLSIN2604417, 6 × 20GP). The physical evidence contradicts the paperwork: the containers' **verified gross mass (VGM) shows 77,466 kg of cargo against 135,000 kg declared** on the B/L and packing list. The invoiced 4,320 m² cannot have been loaded; the weight supports at most ~2,580 m². The invoice price of **US$58.00/m² is 1.76× the market benchmark** (US$28–38/m²), and the shipper was incorporated ten months before the shipment.

The loss was surveyed **17 days after discharge**, at the claimant's own warehouse, by **Northport Cargo Inspection Services** — appointed by the claimant, not by us, and sharing a **director (Ramon T. Villareal) and registered address** with both the claimant and its freight forwarder. One survey photo is a near-duplicate of a photo filed on paid claim **MC-2988**. The same surveyor appears on **5 prior paid breakage claims (US$644,700.50) across 3 consignees**.

**Bottom line**: **DECLINE** MC-3107 as presented and **REFER FOR INVESTIGATION**. No recovery against the carrier is available (clean EIR, seals intact, no notice of claim). Open a review of the five prior claims surveyed by SVY-004.

---

## ENTITIES INVOLVED

### CNE-012 — Luzon Premier Glass & Glazing Corp. (Claimant / Consignee)
- **Incorporated**: 2021-03-18 · Makati City · ~14 shipments per year
- **Claims in 24 months**: 4 on ~28 shipments (**14.3% claim rate** — book average is below 3%)
- **Prior paid claims**: MC-2711, MC-2846, MC-2957 — all breakage, all surveyed by SVY-004 (US$446,465.50)
- **Director**: Ramon T. Villareal (DIR-001)

### SVY-004 — Northport Cargo Inspection Services Inc. (Surveyor)
- **Not on the insurer's surveyor panel**; appointed by the assured
- **Shares director DIR-001 and the registered address** Unit 1204, Paseo Meridian Tower, 88 Paseo de Roxas, Makati City with the claimant
- **History**: 5 prior paid breakage claims across 3 consignees, US$644,700.50

### FWD-002 — Swiftlink Freight Forwarding Inc. (Forwarder)
- **Shares director DIR-001 and the same registered address**
- Booked all three prior Luzon Premier shipments that resulted in claims

### SHR-008 — Orchid Trade Links Pte. Ltd. (Shipper, Singapore)
- Trading company **incorporated 2025-11-04**, ten months before shipment
- No glass-processing facility on record; issued invoice OTL-INV-26-0917

---

## EVIDENCE LEDGER

| # | Evidence | Severity | Source |
|---|----------|----------|--------|
| 1 | VGM cargo weight 77,466 kg vs 135,000 kg declared — 43% short; invoiced quantity cannot have been loaded | CRITICAL | Carrier VGM records vs B/L / packing list (R-003) |
| 2 | Survey photo is a near-duplicate of an image filed on paid claim MC-2988 | CRITICAL | Perceptual-hash image match (R-009) |
| 3 | Surveyor shares director and registered address with the claimant and forwarder | CRITICAL | Corporate registry link analysis (R-004) |
| 4 | Invoice US$58.00/m² = 1.76× market benchmark US$28–38/m² | HIGH | Commodity price benchmark (R-002) |
| 5 | Survey 17 days after discharge, at claimant's warehouse, by assured-appointed surveyor; no joint survey | HIGH | Survey report NCIS-26-0388 (R-005) |
| 6 | EIR clean and all six seals intact at gate-out, yet 71% breakage claimed | HIGH | EIR / seal records (R-008) |
| 7 | No notice of claim to the carrier; insurer notified 9 days after unstuffing | MEDIUM | Claim file (R-006) |
| 8 | Claimant claim rate 14.3% of shipments; shipper incorporated 10 months before shipment | MEDIUM | Claims history / registry (R-007) |
| 9 | Breakage is an insured peril under ICC (A), and the loss falls inside the transit and certificate period | MITIGATING | Certificate CERT-264417 / ICC (A) 2009 |

---

## DOCUMENT CROSS-CHECK

| Document | Figure | Consistent? |
|----------|--------|-------------|
| Commercial invoice OTL-INV-26-0917 | 4,320 m² × US$58.00 = US$250,560.00 (FOB Singapore) | Value 1.76× benchmark |
| Packing list | 108 A-frame racks, 135,000 kg | Matches invoice |
| Bill of lading MCLSIN2604417 | 135,000 kg — *Shipper's load, stow and count; said to contain* | Shipper's figures, not verified by carrier |
| VGM (6 × 20GP) | 90,966 kg gross − 13,500 kg tare = **77,466 kg cargo** | **43% below declared weight** |

**Interpretation**: The B/L, invoice and packing list agree with each other because they all carry the shipper's own figures. The VGM is the only independent physical measurement — and it does not support the invoiced quantity. At 30 kg/m², 77,466 kg supports at most ~2,580 m² of glass. Either the containers were short-loaded or the invoice overstates what was shipped.

---

## SURVEY & EVIDENCE INTEGRITY

- **Survey NCIS-26-0388** by Northport Cargo Inspection Services — appointed by the assured, not on the insurer's panel
- Conducted **2026-09-14**, 17 days after discharge, at the consignee's warehouse in Valenzuela City, **after the cargo had already been unstuffed**; no joint survey with the carrier
- **Photo reuse**: one of 14 survey photos matches an image filed on MC-2988 (Rizal Construction Materials Inc., paid 2026-04-15), which was also surveyed by SVY-004
- The surveyor's stated cause ("rough handling in transit") is not consistent with a clean EIR and intact seals at gate-out

---

## COVERAGE ANALYSIS (ICC 2009)

- **ICC (A)** covers breakage as a risk of loss or damage, subject to the exclusions — the peril itself would be insured
- **Transit (cl. 8)**: loss reported within the insured transit — not in issue
- **Duty of assured (cl. 16)**: the assured must ensure that rights against carriers are properly preserved and exercised. No notice of claim was served on the carrier, and cargo was accepted on a clean EIR
- **Hague-Visby Rules Art. III r.6**: without notice of loss at removal (or within 3 days where damage is not apparent), removal is *prima facie* evidence of delivery as described in the B/L — the carrier recovery is effectively lost
- **Utmost good faith / fraudulent claims (Marine Insurance Act 1906, s.17)**: if the claim is shown to be fraudulent, it is not recoverable
- **Internal guideline MC-GL-01**: claims above US$50,000 require a survey by an insurer-appointed panel surveyor — not met

---

## NETWORK ANALYSIS

```
                     DIR-001 Ramon T. Villareal
              ┌──────────────┼──────────────┐
         director of    director of     director of
              ▼              ▼              ▼
   CNE-012 Luzon Premier  SVY-004 Northport  FWD-002 Swiftlink
   (claimant)             (surveyor)         (forwarder)
              └────── same registered address: Unit 1204, Paseo Meridian Tower, Makati ──────┘

   SVY-004 surveyed:  MC-2711, MC-2846, MC-2957 (CNE-012) · MC-2988 (CNE-007) · MC-3012 (CNE-004) · MC-3107
```

- **Ring pattern**: claimant, surveyor and forwarder under common control; the surveyor validates the claimant's losses
- **Scope**: 6 claims, 3 consignees, **US$849,193.79** claimed in 20 months (US$644,700.50 already paid)

---

## TIMELINE

| Date | Event |
|------|-------|
| 2025-11-04 | Shipper Orchid Trade Links Pte. Ltd. incorporated in Singapore |
| 2026-08-24 | 6 × 20GP shipped on board MERIDIAN HARMONY 034N, Singapore (PSA) |
| 2026-08-28 | Discharged at Manila (MICT) |
| 2026-08-31 | Gate-out — EIR clean, all seals intact |
| 2026-09-02 | Containers unstuffed at claimant's warehouse; breakage reported |
| 2026-09-11 | Insurer notified (9 days after unstuffing) |
| 2026-09-14 | Survey by assured-appointed SVY-004, 17 days after discharge |
| 2026-10-02 | Claim filed: US$204,493.29 |
| — | No notice of claim ever served on the carrier |

---

## PRECEDENT CASES (internal)

### MC-SIU-2025-0217 — Over-valued glass shipments, related-party surveyor
- Consignee and surveyor under common ownership; invoices 1.6–1.9× market; 4 claims, US$512,000 paid
- **Outcome**: claims declined, recovery action on paid claims, surveyor removed from all files
- **Relevance**: DIRECT PARALLEL — related-party survey plus over-valuation

### MC-SIU-2024-0088 — Short-loaded containers, paperwork weights
- Invoice and packing list overstated quantity; terminal weights showed 35–50% less cargo
- **Outcome**: claim declined; referred to authorities
- **Relevance**: DIRECT PARALLEL — VGM contradicts declared weight

---

## FINANCIAL POSITION

| Line | Amount (US$) |
|------|--------------|
| Invoice value (FOB) | 250,560.00 |
| Insured value (CIF + 10%) | 288,018.72 |
| **Amount claimed (71%)** | **204,493.29** |
| Recovery against carrier | Nil — clean EIR, seals intact, no notice of claim |
| **Payment avoided if declined** | **204,493.29** |
| Prior paid claims surveyed by SVY-004 (for review) | 644,700.50 |

---

## RECOMMENDATIONS

1. **DECLINE** MC-3107 as presented; reserve all rights under the certificate and at law.
2. **REFER FOR INVESTIGATION** — appoint an independent panel surveyor and request the shipper's loading tally, container-stuffing photos and the terminal weighbridge tickets.
3. **REVIEW** the five prior claims surveyed by SVY-004 (US$644,700.50 paid) for recovery.
4. **REMOVE** SVY-004 from all open files; require insurer-appointed surveyors for this assured.
5. **UNDERWRITING**: review the open cover OC-SG-2026-0142 for non-renewal or special conditions.

---
*Generated by ARIA — Marine Cargo Claims Copilot · All names fictional*
"""


def _send(ws, loop, event_type, data):
    from api import ws_send
    asyncio.run_coroutine_threadsafe(ws_send(ws, event_type, data), loop)
    time.sleep(0.05)


def _log_and_send(ws, loop, agent, message, delay=0.3, log_path=None):
    _send(ws, loop, "log", {"agent": agent, "message": message})
    if log_path:
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{agent}\n{message}\n")
        except Exception:
            pass
    time.sleep(delay)


def demo_dossier_text() -> str:
    return DEMO_FINAL_DOSSIER.format(date=datetime.now().strftime("%Y-%m-%d %H:%M"))


def run_demo_investigation_sync(ws, loop):
    """Replay the scripted MC-3107 investigation. Called from a thread."""

    _run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    _logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
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
    log("Orchestrator", "LLM responded in 1.3s")
    log("Orchestrator", "Phase transition: start -> investigate")
    s("phase_change", {"phase": "investigate", "loop_count": 1})
    s("node_exit", {"node": "orchestrator", "elapsed": 1.5, "phase": "investigate", "loop_count": 1})

    # ===== ITERATION 2: Investigation — initial scan =====
    s("node_enter", {"node": "investigation", "iteration": 2})
    log("Investigation", "Starting investigation sub-agent (7 tools available)...")
    log("Investigation", "Invoking LLM + tool loop...")

    log("tool", "tool:scan_suspicious_entities -> Scanning case queue (risk > 40)...")
    time.sleep(1.0)
    log("tool", "tool:scan_suspicious_entities -> 3 HIGH-risk claims; top: MC-3107 (99.0) — CNE-012 Luzon Premier Glass & Glazing Corp.")

    log("tool", "tool:profile_entity -> Profiling CNE-012 (Luzon Premier Glass & Glazing Corp.)...")
    time.sleep(0.8)
    log("tool", "tool:profile_entity -> Consignee, Makati City, ~14 shipments/yr; 4 claims in 24 months, all breakage")

    log("tool", "tool:get_claim_details -> Fetching claim MC-3107...")
    time.sleep(0.5)
    log("tool", "tool:get_claim_details -> Breakage US$204,493.29 (71% of insured value); 6 × 20GP IGU glass, SIN → MNL; "
                "rules R-003, R-004 (BLOCK), R-002, R-005, R-006, R-007, R-008, R-012 (FLAG)")

    log("tool", "tool:compare_to_peers -> Comparing CNE-012 claim rate vs consignee peers...")
    time.sleep(0.5)
    log("tool", "tool:compare_to_peers -> Claim rate 14.3% of shipments vs peer median 1.7% (~8x)")

    log("Investigation", "Sub-agent finished in 8.4s | Tool calls made: 4")
    log("Investigation", "Summary: MC-3107 is a large breakage claim from a high-frequency claimant; weight and survey rules triggered...")
    s("node_exit", {"node": "investigation", "elapsed": 10.0,
                    "findings_preview": "MC-3107 risk 99.0, US$204,493.29 breakage (71% of insured value). CNE-012 has 4 claims in 24 months (14.3% claim rate). Weight and survey rules triggered..."})

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
    log("tool", "tool:assess_evidence -> Assessing 'overvalued_phantom_cargo' (4 evidence points)...")
    time.sleep(0.8)
    log("tool", "tool:assess_evidence -> INSUFFICIENT (2 passed, 3 failed)")
    log("tool", "tool:assess_evidence -> Missing: document_reconciliation, value_benchmark, evidence_integrity")
    log("Dossier", "Evidence assessed as INSUFFICIENT - looping back to investigation")
    s("dossier_rejected", {
        "message": "Dossier rejected — evidence INSUFFICIENT. 3 of 5 critical checks failed.",
        "evidence_gaps": """CASE WRITER DENIAL NOTE — Iteration 1
======================================

CLAIM: Breakage on MC-3107 — CNE-012 (Luzon Premier Glass & Glazing Corp.)
ASSESSMENT: INSUFFICIENT — Cannot proceed to formal dossier

FINDINGS SO FAR:
• Risk 99.0 — highest in the queue; US$204,493.29 claimed (71% of insured value)
• Claimant has 4 claims in 24 months (14.3% claim rate)
• Weight and survey rules triggered

DEFICIENCIES:
1. DOCUMENT RECONCILIATION (CRITICAL): The B/L, commercial invoice, packing list and VGM have not been reconciled line by line. A frequency pattern alone is not grounds to decline a claim.
   → Action: Reconcile declared weight and quantity against the container VGMs.

2. VALUE BENCHMARK (REQUIRED): The invoiced unit price has not been compared with market prices for this glass grade.
   → Action: Benchmark US$58.00/m² against the commodity reference.

3. EVIDENCE INTEGRITY (REQUIRED): The 14 survey photos have not been checked for reuse across other claims.
   → Action: Run the image-reuse check against the full claims archive.

NEXT STEPS: Investigation agent to close these three gaps before re-submission."""
    })
    s("node_exit", {"node": "dossier", "elapsed": 14.0, "evidence_sufficient": False})

    # ===== ITERATION 5: Orchestrator → Investigation =====
    s("node_enter", {"node": "orchestrator", "iteration": 5})
    log("Orchestrator", "--- Iteration 3 | Current phase: investigate ---")
    log("Orchestrator", "Evidence INSUFFICIENT - looping back to investigation")
    log("Orchestrator", "Phase transition: investigate -> investigate")
    s("phase_change", {"phase": "investigate", "loop_count": 3})
    s("node_exit", {"node": "orchestrator", "elapsed": 15.5, "phase": "investigate", "loop_count": 3})

    # ===== ITERATION 6: Investigation — documents, value, images =====
    s("node_enter", {"node": "investigation", "iteration": 6})
    log("Investigation", "Starting investigation sub-agent (addressing evidence gaps)...")
    log("Investigation", "Evidence gaps: document reconciliation, value benchmark, evidence integrity")

    log("tool", "tool:get_claim_details -> Reconciling B/L MCLSIN2604417, invoice OTL-INV-26-0917, packing list and VGM...")
    time.sleep(1.0)
    log("tool", "tool:get_claim_details -> Declared 135,000 kg (B/L, packing list) vs VGM 90,966 kg gross − 13,500 kg tare = 77,466 kg cargo (43% short)")
    log("tool", "tool:get_claim_details -> At 30 kg/m², VGM supports at most ~2,580 m² — invoice claims 4,320 m²")

    log("tool", "tool:compare_to_peers -> Benchmarking invoiced price vs market for low-E IGU 6+12A+6...")
    time.sleep(0.7)
    log("tool", "tool:compare_to_peers -> US$58.00/m² vs benchmark US$28–38/m² → 1.76x")

    log("tool", "tool:get_claim_details -> Checking 14 survey photos against the claims image archive...")
    time.sleep(0.8)
    log("tool", "tool:get_claim_details -> MATCH: survey photo mc3107_2 near-duplicate of image filed on MC-2988 (paid 2026-04-15)")

    log("Investigation", "Sub-agent finished in 7.1s | Tool calls made: 4")
    s("node_exit", {"node": "investigation", "elapsed": 23.0,
                    "findings_preview": "VGM shows 43% less cargo than declared; invoice 1.76x market; a survey photo was reused from paid claim MC-2988. Coverage basis and network still open..."})

    # ===== ITERATION 7: Orchestrator → Dossier =====
    s("node_enter", {"node": "orchestrator", "iteration": 7})
    log("Orchestrator", "--- Iteration 4 | Current phase: investigate ---")
    log("Orchestrator", "Phase transition: investigate -> compile")
    s("phase_change", {"phase": "compile", "loop_count": 4})
    s("node_exit", {"node": "orchestrator", "elapsed": 24.5, "phase": "compile", "loop_count": 4})

    # ===== ITERATION 8: Dossier REJECTS AGAIN =====
    s("node_enter", {"node": "dossier", "iteration": 8})
    log("Dossier", "Starting dossier sub-agent...")
    log("tool", "tool:assess_evidence -> Assessing 'overvalued_phantom_cargo' (7 evidence points)...")
    time.sleep(0.8)
    log("tool", "tool:assess_evidence -> INSUFFICIENT (4 passed, 2 failed)")
    log("tool", "tool:assess_evidence -> Missing: coverage_basis, network_confirmation")
    log("Dossier", "Evidence INSUFFICIENT — missing coverage basis and network confirmation")
    s("dossier_rejected", {
        "message": "Dossier rejected — still INSUFFICIENT. 2 of 6 critical checks failed.",
        "evidence_gaps": """CASE WRITER DENIAL NOTE — Iteration 2
======================================

CLAIM: Breakage on MC-3107 — CNE-012 (Luzon Premier Glass & Glazing Corp.)
ASSESSMENT: INSUFFICIENT — strong physical and document evidence, but a decline must be defensible

EVIDENCE ESTABLISHED (4 of 6 checks passed):
✓ Document reconciliation: VGM 43% below declared weight
✓ Value benchmark: invoice 1.76x market
✓ Evidence integrity: survey photo reused from MC-2988
✓ Frequency: 14.3% claim rate

REMAINING DEFICIENCIES:
1. COVERAGE BASIS (REQUIRED): No clause or legal references cited. Breakage is an insured peril under ICC (A), so a decline must rest on the assured's duties and on fraud — cite ICC cl. 16, Hague-Visby Art. III r.6 and the utmost-good-faith principle.
   → Action: Run search_regulatory_rules(['breakage'], 'duty of assured notice to carrier fraudulent claim').

2. NETWORK CONFIRMATION (REQUIRED): The surveyor was appointed by the assured. Its independence has not been tested.
   → Action: Map directors and registered addresses for the claimant, surveyor and forwarder; pull the surveyor's claim history.

NOTE: Once these are closed, the case is ready for a decline recommendation."""
    })
    s("node_exit", {"node": "dossier", "elapsed": 27.0, "evidence_sufficient": False})

    # ===== ITERATION 9: Orchestrator → Investigation =====
    s("node_enter", {"node": "orchestrator", "iteration": 9})
    log("Orchestrator", "--- Iteration 5 | Current phase: investigate ---")
    log("Orchestrator", "Phase transition: investigate -> investigate")
    s("phase_change", {"phase": "investigate", "loop_count": 5})
    s("node_exit", {"node": "orchestrator", "elapsed": 28.5, "phase": "investigate", "loop_count": 5})

    # ===== ITERATION 10: Investigation — network + surveyor history =====
    s("node_enter", {"node": "investigation", "iteration": 10})
    log("Investigation", "Mapping claimant, surveyor and forwarder relationships...")

    log("tool", "tool:find_connections -> Tracing directors and registered addresses for CNE-012, SVY-004, FWD-002...")
    time.sleep(1.0)
    log("tool", "tool:find_connections -> DIR-001 Ramon T. Villareal is a director of all three; same address: Unit 1204, Paseo Meridian Tower, Makati City")

    log("tool", "tool:get_surveyor_history -> Pulling SVY-004 (Northport Cargo Inspection Services) history, 24 months...")
    time.sleep(0.9)
    log("tool", "tool:get_surveyor_history -> Not on insurer panel; 5 prior paid breakage claims across 3 consignees, US$644,700.50")

    log("tool", "tool:find_ring -> Checking for a claimant–surveyor–forwarder ring around DIR-001...")
    time.sleep(0.6)
    log("tool", "tool:find_ring -> RING CONFIRMED: 6 claims, 3 consignees, US$849,193.79 claimed in 20 months")

    log("Investigation", "Sub-agent finished in 5.9s | Tool calls made: 3")
    s("node_exit", {"node": "investigation", "elapsed": 33.0,
                    "findings_preview": "Claimant, surveyor and forwarder share director DIR-001 and a registered address. SVY-004 surveyed 5 prior paid claims (US$644,700.50). Ring confirmed..."})

    # ===== ITERATION 11: Orchestrator → Dossier (final) =====
    s("node_enter", {"node": "orchestrator", "iteration": 11})
    log("Orchestrator", "--- Iteration 6 | Current phase: investigate ---")
    log("Orchestrator", "Phase transition: investigate -> compile")
    s("phase_change", {"phase": "compile", "loop_count": 6})
    s("node_exit", {"node": "orchestrator", "elapsed": 34.5, "phase": "compile", "loop_count": 6})

    # ===== ITERATION 12: Dossier ACCEPTS =====
    s("node_enter", {"node": "dossier", "iteration": 12})
    log("Dossier", "Starting dossier sub-agent...")
    log("tool", "tool:assess_evidence -> Assessing 'overvalued_phantom_cargo' (10 evidence points)...")
    time.sleep(0.8)
    log("tool", "tool:assess_evidence -> SUFFICIENT (6 passed, 0 failed)")

    log("tool", "tool:search_regulatory_rules -> Searching clauses and rules for breakage / duty of assured / fraud...")
    time.sleep(0.6)
    log("tool", "tool:search_regulatory_rules -> Found 4: ICC-16 (duty of assured), HVR-III-6 (notice to carrier), MIA-17 (utmost good faith), MC-GL-01 (panel surveyor)")

    log("tool", "tool:find_similar_cases -> Looking up precedents for overvalued_phantom_cargo...")
    time.sleep(0.5)
    log("tool", "tool:find_similar_cases -> Found 2 precedents: MC-SIU-2025-0217, MC-SIU-2024-0088")

    log("tool", "tool:estimate_recovery -> Carrier recovery: nil (clean EIR, seals intact, no notice). Payment avoided: US$204,493.29")
    time.sleep(0.5)

    log("tool", "tool:compile_dossier -> Generating marine cargo investigation dossier...")
    time.sleep(1.0)
    log("tool", "tool:compile_dossier -> Dossier generated (8,900 chars)")

    log("Dossier", "Evidence assessed as SUFFICIENT")
    s("dossier_accepted", {"message": "Evidence SUFFICIENT — dossier compiled."})
    s("node_exit", {"node": "dossier", "elapsed": 39.0, "evidence_sufficient": True})

    # ===== Final orchestrator → done =====
    s("node_enter", {"node": "orchestrator", "iteration": 13})
    log("Orchestrator", "Phase transition: compile -> done")
    s("phase_change", {"phase": "done", "loop_count": 7})
    s("node_exit", {"node": "orchestrator", "elapsed": 40.0, "phase": "done", "loop_count": 7})

    dossier_text = demo_dossier_text()
    s("investigation_complete", {
        "iterations": 13,
        "total_time": 40.0,
        "phase": "done",
        "loop_count": 7,
        "evidence_sufficient": True,
        "dossier": dossier_text,
        "findings": {
            "last_investigation": ("Over-valued, part-phantom cargo: MC-3107 (CNE-012), US$204,493.29 claimed; VGM 43% below "
                                   "declared weight; invoice 1.76x market; survey photo reused from MC-2988; surveyor SVY-004 and "
                                   "forwarder FWD-002 share director DIR-001 and address with the claimant. Recommend DECLINE and "
                                   "REFER FOR INVESTIGATION."),
        },
    })
    return dossier_text
