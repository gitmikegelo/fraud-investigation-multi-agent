"""FastAPI Backend for Claims Examiner Workflow Copilot (Marine Cargo)."""

import sys
import os
import json
import asyncio
import traceback
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'), override=False)
except ImportError:
    pass

from main import initialize_marine_data, _context_dict, DataContext, DOMAIN_MODE
from cases import CaseStatus
from data.generate_marine import DEMO_TODAY
from intelligence.document_vision import run_vision_document_checks, find_claim_images

from intelligence.checklist_marine import run_full_checklist, run_checklist_step, CHECKLIST_STEPS


def _build_marine_checklist_ctx(claim_id: str) -> dict:
    """Build checklist context for marine cargo mode.

    Runs vision forensics on the claim's evidence images when present. Results are
    disk-cached (see document_vision), so a rehearsed demo replays without Bedrock.
    Fails soft — a missing image or a failed request leaves the step to manual review.
    """
    live_doc_results = dict(data_ctx.claim_doc_results)
    images = find_claim_images(claim_id)
    duplicates = data_ctx.supplemental_data.get("duplicate_images", {}).get(claim_id, [])
    if images:
        try:
            vision_results = run_vision_document_checks(
                claim_id, skip_images={m["image"] for m in duplicates})
            if vision_results:
                live_doc_results[claim_id] = vision_results
                data_ctx.claim_doc_results[claim_id] = vision_results
        except Exception as e:
            print(f"  ⚠ Vision analysis failed for {claim_id}: {e} — manual review")
    ctx = _context_dict(data_ctx.supplemental_data)
    ctx.update({
        "claim_rules": data_ctx.claim_rules,
        "claim_risk_scores": data_ctx.claim_risk_scores,
        "claim_doc_results": live_doc_results,
        "duplicate_images": data_ctx.supplemental_data.get("duplicate_images", {}),
        "has_claim_images": bool(images),
    })
    return ctx

data_ctx: Optional[DataContext] = None

