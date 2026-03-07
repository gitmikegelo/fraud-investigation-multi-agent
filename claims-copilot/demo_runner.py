"""
Deterministic Demo Runner
==========================
Replays a fixed investigation scenario over WebSocket with realistic
timing.  No LLM / Bedrock calls are made.

Scenario
--------
1.  Orchestrator routes to Investigation (Phase: investigate)
2.  Investigation scans claims, profiles top 3 entities
3.  Orchestrator routes to Dossier (Phase: compile)
4.  Dossier REJECTS — insufficient evidence (missing temporal pattern)
    ↻ loops back to Investigation
5.  Investigation gathers peer comparisons + referral history
6.  Orchestrator routes to Dossier (Phase: compile)
7.  Dossier REJECTS AGAIN — still insufficient (missing ring density)
    ↻ loops back to Investigation
8.  Investigation performs ring analysis + connection mapping
9.  Orchestrator routes to Dossier (Phase: compile)
10. Dossier ACCEPTS — evidence sufficient → produces final dossier
"""

import asyncio
import time
import os
from datetime import datetime

# ---------------------------------------------------------------------------
# Static dossier content (mirrors the structure of the real dossier output)
# ---------------------------------------------------------------------------

DEMO_FINAL_DOSSIER = r"""# FRAUD INVESTIGATION DOSSIER
**Case Hypothesis**: Coordinated medical billing fraud ring with upcoding pattern
**Date Generated**: {date}
**Status**: Evidence Sufficient - Ready for Action

## EXECUTIVE SUMMARY
This investigation identified a suspected Coordinated medical billing fraud ring with upcoding pattern involving 3 entities with an estimated recovery of $286,959.10.

The scheme exhibits 6 independent evidence points with statistical significance exceeding 2 standard deviations from peer norms. Pattern analysis indicates coordinated behavior inconsistent with legitimate billing practices.

**Recommended Action**: Immediate audit and potential referral to OIG.

## ENTITIES INVOLVED
| # | Entity | Type | Anomaly Score | Total Billed |
|---|--------|------|---------------|--------------|
| 1 | P-6610 | Provider – Cardiology (Southeast) | 3.70 | $485,000.00 |
| 2 | P-6640 | Provider – Cardiology (Southeast) | 2.90 | $285,000.00 |
| 3 | P-6620 | Provider – Internal Medicine (Southeast) | 2.50 | $125,000.00 |

## EVIDENCE SUMMARY
| # | Evidence Point | Detail |
|---|---------------|--------|
| 1 | Ring detected | 5 entities in fraud ring |
| 2 | High billing volume | Total billed $895,000.00 |
| 3 | Network density | 18 edges connecting ring members |
| 4 | Multiple high-anomaly providers | P-6610 (3.70), P-6640 (2.90), P-6620 (2.50) |
| 5 | Temporal pattern | Referral concentration shift >50% in last 10 months |
| 6 | Peer deviation | avg_billed_per_claim z-score 3.2 for P-6610 |

## STATISTICAL ANALYSIS
| Metric | Entity Value | Peer Average | Z-Score | Significance |
|--------|-------------|-------------|---------|-------------|
| avg_billed_per_claim (P-6610) | $4,250.00 | $1,328.00 | 3.20 | ★★★ |
| claims_per_month (P-6640) | 4.25 | 2.18 | 2.20 | ★★ |
| unique_patients (P-6620) | 98 | 67 | 1.80 | ★★ |
| 99215_rate (P-6610) | 38% | 12% | 3.10 | ★★★ |

## NETWORK ANALYSIS
- **Connected Entities**: 5
- **Connection Density**: 18.00
- **Ring Indicators**: Yes
- **High-Anomaly Connected Entities**:
  - P-6610 (Cardiology, Southeast) — anomaly 3.70
  - P-6640 (Cardiology, Southeast) — anomaly 2.90
  - P-6620 (Internal Medicine, Southeast) — anomaly 2.50

## BILLING RULE VIOLATIONS
### CMS-EM-002: E&M Level 5 Documentation Requirements
**Summary**: 99215 requires high MDM complexity or 40-54 minutes documented.

**Red Flags**:
- 99215 rate >15% of E&M
- Patient population doesn't support high complexity
- Missing documentation elements

### CMS-EM-001: E&M Level 4 Documentation Requirements
**Summary**: 99214 requires moderate MDM or 30-39 minutes documented time.

**Red Flags**:
- 99214 rate >50% of E&M
- Documentation lacks MDM support
- Time not documented when billed by time

### DOCTOR_SHOPPING: Doctor Shopping Pattern
**Red Flags**:
- Patient visiting 4+ providers for similar services
- High concentration of pain management codes
- Geographic spread inconsistent with residence

### UPCODING_RING: Upcoding Ring Pattern
**Red Flags**:
- Primary provider CPT concentration >2 SD above peers
- Referral concentration shift >50% in recent months
- Shared patient population between providers

### OIG-UPCODING-001: Upcoding - General Definition
**Summary**: Upcoding is billing for more expensive services than provided.

**Red Flags**:
- E&M distribution skewed toward 99214/99215
- Procedure mix inconsistent with patient acuity
- Documentation doesn't support billed level

## PRECEDENT CASES
| Case ID | Scheme | Recovery | Outcome | Year |
|---------|--------|----------|---------|------|
| OIG-2024-0157 | Upcoding Ring – Orthopedic Surgery (5 surgeons, CPT 27447 at 85% vs peer 21%) | $3,400,000 | Settlement + exclusion | 2024 |
| DOJ-2023-0089 | Kickback Referral Scheme – Cardiology (closed referral loop, 82% from 2 sources) | $2,100,000 | Criminal conviction | 2023 |
| CMS-2025-0234 | Upcoding – Pain Management (facet injections 4.2 SD above peers) | $890,000 | Repayment + probation | 2025 |

## RECOVERY ESTIMATE
| Item | Amount |
|------|--------|
| Total Flagged Claims | 3 |
| Total Billed | $895,000.00 |
| Gross Recoverable | $107,400.00 |
| Collectability Score | 73% |
| **Net Expected Recovery** | **$78,402.00** |

### Breakdown by CPT Code
| CPT Code | Claims | Total Billed | Est. Recovery |
|----------|--------|--------------|---------------|
| 93458 | 1 | $485,000 | $58,200 |
| 93306 | 1 | $285,000 | $34,200 |
| 99214 | 1 | $125,000 | $15,000 |

## RECOMMENDED ACTIONS
1. **Immediate**: Initiate comprehensive audit of all flagged claims
2. **Urgent**: Interview entity representatives for documentation
3. **Priority**: Refer to OIG for potential exclusion proceedings
4. **Follow-up**: Monitor any pattern changes during investigation
5. **Recovery**: Pursue recoupment of overpayments

---
*This dossier was generated by the Claims Investigation Copilot AI system.*
"""


