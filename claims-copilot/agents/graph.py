"""
LangGraph State Machine - Wires the 3 agents together
"""

import time
from datetime import datetime
from langgraph.graph import StateGraph, END
from .nodes import (
    InvestigationState,
    orchestrator_node,
    investigation_node,
    dossier_node
)


def route_after_orchestrator(state: InvestigationState) -> str:
    """
    Determine where to go after orchestrator decision.
    
    Routes:
    - "investigation" if phase is scan or investigate
    - "dossier" if phase is compile
    - "end" if phase is done
    """
    phase = state.get('current_phase', 'investigate')
    
    if phase in ['scan', 'investigate']:
        return 'investigation'
    elif phase == 'compile':
        return 'dossier'
    elif phase == 'done':
        return 'end'
    else:
        return 'investigation'


def route_after_dossier(state: InvestigationState) -> str:
    """
    Determine where to go after dossier agent.
    
    Always returns to orchestrator to decide:
    - If evidence sufficient -> orchestrator will end
    - If insuffient -> orchestrator sends back to investigation
    """
    return 'orchestrator'


def create_investigation_graph():
    """
    Create the LangGraph workflow for fraud investigation.
    
    Flow:
        START 
          ↓
        orchestrator ←─────────────┐
          ↓│  │                     │
          │  │ (route)             │
          │  │                     │
          │  ├→ investigation ─────┤
          │  │                     │  
          │  └→ dossier ───────────┘
          │
          ↓
        END
    """
    
    # Create graph
    graph = StateGraph(InvestigationState)
    
    # Add nodes
    graph.add_node('orchestrator', orchestrator_node)
    graph.add_node('investigation', investigation_node)
    graph.add_node('dossier', dossier_node)
    
    # Set entry point
    graph.set_entry_point('orchestrator')
    
    # Add edges
    
    # Orchestrator routes to investigation, dossier, or END
    graph.add_conditional_edges(
        'orchestrator',
        route_after_orchestrator,
        {
            'investigation': 'investigation',
            'dossier': 'dossier',
            'end': END
        }
    )
    
    # Investigation always returns to orchestrator
    graph.add_edge('investigation', 'orchestrator')
    
    # Dossier always returns to orchestrator (who decides to end or continue)
    graph.add_edge('dossier', 'orchestrator')
    
    # Compile the graph
    app = graph.compile()
    
    return app


def run_investigation(initial_query: str = "Investigate suspicious billing patterns", max_iterations: int = 10):
    """
    Run a fraud investigation using the agent graph.
    
    Args:
        initial_query: Starting prompt for the investigation
        max_iterations: Maximum number of loop iterations (safety limit)
    
    Returns:
        Final state with findings and dossier
    """
    from langchain_core.messages import HumanMessage
    
    app = create_investigation_graph()
    
    # Initial state
    initial_state = {
        'messages': [HumanMessage(content=initial_query)],
        'current_phase': 'start',
        'findings': {},
        'dossier': '',
        'evidence_sufficient': False,
        'loop_count': 0,
        'compile_loop_count': 0
    }
    
    # Run the graph
    final_state = None
    iterations = 0
    graph_start = time.time()
    
    print(f"\n{'─' * 60}")
    print(f"  AGENT GRAPH STARTED at {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'─' * 60}\n")
    
    for state in app.stream(initial_state):
        iterations += 1
        final_state = state
        elapsed = time.time() - graph_start
        
        # Print high-level node transitions
        if 'orchestrator' in state:
            current_phase = state['orchestrator'].get('current_phase', 'unknown')
            loop_count = state['orchestrator'].get('loop_count', 0)
            print(f"\n{'=' * 60}")
            print(f"  ORCHESTRATOR complete | Phase -> {current_phase} | Loop {loop_count} | +{elapsed:.0f}s")
            print(f"{'=' * 60}")
        elif 'investigation' in state:
            print(f"\n{'=' * 60}")
            print(f"  INVESTIGATION AGENT complete | +{elapsed:.0f}s")
            print(f"{'=' * 60}")
        elif 'dossier' in state:
            sufficient = state['dossier'].get('evidence_sufficient', False)
            print(f"\n{'=' * 60}")
            print(f"  DOSSIER AGENT complete | Evidence sufficient: {sufficient} | +{elapsed:.0f}s")
            print(f"{'=' * 60}")
        
        # Safety check
        if iterations >= max_iterations:
            print(f"\n⚠️  Reached max iterations ({max_iterations})")
            break
        
        # Check if done
        current_state = list(state.values())[0]
        if current_state.get('current_phase') == 'done':
            break
    
    total = time.time() - graph_start
    print(f"\n{'─' * 60}")
    print(f"  AGENT GRAPH FINISHED | {iterations} node steps | {total:.1f}s total")
    print(f"{'─' * 60}\n")
    
    return final_state


if __name__ == "__main__":
    # Test the graph structure
    app = create_investigation_graph()
    print("Investigation graph created successfully!")
    print(f"Nodes: {app.get_graph().nodes}")
