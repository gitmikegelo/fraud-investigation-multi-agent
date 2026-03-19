"""FastAPI Backend for Prudential Supplemental Health Examiner Workflow Copilot."""

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

from main import initialize_data, DataContext
from cases import CaseStatus
from intelligence.checklist import run_full_checklist, run_checklist_step, CHECKLIST_STEPS
from intelligence.document_vision import run_vision_document_checks, find_claim_images


def _build_checklist_ctx(claim_id: str) -> dict:
    """Build checklist context, replacing cached doc results with live vision if images exist."""
    live_doc_results = dict(data_ctx.claim_doc_results)
    images = find_claim_images(claim_id)
    if images:
        try:
            vision_results = run_vision_document_checks(claim_id)
            if vision_results:
                live_doc_results[claim_id] = vision_results
        except Exception as e:
            print(f"  ⚠ Vision analysis failed for {claim_id}: {e} — using cached metadata")
    return {
        "claims": data_ctx.supplemental_claims,
        "members": data_ctx.supplemental_data.get("members", []),
        "dependents": data_ctx.supplemental_data.get("dependents", []),
        "policies": data_ctx.supplemental_data.get("policies", []),
        "workflow_tasks": data_ctx.supplemental_data.get("workflow_tasks", []),
        "claim_rules": data_ctx.claim_rules,
        "claim_risk_scores": data_ctx.claim_risk_scores,
        "claim_doc_results": live_doc_results,
    }

data_ctx: Optional[DataContext] = None

