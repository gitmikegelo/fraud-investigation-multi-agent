"""
LangGraph Agent Nodes with AWS Bedrock Claude 3.5 Haiku
"""

import json
import time
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_aws import ChatBedrockConverse
from langgraph.prebuilt import create_react_agent
from langchain_core.callbacks import BaseCallbackHandler

# Max characters for input messages to avoid context window overflow
MAX_MESSAGE_LENGTH = 4000  # More conservative limit for Claude Haiku
MAX_FINDINGS_LENGTH = 3000
MAX_PRIOR_FINDINGS = 1500
MAX_EVIDENCE_GAPS = 800
MAX_AGENT_ITERATIONS = 8  # Limit tool call iterations to prevent context overflow


def _log(agent: str, message: str):
    """Print a timestamped progress log line."""
    from datetime import datetime
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"  [{ts}] [{agent}] {message}", flush=True)


def _log_llm_input(agent_name: str, messages: list):
    """Log detailed information about LLM input for debugging."""
    total_chars = 0
    _log(agent_name, f'=== LLM INPUT DEBUG ({len(messages)} messages) ===')
    for i, msg in enumerate(messages):
        msg_type = type(msg).__name__
        content = ""
        if hasattr(msg, 'content'):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
        content_len = len(content)
        total_chars += content_len
        
        # Log full content (let frontend handle truncation/expansion)
        # Format the content for better readability
        formatted_content = content.replace('\n', ' ') if content else "(empty)"
        _log(agent_name, f'  [{i}] {msg_type}: {content_len} chars | "{formatted_content}"')
        
        # Check for tool calls
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            _log(agent_name, f'      -> Has {len(msg.tool_calls)} tool calls')
    
    _log(agent_name, f'=== TOTAL INPUT: {total_chars} chars ===')
    
    # Warn if input seems large
    if total_chars > 10000:
        _log(agent_name, f'!!! WARNING: Input is very large ({total_chars} chars) - may exceed context window !!!')
    
    return total_chars


def _truncate_text(text: str, max_length: int, label: str = "content") -> str:
    """Truncate text to max_length, adding a note if truncated."""
    if not text or len(text) <= max_length:
        return text
    truncated = text[:max_length]
    # Try to truncate at a sentence or paragraph boundary
    last_period = truncated.rfind('.')
    last_newline = truncated.rfind('\n')
    cut_point = max(last_period, last_newline)
    if cut_point > max_length * 0.7:  # Only use boundary if it's not too far back
        truncated = truncated[:cut_point + 1]
    _log('System', f'Truncated {label} from {len(text)} to {len(truncated)} chars')
    return truncated + f"\n\n... ({label} truncated for brevity) ..."


def _safe_agent_invoke(agent, messages: list, agent_name: str, fallback_message: str = ""):
    """
    Safely invoke an agent with error handling for Bedrock context window errors.
    Returns the result dict or a fallback response.
    """
    # Log what we're sending
    _log_llm_input(agent_name, messages)
    
    try:
        # Use recursion_limit to prevent too many tool calls from accumulating
        return agent.invoke(
            {'messages': messages},
            config={'recursion_limit': MAX_AGENT_ITERATIONS * 2}  # Each tool call is ~2 steps
        )
    except Exception as e:
        error_msg = str(e).lower()
        _log(agent_name, f'!!! EXCEPTION: {str(e)[:300]}')
        
        # Check for context length / input too long errors
        if 'too long' in error_msg or 'validationexception' in error_msg or 'context' in error_msg:
            _log(agent_name, f'WARNING: Input too long for model, using truncated fallback')
            # Try with aggressively truncated message
            if messages:
                truncated_content = _truncate_text(
                    messages[0].content if hasattr(messages[0], 'content') else str(messages[0]),
                    MAX_MESSAGE_LENGTH // 3,  # Even more aggressive truncation
                    "input message"
                )
                try:
                    return agent.invoke(
                        {'messages': [HumanMessage(content=truncated_content)]},
                        config={'recursion_limit': 4}  # Very limited retries
                    )
                except Exception as retry_err:
                    _log(agent_name, f'Retry also failed: {str(retry_err)[:100]}')
            
            # Return a minimal fallback response
            return {
                'messages': [AIMessage(content=fallback_message or f"[{agent_name}] Analysis could not complete due to context length limits. Proceeding with available information.")]
            }
        else:
            _log(agent_name, f'ERROR: Agent invocation failed: {str(e)[:200]}')
            return {
                'messages': [AIMessage(content=fallback_message or f"[{agent_name}] Error during analysis: {str(e)[:200]}")]
            }

