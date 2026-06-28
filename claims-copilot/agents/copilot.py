"""Conversational copilot agent with session management for Prudential Supplemental Health."""

from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent


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

        import domains  # noqa: F401
        from core.registry import get_active_plugin
        copilot_prompt = get_active_plugin().copilot_prompt
        context = f"""Currently reviewing claim:
- Claim ID: {case_id}
- Claimant: {subject_name} (ID: {subject_id})
- Claim Type: {case_type}
- Flag reason: {flag_reason}

When asked about 'this claim', refer to {case_id} for {subject_name}.
"""
        system_prompt = context + copilot_prompt
        session.messages = [SystemMessage(content=system_prompt)]
        _sessions[case_id] = session
    return _sessions[case_id]


def get_tools_for_case_type(case_type: str) -> List:
    import domains  # noqa: F401
    from core.registry import get_active_plugin
    return get_active_plugin().copilot_tools


def handle_analyst_message_sync(case_id: str, case_type: str, analyst_message: str,
                                subject_id: str = None, subject_name: str = None, flag_reason: str = "") -> str:
    """Process one analyst message synchronously. Returns agent response text."""
    session = get_or_create_session(case_id, case_type, subject_id, subject_name, flag_reason)
    tools = get_tools_for_case_type(case_type)

    session.messages.append(HumanMessage(content=analyst_message))

    from agents.nodes import get_bedrock_llm
    llm = get_bedrock_llm(temperature=0.1, max_tokens=4096, agent_name="copilot")
    agent = create_react_agent(llm, tools)

    try:
        result = agent.invoke({"messages": session.messages})
    except Exception as e:
        err = f"Error: {str(e)[:200]}"
        session.messages.append(AIMessage(content=err))
        return err

    response_text = "I couldn't generate a response."
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            response_text = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    session.messages.append(AIMessage(content=response_text))

    for msg in result["messages"]:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                session.tools_called.append(tc["name"])

    return response_text