# ---------------------------------------------------------------------------
# Helper — send typed events over WebSocket (same signature as api.py)
# ---------------------------------------------------------------------------

def _send_factory(ws, loop, log_file=None):
    """Return a blocking-safe send() that pushes an event to the WS and writes to log file."""
    def send(event_type: str, data: dict):
        payload = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            **data,
        }
        asyncio.run_coroutine_threadsafe(ws.send_json(payload), loop)
        
        # Write log events to file
        if log_file and event_type == "log":
            try:
                agent = data.get("agent", "")
                message = data.get("message", "")
                log_file.write(f"{agent}\n{message}\n")
                log_file.flush()
            except Exception:
                pass
        
        time.sleep(0.05)          # let the event loop flush
    return send


def _log_send(send_fn, agent: str, message: str):
    """Emit a single log event over WebSocket."""
    send_fn("log", {"agent": agent, "message": message})


# ---------------------------------------------------------------------------
# Scripted event sequence
# ---------------------------------------------------------------------------

def run_demo_investigation_sync(ws, loop):
    """
    Emit the full demo investigation over WebSocket.
    Called from a thread — mirrors _run_investigation_sync in api.py.
    """
    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_file_path = os.path.join(logs_dir, f"investigation_demo_{timestamp}.txt")
    log_file = open(log_file_path, "w", encoding="utf-8")
    print(f"[DEMO] Logging to: logs/investigation_demo_{timestamp}.txt")
    
    try:
        send = _send_factory(ws, loop, log_file)
        graph_start = time.time()

        initial_query = (
            "Investigate the claims data for potential fraud. Start by scanning for "
            "high-anomaly providers, then profile the top suspicious entities, analyze "
            "their connections, and compile a complete dossier if evidence is sufficient."
        )

        send("status", {"message": "Creating investigation graph..."})
        time.sleep(0.3)
        send("graph_start", {"query": initial_query})
        time.sleep(0.15)

        # =====================================================================
        # Iteration 1 — Initial scan
        # =====================================================================
        _iteration_1(send, graph_start)

        # =====================================================================
        # Iteration 2 — Deeper investigation after first rejection
        # =====================================================================
        _iteration_2(send, graph_start)

        # =====================================================================
        # Iteration 3 — Ring analysis after second rejection
        # =====================================================================
        _iteration_3(send, graph_start)

        # =====================================================================
        # Final result
        # =====================================================================
        total_time = time.time() - graph_start

        dossier_text = DEMO_FINAL_DOSSIER.format(
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

        send("investigation_complete", {
            "iterations": 9,
            "total_time": round(total_time, 1),
            "phase": "done",
            "loop_count": 5,
            "evidence_sufficient": True,
            "dossier": dossier_text,
            "findings": {
                "last_investigation": (
                    "Fraud Ring Analysis:\n"
                    "- Cardiology network ring detected (5 providers)\n"
                    "- Ring composition: P-6610, P-6640, P-6620, P-6630, P-6650\n"
                    "- Total billed: $895,000 across network\n"
                    "- Highest connection density involves P-6610, P-6640, P-6620\n"
                    "- Temporal pattern confirmed: referral shift >50% in 10 months\n"
                    "- Peer deviation: avg_billed_per_claim z-score 3.2 for P-6610\n"
                    "- Ring density 18.00 with gradual referral concentration"
                ),
            },
        })
    
    finally:
        # Close log file
        if log_file:
            try:
                log_file.close()
                print(f"[DEMO] Logs saved to: {log_file_path}")
            except Exception:
                pass


# -------------------------------------------------------------------------
# Iteration 1
# -------------------------------------------------------------------------

def _iteration_1(send, graph_start):
    """Orchestrator → Investigation (scan + profile) → Orchestrator → Dossier → REJECTED."""

    elapsed = lambda: round(time.time() - graph_start, 1)

    # -- Orchestrator 1 --
    send("node_enter", {"node": "orchestrator", "iteration": 1})
    time.sleep(0.2)
    _log_send(send, "Orchestrator", "--- Iteration 1 | Current phase: start ---")
    _log_send(send, "Orchestrator", "Calling LLM for routing decision...")
    time.sleep(0.9)

    _log_send(send, "Orchestrator", ">>> LLM Call #1 (messages interface, 1 message groups)")
    time.sleep(0.1)
    _log_send(send, "Orchestrator", "Group[0]: 2 messages")
    _log_send(send, "Orchestrator", '[0] SystemMessage: 760 chars | "You are Lead Investigator for healthcare fraud detection. Coordinate investigation by delegating to: - Investigation Agent: Scans claims, profi…')
    _log_send(send, "Orchestrator", '[1] HumanMessage: 221 chars | "Investigate the claims data for potential fraud. Start by scanning for high-anomaly providers, then profile the top suspicious entities, analyze …')
    _log_send(send, "Orchestrator", ">>> Total input chars: 981")
    time.sleep(3.25)
    _log_send(send, "Orchestrator", "LLM responded in 8.3s")
    _log_send(send, "Orchestrator", "Phase transition: start -> investigate")

    send("phase_change", {"phase": "investigate", "loop_count": 1})
    send("node_exit", {
        "node": "orchestrator", "elapsed": elapsed(),
        "phase": "investigate", "loop_count": 1,
    })
    time.sleep(0.15)

    # -- Investigation 1 --
    send("node_enter", {"node": "investigation", "iteration": 2})
    time.sleep(0.15)
    _log_send(send, "Investigation", "Starting investigation sub-agent (7 tools available)...")
    _log_send(send, "Investigation", "Invoking LLM + tool loop (this may take a while)...")
    _log_send(send, "Investigation", "Initial message to agent: 980 chars")
    _log_send(send, "Investigation", 'Message preview: I\'ll coordinate the investigation into potential healthcare fraud by working with our Investigation Agent to scan claims data and identify suspicious entities. IN…')
    time.sleep(0.25)

    # LLM Call 1 — scan decision
    _log_send(send, "Investigation", "=== LLM INPUT DEBUG (1 messages) ===")
    _log_send(send, "Investigation", '[0] HumanMessage: 980 chars | "I\'ll coordinate the investigation into potential healthcare fraud by working with our Investigation Agent to scan claims data and identify suspicio…')
    _log_send(send, "Investigation", "=== TOTAL INPUT: 980 chars ===")
    _log_send(send, "Investigation", ">>> LLM Call #1 (messages interface, 1 message groups)")
    _log_send(send, "Investigation", "Group[0]: 2 messages")
    _log_send(send, "Investigation", '[0] SystemMessage: 906 chars | "You are Detective Agent for healthcare fraud. Use your tools efficiently to find billing anomalies. Be concise. ## Tools (use 3-4 max per inve…')
    _log_send(send, "Investigation", '[1] HumanMessage: 980 chars | "I\'ll coordinate the investigation into potential healthcare fraud by working with our Investigation Agent to scan claims data and identify suspic…')
    _log_send(send, "Investigation", ">>> Total input chars: 1886")
    time.sleep(6.5)

    # scan_new_claims tool
    _log_send(send, "tool", "Scanning claims (last 90 days, anomaly > 0.5)...")
    time.sleep(2.5)
    _log_send(send, "tool", "Found 8 high-anomaly entities (0.0s)")

    # LLM Call 2 — profile decision
    _log_send(send, "Investigation", ">>> LLM Call #2 (messages interface, 1 message groups)")
    _log_send(send, "Investigation", "Group[0]: 4 messages")
    _log_send(send, "Investigation", '[0] SystemMessage: 906 chars | "You are Detective Agent for healthcare fraud…')
    _log_send(send, "Investigation", '[2] AIMessage: 263 chars | "[{\'type\': \'text\', \'text\': \'I\'ll help you investigate potential healthcare fraud…')
    _log_send(send, "Investigation", "-> tool_call: {'name': 'scan_new_claims', 'args': {'since_days': 90}}")
    _log_send(send, "Investigation", '[3] ToolMessage: 808 chars | "[{\\"entity_id\\": \\"P-6610\\", \\"anomaly_score\\": 0.8, \\"total_billed\\": 485201.87}, {\\"entity_id\\": \\"P-6640\\"…')
    _log_send(send, "Investigation", ">>> Total input chars: 3073")
    time.sleep(4.5)

    # profile_entity calls
    _log_send(send, "tool", "Profiling P-6610...")
    time.sleep(1.0)
    _log_send(send, "tool", "Profiling P-6640...")
    time.sleep(1.0)
    _log_send(send, "tool", "Profiling P-6620...")
    time.sleep(1.0)

    # LLM Call 3 — summary
    _log_send(send, "Investigation", ">>> LLM Call #3 (messages interface, 1 message groups)")
    _log_send(send, "Investigation", "Group[0]: 8 messages")
    _log_send(send, "Investigation", '[5] ToolMessage: 904 chars | "{\\"provider_id\\": \\"P-6610\\", \\"specialty\\": \\"Cardiology\\"…')
    _log_send(send, "Investigation", '[6] ToolMessage: 1095 chars | "{\\"provider_id\\": \\"P-6640\\", \\"specialty\\": \\"Cardiology\\"…')
    _log_send(send, "Investigation", '[7] ToolMessage: 1135 chars | "{\\"provider_id\\": \\"P-6620\\", \\"specialty\\": \\"Internal Medicine\\"…')
    _log_send(send, "Investigation", ">>> Total input chars: 7065")
    time.sleep(4.5)

    _log_send(send, "Investigation", "Sub-agent finished in 28.4s | Tool calls made: 2")
    _log_send(send, "Investigation", "Summary preview: Initial Scan Findings — 8 high-anomaly entities detected. Top 3: P-6610 (Cardiology, anomaly 0.80, $485K), P-6640 (Cardiology, anomaly 0.68, $285K), P-6620 (IM, anomaly 0.62, $125K)…")

    send("node_exit", {
        "node": "investigation", "elapsed": elapsed(),
        "findings_preview": "Initial Scan: 8 high-anomaly entities. Top 3: P-6610 (0.80), P-6640 (0.68), P-6620 (0.62)",
    })
    time.sleep(0.15)

    # -- Orchestrator 2 → compile --
    send("node_enter", {"node": "orchestrator", "iteration": 3})
    time.sleep(0.15)
    _log_send(send, "Orchestrator", "--- Iteration 2 | Current phase: investigate ---")
    _log_send(send, "Orchestrator", "Calling LLM for routing decision...")
    time.sleep(1.75)
    _log_send(send, "Orchestrator", "LLM responded in 3.5s")
    _log_send(send, "Orchestrator", "Phase transition: investigate -> compile")

    send("phase_change", {"phase": "compile", "loop_count": 2})
    send("node_exit", {
        "node": "orchestrator", "elapsed": elapsed(),
        "phase": "compile", "loop_count": 2,
    })
    time.sleep(0.15)

    # -- Dossier 1 → REJECTED --
    send("node_enter", {"node": "dossier", "iteration": 4})
    time.sleep(0.15)
    _log_send(send, "Dossier", "Starting dossier sub-agent (5 tools available)...")
    _log_send(send, "Dossier", "Findings payload size: 412 chars")
    _log_send(send, "Dossier", "Invoking LLM + tool loop (evidence assessment & compilation)...")
    _log_send(send, "Dossier", "Initial message to agent: 480 chars")
    _log_send(send, "Dossier", 'Message preview: Assess the following investigation findings and compile a dossier: {\'last_investigation\': \'Initial Scan Findings — 8 high-anomaly entities detected. Top 3: P-6610…')
    time.sleep(0.5)

    _log_send(send, "Dossier", ">>> LLM Call #1 (messages interface, 1 message groups)")
    _log_send(send, "Dossier", "Group[0]: 2 messages")
    _log_send(send, "Dossier", '[0] SystemMessage: 1089 chars | "You are Case Writer Agent for fraud investigation…')
    _log_send(send, "Dossier", '[1] HumanMessage: 480 chars | "Assess the following investigation findings…')
    _log_send(send, "Dossier", ">>> Total input chars: 1569")
    time.sleep(2.75)

    _log_send(send, "tool", 'Assessing evidence for "Coordinated medical billing fraud ring" (3 points)...')
    time.sleep(0.75)
    _log_send(send, "tool", "Result: INSUFFICIENT (2 passed, 2 failed)")
    time.sleep(0.5)

    _log_send(send, "Dossier", ">>> LLM Call #2 (messages interface, 1 message groups)")
    _log_send(send, "Dossier", "Group[0]: 4 messages")
    _log_send(send, "Dossier", ">>> Total input chars: 2480")
    time.sleep(2.0)

    _log_send(send, "Dossier", "Sub-agent finished in 14.2s | Tool calls made: 1")
    _log_send(send, "Dossier", "Evidence assessed as INSUFFICIENT - looping back to investigation")
    _log_send(send, "Dossier", "Setting next phase -> investigate (evidence gaps forwarded to investigator)")

    send("node_exit", {
        "node": "dossier", "elapsed": elapsed(),
        "evidence_sufficient": False,
    })
    send("dossier_rejected", {
        "message": "Dossier rejected the investigation — evidence is INSUFFICIENT. Looping back to investigation.",
        "evidence_gaps": """## INSUFFICIENT EVIDENCE FOR PROSECUTION

The current investigation has identified high-anomaly providers but lacks critical corroborating evidence required for a defensible fraud case:

**Missing Evidence:**
1. **Temporal Pattern Analysis**: No referral history or time-series data showing coordinated behavior evolution. Need to demonstrate billing pattern shifts over time that indicate collusion rather than coincidental similarity.

2. **Network Structure**: While multiple suspicious entities identified, no formal ring analysis or connection mapping performed. Must establish network density, shared patients, and coordination indicators to prove organized fraud vs. independent bad actors.

**Recommendation**: Investigation agent should use tools like get_referral_history() and find_ring() to gather structural evidence before resubmitting.""",
    })
    time.sleep(0.25)


# -------------------------------------------------------------------------
# Iteration 2 — peer comparison + referral history
# -------------------------------------------------------------------------

def _iteration_2(send, graph_start):
    """Orchestrator → Investigation (peers + referrals) → Orchestrator → Dossier → REJECTED."""

    elapsed = lambda: round(time.time() - graph_start, 1)

    # -- Orchestrator 3 → investigate --
    send("node_enter", {"node": "orchestrator", "iteration": 5})
    time.sleep(0.15)
    _log_send(send, "Orchestrator", "--- Iteration 3 | Current phase: compile ---")
    _log_send(send, "Orchestrator", "Evidence INSUFFICIENT - looping back to investigation")
    _log_send(send, "Orchestrator", "Calling LLM for routing decision...")
    time.sleep(1.5)
    _log_send(send, "Orchestrator", "LLM responded in 3.0s")
    _log_send(send, "Orchestrator", "Phase transition: compile -> investigate")

    send("phase_change", {"phase": "investigate", "loop_count": 3})
    send("node_exit", {
        "node": "orchestrator", "elapsed": elapsed(),
        "phase": "investigate", "loop_count": 3,
    })
    time.sleep(0.15)

    # -- Investigation 2 — peer comparison + referral history --
    send("node_enter", {"node": "investigation", "iteration": 6})
    time.sleep(0.15)
    _log_send(send, "Investigation", "Starting investigation sub-agent (7 tools available)...")
    _log_send(send, "Investigation", "Invoking LLM + tool loop (this may take a while)...")
    _log_send(send, "Investigation", "Initial message to agent: 1420 chars")
    _log_send(send, "Investigation", "Message preview: ## Prior Investigation Findings (do NOT repeat this work):\\nInitial Scan…\\n\\n## EVIDENCE GAPS (the dossier agent rejected the first investigation):\\nMissing: (1) Temporal billing pattern…")
    time.sleep(0.25)

    _log_send(send, "Investigation", "=== LLM INPUT DEBUG (1 messages) ===")
    _log_send(send, "Investigation", "[0] HumanMessage: 1420 chars")
    _log_send(send, "Investigation", "=== TOTAL INPUT: 1420 chars ===")
    _log_send(send, "Investigation", ">>> LLM Call #1 (messages interface, 1 message groups)")
    _log_send(send, "Investigation", "Group[0]: 2 messages")
    _log_send(send, "Investigation", '[0] SystemMessage: 906 chars | "You are Detective Agent for healthcare fraud…')
    _log_send(send, "Investigation", "[1] HumanMessage: 1420 chars")
    _log_send(send, "Investigation", ">>> Total input chars: 2326")
    time.sleep(3.0)

    # compare_to_peers
    _log_send(send, "tool", "Comparing P-6610 to peers on avg_billed_per_claim...")
    time.sleep(1.0)
    _log_send(send, "tool", "P-6610: $4,250 vs peer avg $1,328 (z-score 3.2)")
    time.sleep(0.25)
    _log_send(send, "tool", "Comparing P-6640 to peers on avg_billed_per_claim...")
    time.sleep(0.9)
    _log_send(send, "tool", "P-6640: $2,850 vs peer avg $1,412 (z-score 2.1)")
    time.sleep(0.25)

    # LLM call 2
    _log_send(send, "Investigation", ">>> LLM Call #2 (messages interface, 1 message groups)")
    _log_send(send, "Investigation", "Group[0]: 6 messages")
    _log_send(send, "Investigation", ">>> Total input chars: 4890")
    time.sleep(2.5)

    # get_referral_history
    _log_send(send, "tool", "Fetching referral history for P-6610 (last 12 months)...")
    time.sleep(1.25)
    _log_send(send, "tool", "Found 32 referrals; top referral sources: P-6620 (38% of inbound), P-6630 (34% of inbound)")
    time.sleep(0.25)
    _log_send(send, "tool", "Fetching referral history for P-6640 (last 12 months)...")
    time.sleep(1.1)
    _log_send(send, "tool", "Found 26 referrals; top referral source: P-6610 (42% of inbound)")
    time.sleep(0.25)

    # LLM call 3
    _log_send(send, "Investigation", ">>> LLM Call #3 (messages interface, 1 message groups)")
    _log_send(send, "Investigation", "Group[0]: 10 messages")
    _log_send(send, "Investigation", ">>> Total input chars: 8120")
    time.sleep(2.75)

    _log_send(send, "Investigation", "Sub-agent finished in 32.1s | Tool calls made: 4")
    _log_send(send, "Investigation", "Summary preview: Peer Comparison & Referral Analysis — P-6610 avg_billed z-score 3.2, P-6640 avg_billed z-score 2.1. Referral loop detected: P-6620→P-6610 (38%), P-6630→P-6610 (34%), P-6610→P-6640 (42%). Temporal sh…")

    send("node_exit", {
        "node": "investigation", "elapsed": elapsed(),
        "findings_preview": "Peer comparison: P-6610 z-score 3.2, P-6640 z-score 2.1. Referral network: P-6620→P-6610 (38%), P-6630→P-6610 (34%), P-6610→P-6640 (42%).",
    })
    time.sleep(0.15)

    # -- Orchestrator 4 → compile --
    send("node_enter", {"node": "orchestrator", "iteration": 7})
    time.sleep(0.15)
    _log_send(send, "Orchestrator", "--- Iteration 4 | Current phase: investigate ---")
    _log_send(send, "Orchestrator", "Calling LLM for routing decision...")
    time.sleep(1.6)
    _log_send(send, "Orchestrator", "LLM responded in 3.2s")
    _log_send(send, "Orchestrator", "Phase transition: investigate -> compile")

    send("phase_change", {"phase": "compile", "loop_count": 4})
    send("node_exit", {
        "node": "orchestrator", "elapsed": elapsed(),
        "phase": "compile", "loop_count": 4,
    })
    time.sleep(0.15)

    # -- Dossier 2 → REJECTED --
    send("node_enter", {"node": "dossier", "iteration": 8})
    time.sleep(0.15)
    _log_send(send, "Dossier", "Starting dossier sub-agent (5 tools available)...")
    _log_send(send, "Dossier", "Findings payload size: 892 chars")
    _log_send(send, "Dossier", "Invoking LLM + tool loop (evidence assessment & compilation)...")
    _log_send(send, "Dossier", "Initial message to agent: 960 chars")
    _log_send(send, "Dossier", 'Message preview: Assess the following investigation findings and compile a dossier: {\'last_investigation\': \'Peer Comparison & Referral Analysis — P-6610 avg_billed z-score 3.2…')
    time.sleep(0.5)

    _log_send(send, "Dossier", ">>> LLM Call #1 (messages interface, 1 message groups)")
    _log_send(send, "Dossier", "Group[0]: 2 messages")
    _log_send(send, "Dossier", '[0] SystemMessage: 1089 chars | "You are Case Writer Agent for fraud investigation…')
    _log_send(send, "Dossier", "[1] HumanMessage: 960 chars")
    _log_send(send, "Dossier", ">>> Total input chars: 2049")
    time.sleep(2.5)

    _log_send(send, "tool", 'Assessing evidence for "Coordinated medical billing fraud ring with upcoding pattern" (5 points)...')
    time.sleep(0.75)
    _log_send(send, "tool", "Result: INSUFFICIENT (3 passed, 1 failed)")
    time.sleep(0.5)

    _log_send(send, "Dossier", ">>> LLM Call #2 (messages interface, 1 message groups)")
    _log_send(send, "Dossier", "Group[0]: 4 messages")
    _log_send(send, "Dossier", ">>> Total input chars: 3200")
    time.sleep(2.25)

    _log_send(send, "Dossier", "Sub-agent finished in 15.8s | Tool calls made: 1")
    _log_send(send, "Dossier", "Evidence assessed as INSUFFICIENT - looping back to investigation")
    _log_send(send, "Dossier", "Setting next phase -> investigate (evidence gaps forwarded to investigator)")

    send("node_exit", {
        "node": "dossier", "elapsed": elapsed(),
        "evidence_sufficient": False,
    })
    send("dossier_rejected", {
        "message": "Dossier rejected the investigation — evidence is INSUFFICIENT. Looping back to investigation.",
        "evidence_gaps": """## INSUFFICIENT EVIDENCE - CONTINUED GAPS

While the investigation has added temporal referral analysis, critical structural evidence remains missing:

**Still Missing:**
1. **Network Density Metrics**: Referral patterns show suspicious temporal clustering, but we lack quantitative ring analysis. Need explicit connection density measurements, shared patient counts, and bidirectional referral evidence to demonstrate coordinated fraud ring structure.

2. **Ring Topology**: No formal ring detection performed using find_ring() or find_connections(). Cannot definitively prove coordinated conspiracy vs. independent upcoding without measuring network cohesion and entity interconnectedness.

**Current Status**: Temporal evidence is suggestive but circumstantial. Network structure analysis is mandatory to meet prosecution standards for organized fraud.

**Recommendation**: Run find_ring() to map network topology and calculate connection density before resubmitting.""",
    })
    time.sleep(0.25)


# -------------------------------------------------------------------------
# Iteration 3 — ring analysis → ACCEPTED
# -------------------------------------------------------------------------

def _iteration_3(send, graph_start):
    """Orchestrator → Investigation (ring + connections) → Orchestrator → Dossier → ACCEPTED."""

    elapsed = lambda: round(time.time() - graph_start, 1)

    # -- Orchestrator 5 → investigate --
    send("node_enter", {"node": "orchestrator", "iteration": 9})
    time.sleep(0.15)
    _log_send(send, "Orchestrator", "--- Iteration 5 | Current phase: compile ---")
    _log_send(send, "Orchestrator", "Evidence INSUFFICIENT - looping back to investigation")
    _log_send(send, "Orchestrator", "Calling LLM for routing decision...")
    time.sleep(1.4)
    _log_send(send, "Orchestrator", "LLM responded in 2.8s")
    _log_send(send, "Orchestrator", "Phase transition: compile -> investigate")

    send("phase_change", {"phase": "investigate", "loop_count": 5})
    send("node_exit", {
        "node": "orchestrator", "elapsed": elapsed(),
        "phase": "investigate", "loop_count": 5,
    })
    time.sleep(0.15)

    # -- Investigation 3 — ring analysis + connections --
    send("node_enter", {"node": "investigation", "iteration": 10})
    time.sleep(0.15)
    _log_send(send, "Investigation", "Starting investigation sub-agent (7 tools available)...")
    _log_send(send, "Investigation", "Invoking LLM + tool loop (this may take a while)...")
    _log_send(send, "Investigation", "Initial message to agent: 1680 chars")
    _log_send(send, "Investigation", "Message preview: ## Prior Investigation Findings (do NOT repeat this work):\\nPeer Comparison & Referral Analysis…\\n\\n## EVIDENCE GAPS:\\nMissing: Ring/network density evidence…")
    time.sleep(0.25)

    _log_send(send, "Investigation", "=== LLM INPUT DEBUG (1 messages) ===")
    _log_send(send, "Investigation", "[0] HumanMessage: 1680 chars")
    _log_send(send, "Investigation", "=== TOTAL INPUT: 1680 chars ===")
    _log_send(send, "Investigation", ">>> LLM Call #1 (messages interface, 1 message groups)")
    _log_send(send, "Investigation", "Group[0]: 2 messages")
    _log_send(send, "Investigation", '[0] SystemMessage: 906 chars | "You are Detective Agent for healthcare fraud…')
    _log_send(send, "Investigation", "[1] HumanMessage: 1680 chars")
    _log_send(send, "Investigation", ">>> Total input chars: 2586")
    time.sleep(3.5)

    # find_ring
    _log_send(send, "tool", "Searching for fraud rings (anomaly >= 0.5, min entities=3)...")
    time.sleep(1.5)
    _log_send(send, "tool", "!!! OUTPUT TRUNCATED from 4550 to 2000 chars")
    time.sleep(0.25)

    # LLM call 2
    _log_send(send, "Investigation", ">>> LLM Call #2 (messages interface, 1 message groups)")
    _log_send(send, "Investigation", "Group[0]: 4 messages")
    _log_send(send, "Investigation", ">>> Total input chars: 5200")
    time.sleep(2.75)

    # find_connections
    _log_send(send, "tool", "Finding connections for P-6610 (depth=2)...")
    time.sleep(1.1)
    _log_send(send, "tool", "Found 5 connected entities (density 18.0)")
    time.sleep(0.25)

    # LLM call 3
    _log_send(send, "Investigation", ">>> LLM Call #3 (messages interface, 1 message groups)")
    _log_send(send, "Investigation", "Group[0]: 6 messages")
    _log_send(send, "Investigation", ">>> Total input chars: 8450")
    time.sleep(2.5)

    _log_send(send, "Investigation", "Sub-agent finished in 37.0s | Tool calls made: 3")
    _log_send(send, "Investigation", "Summary preview: Fraud Ring Analysis: - Cardiology kickback network detected - Ring: 5 providers (P-6610, P-6640, P-6620, P-6630, P-6650), $895K total billed - Connection density 18 edges with gradual referral shift…")

    send("node_exit", {
        "node": "investigation", "elapsed": elapsed(),
        "findings_preview": "Fraud Ring Analysis: 5 entities, $895K billed, density 18.0. P-6610, P-6640, P-6620 confirmed in ring.",
    })
    time.sleep(0.15)

    # -- Orchestrator 6 → compile --
    send("node_enter", {"node": "orchestrator", "iteration": 11})
    time.sleep(0.15)
    _log_send(send, "Orchestrator", "--- Iteration 6 | Current phase: investigate ---")
    _log_send(send, "Orchestrator", "Calling LLM for routing decision...")
    time.sleep(1.85)
    _log_send(send, "Orchestrator", "LLM responded in 3.7s")
    _log_send(send, "Orchestrator", "Phase transition: investigate -> compile")

    send("phase_change", {"phase": "compile", "loop_count": 6})
    send("node_exit", {
        "node": "orchestrator", "elapsed": elapsed(),
        "phase": "compile", "loop_count": 6,
    })
    time.sleep(0.15)

    # -- Dossier 3 → ACCEPTED --
    send("node_enter", {"node": "dossier", "iteration": 12})
    time.sleep(0.15)
    _log_send(send, "Dossier", "Starting dossier sub-agent (5 tools available)...")
    _log_send(send, "Dossier", "Findings payload size: 1520 chars")
    _log_send(send, "Dossier", "Invoking LLM + tool loop (evidence assessment & compilation)...")
    _log_send(send, "Dossier", "Initial message to agent: 1588 chars")
    _log_send(send, "Dossier", 'Message preview: Assess the following investigation findings and compile a dossier: {\'last_investigation\': \'Fraud Ring Analysis:\\n- Three significant rings detected…')
    time.sleep(0.5)

    # LLM call 1 — assess
    _log_send(send, "Dossier", ">>> LLM Call #1 (messages interface, 1 message groups)")
    _log_send(send, "Dossier", "Group[0]: 2 messages")
    _log_send(send, "Dossier", '[0] SystemMessage: 1089 chars | "You are Case Writer Agent for fraud investigation…')
    _log_send(send, "Dossier", "[1] HumanMessage: 1588 chars")
    _log_send(send, "Dossier", ">>> Total input chars: 2677")
    time.sleep(3.0)

    _log_send(send, "tool", 'Assessing evidence for "Coordinated medical billing fraud ring with upcoding pattern" (6 points)...')
    time.sleep(0.75)
    _log_send(send, "tool", "Result: SUFFICIENT (4 passed, 0 failed)")
    time.sleep(0.25)

    # LLM call 2 — billing rules
    _log_send(send, "Dossier", ">>> LLM Call #2 (messages interface, 1 message groups)")
    _log_send(send, "Dossier", "Group[0]: 4 messages")
    _log_send(send, "Dossier", ">>> Total input chars: 3820")
    time.sleep(2.0)

    _log_send(send, "tool", "Searching rules for CPT codes: ['99215', '99214', '99213']...")
    time.sleep(0.75)
    _log_send(send, "tool", "Found 5 relevant rules")
    time.sleep(0.15)
    _log_send(send, "tool", "Truncated list from 3 to 3 items")

    # LLM call 3 — similar cases
    _log_send(send, "Dossier", ">>> LLM Call #3 (messages interface, 1 message groups)")
    _log_send(send, "Dossier", "Group[0]: 6 messages")
    _log_send(send, "Dossier", ">>> Total input chars: 5675")
    time.sleep(1.75)

    _log_send(send, "tool", 'Looking up precedent cases for "upcoding_ring"...')
    time.sleep(0.75)

    # LLM call 4 — recovery estimate
    _log_send(send, "Dossier", ">>> LLM Call #4 (messages interface, 1 message groups)")
    _log_send(send, "Dossier", "Group[0]: 8 messages")
    _log_send(send, "Dossier", ">>> Total input chars: 6942")
    time.sleep(2.0)

    _log_send(send, "tool", "Estimating recovery for 3 flagged claims...")
    time.sleep(1.0)

    # LLM call 5 — compile dossier
    _log_send(send, "Dossier", ">>> LLM Call #5 (messages interface, 1 message groups)")
    _log_send(send, "Dossier", "Group[0]: 10 messages")
    _log_send(send, "Dossier", ">>> Total input chars: 8187")
    time.sleep(2.5)

    _log_send(send, "tool", "Generating final Markdown dossier...")
    time.sleep(1.25)
    _log_send(send, "tool", "Self-heal: using cached billing_rules (LLM passed empty)")
    _log_send(send, "tool", "Self-heal: using cached similar_cases (LLM passed empty)")
    _log_send(send, "tool", "Self-heal: using cached recovery_estimate (LLM passed empty)")
    time.sleep(0.25)

    # LLM call 6 — finalize
    _log_send(send, "Dossier", ">>> LLM Call #6 (messages interface, 1 message groups)")
    _log_send(send, "Dossier", "Group[0]: 12 messages")
    _log_send(send, "Dossier", ">>> Total input chars: 15597")
    _log_send(send, "Dossier", "!!! DANGER: 15597 chars likely exceeds context window !!!")
    time.sleep(2.0)

    _log_send(send, "Dossier", "Sub-agent finished in 28.4s | Tool calls made: 5")
    _log_send(send, "Dossier", "Found compile_dossier output: 4563 chars")
    _log_send(send, "Dossier", "Evidence assessed as SUFFICIENT")
    _log_send(send, "Dossier", "Dossier length: 4563 chars")
    _log_send(send, "Dossier", "Setting next phase -> done")

    send("node_exit", {
        "node": "dossier", "elapsed": elapsed(),
        "evidence_sufficient": True,
    })
    send("dossier_accepted", {
        "message": "Dossier accepted the investigation — evidence is SUFFICIENT.",
    })
    time.sleep(0.15)
