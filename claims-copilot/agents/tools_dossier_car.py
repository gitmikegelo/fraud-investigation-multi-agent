"""
Dossier Agent Tools (Car) — 5 tools for evidence assessment and case compilation
for Car Insurance. Mirrors the travel dossier tools but with auto regulatory rules
(AU-xxx), auto precedent cases, and an auto-themed dossier.
"""

import json
from typing import List, Dict, Annotated
from datetime import datetime


MAX_TOOL_OUTPUT_CHARS = 2000


def _tool_log(name: str, msg: str):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"    [{ts}]   tool:{name} -> {msg}", flush=True)


def _truncate_tool_output(data, max_chars=MAX_TOOL_OUTPUT_CHARS):
    if isinstance(data, list) and len(data) > 3:
        data = data[:3]
    if isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, str) and len(val) > 500:
                data[key] = val[:500] + '...[truncated]'
            elif isinstance(val, list) and len(val) > 3:
                data[key] = val[:3]
    try:
        if len(json.dumps(data, default=str)) > max_chars:
            return {"summary": "Output truncated due to size",
                    "item_count": len(data) if isinstance(data, list) else 1}
    except Exception:
        pass
    return data


# ---------------------------------------------------------------------------
_context = None
_tool_cache = {'regulatory_rules': None, 'similar_cases': None, 'recovery_estimate': None}


def set_context(ctx):
    global _context
    _context = ctx


def clear_tool_cache():
    global _tool_cache
    _tool_cache = {'regulatory_rules': None, 'similar_cases': None, 'recovery_estimate': None}


# =========================================================================
# 1.  assess_evidence
# =========================================================================
def assess_evidence(
    hypothesis: Annotated[str, "Suspected scheme (e.g. 'inflated estimate', 'staged theft')"],
    evidence: Annotated[List[str], "List of evidence points gathered"],
    scheme_pattern: Annotated[str, "Pattern: inflated_estimate, staged_theft, repair_shop_ring, serial_claimer, pre_existing_damage"],
) -> Dict:
    """
    Check if gathered evidence meets sufficiency criteria for escalation.
    MUST be called BEFORE compile_dossier.
    """
    _tool_log('assess_evidence', f'Assessing "{hypothesis}" ({len(evidence)} points)...')
    checks_passed, checks_failed, missing = [], [], []
    all_text = ' '.join(str(e).lower() for e in evidence)

    if len(evidence) >= 3:
        checks_passed.append("multiple_evidence_points")
    else:
        checks_failed.append("multiple_evidence_points")
        missing.append(f"Need >= 3 independent evidence points (have {len(evidence)}). "
                       "Profile additional entities or compare claim amounts to peers.")

    stat_kw = ['z-score', 'z_score', 'z=', 'standard deviation', 'anomaly', 'peer',
               'sigma', 'comparison', 'average', 'mean', 'risk_score', 'risk score', 'acv']
    if any(kw in all_text for kw in stat_kw):
        checks_passed.append("statistical_significance")
    else:
        checks_failed.append("statistical_significance")
        missing.append("Need statistical comparison to peers. Call compare_to_peers() on "
                       "claim_amount or claim_count and report the z-score, or compare to vehicle ACV.")

    temporal_kw = ['month', 'timeline', 'date', 'period', 'spike', 'incident',
                   'effective', 'coverage', 'history', 'before', 'after', 'filed', 'pattern', 'trend']
    if any(kw in all_text for kw in temporal_kw):
        checks_passed.append("temporal_pattern")
    else:
        checks_failed.append("temporal_pattern")
        missing.append("Need temporal analysis: compare incident date vs. policy effective date, "
                       "or claim filing dates relative to a coverage change.")

    if any(kw in scheme_pattern.lower() for kw in ['ring', 'cluster', 'network', 'shop']):
        net_kw = ['ring', 'connection', 'network', 'shop', 'density',
                  'entities', 'relationship', 'linked', 'cluster', 'watchlist']
        if any(kw in all_text for kw in net_kw):
            checks_passed.append("network_evidence")
        else:
            checks_failed.append("network_evidence")
            missing.append("Need network analysis for a ring pattern. Call find_connections() on "
                           "the target and find_ring() to surface repair-shop clusters.")

    rule_kw = ['rule', 'au-0', 'r-0', 'regulation', 'violation', 'triggered', 'severity', 'policy']
    if any(kw in all_text for kw in rule_kw):
        checks_passed.append("regulatory_citation")
    else:
        checks_failed.append("regulatory_citation")
        missing.append("Need regulatory context. Call search_regulatory_rules() to find "
                       "applicable AU-001 through AU-006 auto rules.")

    if any(kw in scheme_pattern.lower() for kw in ['estimate', 'padding', 'document', 'photo', 'damage']):
        doc_kw = ['photo', 'estimate', 'document', 'staged', 'metadata', 'manipulat',
                  'damage', 'screenshot', 'forged', 'altered', 'tampering', 'acv']
        if any(kw in all_text for kw in doc_kw):
            checks_passed.append("document_evidence")
        else:
            checks_failed.append("document_evidence")
            missing.append("Need evidence-image findings. Review the claim's damage-photo / estimate "
                           "vision checks (staged damage, inflated line items, ACV mismatch).")

    critical = ["multiple_evidence_points", "statistical_significance", "temporal_pattern"]
    critical_passed = all(c in checks_passed for c in critical)
    assessment = "SUFFICIENT" if (critical_passed and len(checks_failed) <= 1 and len(evidence) >= 4) else "INSUFFICIENT"

    _tool_log('assess_evidence', f'Result: {assessment} ({len(checks_passed)} passed, {len(checks_failed)} failed)')
    return {
        "assessment": assessment,
        "hypothesis": hypothesis,
        "scheme_pattern": scheme_pattern,
        "evidence_count": len(evidence),
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "missing_evidence": missing,
        "recommendation": ("Proceed to compile dossier" if assessment == "SUFFICIENT"
                           else "Gather additional evidence before proceeding"),
    }


