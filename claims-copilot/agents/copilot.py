"""
Conversational copilot agent with session management.
Analyst sends messages, agent picks tools and responds.
"""

from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent


@dataclass
class CopilotSession:
    session_id: str
    case_id: str
    case_type: str  # "provider_fraud" | "disability_claim"
    subject_id: str  # The entity being investigated (provider ID or claim ID)
    subject_name: str  # Human-readable name
    flag_reason: str = ""  # Why this case was flagged
    messages: List = field(default_factory=list)
    tools_called: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


_sessions: Dict[str, CopilotSession] = {}


def get_or_create_session(case_id: str, case_type: str, subject_id: str = None, 
                          subject_name: str = None, flag_reason: str = "") -> CopilotSession:
    if case_id not in _sessions:
        session = CopilotSession(
            session_id=f"sess-{case_id}", 
            case_id=case_id, 
            case_type=case_type,
            subject_id=subject_id or case_id,
            subject_name=subject_name or case_id,
            flag_reason=flag_reason
        )

        # Build context-aware system prompt
        context = f"""
Currently investigating:
- Case ID: {case_id}
- Subject: {subject_name} (ID: {subject_id})
- Flag reason: {flag_reason}

"""

        if case_type == "provider_fraud":
            from agents.prompts import INVESTIGATION_PROMPT
            system_prompt = context + INVESTIGATION_PROMPT + f"\n\nWhen asked about 'this provider', refer to {subject_id}."
            session.messages = [SystemMessage(content=system_prompt)]
        else:
            from agents.prompts_disability import DISABILITY_COPILOT_PROMPT
            system_prompt = context + DISABILITY_COPILOT_PROMPT + f"\n\nWhen asked about 'this claim', refer to claim {case_id} for claimant {subject_name}."
            session.messages = [SystemMessage(content=system_prompt)]

        _sessions[case_id] = session
    return _sessions[case_id]

def get_tools_for_case_type(case_type: str) -> List:
    if case_type == "provider_fraud":
        from agents.tools_investigation import (
            profile_entity, compare_to_peers, get_claim_details,
            find_connections, find_ring, get_referral_history,
        )
        from agents.tools_dossier import (
            search_billing_rules, find_similar_cases, estimate_recovery, compile_dossier,
        )
        return [profile_entity, compare_to_peers, get_claim_details,
                find_connections, find_ring, get_referral_history,
                search_billing_rules, find_similar_cases, estimate_recovery, compile_dossier]
    else:
        from agents.tools_disability import DISABILITY_TOOLS
        from agents.tools_dossier import compile_dossier
        return DISABILITY_TOOLS + [compile_dossier]


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
        err = f"Error processing message: {str(e)[:200]}"
        session.messages.append(AIMessage(content=err))
        return err

    # Find the last non-tool-call AI response
    response_text = "I couldn't generate a response."
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            response_text = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    session.messages.append(AIMessage(content=response_text))

    # Log tool usage
    for msg in result["messages"]:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                session.tools_called.append(tc["name"])

    return response_text