try:
    # Source DOMAIN_MODE from main.py (the single source of truth) rather than the
    # raw env var, so the investigation/dossier agents can never load a different
    # domain's tools+prompts than the data context that api.py initialised. Falling
    # back to the env var only if main can't be imported.
    try:
        from main import DOMAIN_MODE as _DOMAIN_MODE
    except ImportError:
        import os as _os
        _DOMAIN_MODE = _os.getenv("DOMAIN_MODE", "travel")
    if _DOMAIN_MODE == "travel":
        from .prompts_investigation_travel import (
            ORCHESTRATOR_PROMPT,
            INVESTIGATION_PROMPT,
            DOSSIER_PROMPT,
        )
        from .tools_investigation_travel import INVESTIGATION_TOOLS
        from .tools_dossier_travel import DOSSIER_TOOLS, clear_tool_cache
    else:
        from .prompts import (
            ORCHESTRATOR_PROMPT,
            INVESTIGATION_PROMPT,
            DOSSIER_PROMPT,
        )
        from .tools_investigation import INVESTIGATION_TOOLS
        from .tools_dossier import DOSSIER_TOOLS, clear_tool_cache
except ImportError:
    ORCHESTRATOR_PROMPT = INVESTIGATION_PROMPT = DOSSIER_PROMPT = ""
    INVESTIGATION_TOOLS = DOSSIER_TOOLS = []
    def clear_tool_cache(): pass
# Note: ORCHESTRATOR_PROMPT uses .format() with current_phase, loop_count, findings_summary


# ============================================================================
# State Definition
# ============================================================================

class InvestigationState(TypedDict):
    """State for the investigation workflow."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_phase: str  # scan / investigate / compile / done
    findings: dict
    dossier: str
    evidence_sufficient: bool
    loop_count: int
    compile_loop_count: int


# ============================================================================
# LLM Setup
# ============================================================================

class LLMInputLogger(BaseCallbackHandler):
    """Callback handler that logs every LLM call input."""
    
    def __init__(self, agent_name: str = "LLM"):
        self.agent_name = agent_name
        self.call_count = 0
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Log when LLM starts with prompts (older interface)."""
        self.call_count += 1
        _log(self.agent_name, f'>>> LLM Call #{self.call_count} (prompts interface)')
        total_chars = 0
        for i, prompt in enumerate(prompts):
            chars = len(prompt)
            total_chars += chars
            formatted = prompt.replace('\n', ' ') if prompt else '(empty)'
            _log(self.agent_name, f'  Prompt[{i}]: {chars} chars | "{formatted}"')
        _log(self.agent_name, f'>>> Total prompt chars: {total_chars}')
    
    def on_chat_model_start(self, serialized, messages, **kwargs):
        """Log when chat model starts with messages (newer interface)."""
        self.call_count += 1
        _log(self.agent_name, f'>>> LLM Call #{self.call_count} (messages interface, {len(messages)} message groups)')
        
        total_chars = 0
        for group_idx, msg_group in enumerate(messages):
            _log(self.agent_name, f'  Group[{group_idx}]: {len(msg_group)} messages')
            for msg_idx, msg in enumerate(msg_group):
                msg_type = type(msg).__name__
                content = ""
                if hasattr(msg, 'content'):
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                chars = len(content)
                total_chars += chars
                formatted = content.replace('\n', ' ') if content else "(empty)"
                _log(self.agent_name, f'    [{msg_idx}] {msg_type}: {chars} chars | "{formatted}"')
                
                # Log tool calls if present
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tc_str = str(tc)
                        total_chars += len(tc_str)
                        _log(self.agent_name, f'        -> tool_call: {tc_str}')
        
        _log(self.agent_name, f'>>> Total input chars: {total_chars}')
        if total_chars > 15000:
            _log(self.agent_name, f'!!! DANGER: {total_chars} chars likely exceeds context window !!!')


def get_bedrock_llm(temperature: float = 0.1, max_tokens: int = 4096, agent_name: str = "LLM"):
    """Get AWS Bedrock Claude 3 Sonnet instance using Converse API."""
    import os
    model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
    region = os.getenv('AWS_REGION', 'us-east-1')
    return ChatBedrockConverse(
        model=model_id,
        temperature=temperature,
        max_tokens=max_tokens,
        region_name=region,
        callbacks=[LLMInputLogger(agent_name)],
    )