# One-liner descriptions shown in the progressive checklist UI
CHECKLIST_DESCRIPTIONS = {
    1: "Validating required fields and initial assignment",
    2: "Confirming policy is active and coverage matches",
    3: "Running fraud scoring and rule-based screening",
    4: "Checking dependent anomalies and network flags",
    5: "Reviewing medical documentation and records status",
    6: "Verifying coverage limits and policy alignment",
    7: "Compiling final determination for examiner review",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global data_ctx
    print("[API] Initializing data context...")
    data_ctx = initialize_data()
    # Set tool contexts
    try:
        from agents.tools_supplemental import set_context as set_supp_context
        set_supp_context(data_ctx)
    except ImportError:
        pass
    try:
        from agents.tools_dossier import set_context as set_dossier_context
        set_dossier_context(data_ctx)
    except ImportError:
        pass
    print(f"[API] Data context ready. {len(data_ctx.case_queue)} claims loaded.")
    yield


app = FastAPI(title="Prudential Supplemental Health Examiner Workflow Copilot", lifespan=lifespan)

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
    return {"status": "ok", "data_loaded": data_ctx is not None,
            "claims_count": len(data_ctx.case_queue) if data_ctx else 0}


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

    today = datetime(2026, 3, 15)
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

    # Build checklist context with live vision analysis for Step 5
    checklist_ctx = await asyncio.to_thread(_build_checklist_ctx, claim_id)

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
    """Active policy changes affecting claims."""
    if not data_ctx:
        return {"error": "Data not loaded"}

    alerts = []
    for policy in data_ctx.supplemental_data.get("policies", []):
        if policy.owner_change_date or policy.beneficiary_change_date:
            member = data_ctx.get_member(policy.member_id)
            alerts.append({
                "policy_id": policy.policy_id,
                "member_id": policy.member_id,
                "member_name": member.full_name if member else policy.member_id,
                "change_type": "ownership" if policy.owner_change_date else "beneficiary",
                "change_date": policy.owner_change_date or policy.beneficiary_change_date,
                "plan_type": policy.plan_type,
            })
    return {"alerts": alerts}


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

    claim = data_ctx.get_claim(claim_id)
    member = data_ctx.get_member(claim.member_id) if claim else None
    employer = data_ctx.get_employer(claim.employer_id) if claim and claim.employer_id else None
    provider = data_ctx.get_provider(claim.provider_id) if claim else None
    policy = data_ctx.get_policy(claim.policy_id) if claim else None
    risk = data_ctx.claim_risk_scores.get(claim_id)
    rules = data_ctx.claim_rules.get(claim_id, [])
    doc_results = data_ctx.claim_doc_results.get(claim_id, [])
    tasks = data_ctx.get_claim_tasks(claim_id)
    deps = data_ctx.get_member_dependents(claim.member_id) if claim else []
    member_claims = data_ctx.get_member_claims(claim.member_id) if claim else []

    triggered_rules = [r for r in rules if r.triggered]
    failed_docs = [d for d in doc_results if not d.passed]
    critical_docs = [d for d in failed_docs if d.severity == "CRITICAL"]

    # Related claims across the book
    if claim:
        same_employer_claims = [
            c for c in data_ctx.supplemental_claims
            if c.employer_id == claim.employer_id and c.claim_id != claim_id
        ]
        same_provider_claims = [
            c for c in data_ctx.supplemental_claims
            if c.provider_id == claim.provider_id and c.claim_id != claim_id
        ]
    else:
        same_employer_claims = []
        same_provider_claims = []

    # Pre-compute formatted values to avoid f-string ternary+format conflicts
    claim_amount_str = f"${claim.claim_amount:,.2f}" if claim else "$0.00"
    coverage_str = f"${policy.coverage_amount:,.2f}" if policy and policy.coverage_amount else "$0.00"
    employer_total = sum(c.claim_amount for c in same_employer_claims)
    provider_total = sum(c.claim_amount for c in same_provider_claims)

    # Build structured context for the LLM
    context_block = f"""
CLAIM: {claim_id}
Member: {member.full_name if member else 'Unknown'} ({claim.member_id if claim else 'N/A'})
Employer: {employer.name if employer else 'Unknown'} | State: {employer.state if employer else 'N/A'}
Claim Type: {claim.claim_type if claim else 'N/A'} | Claim Amount: {claim_amount_str}
Date of Service: {claim.date_of_service if claim else 'N/A'} | Date Filed: {claim.date_filed if claim else 'N/A'}
Claim Source: {claim.claim_source if claim else 'N/A'}
Provider: {provider.name if provider else 'Unknown'} ({claim.provider_id if claim else 'N/A'}) | Specialty: {provider.specialty if provider else 'N/A'} | Is Mill: {provider.is_mill if provider else False}
Policy: {policy.policy_id if policy else 'N/A'} | Plan Type: {policy.plan_type if policy else 'N/A'} | Coverage: {coverage_str} | Status: {policy.status if policy else 'N/A'}
Policy Effective: {policy.effective_date if policy else 'N/A'} | Owner Change: {policy.owner_change_date if policy else 'None'} | Beneficiary Change: {policy.beneficiary_change_date if policy else 'None'}
Suspicious Banner: {member.suspicious_banner if member else False}

RISK: {risk.total_score if risk else 0}/100 ({risk.tier if risk else 'N/A'})
Top Risk Factors: {'; '.join(risk.top_factors[:5]) if risk and risk.top_factors else 'None'}
Rules Boost: {risk.rules_boost if risk else 0}

ENROLLED DEPENDENTS: {len(deps)}
{chr(10).join(f'  - {d.first_name} {d.last_name} ({d.relationship}, DOB: {d.dob})' for d in deps[:20])}
{"  ... and " + str(len(deps) - 20) + " more" if len(deps) > 20 else ""}

RULES TRIGGERED ({len(triggered_rules)}):
{chr(10).join(f'  [{r.rule_id}] {r.severity} — {r.rule_name}: {r.explanation}' for r in triggered_rules) if triggered_rules else '  None'}

DOCUMENT ANALYSIS FAILURES ({len(failed_docs)}):
{chr(10).join(f'  [{d.check_id}] {d.severity} — {d.check_name}: {d.explanation}' for d in failed_docs) if failed_docs else '  All document checks passed'}

MEMBER CLAIMS HISTORY ({len(member_claims)} total):
{chr(10).join(f'  - {c.claim_id}: {c.claim_type}, ${c.claim_amount:,.2f}, filed {c.date_filed}, status: {c.status}' for c in member_claims[:10]) if member_claims else '  No prior claims'}

SAME-EMPLOYER CLAIMS (excluding this one): {len(same_employer_claims)} claims, total ${employer_total:,.2f}
SAME-PROVIDER CLAIMS (excluding this one): {len(same_provider_claims)} claims, total ${provider_total:,.2f}

WORKFLOW TASKS ({len(tasks)}):
{chr(10).join(f'  - {t.task_type}: {t.status}' + (f' ({t.days_waiting}d waiting)' if t.days_waiting else '') for t in tasks) if tasks else '  No tasks'}
"""

    dossier_prompt = f"""You are a Senior Special Investigations Unit (SIU) analyst at Prudential Insurance writing a formal claim investigation dossier. Write a comprehensive, professional escalation report in Markdown.

Use ONLY the factual data provided below. Do not invent numbers. Write with clarity, precision, and the authority of an experienced fraud investigator. Each section should tell the story of what the data shows.

---
CLAIM INTELLIGENCE DATA:
{context_block}
---

Write the following sections in this exact order. Use proper Markdown headers (##, ###). Be specific, cite numbers, and connect the dots across sections where patterns exist.

## EXECUTIVE SUMMARY
2–3 paragraphs. Lead with the risk determination (HIGH/MEDIUM/LOW). Describe what type of potential fraud or anomaly this represents. State the recommended action and why. Write this as if handing it to a VP who has 60 seconds.

## CLAIM OVERVIEW
A concise table with all key claim identifiers (Claim ID, Member, Employer, Claim Type, Amount, Dates, Provider, Policy, Risk Score).

## MEMBER & DEPENDENT ANALYSIS
Narrative analysis of the member's dependent enrollment (count, relationship patterns, flagged anomalies). If dependent count is abnormal, explain what a normal count looks like and why this deviates. Note any suspicious banner status.

## FRAUD INDICATORS & RULES ANALYSIS
For each triggered rule, write a paragraph explaining: what the rule detects, what the data shows for this claim, and why it is significant. Connect indicators to each other where they form a pattern. If no rules triggered, state that and explain what that means for the determination.

## DOCUMENT INTEGRITY ASSESSMENT
Narrative analysis of document check results. For each failure, explain what it could indicate (fraud vs innocent explanation). Assess overall document integrity. If no failures, confirm documentation is compliant.

## FINANCIAL EXPOSURE ANALYSIS
Calculate and explain: current claim amount, potential dependent exposure if claim pays out, realistic maximum exposure if pattern scales, and any recovery estimate. Be specific with arithmetic.

## NETWORK & RELATED CLAIMS
Summarize same-employer and same-provider claim patterns. Note any cross-claim signals. Quantify the scope.

## POLICY & COVERAGE ANALYSIS
Assess whether the claim is within policy coverage, any type mismatches, date alignment, and any policy changes (owner/beneficiary) that create alert conditions.

## WORKFLOW STATUS
Summarize open tasks, TAT compliance, and any pending medical record requests.

## RECOMMENDED ACTION
One of: APPROVE / PEND / DENY / ESCALATE TO SIU. Provide a direct, justified recommendation with the specific next steps the examiner must take. Be actionable.

## EVIDENCE SUMMARY FOR SIU
Bullet list of the key evidence points — written in a format suitable for legal review or prosecutor referral.

---
*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · Prudential Supplemental Health SIU · ARIA Examiner Workflow Copilot*
"""

    try:
        from agents.nodes import get_bedrock_llm
        from langchain_core.messages import HumanMessage
        llm = get_bedrock_llm(temperature=0.05, max_tokens=8000, agent_name="dossier")
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
                checklist_ctx = await asyncio.to_thread(_build_checklist_ctx, claim_id)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