# One-liner descriptions shown in the progressive checklist UI
CHECKLIST_DESCRIPTIONS = {
    1: "Validating claim completeness, notification timing and claim frequency",
    2: "Cross-checking B/L, commercial invoice, packing list and VGM",
    3: "Confirming the loss falls within the insured transit (ICC cl. 8)",
    4: "AI forensics on survey photos and documents, reused-image check",
    5: "Checking survey timing, appointment and surveyor independence",
    6: "Verifying ICC clause cover, exclusions, sum insured and recovery rights",
    7: "Compiling final determination for claims handler review",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global data_ctx
    print(f"[API] Initializing data context (mode: {DOMAIN_MODE})...")
    data_ctx = initialize_marine_data()
    try:
        from agents.tools_marine import set_context as set_marine_context
        set_marine_context(data_ctx)
    except ImportError:
        pass
    # Investigation + dossier tool context
    _inv_mod, _dossier_mod = "agents.tools_investigation_marine", "agents.tools_dossier_marine"
    try:
        import importlib
        importlib.import_module(_inv_mod).set_context(data_ctx)
    except (ImportError, AttributeError):
        pass
    try:
        import importlib
        importlib.import_module(_dossier_mod).set_context(data_ctx)
    except (ImportError, AttributeError):
        pass
    print(f"[API] Data context ready. {len(data_ctx.case_queue)} claims loaded.")
    yield


_APP_TITLE = "Marine Cargo Claims Copilot"
app = FastAPI(title=_APP_TITLE, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


def _case_to_dict(c):
    """Serialize a Case to dict."""
    return {
        "case_id": c.case_id,
        "case_type": c.case_type.value,
        "claim_type": c.claim_type.value,
        "subject_id": c.subject_id,
        "subject_name": c.subject_name,
        "priority": c.priority.value,
        "flag_reason": c.flag_reason,
        "risk_score": c.risk_score,
        "claim_source": c.claim_source,
        "status": c.status.value,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "date_filed": c.date_filed.strftime("%Y-%m-%d") if hasattr(c.date_filed, 'strftime') else str(c.date_filed) if c.date_filed else None,
        "key_metrics": c.key_metrics,
        "rules_triggered": c.rules_triggered,
        "workflow_tasks": c.workflow_tasks,
        "document_flags": c.document_flags,
        "checklist_state": c.checklist_state,
        "employer_name": c.employer_name,
        "member_id": c.member_id,
        "provider_name": c.provider_name,
        "claim_amount": c.claim_amount,
        "coverage_start": c.coverage_start,
        "coverage_end": c.coverage_end,
        "summary": c.summary,
        "dossier": c.dossier,
    }


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    # Surface the running process's mode so a stale/wrong-domain server is obvious at a glance.
    try:
        import agents.nodes as _nodes
        _investigation_domain = "marine" if "Marine Cargo" in getattr(_nodes, "INVESTIGATION_PROMPT", "") else "unknown"
    except Exception:
        _investigation_domain = "unknown"
    return {"status": "ok", "data_loaded": data_ctx is not None,
            "claims_count": len(data_ctx.case_queue) if data_ctx else 0,
            "domain_mode": DOMAIN_MODE,
            "demo_mode": is_demo_mode(),
            "investigation_domain": _investigation_domain}


@app.get("/api/config")
async def get_config():
    if not data_ctx:
        return {"error": "Data not loaded"}
    cfg = data_ctx.domain_config
    return {
        "name": cfg.name,
        "display_name": cfg.display_name,
        "claim_types": cfg.claim_types,
        "risk_tiers": cfg.risk_tiers,
        "checklist_steps": cfg.checklist_steps,
    }


# ── Claims Queue ─────────────────────────────────────────────────────────────

@app.get("/api/claims")
async def get_claims(
    claim_type: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    date_range: Optional[str] = "today",
):
    """Get claims with filtering. date_range: today|this_week|all (default: today)."""
    if not data_ctx:
        return {"error": "Data not loaded"}

    today = DEMO_TODAY
    week_start = today - timedelta(days=today.weekday())

    cases = list(data_ctx.case_queue)

    # Date filtering
    if date_range == "today":
        today_str = today.strftime("%Y-%m-%d")
        cases = [c for c in cases if str(c.date_filed) == today_str]
    elif date_range == "this_week":
        week_str = week_start.strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")
        cases = [c for c in cases if week_str <= str(c.date_filed) <= today_str]

    # Type/priority/status filtering
    if claim_type:
        cases = [c for c in cases if c.claim_type.value == claim_type]
    if priority:
        cases = [c for c in cases if c.priority.value == priority]
    if status:
        cases = [c for c in cases if c.status.value == status]

    # Counts
    all_cases = data_ctx.case_queue
    today_str = today.strftime("%Y-%m-%d")
    week_str = week_start.strftime("%Y-%m-%d")

    by_date = {
        "today": sum(1 for c in all_cases if str(c.date_filed) == today_str),
        "this_week": sum(1 for c in all_cases if week_str <= str(c.date_filed) <= today_str),
        "all": len(all_cases),
    }
    by_type = {}
    by_priority = {}
    for c in cases:
        by_type[c.claim_type.value] = by_type.get(c.claim_type.value, 0) + 1
        by_priority[c.priority.value] = by_priority.get(c.priority.value, 0) + 1

    return {
        "claims": [_case_to_dict(c) for c in cases],
        "counts": {
            "total": len(cases),
            "by_date": by_date,
            "by_type": by_type,
            "by_priority": by_priority,
        },
    }


@app.get("/api/claims/{claim_id}")
async def get_claim_detail(claim_id: str):
    """Full claim detail with risk, rules, docs, tasks, checklist."""
    if not data_ctx:
        return {"error": "Data not loaded"}
    case = data_ctx.get_case(claim_id)
    if not case:
        return {"error": f"Claim {claim_id} not found"}

    result = _case_to_dict(case)

    # Add risk breakdown
    risk = data_ctx.claim_risk_scores.get(claim_id)
    if risk:
        result["risk_breakdown"] = {
            "total_score": risk.total_score,
            "tier": risk.tier,
            "top_factors": risk.top_factors,
            "rules_boost": risk.rules_boost,
            "feature_contributions": [
                {"category": f.category, "feature_name": f.feature_name,
                 "raw_value": round(f.raw_value, 3), "normalized": round(f.normalized, 3),
                 "contribution": round(f.contribution, 4)}
                for f in risk.feature_contributions if f.contribution > 0.001
            ],
        }

    # Add rules
    rules = data_ctx.claim_rules.get(claim_id, [])
    result["rules_detail"] = [
        {"rule_id": r.rule_id, "rule_name": r.rule_name, "severity": r.severity,
         "triggered": r.triggered, "explanation": r.explanation}
        for r in rules
    ]

    # Add document checks
    doc_results = data_ctx.claim_doc_results.get(claim_id, [])
    result["document_checks"] = [
        {"check_id": d.check_id, "check_name": d.check_name, "passed": d.passed,
         "explanation": d.explanation, "severity": d.severity}
        for d in doc_results
    ]

    return result


@app.post("/api/claims/{claim_id}/status")
async def update_claim_status(claim_id: str, body: dict):
    if not data_ctx:
        return {"error": "Data not loaded"}
    case = data_ctx.get_case(claim_id)
    if not case:
        return {"error": f"Claim {claim_id} not found"}
    try:
        case.status = CaseStatus(body.get("status"))
    except ValueError:
        return {"error": "Invalid status"}
    return {"case_id": claim_id, "status": case.status.value}


# ── Intelligence Endpoints ───────────────────────────────────────────────────

@app.get("/api/claims/{claim_id}/risk")
async def get_claim_risk(claim_id: str):
    if not data_ctx:
        return {"error": "Data not loaded"}
    risk = data_ctx.claim_risk_scores.get(claim_id)
    if not risk:
        return {"error": f"No risk data for {claim_id}"}
    return {
        "claim_id": claim_id,
        "total_score": risk.total_score,
        "tier": risk.tier,
        "top_factors": risk.top_factors,
        "rules_boost": risk.rules_boost,
        "feature_contributions": [
            {"category": f.category, "feature_name": f.feature_name,
             "raw_value": round(f.raw_value, 3), "contribution": round(f.contribution, 4)}
            for f in risk.feature_contributions if f.contribution > 0.001
        ],
    }


@app.get("/api/claims/{claim_id}/rules")
async def get_claim_rules(claim_id: str):
    if not data_ctx:
        return {"error": "Data not loaded"}
    rules = data_ctx.claim_rules.get(claim_id, [])
    return {
        "claim_id": claim_id,
        "rules": [
            {"rule_id": r.rule_id, "rule_name": r.rule_name, "severity": r.severity,
             "triggered": r.triggered, "explanation": r.explanation}
            for r in rules
        ],
        "triggered_count": sum(1 for r in rules if r.triggered),
    }


@app.get("/api/claims/{claim_id}/documents")
async def get_claim_documents(claim_id: str):
    if not data_ctx:
        return {"error": "Data not loaded"}
    doc_results = data_ctx.claim_doc_results.get(claim_id, [])
    return {
        "claim_id": claim_id,
        "checks": [
            {"check_id": d.check_id, "check_name": d.check_name, "passed": d.passed,
             "explanation": d.explanation, "severity": d.severity}
            for d in doc_results
        ],
        "failed_count": sum(1 for d in doc_results if not d.passed),
        "critical_count": sum(1 for d in doc_results if not d.passed and d.severity == "CRITICAL"),
    }


@app.get("/api/claims/{claim_id}/document-image")
async def get_claim_document_image(claim_id: str):
    """Serve the document image file for a claim."""
    images = find_claim_images(claim_id)
    if not images:
        return {"error": f"No document image found for {claim_id}"}
    image_path = images[0]
    media_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
    media_type = media_types.get(image_path.suffix.lower(), "image/png")
    return FileResponse(str(image_path), media_type=media_type)


@app.get("/api/claims/{claim_id}/checklist")
async def get_claim_checklist(claim_id: str):
    if not data_ctx:
        return {"error": "Data not loaded"}

    # Build checklist context — runs live vision on the claim's evidence image when
    # present, so build off the event loop to avoid blocking on Bedrock.
    checklist_ctx = await asyncio.to_thread(_build_marine_checklist_ctx, claim_id)

    results = run_full_checklist(claim_id, checklist_ctx)
    return {
        "claim_id": claim_id,
        "steps": [
            {"step_number": r.step_number, "step_name": r.step_name, "status": r.status,
             "auto_passed": r.auto_passed, "findings": r.findings, "details": r.details}
            for r in results
        ],
        "passed_count": sum(1 for r in results if r.status == "pass"),
        "needs_review_count": sum(1 for r in results if r.status == "needs_review"),
        "failed_count": sum(1 for r in results if r.status == "fail"),
    }


@app.get("/api/claims/{claim_id}/tasks")
async def get_claim_tasks(claim_id: str):
    if not data_ctx:
        return {"error": "Data not loaded"}
    tasks = data_ctx.get_claim_tasks(claim_id)
    return {
        "claim_id": claim_id,
        "tasks": [
            {"task_id": t.task_id, "task_type": t.task_type, "status": t.status,
             "assigned_date": t.assigned_date, "due_date": t.due_date,
             "completed_date": t.completed_date, "days_waiting": t.days_waiting}
            for t in tasks
        ],
    }


# ── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/api/claims/stats")
async def get_claims_stats():
    if not data_ctx:
        return {"error": "Data not loaded"}
    stats = data_ctx.get_stats()

    # Add pattern details
    pattern_details = []
    for p in data_ctx.detected_patterns[:20]:
        pattern_details.append({
            "pattern_type": p.pattern_type,
            "description": p.description,
            "severity": p.severity,
            "entity_count": len(p.entities),
        })

    stats["pattern_details"] = pattern_details
    return stats


@app.get("/api/policy-alerts")
async def get_policy_alerts():
    """Policy-change alerts are not used in the marine cargo domain."""
    return {"alerts": []}


# ── AI Dossier Generation ────────────────────────────────────────────────────

@app.post("/api/claims/{claim_id}/generate_dossier")
async def generate_ai_dossier(claim_id: str):
    """
    Generate a comprehensive LLM-written dossier for a claim.
    Gathers all intelligence layers and uses Claude to write narrative sections.
    """
    if not data_ctx:
        return {"error": "Data not loaded"}

    case = data_ctx.get_case(claim_id)
    if not case:
        return {"error": f"Claim {claim_id} not found"}

    # Demo mode: the hero claim always shows the reviewed, scripted dossier (no LLM call).
    if is_demo_mode() and claim_id == "MC-3107":
        from demo_runner_marine import demo_dossier_text
        case.dossier = demo_dossier_text()
        return {"claim_id": claim_id, "dossier": case.dossier, "generated_at": datetime.now().isoformat()}

    claim = data_ctx.get_claim(claim_id)
    consignee =data_ctx.get_consignee(claim.consignee_id) if claim else None
    shipment = data_ctx.get_shipment(claim.shipment_id) if claim else None
    policy = data_ctx.get_policy(claim.policy_id) if claim else None
    survey = data_ctx.get_survey(claim.survey_id) if claim and claim.survey_id else None
    surveyor = data_ctx.get_surveyor(claim.surveyor_id) if claim and claim.surveyor_id else None
    forwarder = data_ctx.get_forwarder(shipment.forwarder_id) if shipment else None
    shipper = data_ctx.get_shipper(shipment.shipper_id) if shipment else None
    risk = data_ctx.claim_risk_scores.get(claim_id)
    rules = data_ctx.claim_rules.get(claim_id, [])
    doc_results = data_ctx.claim_doc_results.get(claim_id, [])
    tasks = data_ctx.get_claim_tasks(claim_id)

    triggered_rules = [r for r in rules if r.triggered]
    failed_docs = [d for d in doc_results if not d.passed]
    subject_name = consignee.name if consignee else case.subject_name

    prior_consignee = data_ctx.get_prior_claims(party_id=claim.consignee_id) if claim else []
    prior_surveyor = data_ctx.get_prior_claims(surveyor_id=claim.surveyor_id) if claim and claim.surveyor_id else []
    network_lines = []
    if consignee:
        for ent in (surveyor, forwarder):
            if not ent:
                continue
            shared = set(ent.director_ids) & set(consignee.director_ids)
            if shared:
                names = ", ".join(data_ctx.get_director(d).full_name for d in shared)
                network_lines.append(f"{ent.name} shares director(s) {names} with the claimant")
            if ent.registered_address and ent.registered_address == consignee.registered_address:
                network_lines.append(f"{ent.name} shares the claimant's registered address ({ent.registered_address})")

    containers = chr(10).join(
        f"  - {c.container_no} ({c.size_type}) seal load {c.seal_no_loading} / discharge {c.seal_no_discharge}, "
        f"VGM {c.vgm_kg:,} kg, tare {c.tare_kg:,} kg" for c in (shipment.containers if shipment else []))

    analyst_entity = "Marine Cargo Claims"
    context_block = f"""
CLAIM: {claim_id} | Type: {claim.claim_type} | Amount claimed: ${claim.claim_amount:,.2f}
Claimant (consignee): {subject_name} ({claim.consignee_id}) — incorporated {getattr(consignee, 'incorporated', 'N/A')}, ~{getattr(consignee, 'shipments_per_year', 'N/A')} shipments/yr
Loss description: {claim.loss_description}
Dates: loss discovered {claim.date_of_loss}; insurer notified {claim.notice_to_insurer_date}; carrier notified {claim.notice_to_carrier_date or 'NOT NOTIFIED'}; filed {claim.date_filed}

SHIPMENT: B/L {shipment.bl_number} | {shipment.carrier} {shipment.vessel} voy. {shipment.voyage}
Route: {shipment.port_of_loading} -> {shipment.port_of_discharge} | Incoterm {shipment.incoterm}
Shipped on board {shipment.shipped_on_board}; discharged {shipment.discharge_date}; gate-out {shipment.gate_out_date}
Commodity: {shipment.commodity} | Quantity {shipment.quantity:,.0f} {shipment.unit} @ ${shipment.unit_price:,.2f}
Invoice {shipment.invoice_no}: ${shipment.invoice_value:,.2f} | Shipper: {getattr(shipper, 'name', 'N/A')} (incorporated {getattr(shipper, 'incorporated', 'N/A')})
B/L clause: {shipment.bl_clause} | B/L gross weight {shipment.gross_weight_bl_kg:,} kg | VGM cargo weight {shipment.vgm_cargo_kg:,} kg
EIR at discharge: {shipment.eir_remarks_discharge}
Containers:
{containers}
Forwarder: {getattr(forwarder, 'name', 'N/A')}

INSURANCE: Certificate {policy.policy_id} under open cover {policy.open_cover_no} | {policy.clause} | Insured value ${policy.insured_value:,.2f} ({policy.basis_of_valuation}) | Excess ${policy.excess:,.2f}

SURVEY: {getattr(survey, 'report_no', 'None')} by {getattr(surveyor, 'name', 'N/A')} ({'insurer panel' if surveyor and surveyor.insurer_panel else 'NOT on insurer panel'}), appointed by {getattr(survey, 'appointed_by', 'N/A')}, on {getattr(survey, 'survey_date', 'N/A')} at {getattr(survey, 'survey_location', 'N/A')}; joint with carrier: {getattr(survey, 'joint_with_carrier', 'N/A')}; cause: {getattr(survey, 'cause_of_loss', 'N/A')}; damage {getattr(survey, 'damage_pct', 0)}%

RISK: {risk.total_score if risk else 0}/100 ({risk.tier if risk else 'N/A'}) | Top factors: {'; '.join(risk.top_factors[:5]) if risk and risk.top_factors else 'None'}

RULES TRIGGERED ({len(triggered_rules)}):
{chr(10).join(f'  [{r.rule_id}] {r.severity} — {r.rule_name}: {r.explanation}' for r in triggered_rules) if triggered_rules else '  None'}

DOCUMENT FORENSICS FAILURES ({len(failed_docs)}):
{chr(10).join(f'  [{d.check_id}] {d.severity} — {d.check_name}: {d.explanation}' for d in failed_docs) if failed_docs else '  No failures (or no images analysed)'}

NETWORK:
{chr(10).join('  - ' + x for x in network_lines) if network_lines else '  No shared directors or addresses found'}
Prior paid claims — this claimant: {len(prior_consignee)} (${sum(p.amount_paid for p in prior_consignee):,.2f})
Prior paid claims — this surveyor: {len(prior_surveyor)} across {len({p.consignee_id for p in prior_surveyor})} consignee(s) (${sum(p.amount_paid for p in prior_surveyor):,.2f})

WORKFLOW TASKS:
{chr(10).join(f'  - {t.task_type}: {t.status}' + (f' ({t.notes})' if t.notes else '') for t in tasks) if tasks else '  No tasks'}
"""

    dossier_prompt = f"""You are a senior marine cargo claims investigator at {analyst_entity} writing a formal claim investigation dossier. Write a professional report in Markdown.

Use ONLY the factual data below. Do not invent numbers, names or dates. Use correct marine insurance terminology (bill of lading, VGM, EIR, Institute Cargo Clauses, duty of assured, recovery/subrogation). Where a finding could have an innocent explanation, say so.

---
CLAIM INTELLIGENCE DATA:
{context_block}
---

Write these sections in this order, with ## headers:

## EXECUTIVE SUMMARY
2 short paragraphs for a senior executive with 60 seconds. Lead with the determination (HIGH/MEDIUM/LOW risk), what the evidence shows, the recommended action and the financial effect.

## CLAIM & SHIPMENT OVERVIEW
A table: Claim ID, Claimant, Commodity, B/L, Vessel/Voyage, Route, Containers, Invoice value, Insured value, Amount claimed, Clause, Risk score.

## DOCUMENT CROSS-CHECK
Compare the B/L, commercial invoice, packing list and VGM. Explain any weight, quantity or value inconsistency and what it implies.

## SURVEY & EVIDENCE INTEGRITY
Survey timing, who appointed the surveyor, joint survey, location, and any evidence-image findings.

## COVERAGE ANALYSIS (ICC)
Is the peril covered under the stated clause? Transit period (cl. 8), exclusions (cl. 4), duty of assured and preservation of recovery rights (cl. 16), sum insured.

## NETWORK & RELATED CLAIMS
Shared directors/addresses and prior claims. Quantify.

## FINANCIAL POSITION
Amount claimed, amount substantiated (if determinable), recovery prospects against the carrier. Show arithmetic.

## RECOMMENDED ACTION
One of: APPROVE / APPROVE AND PURSUE RECOVERY / DECLINE / REFER FOR INVESTIGATION. Give the specific next steps.

---
*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · {analyst_entity} · ARIA Claims Copilot*
"""

    try:
        from agents.nodes import get_bedrock_llm
        from langchain_core.messages import HumanMessage
        llm = get_bedrock_llm(temperature=0.05, max_tokens=4096, agent_name="dossier")
        result = await asyncio.to_thread(llm.invoke, [HumanMessage(content=dossier_prompt)])
        dossier_text = result.content if isinstance(result.content, str) else str(result.content)
    except Exception as e:
        traceback.print_exc()
        return {"error": f"LLM generation failed: {str(e)[:300]}"}

    # Cache it on the case
    for c in data_ctx.case_queue:
        if c.case_id == claim_id:
            c.dossier = dossier_text
            break

    return {"claim_id": claim_id, "dossier": dossier_text, "generated_at": datetime.now().isoformat()}


@app.post("/api/claims/{claim_id}/generate_letter")
async def generate_claimant_letter(claim_id: str):
    """
    Generate a short, plain-language letter addressed to the claimant/policyholder.

    Unlike the internal SIU dossier, this is claimant-facing: it must NOT expose
    risk scores, rule IDs, fraud terminology, or investigation internals. Claude
    reads the same intelligence context but decides the appropriate tone/outcome
    (review complete & in order, additional information needed, or under further
    review) and keeps the letter minimal and reassuring.
    """
    if not data_ctx:
        return {"error": "Data not loaded"}

    case = data_ctx.get_case(claim_id)
    if not case:
        return {"error": f"Claim {claim_id} not found"}

    claim = data_ctx.get_claim(claim_id)
    subject_id = getattr(claim, 'insured_id', '') if claim else ''
    insured = data_ctx.get_insured(subject_id) if subject_id else None
    risk = data_ctx.claim_risk_scores.get(claim_id)
    rules = data_ctx.claim_rules.get(claim_id, [])
    doc_results = data_ctx.claim_doc_results.get(claim_id, [])
    tasks = data_ctx.get_claim_tasks(claim_id)

    triggered_rules = [r for r in rules if r.triggered]
    failed_docs = [d for d in doc_results if not d.passed]
    open_tasks = [t for t in tasks if getattr(t, 'status', '') in ("pending", "in_progress", "overdue")]

    subject_name = getattr(insured, 'full_name', None) or case.subject_name
    claim_type = (claim.claim_type if claim else case.claim_type.value).replace('_', ' ')
    incident_date = getattr(claim, 'date_of_loss', 'N/A') if claim else 'N/A'
    today = datetime.now().strftime('%B %d, %Y')

    # Internal signal summary — used ONLY to help Claude pick the right tone.
    # None of these internals are permitted to appear in the letter text.
    internal_signal = f"""
INTERNAL REVIEW SIGNALS (for tone selection ONLY — never mention these in the letter):
- Risk tier: {risk.tier if risk else 'LOW'}
- Triggered fraud rules: {len(triggered_rules)}
- Failed document checks: {len(failed_docs)}
- Open/pending workflow tasks: {len(open_tasks)}
"""

    letter_prompt = f"""You are a claims correspondence officer at a marine cargo insurer. Write a short, professional letter addressed to the claimant (the assured / consignee) about their cargo claim.

You are given internal review signals below. Use them ONLY to decide the appropriate outcome and tone. Choose ONE of these three situations based on the signals:
  1. REVIEW COMPLETE, IN ORDER — if the internal signals are clean (LOW risk, no failed document checks, no open tasks). Reassure them their claim has been reviewed and is proceeding normally.
  2. ADDITIONAL INFORMATION NEEDED — if there are failed document checks or open tasks but the situation is routine. Politely ask them to expect a follow-up / provide documentation, without alarm.
  3. UNDER FURTHER REVIEW — if signals are elevated (MEDIUM/HIGH risk or triggered rules). Neutrally inform them their claim requires additional review and that no action is needed from them at this time unless contacted.

STRICT RULES FOR THE LETTER BODY:
- NEVER mention: fraud, investigation, SIU, risk scores, risk tiers, rule names/IDs, watchlists, or any internal scoring.
- Keep it to 2-3 short paragraphs. Warm, plain, professional. No jargon.
- Reference the claim in general terms (claim reference, {claim_type} claim) — do not disclose internal findings.
- Do not promise or deny the outcome of the claim; only describe the current status and next steps.
- Format as a proper business letter in Markdown: date, addressee, salutation, body, and sign-off ("Claims Review Team").

CLAIM CONTEXT:
- Date: {today}
- Claimant: {subject_name}
- Claim reference: {claim_id}
- Claim type: {claim_type} claim
- Date loss discovered: {incident_date}
{internal_signal}
Write only the letter, nothing else."""

    try:
        from agents.nodes import get_bedrock_llm
        from langchain_core.messages import HumanMessage
        llm = get_bedrock_llm(temperature=0.2, max_tokens=1024, agent_name="letter")
        result = await asyncio.to_thread(llm.invoke, [HumanMessage(content=letter_prompt)])
        letter_text = result.content if isinstance(result.content, str) else str(result.content)
    except Exception as e:
        traceback.print_exc()
        return {"error": f"LLM generation failed: {str(e)[:300]}"}

    # Cache it on the case
    for c in data_ctx.case_queue:
        if c.case_id == claim_id:
            c.letter = letter_text
            break

    return {"claim_id": claim_id, "letter": letter_text, "generated_at": datetime.now().isoformat()}


# ── Chat WebSocket ───────────────────────────────────────────────────────────

@app.websocket("/ws/chat/{claim_id}")
async def chat_websocket(websocket: WebSocket, claim_id: str):
    await websocket.accept()
    if not data_ctx:
        await websocket.send_json({"type": "error", "message": "Data not loaded"})
        await websocket.close()
        return

    case = data_ctx.get_case(claim_id)
    if not case:
        await websocket.send_json({"type": "error", "message": f"Claim {claim_id} not found"})
        await websocket.close()
        return

    # Send initial context
    risk = data_ctx.claim_risk_scores.get(claim_id)
    rules = data_ctx.claim_rules.get(claim_id, [])
    triggered = [r for r in rules if r.triggered]

    await websocket.send_json({
        "type": "connected",
        "case_id": claim_id,
        "case_type": case.case_type.value,
        "claim_type": case.claim_type.value,
        "subject_name": case.subject_name,
        "risk_score": case.risk_score,
        "risk_tier": risk.tier if risk else "LOW",
        "rules_triggered": len(triggered),
        "workflow_tasks": case.workflow_tasks,
        "employer_name": case.employer_name,
        "claim_amount": case.claim_amount,
        "timestamp": datetime.now().isoformat(),
    })

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "end_session":
                break

            # ── Progressive checklist runner ─────────────────────────────
            if data.get("action") == "run_checklist":
                # Run vision analysis before checklist so Step 5 uses real image inspection
                checklist_ctx = await asyncio.to_thread(_build_marine_checklist_ctx, claim_id)
                # Send initial checklist skeleton
                steps_skeleton = [
                    {"step_number": sn, "step_name": sname,
                     "description": CHECKLIST_DESCRIPTIONS.get(sn, ""),
                     "status": "pending"}
                    for sn, sname in CHECKLIST_STEPS
                ]
                await websocket.send_json({
                    "type": "checklist_start",
                    "steps": steps_skeleton,
                    "timestamp": datetime.now().isoformat(),
                })

                all_results = []
                for step_num, step_name in CHECKLIST_STEPS:
                    # Send "running" status for current step
                    await websocket.send_json({
                        "type": "checklist_step",
                        "step_number": step_num,
                        "step_name": step_name,
                        "description": CHECKLIST_DESCRIPTIONS.get(step_num, ""),
                        "status": "running",
                        "timestamp": datetime.now().isoformat(),
                    })
                    # Run the step in a thread to avoid blocking
                    result = await asyncio.to_thread(
                        run_checklist_step, step_num, claim_id, checklist_ctx
                    )
                    step_result = {
                        "step_number": result.step_number,
                        "step_name": result.step_name,
                        "status": result.status,
                        "auto_passed": result.auto_passed,
                        "findings": result.findings,
                        "details": result.details,
                        "description": CHECKLIST_DESCRIPTIONS.get(step_num, ""),
                    }
                    all_results.append(step_result)
                    # Send completed step
                    await websocket.send_json({
                        "type": "checklist_step",
                        **step_result,
                        "timestamp": datetime.now().isoformat(),
                    })
                    # Small delay for visual effect
                    await asyncio.sleep(0.35)

                # Persist to case
                summary = {
                    "passed": sum(1 for r in all_results if r["status"] == "pass"),
                    "needs_review": sum(1 for r in all_results if r["status"] == "needs_review"),
                    "failed": sum(1 for r in all_results if r["status"] == "fail"),
                }
                case.checklist_state = {"steps": all_results, "summary": summary}

                await websocket.send_json({
                    "type": "checklist_complete",
                    "checklist": {"steps": all_results, "summary": summary},
                    "timestamp": datetime.now().isoformat(),
                })
                continue

            # ── Normal chat message ──────────────────────────────────────
            if data.get("action") == "message":
                text = data.get("text", "")
                if not text:
                    continue
                await websocket.send_json({"type": "thinking", "timestamp": datetime.now().isoformat()})
                try:
                    from agents.copilot import handle_analyst_message_sync
                    response = await asyncio.to_thread(
                        handle_analyst_message_sync,
                        case_id=claim_id,
                        case_type=case.case_type.value,
                        analyst_message=text,
                        subject_id=case.subject_id,
                        subject_name=case.subject_name,
                        flag_reason=case.flag_reason,
                    )
                except Exception as e:
                    traceback.print_exc()
                    await websocket.send_json({"type": "error", "message": str(e)[:500]})
                    continue
                await websocket.send_json({
                    "type": "response",
                    "text": response,
                    "timestamp": datetime.now().isoformat(),
                })
    except WebSocketDisconnect:
        pass


# ── Investigation WebSocket (3-Agent Orchestration) ─────────────────────────

import time as _time
from demo_config import is_demo_mode

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
        if original_fn:
            original_fn(agent_or_name, message)
        if _active_log_file:
            try:
                _active_log_file.write(f"{agent_or_name}\n{message}\n")
                _active_log_file.flush()
            except Exception:
                pass
        if _active_ws and _active_loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    ws_send(_active_ws, "log", {"agent": agent_or_name, "message": message}),
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

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    _log_file_path = os.path.join(logs_dir, f"investigation_{timestamp}.txt")
    _active_log_file = open(_log_file_path, "w", encoding="utf-8")
    print(f"[API] Logging to: logs/investigation_{timestamp}.txt")

    import agents.nodes as nodes_mod
    tinv = None
    tdos = None
    # Patch the tool modules that are actually in use for this domain so their
    # tool:* log lines are captured to the single per-run file.
    _inv_name, _dos_name = "agents.tools_investigation_marine", "agents.tools_dossier_marine"
    try:
        import importlib
        tinv = importlib.import_module(_inv_name)
    except ImportError:
        pass
    try:
        import importlib
        tdos = importlib.import_module(_dos_name)
    except ImportError:
        pass

    if _original_node_log is None:
        _original_node_log = nodes_mod._log
        _original_tool_log_inv = getattr(tinv, '_tool_log', None) if tinv else None
        _original_tool_log_dos = getattr(tdos, '_tool_log', None) if tdos else None

    nodes_mod._log = _make_ws_log("node", _original_node_log)
    if tinv and hasattr(tinv, '_tool_log'):
        tinv._tool_log = _make_ws_log("tool", _original_tool_log_inv)
    if tdos and hasattr(tdos, '_tool_log'):
        tdos._tool_log = _make_ws_log("tool", _original_tool_log_dos)


def _unpatch_loggers():
    global _active_ws, _active_loop, _active_log_file, _log_file_path
    import agents.nodes as nodes_mod

    if _original_node_log:
        nodes_mod._log = _original_node_log
    try:
        import agents.tools_investigation_marine as tinv
        if _original_tool_log_inv:
            tinv._tool_log = _original_tool_log_inv
    except ImportError:
        pass
    try:
        import agents.tools_dossier_marine as tdos
        if _original_tool_log_dos:
            tdos._tool_log = _original_tool_log_dos
    except ImportError:
        pass

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


def _build_investigation_query(claim_id: str, case, checklist_context: dict = None) -> str:
    """Build a focused initial query for the 3-agent orchestration scoped to one claim."""
    claim = data_ctx.get_claim(claim_id) if data_ctx else None
    shipment = data_ctx.get_shipment(claim.shipment_id) if claim else None
    risk = data_ctx.claim_risk_scores.get(claim_id) if data_ctx else None
    rules = data_ctx.claim_rules.get(claim_id, []) if data_ctx else []
    doc_results = data_ctx.claim_doc_results.get(claim_id, []) if data_ctx else []

    triggered_rules = [r for r in rules if r.triggered]
    failed_docs = [d for d in doc_results if not d.passed]

    lines = [
        f"Investigate marine cargo claim {claim_id} for potential fraud.",
        f"Claimant (consignee): {case.subject_name} ({case.subject_id})",
        f"Claim type: {case.claim_type.value if hasattr(case.claim_type, 'value') else case.claim_type}",
        f"Risk score: {case.risk_score}",
    ]
    if claim:
        lines.append(f"Claim amount: ${claim.claim_amount:,.2f}")
        lines.append(f"Surveyor: {claim.surveyor_id or 'N/A'}")
    if shipment:
        lines.append(f"Shipment: B/L {shipment.bl_number}, {shipment.description}, "
                     f"forwarder {shipment.forwarder_id}, shipper {shipment.shipper_id}")
    if risk:
        lines.append(f"Risk tier: {risk.tier}")
        if risk.top_factors:
            lines.append(f"Top risk factors: {'; '.join(risk.top_factors[:5])}")
    if triggered_rules:
        lines.append(f"Rules triggered ({len(triggered_rules)}):")
        for r in triggered_rules[:8]:
            lines.append(f"  [{r.severity}] {r.rule_name}: {r.explanation}")
    if failed_docs:
        lines.append(f"Document check failures ({len(failed_docs)}):")
        for d in failed_docs[:5]:
            lines.append(f"  [{d.severity}] {d.check_name}: {d.explanation}")

    if checklist_context and checklist_context.get("steps"):
        lines.append("\n--- PRIOR CHECKLIST FINDINGS ---")
        for step in checklist_context["steps"]:
            lines.append(f"[Step {step.get('step_number')}: {step.get('step_name')}] status={step.get('status', 'unknown')}")
            for f in (step.get("findings") or [])[:5]:
                lines.append(f"  {f}")

    lines.append("\nStart by scanning for suspicious entities linked to this claim (claimant, surveyor, forwarder, "
                 "shipper), profile them, map shared directors and addresses, and compile a complete dossier.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Run investigation graph in a thread, streaming events via WS
# ---------------------------------------------------------------------------
def _run_investigation_sync(ws: WebSocket, loop: asyncio.AbstractEventLoop,
                            initial_query: str):
    """Execute the LangGraph workflow synchronously (called from a thread)."""
    from langchain_core.messages import HumanMessage
    from agents.graph import create_investigation_graph
    from agents.nodes import clear_agent_caches

    clear_agent_caches()

    def send(event_type: str, data: dict):
        asyncio.run_coroutine_threadsafe(ws_send(ws, event_type, data), loop)
        _time.sleep(0.05)

    send("status", {"message": "Creating investigation graph..."})

    app_graph = create_investigation_graph()

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
    graph_start = _time.time()
    final_state = None

    best_dossier = ""
    best_findings = {}
    best_evidence_sufficient = False

    for state in app_graph.stream(initial_state):
        iterations += 1
        elapsed = _time.time() - graph_start
        final_state = state

        node_output = list(state.values())[0] if state else {}

        step_dossier = node_output.get("dossier", "")
        if step_dossier and len(step_dossier) > len(best_dossier):
            best_dossier = step_dossier

        step_findings = node_output.get("findings", {})
        if step_findings:
            best_findings.update(step_findings)

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
            if not ev_sufficient:
                gaps = node_state.get("findings", {}).get("evidence_gaps", "")
                send("dossier_rejected", {
                    "message": "Dossier rejected — evidence is INSUFFICIENT. Looping back.",
                    "evidence_gaps": gaps,
                })
            else:
                send("dossier_accepted", {
                    "message": "Dossier accepted — evidence is SUFFICIENT.",
                })

        if iterations >= max_iterations:
            send("status", {"message": f"Reached max iterations ({max_iterations})"})
            break

        if node_output.get("current_phase") == "done":
            break

    total_time = _time.time() - graph_start
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


@app.websocket("/ws/investigate/{claim_id}")
async def investigate_websocket(websocket: WebSocket, claim_id: str):
    """WebSocket endpoint for 3-agent fraud investigation scoped to a single claim."""
    await websocket.accept()
    if not data_ctx:
        await ws_send(websocket, "error", {"message": "Data not loaded"})
        await websocket.close()
        return

    case = data_ctx.get_case(claim_id)
    if not case:
        await ws_send(websocket, "error", {"message": f"Claim {claim_id} not found"})
        await websocket.close()
        return

    # Receive initial config (action + checklist context)
    try:
        init_data = await asyncio.wait_for(websocket.receive_json(), timeout=10)
    except Exception:
        init_data = {}

    checklist_context = init_data.get("checklist_context", None)

    await ws_send(websocket, "connected", {
        "claim_id": claim_id,
        "subject_name": case.subject_name,
        "message": f"Connected — investigating {case.subject_name}",
    })

    loop = asyncio.get_event_loop()

    try:
        # The scripted replay tells MC-3107's story only; other claims run the live agents.
        if is_demo_mode() and claim_id == "MC-3107":
            from demo_runner_marine import run_demo_investigation_sync
            _patch_loggers(websocket, loop)
            try:
                demo_dossier = await loop.run_in_executor(
                    None, run_demo_investigation_sync, websocket, loop
                )
            finally:
                _unpatch_loggers()
            if demo_dossier:
                case.dossier = demo_dossier
        else:
            initial_query = _build_investigation_query(claim_id, case, checklist_context)
            _patch_loggers(websocket, loop)
            try:
                await loop.run_in_executor(
                    None, _run_investigation_sync, websocket, loop, initial_query
                )
            finally:
                _unpatch_loggers()

            # Cache dossier on the case (best_dossier is set by _run_investigation_sync)
            try:
                if best_dossier:
                    case.dossier = best_dossier
            except NameError:
                pass
    except WebSocketDisconnect:
        _unpatch_loggers()
    except Exception as e:
        traceback.print_exc()
        try:
            await ws_send(websocket, "error", {"message": str(e)[:500]})
        except Exception:
            pass
        _unpatch_loggers()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
