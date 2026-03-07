"""
FastAPI Backend with WebSocket for real-time investigation streaming.
"""

import sys
import os
import json
import time
import asyncio
import traceback
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from demo_config import is_demo_mode
from demo_runner import run_demo_investigation_sync

from main import initialize_data, DataContext
from agents.tools_investigation import set_context as set_investigation_context
from agents.tools_dossier import set_context as set_dossier_context
from agents.nodes import clear_agent_caches
from data.graph import find_connections, find_rings, get_ring_edges


# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
data_ctx: Optional[DataContext] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data on startup."""
    global data_ctx
    print("[API] Initializing data context...")
    data_ctx = initialize_data()
    set_investigation_context(data_ctx)
    set_dossier_context(data_ctx)
    print("[API] Data context ready.")
    yield


app = FastAPI(title="Claims Investigation Copilot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers – send typed events over WebSocket
# ---------------------------------------------------------------------------
async def ws_send(ws: WebSocket, event_type: str, data: dict):
    """Send a JSON event over WebSocket."""
    payload = {"type": event_type, "timestamp": datetime.now().isoformat(), **data}
    await ws.send_json(payload)


# ---------------------------------------------------------------------------
# Patched _log that also pushes to the active WebSocket and writes to file
# ---------------------------------------------------------------------------
_active_ws: Optional[WebSocket] = None
_active_loop: Optional[asyncio.AbstractEventLoop] = None
_active_log_file = None
_log_file_path = None

_original_node_log = None
_original_tool_log_inv = None
_original_tool_log_dos = None


def _make_ws_log(agent_label: str, original_fn):
    """Create a patched log function that also sends WS events and writes to log file."""
    def _patched(agent_or_name: str, message: str):
        # Call original
        if original_fn:
            original_fn(agent_or_name, message)
        # Write to log file
        if _active_log_file:
            try:
                _active_log_file.write(f"{agent_or_name}\n{message}\n")
                _active_log_file.flush()
            except Exception:
                pass
        # Send to WS if connected
        if _active_ws and _active_loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    ws_send(_active_ws, "log", {
                        "agent": agent_or_name,
                        "message": message,
                    }),
                    _active_loop,
                )
            except Exception:
                pass
    return _patched


def _patch_loggers(ws: WebSocket, loop: asyncio.AbstractEventLoop):
    """Monkey-patch the _log / _tool_log functions to pipe to WS and file."""
    global _active_ws, _active_loop, _active_log_file, _log_file_path
    global _original_node_log, _original_tool_log_inv, _original_tool_log_dos
    _active_ws = ws
    _active_loop = loop
    
    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    _log_file_path = os.path.join(logs_dir, f"investigation_{timestamp}.txt")
    _active_log_file = open(_log_file_path, "w", encoding="utf-8")
    print(f"[API] Logging to: logs/investigation_{timestamp}.txt")

    import agents.nodes as nodes_mod
    import agents.tools_investigation as tinv
    import agents.tools_dossier as tdos

    if _original_node_log is None:
        _original_node_log = nodes_mod._log
        _original_tool_log_inv = tinv._tool_log
        _original_tool_log_dos = tdos._tool_log

    nodes_mod._log = _make_ws_log("node", _original_node_log)
    tinv._tool_log = _make_ws_log("tool", _original_tool_log_inv)
    tdos._tool_log = _make_ws_log("tool", _original_tool_log_dos)


def _unpatch_loggers():
    global _active_ws, _active_loop, _active_log_file, _log_file_path
    import agents.nodes as nodes_mod
    import agents.tools_investigation as tinv
    import agents.tools_dossier as tdos

    if _original_node_log:
        nodes_mod._log = _original_node_log
        tinv._tool_log = _original_tool_log_inv
        tdos._tool_log = _original_tool_log_dos

    # Close log file
    if _active_log_file:
        try:
            _active_log_file.close()
            print(f"[API] Logs saved to: {_log_file_path}")
        except Exception:
            pass
        _active_log_file = None
        _log_file_path = None

    _active_ws = None
    _active_loop = None


# ---------------------------------------------------------------------------
# Run the LangGraph graph in a thread, streaming events via WS
# ---------------------------------------------------------------------------
def _run_investigation_sync(ws: WebSocket, loop: asyncio.AbstractEventLoop):
    """
    Execute the LangGraph workflow synchronously (called from a thread).
    Sends structured events back to the WS through the event loop.
    """
    from langchain_core.messages import HumanMessage
    from agents.graph import create_investigation_graph

    # Clear cached agents so fresh prompts are loaded
    clear_agent_caches()

    def send(event_type: str, data: dict):
        asyncio.run_coroutine_threadsafe(ws_send(ws, event_type, data), loop)
        # Small sleep so the event loop can flush
        time.sleep(0.05)

    send("status", {"message": "Creating investigation graph..."})

    app_graph = create_investigation_graph()

    initial_query = (
        "Investigate the claims data for potential fraud. Start by scanning for "
        "high-anomaly providers, then profile the top suspicious entities, analyze "
        "their connections, and compile a complete dossier if evidence is sufficient."
    )

    initial_state = {
        "messages": [HumanMessage(content=initial_query)],
        "current_phase": "start",
        "findings": {},
        "dossier": "",
        "evidence_sufficient": False,
        "loop_count": 0,
        "compile_loop_count": 0,
    }

    send("graph_start", {"query": initial_query})

    iterations = 0
    max_iterations = 15
    graph_start = time.time()
    final_state = None

    # Accumulate dossier & findings across all streamed node outputs,
    # because the final streamed state may be the orchestrator which
    # doesn't always carry the dossier text forward.
    best_dossier = ""
    best_findings = {}
    best_evidence_sufficient = False

    for state in app_graph.stream(initial_state):
        iterations += 1
        elapsed = time.time() - graph_start
        final_state = state

        # Grab the node output from this step
        node_output = list(state.values())[0] if state else {}

        # Accumulate best dossier (prefer the longest non-empty one)
        step_dossier = node_output.get("dossier", "")
        if step_dossier and len(step_dossier) > len(best_dossier):
            best_dossier = step_dossier

        # Accumulate findings (merge, keep newest values)
        step_findings = node_output.get("findings", {})
        if step_findings:
            best_findings.update(step_findings)

        # Track evidence sufficiency
        if node_output.get("evidence_sufficient"):
            best_evidence_sufficient = True

        if "orchestrator" in state:
            node_state = state["orchestrator"]
            send("node_enter", {"node": "orchestrator", "iteration": iterations})
            send("phase_change", {
                "phase": node_state.get("current_phase", "unknown"),
                "loop_count": node_state.get("loop_count", 0),
            })
            send("node_exit", {
                "node": "orchestrator",
                "elapsed": round(elapsed, 1),
                "phase": node_state.get("current_phase", "unknown"),
                "loop_count": node_state.get("loop_count", 0),
            })
        elif "investigation" in state:
            node_state = state["investigation"]
            send("node_enter", {"node": "investigation", "iteration": iterations})
            findings = node_state.get("findings", {})
            summary = findings.get("last_investigation", "")[:500]
            send("node_exit", {
                "node": "investigation",
                "elapsed": round(elapsed, 1),
                "findings_preview": summary,
            })
        elif "dossier" in state:
            node_state = state["dossier"]
            send("node_enter", {"node": "dossier", "iteration": iterations})
            ev_sufficient = node_state.get("evidence_sufficient", False)
            send("node_exit", {
                "node": "dossier",
                "elapsed": round(elapsed, 1),
                "evidence_sufficient": ev_sufficient,
            })
            # Emit dedicated rejection / acceptance events
            if not ev_sufficient:
                gaps = node_state.get("findings", {}).get("evidence_gaps", "")
                send("dossier_rejected", {
                    "message": "Dossier rejected the investigation — evidence is INSUFFICIENT. Looping back to investigation.",
                    "evidence_gaps": gaps,
                })
            else:
                send("dossier_accepted", {
                    "message": "Dossier accepted the investigation — evidence is SUFFICIENT.",
                })

        if iterations >= max_iterations:
            send("status", {"message": f"Reached max iterations ({max_iterations})"})
            break

        current = node_output
        if current.get("current_phase") == "done":
            break

    total_time = time.time() - graph_start

    # Build result payload using accumulated state
    last = list(final_state.values())[-1] if final_state else {}
    result = {
        "iterations": iterations,
        "total_time": round(total_time, 1),
        "phase": last.get("current_phase", "unknown"),
        "loop_count": last.get("loop_count", 0),
        "evidence_sufficient": best_evidence_sufficient,
        "dossier": best_dossier,
        "findings": {k: str(v) for k, v in best_findings.items()},
    }

    send("investigation_complete", result)


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok", "data_loaded": data_ctx is not None}


@app.get("/api/graph-schema")
async def graph_schema():
    """Return the static graph structure for the frontend to render."""
    return {
        "nodes": [
            {"id": "start", "label": "START", "type": "terminal"},
            {"id": "orchestrator", "label": "Orchestrator", "type": "agent", "description": "Lead Investigator – routes & decides"},
            {"id": "investigation", "label": "Investigation", "type": "agent", "description": "Detective – 7 tools for fraud analysis"},
            {"id": "dossier", "label": "Dossier", "type": "agent", "description": "Case Writer – evidence & compilation"},
            {"id": "end", "label": "END", "type": "terminal"},
        ],
        "edges": [
            {"from": "start", "to": "orchestrator", "label": ""},
            {"from": "orchestrator", "to": "investigation", "label": "scan / investigate"},
            {"from": "orchestrator", "to": "dossier", "label": "compile"},
            {"from": "orchestrator", "to": "end", "label": "done"},
            {"from": "investigation", "to": "orchestrator", "label": "report"},
            {"from": "dossier", "to": "orchestrator", "label": "assess"},
        ],
    }


@app.get("/api/anomaly-summary")
async def anomaly_summary():
    """Quick data summary for the dashboard."""
    if not data_ctx:
        return {"error": "Data not loaded"}
    high = data_ctx.get_high_anomaly_providers(0.5)
    return {
        "total_providers": len(data_ctx.providers_df),
        "total_claims": len(data_ctx.claims_df),
        "high_anomaly_count": len(high),
        "top_providers": [
            {
                "entity_id": row["entity_id"],
                "anomaly_score": round(float(row["anomaly_score"]), 2),
                "total_billed": round(float(row["total_billed"]), 2),
            }
            for _, row in high.head(10).iterrows()
        ],
    }


@app.get("/api/fraud-network")
async def fraud_network(
    min_anomaly: float = 0.5,
    min_ring_size: int = 3,
    focus_entity: str = None,
    depth: int = 2,
):
    """
    Return the fraud network graph data for visualization.

    Two modes:
    - Default: returns all fraud rings + their edges
    - focus_entity: returns the ego-network around a specific entity
    """
    if not data_ctx:
        return {"error": "Data not loaded"}

    G = data_ctx.graph
    nodes_out = []
    edges_out = []
    seen_nodes = set()

    # Helper: enrich a node for the frontend
    def _node_dict(nid):
        if nid in seen_nodes:
            return None
        seen_nodes.add(nid)
        nd = G.nodes.get(nid, {})
        entity_type = nd.get("entity_type", "unknown")
        anomaly = round(float(nd.get("anomaly_score", 0)), 2)
        total_billed = round(float(nd.get("total_billed", 0)), 2)

        # Lookup extra info
        label = nid
        specialty = None
        if entity_type == "provider":
            prow = data_ctx.providers_df[data_ctx.providers_df["provider_id"] == nid]
            if len(prow):
                label = f"{nid}"
                specialty = prow.iloc[0].get("specialty", None)
        elif entity_type == "member":
            label = nid
        elif entity_type == "facility":
            frow = data_ctx.facilities_df[data_ctx.facilities_df["facility_id"] == nid]
            if len(frow):
                label = f"{nid}"

        return {
            "id": nid,
            "label": label,
            "entity_type": entity_type,
            "anomaly_score": anomaly,
            "total_billed": total_billed,
            "specialty": specialty,
        }

    # ----- Focus mode: ego-network around one entity -----
    if focus_entity:
        conns = find_connections(G, focus_entity, depth)
        if conns.get("error"):
            return conns

        # Add center node
        center = _node_dict(focus_entity)
        if center:
            center["is_focus"] = True
            nodes_out.append(center)

        for ent in conns["connected_entities"]:
            nd = _node_dict(ent["entity_id"])
            if nd:
                nd["distance"] = ent["distance"]
                nodes_out.append(nd)

        # Edges within this subgraph
        for src, dst, edata in G.edges(data=True):
            if src in seen_nodes and dst in seen_nodes:
                edges_out.append({
                    "source": src,
                    "target": dst,
                    "relationship": edata.get("relationship", "CONNECTED"),
                    "weight": edata.get("weight", 1),
                    "total_amount": round(float(edata.get("total_amount", 0)), 2),
                })

        return {
            "mode": "focus",
            "focus_entity": focus_entity,
            "nodes": nodes_out,
            "edges": edges_out,
            "density": conns["connection_density"],
        }

    # ----- Default mode: fraud rings -----
    rings = find_rings(G, data_ctx.anomaly_scores_df, min_anomaly, min_ring_size)

    ring_summaries = []
    for ri, ring in enumerate(rings[:5]):  # Top 5 rings
        ring_entity_ids = [e["entity_id"] for e in ring["entities"]]

        for ent in ring["entities"]:
            nd = _node_dict(ent["entity_id"])
            if nd:
                nd["ring_index"] = ri
                nodes_out.append(nd)

        r_edges = get_ring_edges(G, ring_entity_ids)
        for e in r_edges:
            edges_out.append({
                "source": e["src"],
                "target": e["dst"],
                "relationship": e["relationship"],
                "weight": e["weight"],
                "total_amount": round(float(e.get("total_amount", 0)), 2),
                "ring_index": ri,
            })

        ring_summaries.append({
            "ring_index": ri,
            "entity_count": ring["entity_count"],
            "avg_anomaly": ring["avg_anomaly_score"],
            "total_billed": ring["total_billed"],
            "density": ring["connection_density"],
        })

    return {
        "mode": "rings",
        "rings": ring_summaries,
        "nodes": nodes_out,
        "edges": edges_out,
    }


# ---------------------------------------------------------------------------
# WebSocket – real-time investigation stream
# ---------------------------------------------------------------------------
@app.websocket("/ws/investigate")
async def ws_investigate(ws: WebSocket):
    await ws.accept()
    loop = asyncio.get_event_loop()

    _patch_loggers(ws, loop)

    try:
        await ws_send(ws, "connected", {"message": "WebSocket connected"})

        # Wait for the client to send a "start" message
        msg = await ws.receive_text()
        payload = json.loads(msg) if msg else {}

        if payload.get("action") != "start":
            await ws_send(ws, "error", {"message": "Send {action: 'start'} to begin"})
            return

        await ws_send(ws, "status", {"message": "Investigation starting..."})

        # Run the graph in a background thread so the WS stays responsive
        if is_demo_mode():
            print("[API] *** DEMO MODE — using scripted investigation ***")
            await asyncio.to_thread(run_demo_investigation_sync, ws, loop)
        else:
            await asyncio.to_thread(_run_investigation_sync, ws, loop)

    except WebSocketDisconnect:
        print("[API] WebSocket disconnected")
    except Exception as exc:
        traceback.print_exc()
        try:
            await ws_send(ws, "error", {"message": str(exc)})
        except Exception:
            pass
    finally:
        _unpatch_loggers()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