# =========================================================================
# 2.  search_regulatory_rules  (auto rules)
# =========================================================================
def search_regulatory_rules(
    claim_types: Annotated[List[str], "Claim types (collision, comprehensive, theft, liability, medical_payments)"],
    context: Annotated[str, "Description of the suspected scheme"],
) -> List[Dict]:
    """
    Search Car Insurance regulatory rules relevant to the case.
    Returns rules with section_id, title, summary, fraud_indicators, applicable_types.
    """
    _tool_log('search_regulatory_rules', f'Searching rules for types={claim_types}...')

    RULES = [
        {
            "section_id": "AU-001",
            "title": "Coverage Period — Policy Effective After Incident",
            "summary": "A policy whose effective date is after the claimed incident date is invalid "
                       "for that incident. Backdated coverage claims must be denied.",
            "fraud_indicators": [
                "Policy effective date is after the date of incident",
                "Coverage upgraded immediately before the incident",
                "Incident details known prior to coverage purchase",
            ],
            "applicable_types": ["collision", "comprehensive", "theft", "liability", "medical_payments"],
        },
        {
            "section_id": "AU-002",
            "title": "Repair Estimate Requirement",
            "summary": "Collision/comprehensive/liability benefits require a verifiable repair estimate. "
                       "Claims with no estimate must be held pending documentation.",
            "fraud_indicators": [
                "No repair estimate on file for a damage claim",
                "Estimate from an unverifiable or out-of-network shop",
                "Line items inconsistent with the reported damage",
            ],
            "applicable_types": ["collision", "comprehensive", "liability"],
        },
        {
            "section_id": "AU-003",
            "title": "Repair-Shop Watchlist & Ring Detection",
            "summary": "Estimates from watchlisted/out-of-network shops, especially shops linked to "
                       "multiple high-value claims, are flagged for ring investigation.",
            "fraud_indicators": [
                "Repair shop is on the fraud watchlist or unverified",
                "Single shop linked to many high-value claims",
                "Estimate far above comparable repairs for the damage",
            ],
            "applicable_types": ["collision", "comprehensive", "liability"],
        },
        {
            "section_id": "AU-004",
            "title": "Total-Loss / Valuation Padding",
            "summary": "Claim or estimate amounts that exceed the vehicle's actual cash value (ACV) "
                       "indicate total-loss padding and require valuation review.",
            "fraud_indicators": [
                "Claim amount exceeds the vehicle ACV",
                "Estimate > 1.1x the vehicle ACV",
                "Vehicle reported stolen shortly after a max-coverage change",
            ],
            "applicable_types": ["collision", "comprehensive", "theft"],
        },
        {
            "section_id": "AU-005",
            "title": "Serial Claimer / Staged Collision",
            "summary": "Insureds with repeated claims in a short window, especially with soft-tissue "
                       "injury components, are flagged for staged-collision review.",
            "fraud_indicators": [
                "3+ auto claims by the same insured in a short window",
                "Repetitive soft-tissue injury components",
                "Injury claimed without a corroborating police report",
            ],
            "applicable_types": ["collision", "liability", "medical_payments"],
        },
        {
            "section_id": "AU-006",
            "title": "Document & Evidence Integrity",
            "summary": "Repair estimates, police reports, and damage photos must be authentic. "
                       "Manipulated, screenshot, or template-generated documents are rejected.",
            "fraud_indicators": [
                "Estimate amounts/dates show overwriting or misalignment",
                "Police report lacks an official report number",
                "Damage photo shows staged or pre-existing damage",
                "Document appears to be a screenshot or editable template",
            ],
            "applicable_types": ["collision", "comprehensive", "theft", "liability", "medical_payments"],
        },
    ]

    ctx_lower = context.lower()
    scored = []
    for rule in RULES:
        type_match = any(ct.lower() in [t.lower() for t in rule['applicable_types']]
                         for ct in claim_types) if claim_types else True
        keywords = rule['title'].lower() + ' ' + rule['summary'].lower()
        word_hits = sum(1 for w in ctx_lower.split() if w in keywords)
        indicator_hits = sum(1 for ind in rule['fraud_indicators']
                             if any(w in ind.lower() for w in ctx_lower.split()))
        score = (5 if type_match else 0) + word_hits + indicator_hits * 2
        scored.append((score, rule))

    scored.sort(key=lambda x: -x[0])
    results = [r for s, r in scored if s > 0][:5]
    _tool_cache['regulatory_rules'] = results
    _tool_log('search_regulatory_rules', f'Found {len(results)} relevant rules')
    return _truncate_tool_output(results)


