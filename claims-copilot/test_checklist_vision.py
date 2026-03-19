"""Quick test: run full checklist for WC-247 and confirm vision runs in Step 5."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import initialize_data
from agents.tools_supplemental import set_context, run_fraud_checklist

print("Loading context...")
ctx = initialize_data()
set_context(ctx)

print()
print("=== Running full checklist for WC-247 ===")
result = run_fraud_checklist("WC-247")

doc_source = result.get("document_analysis_source", "unknown")
print(f"Document analysis source: {doc_source}")
print()

ICONS = {"pass": "✅", "needs_review": "🟡", "fail": "❌", "error": "⛔"}
for step in result["steps"]:
    icon = ICONS.get(step["status"], "?")
    print(f"  {icon} Step {step['step_number']} — {step['step_name']}: {step['status'].upper()}")
    for f in step["findings"]:
        print(f"       {f}")

print()
s = result["summary"]
print(f"Summary: {s['passed']} passed · {s['needs_review']} needs review · {s['failed']} failed")
