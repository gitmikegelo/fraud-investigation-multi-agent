"""Conversational copilot agent with session management for Marine Cargo claims."""

from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


FALLBACK_NOTE = "_(Live AI unavailable — showing system summary)_"


@dataclass
class CopilotSession:
    session_id: str
    case_id: str
    case_type: str
    subject_id: str
    subject_name: str
    flag_reason: str = ""
    messages: List = field(default_factory=list)
    tools_called: List[str] = field(default_factory=list)
    checklist_state: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


_sessions: Dict[str, CopilotSession] = {}


def get_or_create_session(case_id: str, case_type: str, subject_id: str = None,
                          subject_name: str = None, flag_reason: str = "") -> CopilotSession:
    if case_id not in _sessions:
        session = CopilotSession(
            session_id=f"sess-{case_id}", case_id=case_id, case_type=case_type,
            subject_id=subject_id or case_id, subject_name=subject_name or case_id,
            flag_reason=flag_reason,
        )

        from agents.prompts_marine import MARINE_COPILOT_PROMPT
        context = f"""Currently reviewing marine cargo claim:
- Claim ID: {case_id}
- Claimant (consignee): {subject_name} (ID: {subject_id})
- Case type: {case_type}
- Flag reason: {flag_reason}

When asked about 'this claim', refer to {case_id} for {subject_name}.
"""
        session.messages = [SystemMessage(content=context + MARINE_COPILOT_PROMPT)]
        _sessions[case_id] = session
    return _sessions[case_id]


def get_tools_for_case_type(case_type: str) -> List:
    from agents.tools_marine import ALL_MARINE_TOOLS
    return ALL_MARINE_TOOLS


def _system_summary(case_id: str) -> str:
    """Deterministic, tool-built summary used when the LLM cannot be reached."""
    try:
        from agents.tools_marine import build_system_summary
        body = build_system_summary(case_id)
    except Exception as e:
        body = f"System summary unavailable: {str(e)[:200]}"
    return f"{FALLBACK_NOTE}\n\n{body}"


def handle_analyst_message_sync(case_id: str, case_type: str, analyst_message: str,
                                subject_id: str = None, subject_name: str = None, flag_reason: str = "") -> str:
    """Process one analyst message synchronously. Returns agent response text.

    If the LLM or agent cannot be created or invoked (e.g. Bedrock unavailable), returns a
    deterministic markdown summary built from the claim tools instead of an error string.
    """
    session = get_or_create_session(case_id, case_type, subject_id, subject_name, flag_reason)
    session.messages.append(HumanMessage(content=analyst_message))

    try:
        from langgraph.prebuilt import create_react_agent
        from agents.nodes import get_bedrock_llm
        tools = get_tools_for_case_type(case_type)
        llm = get_bedrock_llm(temperature=0.1, max_tokens=4096, agent_name="copilot")
        agent = create_react_agent(llm, tools)
        result = agent.invoke({"messages": session.messages})
    except Exception as e:
        print(f"  [copilot] Live AI unavailable for {case_id}: {str(e)[:200]} — using system summary", flush=True)
        fallback = _system_summary(case_id)
        session.messages.append(AIMessage(content=fallback))
        return fallback

    response_text = "I couldn't generate a response."
    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            response_text = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    session.messages.append(AIMessage(content=response_text))

    for msg in result.get("messages", []):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                session.tools_called.append(tc["name"])

    return response_text