# alias for prompt compatibility
search_billing_rules = search_regulatory_rules


# =========================================================================
# 3.  find_similar_cases  (auto precedents)
# =========================================================================
def find_similar_cases(
    scheme_pattern: Annotated[str, "inflated_estimate, staged_theft, repair_shop_ring, serial_claimer"],
    specialty: Annotated[str, "Claim type if applicable"] = None,
) -> List[Dict]:
    """Find precedent auto-insurance cases with similar fraud patterns."""
    _tool_log('find_similar_cases', f'Looking up precedents for "{scheme_pattern}"...')

    CASES = {
        "inflated_estimate": [{
            "case_id": "SIU-AU-2025-0142",
            "scheme": "Inflated Repair Estimate — Watchlisted Shop",
            "entities_involved": 3, "total_claims": 11, "total_paid": 142_000,
            "summary": "A single out-of-network body shop submitted estimates averaging 1.5x the "
                       "vehicles' ACV across 11 collision claims, padding line items for undamaged panels.",
            "outcome": "Shop blacklisted, $142K demand issued, 2 insureds referred for review",
            "year": 2025,
        }],
        "staged_theft": [{
            "case_id": "SIU-AU-2024-0091",
            "scheme": "Staged Theft — Total-Loss Padding",
            "entities_involved": 1, "total_claims": 1, "total_paid": 27_000,
            "summary": "Vehicle reported stolen 6 days after a max-coverage policy change. Claim "
                       "exceeded the vehicle ACV; no forced-entry evidence and no police report.",
            "outcome": "Claim denied, insured flagged for enhanced monitoring",
            "year": 2024,
        }],
        "repair_shop_ring": [{
            "case_id": "SIU-AU-2025-0207",
            "scheme": "Repair-Shop Ring",
            "entities_involved": 9, "total_claims": 24, "total_paid": 318_000,
            "summary": "Nine insureds routed collision claims through one watchlisted shop over four "
                       "months, with staged-damage photos and duplicated line items.",
            "outcome": "Shop blacklisted, $318K under recovery review",
            "year": 2025,
        }],
        "serial_claimer": [{
            "case_id": "SIU-AU-2025-0064",
            "scheme": "Serial Claimer — Staged Collisions",
            "entities_involved": 1, "total_claims": 6, "total_paid": 88_000,
            "summary": "Insured filed 6 auto claims in 12 months, always with a soft-tissue injury "
                       "component. Claim frequency was 4.8 SD above the insured peer group.",
            "outcome": "Open claims held, policy non-renewed, $88K under recovery review",
            "year": 2025,
        }],
    }

    results = CASES.get(scheme_pattern.lower(), [])
    if not results:
        for key, val in CASES.items():
            if any(kw in scheme_pattern.lower() for kw in key.split('_')):
                results.extend(val)
        seen = set()
        results = [c for c in results if c['case_id'] not in seen and not seen.add(c['case_id'])]

    _tool_cache['similar_cases'] = results[:3]
    _tool_log('find_similar_cases', f'Found {len(results)} precedent cases')
    return _truncate_tool_output(results[:3])