# ============================================================================
# Agent Nodes
# ============================================================================

def _extract_text(content) -> str:
    """Extract text from message content (handles str or list format)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get('type') == 'text':
                parts.append(block.get('text', ''))
        return '\n'.join(parts)
    return str(content)


def orchestrator_node(state: InvestigationState) -> InvestigationState:
    """
    Lead Investigator - Coordinates the investigation.
    No tools - just routing and decision making.
    """
    loop = state.get('loop_count', 0) + 1
    current_phase = state.get('current_phase', 'scan')
    _log('Orchestrator', f'--- Iteration {loop} | Current phase: {current_phase} ---')
    _log('Orchestrator', 'Calling LLM for routing decision...')
    t0 = time.time()

    llm = get_bedrock_llm(temperature=0.1, agent_name='Orchestrator')
    
    # Build findings summary for the orchestrator to see
    findings = state.get('findings', {})
    findings_summary = ''
    if findings.get('last_investigation'):
        findings_summary = f"## Previous Investigation Findings:\n{findings.get('last_investigation', '')}"
    
    # Build prompt with current state
    system_prompt = ORCHESTRATOR_PROMPT.format(
        current_phase=current_phase,
        loop_count=state.get('loop_count', 0),
        findings_summary=findings_summary
    )
    
    # Get messages - filter to only HumanMessage and AIMessage (no tool calls)
    messages = state.get('messages', [])
    clean_messages = [
        m for m in messages
        if isinstance(m, (HumanMessage, AIMessage)) and not getattr(m, 'tool_calls', None)
    ]
    
    # Add system message
    full_messages = [SystemMessage(content=system_prompt)] + clean_messages
    
    # Get LLM response
    response = llm.invoke(full_messages)
    elapsed = time.time() - t0
    _log('Orchestrator', f'LLM responded in {elapsed:.1f}s')
    
    # Parse response to determine next phase
    response_text = _extract_text(response.content)
    response_lower = response_text.lower()
    
    # Determine phase transitions - first check for explicit NEXT_PHASE directive
    new_phase = current_phase
    
    # 1) Explicit NEXT_PHASE directives from the LLM (highest priority)
    if 'next_phase: done' in response_lower:
        new_phase = 'done'
    elif 'next_phase: compile' in response_lower:
        new_phase = 'compile'
    elif 'next_phase: investigate' in response_lower:
        new_phase = 'investigate'
    # 2) Evidence already marked sufficient -> we're done
    elif state.get('evidence_sufficient'):
        new_phase = 'done'
    # 3) If we just compiled but evidence is INSUFFICIENT -> back to investigate
    elif current_phase == 'compile' and state.get('dossier') and not state.get('evidence_sufficient'):
        _log('Orchestrator', 'Evidence INSUFFICIENT - looping back to investigation')
        new_phase = 'investigate'
    # 4) Dossier generated AND sufficient -> we're done
    elif current_phase == 'compile' and state.get('dossier') and state.get('evidence_sufficient'):
        new_phase = 'done'
    elif current_phase == 'scan' or current_phase == 'start':
        new_phase = 'investigate'
    elif current_phase == 'investigate' and findings.get('last_investigation'):
        # Have findings -> advance to compile
        new_phase = 'compile'
    
    # Safety net: if we've been investigating for 4+ loops with findings, force compile
    if new_phase == 'investigate' and loop >= 4 and findings.get('last_investigation'):
        _log('Orchestrator', f'Safety net: {loop} loops with findings, forcing compile')
        new_phase = 'compile'
    
    # Safety net: if we've been in compile phase and it's been 2+ loops IN compile, force done
    # Only count loops that were actually in compile phase
    compile_loop_count = state.get('compile_loop_count', 0)
    if current_phase == 'compile':
        compile_loop_count += 1
    # Do NOT reset on non-compile phases — accumulate across all iterations
    
    if new_phase == 'compile' and compile_loop_count >= 2:
        _log('Orchestrator', f'Safety net: {compile_loop_count} compile loops, forcing done')
        new_phase = 'done'
    
    _log('Orchestrator', f'Phase transition: {current_phase} -> {new_phase}')

    # Update state
    return {
        'messages': [response],
        'current_phase': new_phase,
        'findings': state.get('findings', {}),
        'dossier': state.get('dossier', ''),
        'evidence_sufficient': state.get('evidence_sufficient', False),
        'loop_count': loop,
        'compile_loop_count': compile_loop_count
    }


# Investigation Agent with tools
investigation_agent = None
dossier_agent = None

def clear_agent_caches():
    """Clear cached agents so they are recreated with fresh prompts."""
    global investigation_agent, dossier_agent
    investigation_agent = None
    dossier_agent = None

def get_investigation_agent():
    """Get or create the investigation agent."""
    global investigation_agent
    if investigation_agent is None:
        llm = get_bedrock_llm(temperature=0.1, max_tokens=4096, agent_name='Investigation')
        investigation_agent = create_react_agent(
            llm,
            INVESTIGATION_TOOLS,
            prompt=INVESTIGATION_PROMPT
        )
    return investigation_agent


def investigation_node(state: InvestigationState) -> InvestigationState:
    """
    Detective Agent - Uses 7 tools to investigate fraud.
    """
    _log('Investigation', 'Starting investigation sub-agent (7 tools available)...')
    t0 = time.time()
    agent = get_investigation_agent()
    
    # Get the last orchestrator message
    messages = state.get('messages', [])
    last_message = messages[-1] if messages else HumanMessage(content="Scan for high anomaly providers")
    
    # Ensure we pass a clean HumanMessage to the sub-agent
    if isinstance(last_message, AIMessage):
        last_message = HumanMessage(content=_extract_text(last_message.content))
    
    # Include prior findings so the sub-agent has context from previous iterations
    findings = state.get('findings', {})
    prior = findings.get('last_investigation', '')
    evidence_gaps = findings.get('evidence_gaps', '')

    # First run: always force a real scan — never let orchestrator hallucinations seed fake IDs
    if not prior:
        last_message = HumanMessage(
            content=(
                "Use the scan_suspicious_entities tool first to identify real high-anomaly agents. "
                "Only use agent IDs returned by that scan for all subsequent tool calls. "
                "Do NOT invent or assume any agent IDs."
            )
        )

    if prior:
        # Truncate prior findings to avoid exceeding model context window
        truncated_prior = _truncate_text(prior, MAX_PRIOR_FINDINGS, "prior findings")
        
        context_msg = (
            f"## Prior Investigation Findings (do NOT repeat this work):\n{truncated_prior}\n\n"
        )
        if evidence_gaps:
            truncated_gaps = _truncate_text(evidence_gaps, MAX_EVIDENCE_GAPS, "evidence gaps")
            context_msg += (
                f"## EVIDENCE GAPS (the dossier agent rejected the first investigation):\n"
                f"{truncated_gaps}\n\n"
                f"You MUST address these gaps. Focus on gathering the MISSING evidence listed above.\n\n"
            )
        context_msg += f"## New Instructions from Lead Investigator:\n{_extract_text(last_message.content)}"
        # Final truncation of entire context message
        context_msg = _truncate_text(context_msg, MAX_MESSAGE_LENGTH, "context message")
        last_message = HumanMessage(content=context_msg)
    else:
        # Even without prior findings, truncate the message if needed
        msg_content = _extract_text(last_message.content) if hasattr(last_message, 'content') else str(last_message)
        if len(msg_content) > MAX_MESSAGE_LENGTH:
            last_message = HumanMessage(content=_truncate_text(msg_content, MAX_MESSAGE_LENGTH, "input message"))
    
    _log('Investigation', 'Invoking LLM + tool loop (this may take a while)...')
    _log('Investigation', f'Initial message to agent: {len(last_message.content)} chars')
    _log('Investigation', f'Message preview: {last_message.content[:200]}...')
    # Run the agent with safe invocation
    result = _safe_agent_invoke(
        agent,
        [last_message],
        'Investigation',
        "Investigation could not complete analysis. Recommend proceeding with available evidence."
    )
    elapsed = time.time() - t0
    
    # Extract findings from agent messages
    agent_messages = result.get('messages', [])
    
    # Count tool calls made
    tool_call_count = sum(
        1 for m in agent_messages
        if isinstance(m, AIMessage) and getattr(m, 'tool_calls', None)
    )
    _log('Investigation', f'Sub-agent finished in {elapsed:.1f}s | Tool calls made: {tool_call_count}')
    
    # Store findings
    findings = state.get('findings', {})
    
    # Extract the final text summary from the agent's last AIMessage
    summary = ''
    for msg in reversed(agent_messages):
        if isinstance(msg, AIMessage) and msg.content and not getattr(msg, 'tool_calls', None):
            summary = _extract_text(msg.content)
            break
    
    if summary:
        findings['last_investigation'] = summary
        # Print a short preview
        preview = summary[:200].replace('\n', ' ')
        _log('Investigation', f'Summary preview: {preview}...')
    
    # Return only a clean summary message to the shared state
    return {
        'messages': [AIMessage(content=f"[Investigation Agent Report]\n\n{summary}")] if summary else [],
        'current_phase': state.get('current_phase', 'investigate'),
        'findings': findings,
        'dossier': state.get('dossier', ''),
        'evidence_sufficient': state.get('evidence_sufficient', False),
        'loop_count': state.get('loop_count', 0),
        'compile_loop_count': state.get('compile_loop_count', 0)
    }


# Dossier Agent with tools

def get_dossier_agent():
    """Get or create the dossier agent."""
    global dossier_agent
    if dossier_agent is None:
        llm = get_bedrock_llm(temperature=0.1, max_tokens=4096, agent_name='Dossier')
        dossier_agent = create_react_agent(
            llm,
            DOSSIER_TOOLS,
            prompt=DOSSIER_PROMPT
        )
    return dossier_agent


def dossier_node(state: InvestigationState) -> InvestigationState:
    """
    Case Writer Agent - Assesses evidence and compiles dossier.
    """
    _log('Dossier', 'Starting dossier sub-agent (5 tools available)...')
    t0 = time.time()
    
    # Clear tool output cache from any previous run
    clear_tool_cache()
    
    agent = get_dossier_agent()
    
    # Get context from findings
    findings = state.get('findings', {})
    findings_summary = str(findings)
    _log('Dossier', f'Findings payload size: {len(findings_summary)} chars')

    # Truncate findings if too large to avoid context window overflow
    if len(findings_summary) > MAX_FINDINGS_LENGTH:
        findings_summary = _truncate_text(findings_summary, MAX_FINDINGS_LENGTH, "findings")

    # Include the original claim context so the dossier can compile even if the
    # investigation tools returned no results (e.g. travel claims crashing scan tool).
    original_claim_context = ""
    for msg in state.get('messages', []):
        if isinstance(msg, HumanMessage):
            original_claim_context = _truncate_text(
                _extract_text(msg.content), 2000, "original claim context"
            )
            break

    dossier_input = f"Assess the following investigation findings and compile a dossier:\n\n{findings_summary}"
    _sparse_signals = ("Investigation could not complete", "DataContext not initialised", "initialization error", "not initialized")
    if original_claim_context and any(s in findings_summary for s in _sparse_signals):
        dossier_input += (
            f"\n\n## Original Claim Context (use this to compile the dossier if investigation data is sparse):\n"
            f"{original_claim_context}"
        )

    # Create message for dossier agent
    dossier_message = HumanMessage(content=dossier_input)
    
    _log('Dossier', 'Invoking LLM + tool loop (evidence assessment & compilation)...')
    _log('Dossier', f'Initial message to agent: {len(dossier_message.content)} chars')
    _log('Dossier', f'Message preview: {dossier_message.content[:200]}...')
    # Run the agent with safe invocation
    result = _safe_agent_invoke(
        agent,
        [dossier_message],
        'Dossier',
        "# FRAUD INVESTIGATION DOSSIER\n\n**Status:** INSUFFICIENT EVIDENCE\n\nUnable to complete analysis due to context limitations. Please retry with a fresh investigation."
    )
    elapsed = time.time() - t0
    
    # Extract dossier and assessment from the agent's messages
    agent_messages = result.get('messages', [])
    tool_call_count = sum(
        1 for m in agent_messages
        if isinstance(m, AIMessage) and getattr(m, 'tool_calls', None)
    )
    _log('Dossier', f'Sub-agent finished in {elapsed:.1f}s | Tool calls made: {tool_call_count}')

    dossier_content = ''
    evidence_sufficient = False
    
    # FIRST: Look for the compile_dossier ToolMessage - this has the actual markdown
    for msg in reversed(agent_messages):
        if isinstance(msg, ToolMessage):
            # Check if this is from compile_dossier by looking at the content
            content = _extract_text(msg.content) if msg.content else ''
            if any(kw in content[:150] for kw in ['INVESTIGATION DOSSIER', 'SUPPLEMENTAL HEALTH', 'FRAUD DOSSIER', 'DEPENDENT FRAUD', 'PROVIDER MILL', 'TRAVEL', 'ZURICH', 'BAGGAGE', 'EXECUTIVE SUMMARY']):
                dossier_content = content
                _log('Dossier', f'Found compile_dossier output: {len(dossier_content)} chars')
                break
    
    # FALLBACK: If no compile_dossier result found, use the last AIMessage
    if not dossier_content:
        for msg in reversed(agent_messages):
            if isinstance(msg, AIMessage) and msg.content and not getattr(msg, 'tool_calls', None):
                dossier_content = _extract_text(msg.content)
                _log('Dossier', f'Using AIMessage fallback: {len(dossier_content)} chars')
                break
    
    # Check tool messages for assess_evidence result — used when fallback fires
    # and the dossier text doesn't contain SUFFICIENT/INSUFFICIENT keywords.
    assess_evidence_sufficient = False
    for msg in agent_messages:
        if isinstance(msg, ToolMessage) and msg.content:
            tool_content = _extract_text(msg.content) if msg.content else ''
            try:
                tool_json = json.loads(tool_content)
                if isinstance(tool_json, dict) and tool_json.get('assessment') == 'SUFFICIENT':
                    assess_evidence_sufficient = True
                    _log('Dossier', 'assess_evidence tool returned SUFFICIENT (used for fallback check)')
                    break
            except Exception:
                pass

    if dossier_content:
        # Check if evidence was assessed as sufficient.
        # Strip leading agent wrapper labels before checking keywords so that
        # "[Dossier Agent: INSUFFICIENT EVIDENCE]" doesn't poison a real dossier.
        check_content = dossier_content
        for strip_prefix in ('[Dossier Agent: INSUFFICIENT EVIDENCE]', '[Dossier Agent:'):
            if check_content.startswith(strip_prefix):
                check_content = check_content[check_content.find('\n')+1:].lstrip()
                break
        content_upper = check_content.upper()
        # IMPORTANT: check for INSUFFICIENT first — "SUFFICIENT" is a substring of "INSUFFICIENT"
        if 'INSUFFICIENT' in content_upper or 'NOT SUFFICIENT' in content_upper or 'INCOMPLETE' in content_upper:
            evidence_sufficient = False
            _log('Dossier', 'Evidence assessed as INSUFFICIENT - looping back to investigation')
        elif 'SUFFICIENT' in content_upper:
            evidence_sufficient = True
            _log('Dossier', 'Evidence assessed as SUFFICIENT')
        elif assess_evidence_sufficient:
            # Fallback text has no SUFFICIENT keyword but the tool confirmed it — trust the tool
            evidence_sufficient = True
            _log('Dossier', 'Evidence assessment unclear in text but assess_evidence returned SUFFICIENT — treating as sufficient')
        else:
            _log('Dossier', 'Evidence assessment unclear - treating as INSUFFICIENT')
        _log('Dossier', f'Dossier length: {len(dossier_content)} chars')
    
    if evidence_sufficient:
        # Evidence is good — finalize the dossier and end
        next_phase = 'done'
        _log('Dossier', f'Setting next phase -> {next_phase}')
        return {
            'messages': [AIMessage(content=f"[Dossier Agent Report]\n\n{dossier_content}")] if dossier_content else [],
            'current_phase': next_phase,
            'findings': findings,
            'dossier': dossier_content,
            'evidence_sufficient': True,
            'loop_count': state.get('loop_count', 0),
            'compile_loop_count': state.get('compile_loop_count', 0)
        }
    else:
        # Evidence is INSUFFICIENT — loop back to investigation
        # DO NOT put the "go gather more evidence" text in the dossier field
        # Instead, pass the gaps through findings so the investigator knows what to look for
        next_phase = 'investigate'
        _log('Dossier', f'Setting next phase -> {next_phase} (evidence gaps forwarded to investigator)')
        findings['evidence_gaps'] = dossier_content  # What's missing
        return {
            'messages': [AIMessage(content=f"[Dossier Agent: INSUFFICIENT EVIDENCE]\n\nLooping back to investigation. Gaps identified:\n\n{dossier_content}")],
            'current_phase': next_phase,
            'findings': findings,
            'dossier': '',  # Don't set dossier — nothing to show the user yet
            'evidence_sufficient': False,
            'loop_count': state.get('loop_count', 0),
            'compile_loop_count': state.get('compile_loop_count', 0)
        }
