"""
Dossier Agent Tools (Travel) — 5 tools for evidence assessment and case compilation
for Zurich Travel Guard. Mirrors agents/tools_dossier.py but with travel regulatory
rules (TG-xxx), travel precedent cases, and a travel-themed dossier.
"""

import re
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
# 1.  assess_evidence  (domain-neutral; travel scheme keywords)
# =========================================================================
def assess_evidence(
    hypothesis: Annotated[str, "Suspected scheme (e.g. 'destination fraud ring', 'baggage padding')"],
    evidence: Annotated[List[str], "List of evidence points gathered"],
    scheme_pattern: Annotated[str, "Pattern: destination_fraud_ring, phantom_booking, baggage_padding, fabricated_delay, serial_claimer"],
) -> Dict:
    """
    Check if gathered evidence meets sufficiency criteria for escalation.
    MUST be called BEFORE compile_dossier.
    """
    _tool_log('assess_evidence', f'Assessing "{hypothesis}" ({len(evidence)} points)...')
    checks_passed, checks_failed, missing = [], [], []
    all_text = ' '.join(str(e).lower() for e in evidence)

    # 1: multiple evidence points
    if len(evidence) >= 3:
        checks_passed.append("multiple_evidence_points")
    else:
        checks_failed.append("multiple_evidence_points")
        missing.append(f"Need >= 3 independent evidence points (have {len(evidence)}). "
                       "Profile additional entities or compare claim amounts to peers.")

    # 2: statistical significance
    stat_kw = ['z-score', 'z_score', 'z=', 'standard deviation', 'anomaly', 'peer',
               'sigma', 'comparison', 'average', 'mean', 'risk_score', 'risk score']
    if any(kw in all_text for kw in stat_kw):
        checks_passed.append("statistical_significance")
    else:
        checks_failed.append("statistical_significance")
        missing.append("Need statistical comparison to peers. Call compare_to_peers() on "
                       "claim_amount, claim_count, or baggage_value and report the z-score.")

    # 3: temporal / pattern
    temporal_kw = ['month', 'timeline', 'date', 'period', 'delay', 'spike', 'flight',
                   'booking', 'trip', 'history', 'before', 'after', 'filed', 'pattern', 'trend']
    if any(kw in all_text for kw in temporal_kw):
        checks_passed.append("temporal_pattern")
    else:
        checks_failed.append("temporal_pattern")
        missing.append("Need temporal analysis: compare claimed delay vs. flight tracking, "
                       "booking dates vs. trip window, or filing dates relative to policy purchase.")

    # 4: network (ring-type)
    if any(kw in scheme_pattern.lower() for kw in ['ring', 'cluster', 'network', 'destination']):
        net_kw = ['ring', 'connection', 'network', 'destination', 'provider', 'density',
                  'entities', 'relationship', 'linked', 'cluster', 'watchlist']
        if any(kw in all_text for kw in net_kw):
            checks_passed.append("network_evidence")
        else:
            checks_failed.append("network_evidence")
            missing.append("Need network analysis for a ring pattern. Call find_connections() on "
                           "the target and find_ring() to surface destination/provider clusters.")

    # 5: regulatory citation
    rule_kw = ['rule', 'tg-0', 'r-0', 'regulation', 'violation', 'triggered', 'severity', 'policy']
    if any(kw in all_text for kw in rule_kw):
        checks_passed.append("regulatory_citation")
    else:
        checks_failed.append("regulatory_citation")
        missing.append("Need regulatory context. Call search_regulatory_rules() to find "
                       "applicable TG-001 through TG-010 travel rules.")

    # 6: document/photo integrity (doc/photo schemes)
    if any(kw in scheme_pattern.lower() for kw in ['baggage', 'padding', 'document', 'photo', 'fabricat']):
        doc_kw = ['photo', 'receipt', 'document', 'staged', 'metadata', 'manipulat',
                  'watermark', 'screenshot', 'forged', 'altered', 'tampering']
        if any(kw in all_text for kw in doc_kw):
            checks_passed.append("document_evidence")
        else:
            checks_failed.append("document_evidence")
            missing.append("Need evidence-image findings. Review the claim's photo/receipt "
                           "vision checks (staged damage, manipulation, missing receipts).")

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
# 2.  search_regulatory_rules  (travel rules)
# =========================================================================
def search_regulatory_rules(
    claim_types: Annotated[List[str], "Claim types (trip_cancellation, trip_interruption, medical_emergency, baggage_loss, travel_delay)"],
    context: Annotated[str, "Description of the suspected scheme"],
) -> List[Dict]:
    """
    Search Zurich Travel Guard regulatory rules relevant to the case.
    Returns rules with section_id, title, summary, fraud_indicators, applicable_types.
    """
    _tool_log('search_regulatory_rules', f'Searching rules for types={claim_types}...')

    RULES = [
        {
            "section_id": "TG-001",
            "title": "Pre-Existing Condition / Coverage Window",
            "summary": "Medical emergency claims with a date of incident shortly after policy purchase, "
                       "or for declared-but-not-upgraded pre-existing conditions, require review.",
            "fraud_indicators": [
                "Medical incident within 30 days of policy purchase",
                "Diagnosis consistent with a pre-existing condition not declared",
                "Maximum medical coverage purchased just before travel",
            ],
            "applicable_types": ["medical_emergency", "trip_cancellation", "trip_interruption"],
        },
        {
            "section_id": "TG-002",
            "title": "Booking Confirmation Requirement",
            "summary": "Trip cancellation/interruption benefits require a verifiable confirmed booking. "
                       "Claims with no airline/hotel confirmation must be denied or held.",
            "fraud_indicators": [
                "No confirmed flight or hotel booking on file",
                "Booking reference cannot be verified with the airline/GDS",
                "Cancellation claimed before any booking existed",
            ],
            "applicable_types": ["trip_cancellation", "trip_interruption"],
        },
        {
            "section_id": "TG-003",
            "title": "Destination Fraud Ring — Watchlisted Providers",
            "summary": "Overseas medical claims from watchlisted or unverified providers in destinations "
                       "with known coordinated fraud activity are flagged for ring investigation.",
            "fraud_indicators": [
                "Treating provider is on the fraud watchlist or unverified in-network",
                "Destination flagged as a known fraud ring",
                "Hospital bill far exceeds the destination's expected cost-per-day",
                "Multiple travelers routed through the same overseas facility",
            ],
            "applicable_types": ["medical_emergency"],
        },
        {
            "section_id": "TG-004",
            "title": "Baggage Valuation — Outlier and Receipt Verification",
            "summary": "Baggage claims must be substantiated by receipts/ownership proof. Claims several "
                       "SD above peer value, or exceeding the policy baggage limit, require verification.",
            "fraud_indicators": [
                "Baggage claim value > 3x the peer average for the type",
                "Exclusively luxury items with no purchase receipts",
                "Claim amount exceeds the policy baggage coverage limit",
                "Submitted damage photo shows staged or inconsistent damage",
            ],
            "applicable_types": ["baggage_loss"],
        },
        {
            "section_id": "TG-005",
            "title": "Flight Delay Verification — Tracking Consistency",
            "summary": "Travel delay benefits require the claimed delay to match independent flight "
                       "tracking (FlightStats/IATA). On-time flights reported as delayed are denied.",
            "fraud_indicators": [
                "Claimed delay hours conflict with flight-tracking records",
                "Flight shows on-time departure but a multi-hour delay is claimed",
                "No corroborating airport/airline delay documentation",
            ],
            "applicable_types": ["travel_delay"],
        },
        {
            "section_id": "TG-006",
            "title": "Policy Purchased After Event",
            "summary": "A policy purchased after the claimed incident date is invalid for that incident.",
            "fraud_indicators": [
                "Policy purchase date is after the date of incident",
                "Incident details known prior to coverage purchase",
            ],
            "applicable_types": ["trip_cancellation", "trip_interruption", "medical_emergency",
                                  "baggage_loss", "travel_delay"],
        },
        {
            "section_id": "TG-007",
            "title": "Serial Claimer — Benefit Harvesting",
            "summary": "Travelers with repeated claims across trips, especially with a repetitive "
                       "diagnosis/loss pattern, are flagged for benefit-harvesting review.",
            "fraud_indicators": [
                "3+ claims by the same traveler in a short window",
                "Repetitive diagnosis (always food poisoning / dehydration)",
                "Claims always filed within a few days of trip start",
            ],
            "applicable_types": ["medical_emergency", "trip_interruption", "baggage_loss", "travel_delay"],
        },
        {
            "section_id": "TG-008",
            "title": "Airline Refund Double-Dip",
            "summary": "Trip cancellation claims where the airline/hotel has already refunded the traveler "
                       "constitute double recovery and must be offset.",
            "fraud_indicators": [
                "Flight booking cancelled/refunded by the airline",
                "Hotel issued a refund for the same dates being claimed",
            ],
            "applicable_types": ["trip_cancellation", "trip_interruption"],
        },
        {
            "section_id": "TG-009",
            "title": "Document & Evidence Integrity",
            "summary": "Receipts, police reports, boarding passes, and medical reports must be authentic. "
                       "Manipulated, screenshot, or template-generated documents are rejected.",
            "fraud_indicators": [
                "Receipt amounts/dates show overwriting or misalignment",
                "Police report lacks an official report number or stamp",
                "Document appears to be a screenshot or editable template",
                "Issuer logo/currency/language conflicts with the claimed destination",
            ],
            "applicable_types": ["medical_emergency", "baggage_loss", "trip_cancellation",
                                  "trip_interruption", "travel_delay"],
        },
        {
            "section_id": "TG-010",
            "title": "Resubmission Abuse — Duplicate and Modified Claims",
            "summary": "Resubmitted claims must have material changes. Repeated resubmission of denied "
                       "claims, or resubmissions with inflated amounts, are flagged.",
            "fraud_indicators": [
                "Claim resubmitted multiple times after denial",
                "Resubmission amount exceeds the original by >20%",
                "Different incident details on resubmission for the same trip",
            ],
            "applicable_types": ["trip_cancellation", "trip_interruption", "medical_emergency",
                                  "baggage_loss", "travel_delay"],
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
# 3.  find_similar_cases  (travel precedents)
# =========================================================================
def find_similar_cases(
    scheme_pattern: Annotated[str, "destination_fraud_ring, phantom_booking, baggage_padding, fabricated_delay, serial_claimer"],
    specialty: Annotated[str, "Claim type if applicable"] = None,
) -> List[Dict]:
    """Find precedent travel-insurance cases with similar fraud patterns."""
    _tool_log('find_similar_cases', f'Looking up precedents for "{scheme_pattern}"...')

    CASES = {
        "destination_fraud_ring": [{
            "case_id": "SIU-TG-2025-0142",
            "scheme": "Destination Fraud Ring — Overseas Hospital Mill",
            "entities_involved": 9, "total_claims": 31, "total_paid": 318_000,
            "summary": "Nine travelers filed medical-emergency claims through a single unverified clinic "
                       "in a high-risk Caribbean destination over four months. Bills averaged 6x the "
                       "destination's cost-per-day. The facility was later confirmed to be issuing "
                       "fabricated invoices for procedures never performed.",
            "outcome": "Provider blacklisted, $318K demand issued, 4 travelers referred for prosecution",
            "year": 2025,
        }],
        "phantom_booking": [{
            "case_id": "SIU-TG-2024-0091",
            "scheme": "Phantom Booking — Fabricated Cancellation",
            "entities_involved": 1, "total_claims": 1, "total_paid": 6_200,
            "summary": "Traveler filed a trip-cancellation claim with no verifiable airline or hotel "
                       "booking. The provided PNR did not exist in the airline GDS. Policy had been "
                       "purchased two days before the claimed cancellation.",
            "outcome": "Claim denied, traveler flagged for enhanced monitoring",
            "year": 2024,
        }],
        "baggage_padding": [{
            "case_id": "SIU-TG-2025-0207",
            "scheme": "Baggage Padding — Luxury Item Inflation",
            "entities_involved": 1, "total_claims": 1, "total_paid": 15_200,
            "summary": "Baggage-loss claim listed seven luxury items (Rolex, Louis Vuitton, MacBook Pro) "
                       "totalling 6x the peer average with no purchase receipts. Submitted damage photo "
                       "showed pristine 'destroyed' luggage inconsistent with the claimed cause.",
            "outcome": "Claim reduced to documented items, $11K prevented",
            "year": 2025,
        }],
        "fabricated_delay": [{
            "case_id": "SIU-TG-2024-0318",
            "scheme": "Fabricated Delay — Tracking Mismatch",
            "entities_involved": 1, "total_claims": 1, "total_paid": 1_150,
            "summary": "Traveler claimed a 22-hour delay; IATA FlightStats showed the flight departed "
                       "on time with 0 minutes delay. No airport documentation was produced.",
            "outcome": "Claim denied for lack of corroboration",
            "year": 2024,
        }],
        "serial_claimer": [{
            "case_id": "SIU-TG-2025-0064",
            "scheme": "Serial Claimer — Benefit Harvesting",
            "entities_involved": 1, "total_claims": 8, "total_paid": 47_000,
            "summary": "Traveler filed 8 medical-emergency claims across 14 months, always food poisoning "
                       "or dehydration, always within 3 days of trip start. Claim frequency was 4.8 SD "
                       "above the traveler peer group.",
            "outcome": "All open claims held, policy non-renewed, $47K under recovery review",
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
# 4.  estimate_recovery  (travel collectability factors)
# =========================================================================
def estimate_recovery(
    flagged_claims: Annotated[List[Dict], "List of suspicious claims [{claim_id, claim_amount, ...}]"],
    peer_benchmarks: Annotated[Dict, "Peer benchmarks: {avg_claim_amount, ...}"],
) -> Dict:
    """Estimate recoverable amount from flagged travel claims."""
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

    # Travel collectability: doc quality 0.85 · traveler cooperation 0.75 · statute window 0.95
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
# 5.  compile_dossier  (travel-themed)
# =========================================================================
def compile_dossier(
    case_data: Annotated[Dict, "Complete case data: hypothesis, entities, evidence, stats, network, rules, similar_cases, recovery"],
) -> str:
    """
    Generate the final travel-insurance investigation dossier in Markdown.
    ONLY call this AFTER assess_evidence returns SUFFICIENT.
    """
    _tool_log('compile_dossier', 'Generating final Markdown dossier...')

    hypothesis = case_data.get('hypothesis', 'Suspected Travel Insurance Fraud')
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

    dossier = f"""# TRAVEL INSURANCE FRAUD INVESTIGATION DOSSIER

**Case Hypothesis**: {hypothesis}
**Date Generated**: {now}
**Status**: Evidence Sufficient — Ready for Escalation

---

## EXECUTIVE SUMMARY

This investigation identified a suspected **{hypothesis}** involving {len(entities)} entities with an estimated net recovery of **${sf(recovery.get('net_expected')):,.2f}**.

The scheme was substantiated by {len(evidence)} independent evidence points. Statistical analysis confirmed deviations exceeding normal peer benchmarks. Pattern analysis indicates behaviour inconsistent with legitimate travel claims.

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
            if entity.get('destination'):
                dossier += f"- **Destination**: {entity['destination']}\n"
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
    dossier += "2. **Verification**: Request original booking confirmations, receipts, police reports, and overseas medical records\n"
    dossier += "3. **Investigation**: Verify bookings with the airline/GDS, confirm flight delays with IATA tracking, and conduct provider checks\n"
    dossier += "4. **Recovery**: Issue demand letters for identified overpayments\n"
    dossier += "5. **Prevention**: Flag travelers/providers for enhanced monitoring on future claims\n\n"

    dossier += "---\n\n"
    dossier += "*Generated by Zurich Travel Guard Examiner Workflow Copilot*\n"

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