# =========================================================================
# 4.  estimate_recovery
# =========================================================================
def estimate_recovery(
    flagged_claims: Annotated[List[Dict], "List of suspicious claims [{claim_id, claim_amount, ...}]"],
    peer_benchmarks: Annotated[Dict, "Peer benchmarks: {avg_claim_amount, ...}"],
) -> Dict:
    """Estimate recoverable amount from flagged auto claims."""
    _tool_log('estimate_recovery', f'Estimating recovery for {len(flagged_claims)} claims...')
    if not flagged_claims:
        return {"gross_recoverable": 0, "collectability_score": 0, "net_expected": 0}

    total_claimed = sum(float(c.get('claim_amount', c.get('amount', 0))) for c in flagged_claims)
    peer_avg = float(peer_benchmarks.get('avg_claim_amount', 0))

    if peer_avg > 0:
        entity_avg = total_claimed / len(flagged_claims)
        excess_rate = (entity_avg - peer_avg) / entity_avg if entity_avg > peer_avg else 0.10
        gross = total_claimed * excess_rate
    else:
        excess_rate = 0.15
        gross = total_claimed * excess_rate

    # Auto collectability: doc quality 0.85 · insured cooperation 0.75 · statute window 0.95
    collectability = 0.85 * 0.75 * 0.95
    net_expected = gross * collectability

    type_breakdown = {}
    for c in flagged_claims:
        ct = c.get('claim_type', c.get('type', 'unknown'))
        type_breakdown.setdefault(ct, {'count': 0, 'total': 0})
        type_breakdown[ct]['count'] += 1
        type_breakdown[ct]['total'] += float(c.get('claim_amount', c.get('amount', 0)))

    claim_breakdown = [
        {'claim_type': ct, 'claim_count': d['count'], 'total_claimed': round(d['total'], 2),
         'estimated_recovery': round(d['total'] * excess_rate * collectability, 2)}
        for ct, d in sorted(type_breakdown.items(), key=lambda x: -x[1]['total'])
    ]

    result = {
        "total_flagged_claims": len(flagged_claims),
        "total_claimed": round(total_claimed, 2),
        "peer_avg_per_claim": round(peer_avg, 2),
        "excess_rate": round(excess_rate, 2),
        "gross_recoverable": round(gross, 2),
        "collectability_score": round(collectability, 2),
        "net_expected": round(net_expected, 2),
        "claim_breakdown": claim_breakdown[:5],
    }
    _tool_cache['recovery_estimate'] = result
    _tool_log('estimate_recovery', f'Net expected recovery: ${net_expected:,.2f}')
    return _truncate_tool_output(result)


