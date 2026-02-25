"""
Agents module for Claims Investigation Copilot.
Contains LangGraph agent definitions, tools, and prompts.
"""

from .graph import create_investigation_graph, run_investigation
from .nodes import InvestigationState
from .tools_investigation import INVESTIGATION_TOOLS, set_context as set_investigation_context
from .tools_dossier import DOSSIER_TOOLS, set_context as set_dossier_context

__all__ = [
    'create_investigation_graph',
    'run_investigation',
    'InvestigationState',
    'INVESTIGATION_TOOLS',
    'DOSSIER_TOOLS',
    'set_investigation_context',
    'set_dossier_context',
]
