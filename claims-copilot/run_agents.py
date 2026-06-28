"""
Run Claims Investigation Agents

This script:
1. Initializes the data foundation (from main.py)
2. Sets up agent tools with data context
3. Runs the LangGraph agent workflow
4. Outputs the final dossier
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import initialize_car_data as initialize_data
from agents.tools_investigation_car import set_context as set_investigation_context
from agents.tools_dossier_car import set_context as set_dossier_context
from agents.graph import run_investigation


def main():
    """Run the full investigation with AI agents."""
    
    print("=" * 70)
    print("CLAIMS INVESTIGATION COPILOT - AI Agent Investigation")
    print("=" * 70)
    
    run_start = time.time()

    # Step 1: Initialize data
    print("\n[1/3] Initializing data foundation...")
    t0 = time.time()
    ctx = initialize_data()
    print(f"     Data loaded in {time.time()-t0:.1f}s")
    
    # Step 2: Set context for agent tools
    print("\n[2/3] Configuring AI agents...")
    set_investigation_context(ctx)
    set_dossier_context(ctx)
    print("✓ Investigation tools connected to data")
    print("✓ Dossier tools connected to data")
    print("✓ AWS Bedrock Claude 4.5 Sonnet configured")
    
    # Step 3: Run investigation
    print("\n[3/3] Starting AI agent investigation...")
    print("=" * 70)
    
    initial_query = """
    Investigate the claims data for potential fraud. Start by scanning for 
    high-anomaly providers, then profile the top suspicious entities, analyze 
    their connections, and compile a complete dossier if evidence is sufficient.
    """
    
    final_state = run_investigation(initial_query, max_iterations=20)
    
    total_time = time.time() - run_start
    # Extract results
    print("\n" + "=" * 70)
    print(f"INVESTIGATION COMPLETE  (total wall time: {total_time:.1f}s)")
    print("=" * 70)
    
    if final_state:
        # Get the last state value
        last_state = list(final_state.values())[-1] if final_state else {}
        
        print(f"\nFinal Phase: {last_state.get('current_phase', 'unknown')}")
        print(f"Total Iterations: {last_state.get('loop_count', 0)}")
        print(f"Evidence Sufficient: {last_state.get('evidence_sufficient', False)}")
        
        # Print dossier if available
        dossier = last_state.get('dossier', '')
        if dossier:
            print("\n" + "=" * 70)
            print("FINAL DOSSIER")
            print("=" * 70)
            print(dossier)
            
            # Save to file
            with open('investigation_dossier.md', 'w') as f:
                f.write(dossier)
            print("\n✓ Dossier saved to: investigation_dossier.md")
        
        # Print findings
        findings = last_state.get('findings', {})
        if findings:
            print("\n" + "=" * 70)
            print("KEY FINDINGS")
            print("=" * 70)
            for key, value in findings.items():
                print(f"\n{key}:")
                print(str(value)[:500])  # Truncate long findings
    
    print("\n" + "=" * 70)
    print("Investigation workflow completed!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInvestigation interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