# =========================================================================
# 5.  compile_dossier  (auto-themed)
# =========================================================================
def compile_dossier(
    case_data: Annotated[Dict, "Complete case data: hypothesis, entities, evidence, stats, network, rules, similar_cases, recovery"],
) -> str:
    """
    Generate the final auto-insurance investigation dossier in Markdown.
    ONLY call this AFTER assess_evidence returns SUFFICIENT.
    """
    _tool_log('compile_dossier', 'Generating final Markdown dossier...')

    hypothesis = case_data.get('hypothesis', 'Suspected Auto Insurance Fraud')
    entities = case_data.get('entities', [])
    evidence = case_data.get('evidence', [])
    stats = case_data.get('statistical_analysis', {})
    network = case_data.get('network_analysis', {})
    rules = case_data.get('regulatory_rules', case_data.get('billing_rules', []))
    similar_cases = case_data.get('similar_cases', [])
    recovery = case_data.get('recovery_estimate', {})

    if not rules and _tool_cache.get('regulatory_rules'):
        rules = _tool_cache['regulatory_rules']
    if not similar_cases and _tool_cache.get('similar_cases'):
        similar_cases = _tool_cache['similar_cases']
    if (not recovery or not recovery.get('gross_recoverable')) and _tool_cache.get('recovery_estimate'):
        recovery = _tool_cache['recovery_estimate']

    def sf(val, default=0):
        try:
            return float(val) if val is not None else float(default)
        except (TypeError, ValueError):
            return float(default)

    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    dossier = f"""# AUTO INSURANCE FRAUD INVESTIGATION DOSSIER

**Case Hypothesis**: {hypothesis}
**Date Generated**: {now}
**Status**: Evidence Sufficient — Ready for Escalation

---

## EXECUTIVE SUMMARY

This investigation identified a suspected **{hypothesis}** involving {len(entities)} entities with an estimated net recovery of **${sf(recovery.get('net_expected')):,.2f}**.

The scheme was substantiated by {len(evidence)} independent evidence points. Statistical analysis confirmed deviations exceeding normal peer benchmarks. Pattern analysis indicates behaviour inconsistent with legitimate auto claims.

**Recommended Action**: Escalate to Special Investigations Unit for formal review.

---

## ENTITIES INVOLVED

"""
    for i, entity in enumerate(entities, 1):
        if isinstance(entity, dict):
            eid = entity.get('entity_id', 'UNKNOWN')
            etype = entity.get('entity_type', 'unknown').title()
            dossier += f"\n### Entity {i}: {eid}\n\n- **Type**: {etype}\n"
            if entity.get('risk_score'):
                dossier += f"- **Risk Score**: {entity['risk_score']}/100\n"
            if entity.get('name') or entity.get('entity_name'):
                dossier += f"- **Name**: {entity.get('name', entity.get('entity_name'))}\n"
            if entity.get('claim_amount') or entity.get('total_claimed'):
                amt = sf(entity.get('claim_amount', entity.get('total_claimed')))
                dossier += f"- **Total Claimed**: ${amt:,.2f}\n"
            if entity.get('claim_count'):
                dossier += f"- **Claims**: {entity['claim_count']}\n"
            if entity.get('vehicle'):
                dossier += f"- **Vehicle**: {entity['vehicle']}\n"
            dossier += "\n"
        else:
            dossier += f"\n### Entity {i}: {entity}\n\n"

    dossier += "\n---\n\n## EVIDENCE SUMMARY\n\n"
    for i, ev in enumerate(evidence, 1):
        dossier += f"{i}. {ev}\n"

    dossier += "\n---\n\n## STATISTICAL ANALYSIS\n\n"
    if stats and isinstance(stats, dict):
        dossier += "| Metric | Entity Value | Peer Average | Z-Score | Significance |\n"
        dossier += "|--------|--------------|--------------|---------|-------------|\n"
        for metric, data in stats.items():
            if isinstance(data, dict):
                ev = sf(data.get('entity_value', data.get('value', 0)))
                pa = sf(data.get('peer_avg', data.get('peer_average', 0)))
                zs = sf(data.get('z_score', data.get('z', 0)))
                sig = "⚠️ HIGH" if abs(zs) > 2 else "Normal"
                dossier += f"| {metric} | {ev:,.2f} | {pa:,.2f} | {zs:.2f} | {sig} |\n"
    else:
        dossier += "_No structured statistical data provided._\n"

    dossier += "\n---\n\n## NETWORK ANALYSIS\n\n"
    if network and isinstance(network, dict):
        dossier += f"- **Connected Entities**: {network.get('total_entities', 0)}\n"
        dossier += f"- **Connection Density**: {sf(network.get('connection_density')):,.2f}\n"
        if network.get('relationship_summary'):
            dossier += f"- **Relationships**: {network['relationship_summary']}\n"
        if network.get('patterns'):
            dossier += "\n**Detected Patterns**:\n"
            for p in (network['patterns'] if isinstance(network['patterns'], list) else [network['patterns']]):
                if isinstance(p, dict):
                    dossier += f"- [{p.get('severity', 'MEDIUM')}] {p.get('pattern_type', '')}: {p.get('description', '')}\n"
                else:
                    dossier += f"- {p}\n"
    else:
        dossier += "_No network analysis data provided._\n"

    dossier += "\n---\n\n## REGULATORY RULE VIOLATIONS\n\n"
    if rules:
        for rule in rules:
            if isinstance(rule, dict):
                dossier += f"### {rule.get('section_id', 'RULE')}: {rule.get('title', 'Unknown')}\n\n"
                dossier += f"**Summary**: {rule.get('summary', 'N/A')}\n\n"
                if rule.get('fraud_indicators'):
                    dossier += "**Applicable Red Flags**:\n"
                    for ind in rule.get('fraud_indicators', [])[:4]:
                        dossier += f"- {ind}\n"
                dossier += "\n"
            else:
                dossier += f"- {rule}\n"
    else:
        dossier += "_No regulatory rules cited._\n"

    dossier += "\n---\n\n## PRECEDENT CASES\n\n"
    if similar_cases:
        for case in similar_cases:
            if isinstance(case, dict):
                dossier += f"### {case.get('case_id', 'CASE')}: {case.get('scheme', 'Unknown')}\n\n"
                dossier += f"- **Summary**: {case.get('summary', 'N/A')}\n"
                paid = sf(case.get('total_paid', case.get('total_recovered', 0)))
                dossier += f"- **Total Paid/Recovered**: ${paid:,.0f}\n"
                dossier += f"- **Outcome**: {case.get('outcome', 'Unknown')}\n"
                dossier += f"- **Year**: {case.get('year', 'N/A')}\n\n"
            else:
                dossier += f"- {case}\n"
    else:
        dossier += "_No precedent cases found._\n"

    dossier += "\n---\n\n## RECOVERY ESTIMATE\n\n"
    total_claimed = sf(recovery.get('total_claimed', 0))
    gross = sf(recovery.get('gross_recoverable', 0))
    net = sf(recovery.get('net_expected', 0))
    collect = sf(recovery.get('collectability_score', 0))
    if gross == 0 and total_claimed > 0:
        excess = sf(recovery.get('excess_rate', 0.15))
        gross = round(total_claimed * excess, 2)
        if collect == 0:
            collect = 0.60
        net = round(gross * collect, 2)

    dossier += f"- **Total Flagged Claims**: {recovery.get('total_flagged_claims', len(entities))}\n"
    dossier += f"- **Total Claimed**: ${total_claimed:,.2f}\n"
    dossier += f"- **Gross Recoverable**: ${gross:,.2f}\n"
    dossier += f"- **Collectability Score**: {collect:.0%}\n"
    dossier += f"- **Net Expected Recovery**: **${net:,.2f}**\n\n"

    if recovery.get('claim_breakdown'):
        dossier += "**Breakdown by Claim Type**:\n\n"
        dossier += "| Claim Type | Claims | Total Claimed | Est. Recovery |\n"
        dossier += "|------------|--------|---------------|---------------|\n"
        for item in recovery.get('claim_breakdown', [])[:5]:
            if isinstance(item, dict):
                ct = item.get('claim_type', 'N/A')
                count = item.get('claim_count', 'N/A')
                total = sf(item.get('total_claimed', 0))
                est = sf(item.get('estimated_recovery', 0))
                dossier += f"| {ct} | {count} | ${total:,.0f} | ${est:,.0f} |\n"

    dossier += "\n---\n\n## RECOMMENDED ACTIONS\n\n"
    dossier += "1. **Immediate**: Place flagged claims on payment hold pending SIU review\n"
    dossier += "2. **Verification**: Request original repair estimates, police reports, and damage photos\n"
    dossier += "3. **Investigation**: Re-inspect the vehicle, verify the shop's network status, and confirm ACV\n"
    dossier += "4. **Recovery**: Issue demand letters for identified overpayments\n"
    dossier += "5. **Prevention**: Flag insureds/shops for enhanced monitoring on future claims\n\n"

    dossier += "---\n\n"
    dossier += "*Generated by Car Insurance Examiner Workflow Copilot*\n"

    _tool_log('compile_dossier', f'Dossier generated ({len(dossier)} chars)')
    return dossier


# =========================================================================
DOSSIER_TOOLS = [
    assess_evidence,
    search_regulatory_rules,
    find_similar_cases,
    estimate_recovery,
    compile_dossier,
]
