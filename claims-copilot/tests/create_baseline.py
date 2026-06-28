"""One-time script: generate the golden baseline fixture.

Run from the claims-copilot/ directory:
    python tests/create_baseline.py

Produces tests/fixtures/golden_baseline.json with the hero-case snapshots for
COL-107, THEFT-009, and LIAB-021. Every subsequent workstream must produce
byte-identical results for those three claims — if the numbers drift, the
regression gate (test_golden_baseline.py) will catch it.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import initialize_car_data

HERO_CLAIM_IDS = ["COL-107", "THEFT-009", "LIAB-021"]


def _snapshot_claim(claim_id: str, ctx) -> dict:
    risk = ctx.claim_risk_scores.get(claim_id)
    rules = ctx.claim_rules.get(claim_id, [])

    triggered_rule_ids = sorted(r.rule_id for r in rules if r.triggered)

    # Queue position (0-based index in the sorted case_queue)
    queue_pos = next(
        (i for i, c in enumerate(ctx.case_queue) if c.case_id == claim_id), None
    )

    return {
        "claim_id": claim_id,
        "risk_score": risk.total_score if risk else None,
        "risk_tier": risk.tier if risk else None,
        "rules_boost": risk.rules_boost if risk else None,
        "triggered_rule_ids": triggered_rule_ids,
        "queue_position": queue_pos,
    }


def main():
    fixture_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
    os.makedirs(fixture_dir, exist_ok=True)
    fixture_path = os.path.join(fixture_dir, "golden_baseline.json")

    ctx = initialize_car_data(force_regenerate=True)

    snapshots = {}
    for cid in HERO_CLAIM_IDS:
        snap = _snapshot_claim(cid, ctx)
        snapshots[cid] = snap
        print(f"  {cid}: score={snap['risk_score']}, tier={snap['risk_tier']}, "
              f"rules={snap['triggered_rule_ids']}, queue_pos={snap['queue_position']}")

    # Also capture total queue length and tier distribution as a sanity check
    meta = {
        "total_cases": len(ctx.case_queue),
        "tier_counts": {
            "HIGH": sum(1 for c in ctx.case_queue if c.risk_score >= 60),
            "MEDIUM": sum(1 for c in ctx.case_queue if 30 <= c.risk_score < 60),
            "LOW": sum(1 for c in ctx.case_queue if c.risk_score < 30),
        },
        "top10_queue_ids": [c.case_id for c in ctx.case_queue[:10]],
    }

    output = {"meta": meta, "hero_cases": snapshots}
    with open(fixture_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Baseline written to {fixture_path}")


if __name__ == "__main__":
    main()
