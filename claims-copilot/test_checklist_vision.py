"""Quick test: run full checklist for COL-107 and confirm the car fraud checklist runs."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import initialize_car_data
from agents.tools_car import set_context, run_fraud_checklist

print("Loading context...")
ctx = initialize_car_data()
set_context(ctx)

print()
print("=== Running full checklist for COL-107 ===")
result = run_fraud_checklist("COL-107")

ICONS = {"pass": "✅", "needs_review": "🟡", "fail": "❌", "error": "⛔"}
for step in result["steps"]:
    icon = ICONS.get(step["status"], "?")
    print(f"  {icon} Step {step['step']} — {step['name']}: {step['status'].upper()}")
    for f in step.get("issues", []):
        print(f"       {f}")

print()
print(f"Summary: {result['passed']} passed · {result['needs_review']} needs review · {result['failed']} failed")
print(f"Recommendation: {result['recommendation']}")
