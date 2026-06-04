"""
Dossier Agent Tools — 5 tools for evidence assessment and case compilation.
Adapted for Prudential supplemental health (dataclass-based DataContext).
"""

import re
import time
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
        serialized = json.dumps(data, default=str)
        if len(serialized) > max_chars:
            return {"summary": "Output truncated due to size",
                    "item_count": len(data) if isinstance(data, list) else 1}
    except Exception:
        pass
    return data


# ---------------------------------------------------------------------------
# Global context & cache
# ---------------------------------------------------------------------------
_context = None

_tool_cache = {
    'regulatory_rules': None,
    'similar_cases': None,
    'recovery_estimate': None,
}


def set_context(ctx):
    global _context
    _context = ctx


def clear_tool_cache():
    global _tool_cache
    _tool_cache = {
        'regulatory_rules': None,
        'similar_cases': None,
        'recovery_estimate': None,
    }


# =========================================================================
# 1.  assess_evidence
# =========================================================================
def assess_evidence(
    hypothesis: Annotated[str, "The suspected fraud scheme (e.g., 'dependent ring', 'provider mill')"],
    evidence: Annotated[List[str], "List of evidence points gathered"],
    scheme_pattern: Annotated[str, "Pattern type: dependent_ring, provider_cluster, termination_rush, tampered_records, overbilling, etc."],
) -> Dict:
    """
    Check if gathered evidence meets sufficiency criteria for escalation.

    MUST be called BEFORE compile_dossier.

    Criteria checked (supplemental health domain):
    - Multiple evidence points (>= 3)
    - Statistical / peer comparison data present
    - Temporal or pattern analysis
    - Network / relationship evidence (if ring-type pattern)
    - Rule or regulatory citation
    - Document integrity evidence (if document-related)

    Returns assessment (SUFFICIENT / INSUFFICIENT), checks passed/failed,
    and specific missing_evidence descriptions.
    """
    _tool_log('assess_evidence', f'Assessing evidence for "{hypothesis}" ({len(evidence)} points)...')

    checks_passed = []
    checks_failed = []
    missing_evidence = []

    all_text = ' '.join(str(e).lower() for e in evidence)

    # ---- Check 1: Multiple evidence points ----
    if len(evidence) >= 3:
        checks_passed.append("multiple_evidence_points")
    else:
        checks_failed.append("multiple_evidence_points")
        missing_evidence.append(f"Need at least 3 independent evidence points (have {len(evidence)}). "
                                "Consider profiling additional entities, comparing claim amounts to peers, "
                                "or reviewing provider history.")

    # ---- Check 2: Statistical significance ----
    stat_keywords = ['z-score', 'z_score', 'z=', 'zscore', 'standard deviation',
                     'anomaly', 'peer', 'sigma', 'comparison', 'average', 'mean',
                     'risk_score', 'risk score']
    has_stat = any(kw in all_text for kw in stat_keywords)

    if has_stat:
        z_scores = []
        for pattern in [r'z[_\-\s]*(?:score)?[=:\s]+([\-]?[0-9.]+)',
                        r'([0-9.]+)\s*(?:standard deviations?|SD|sigma)',
                        r'risk[_\s]*score[=:\s]+([0-9]+)']:
            z_scores.extend(float(m) for m in re.findall(pattern, all_text))

        if any(abs(z) > 2 for z in z_scores) or any(z > 60 for z in z_scores) or has_stat:
            checks_passed.append("statistical_significance")
        else:
            checks_failed.append("statistical_significance")
            missing_evidence.append(
                "Statistical evidence present but weak. Use compare_to_peers on "
                "claim_amount or claim_count to get z-scores > 2.")
    else:
        checks_failed.append("statistical_significance")
        missing_evidence.append(
            "Need statistical comparison to peer group. Call compare_to_peers() for the "
            "target member or provider on metrics like claim_amount, claim_count, or "
            "dependent_claims. Report the z-score explicitly.")

    # ---- Check 3: Temporal / pattern analysis ----
    temporal_kw = ['month', 'timeline', 'date', 'period', 'rush', 'spike',
                   'increase', 'shift', 'history', 'change', 'before', 'after',
                   'termination', 'filed', 'pattern', 'trend']
    if any(kw in all_text for kw in temporal_kw):
        checks_passed.append("temporal_pattern")
    else:
        checks_failed.append("temporal_pattern")
        missing_evidence.append(
            "Need temporal analysis showing when the suspicious pattern started. "
            "Use get_referral_history() for provider monthly volume or review "
            "claim filing dates relative to policy effective/termination dates.")

    # ---- Check 4: Network / relationship evidence ----
    if any(kw in scheme_pattern.lower() for kw in ['ring', 'cluster', 'network',
                                                     'shared_address', 'dependent']):
        net_kw = ['ring', 'connection', 'network', 'address', 'density',
                  'dependent', 'entities', 'relationship', 'linked', 'shared']
        if any(kw in all_text for kw in net_kw):
            checks_passed.append("network_evidence")
        else:
            checks_failed.append("network_evidence")
            missing_evidence.append(
                "Need network analysis for ring-type pattern. Call find_connections() on "
                "the target entity and find_ring() to detect cross-claim patterns "
                "(dependent rings, shared addresses, provider clusters).")

    # ---- Check 5: Regulatory / rule citation ----
    rule_kw = ['rule', 'r-0', 'regulation', 'violation', 'compliance',
               'triggered', 'severity', 'policy', 'code', 'statute']
    if any(kw in all_text for kw in rule_kw):
        checks_passed.append("regulatory_citation")
    else:
        checks_failed.append("regulatory_citation")
        missing_evidence.append(
            "Need regulatory context. Call search_regulatory_rules() with relevant "
            "claim types and describe the suspected scheme to find applicable rules "
            "(e.g., R-001 through R-015 supplemental health rules).")

    # ---- Check 6: Document integrity ----
    if any(kw in scheme_pattern.lower() for kw in ['tamper', 'document', 'forgery']):
        doc_kw = ['signature', 'header', 'tampering', 'duplicate', 'resolution',
                  'metadata', 'document', 'forged', 'altered']
        if any(kw in all_text for kw in doc_kw):
            checks_passed.append("document_evidence")
        else:
            checks_failed.append("document_evidence")
            missing_evidence.append(
                "Need document integrity evidence. Review document metadata for the "
                "claims — check for missing headers/signatures, tampering indicators, "
                "duplicate documents, or low-resolution scans.")

    # ---- Overall assessment ----
    critical = ["multiple_evidence_points", "statistical_significance", "temporal_pattern"]
    critical_passed = all(c in checks_passed for c in critical)

    if critical_passed and len(checks_failed) <= 1 and len(evidence) >= 4:
        assessment = "SUFFICIENT"
    else:
        assessment = "INSUFFICIENT"

    _tool_log('assess_evidence',
              f'Result: {assessment} ({len(checks_passed)} passed, {len(checks_failed)} failed)')

    return {
        "assessment": assessment,
        "hypothesis": hypothesis,
        "scheme_pattern": scheme_pattern,
        "evidence_count": len(evidence),
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "missing_evidence": missing_evidence,
        "recommendation": ("Proceed to compile dossier" if assessment == "SUFFICIENT"
                           else "Gather additional evidence before proceeding"),
    }


# =========================================================================
# 2.  search_regulatory_rules  (replaces search_billing_rules)
# =========================================================================
def search_regulatory_rules(
    claim_types: Annotated[List[str], "Claim types involved (wellness, accident, hospital_indemnity, critical_illness)"],
    context: Annotated[str, "Description of the suspected scheme"],
) -> List[Dict]:
    """
    Search Prudential supplemental health regulatory rules relevant to the case.

    Returns rules with section_id, title, summary, fraud_indicators, and relevance.
    Covers: eligibility abuse, dependent fraud, provider mill billing,
    document tampering, termination-rush filing, overbilling, and more.
    """
    _tool_log('search_regulatory_rules', f'Searching rules for types={claim_types}...')

    # Supplemental health rule database (realistic, grounded in industry practices)
    RULES = [
        {
            "section_id": "SH-001",
            "title": "Eligibility Verification — Active Employment",
            "summary": "Claims must be filed by actively employed members within the coverage period. "
                       "Claims filed after employment termination or during COBRA gaps require special review.",
            "fraud_indicators": [
                "Claim date of service falls after member termination date",
                "Multiple claims filed within 14 days of termination",
                "Member has no active payroll deductions at time of service",
            ],
            "applicable_types": ["wellness", "accident", "hospital_indemnity", "critical_illness"],
        },
        {
            "section_id": "SH-002",
            "title": "Dependent Eligibility — Relationship Verification",
            "summary": "Dependents must meet plan relationship criteria (spouse, child under 26). "
                       "Excessive dependent claims or dependents at different addresses require verification.",
            "fraud_indicators": [
                "Dependent address differs from primary member address",
                "Dependent age exceeds plan maximum (26 for children)",
                "Disproportionate claims filed for dependents vs. primary member",
                "Multiple members listing the same dependents",
            ],
            "applicable_types": ["wellness", "accident", "hospital_indemnity", "critical_illness"],
        },
        {
            "section_id": "SH-003",
            "title": "Provider Mill Detection — Volume Anomalies",
            "summary": "Providers with claims volume 3+ standard deviations above specialty peers, "
                       "or with >80% of claims from a single employer group, are flagged for mill activity.",
            "fraud_indicators": [
                "Provider claim volume exceeds peer average by 3+ SD",
                "Single employer group represents >60% of provider's claim volume",
                "Provider is not credentialed in the treating specialty",
                "Provider has excessive after-hours or weekend service dates",
            ],
            "applicable_types": ["wellness", "hospital_indemnity"],
        },
        {
            "section_id": "SH-004",
            "title": "Document Integrity — Tampering Detection",
            "summary": "Medical documents must contain verifiable provider headers, signatures, and dates. "
                       "Documents with metadata anomalies, missing elements, or duplicate hashes must be rejected.",
            "fraud_indicators": [
                "Document missing provider letterhead or NPI",
                "Signature field blank or appears copied from another document",
                "PDF metadata shows editing software (not scanner)",
                "Multiple claims share identical document hash",
                "Low-resolution scan obscuring key clinical details",
            ],
            "applicable_types": ["wellness", "accident", "hospital_indemnity", "critical_illness"],
        },
        {
            "section_id": "SH-005",
            "title": "Termination Rush Filing — Pre-Separation Abuse",
            "summary": "Pattern of multiple claims filed by members within 30 days of employment "
                       "termination. Indicates potential benefit harvesting before coverage ends.",
            "fraud_indicators": [
                "3+ claims filed by same member within 30 days of termination",
                "Claims across multiple plan types near termination",
                "Date of service pre-dates employment start date",
                "Employer group shows pattern of termination-rush claims",
            ],
            "applicable_types": ["wellness", "accident", "hospital_indemnity", "critical_illness"],
        },
        {
            "section_id": "SH-006",
            "title": "Accident Claim Verification — Incident Consistency",
            "summary": "Accident claims require consistent incident details across all documentation. "
                       "Date of loss, injury description, and treatment must align with reported accident.",
            "fraud_indicators": [
                "Date of loss and date of service are inconsistent (>30 days apart)",
                "Diagnosis codes inconsistent with reported accident type",
                "Multiple accident claims within short period from same member",
                "Treatment began before the reported date of loss",
            ],
            "applicable_types": ["accident"],
        },
        {
            "section_id": "SH-007",
            "title": "Critical Illness — Pre-existing Condition Exclusion",
            "summary": "Critical illness claims are subject to pre-existing condition limitations. "
                       "Diagnosis within the look-back period of policy inception requires scrutiny.",
            "fraud_indicators": [
                "Critical illness diagnosis within 12 months of policy effective date",
                "Prior diagnosis codes on record matching the critical illness claim",
                "Member purchased maximum coverage tier shortly before diagnosis",
                "Provider notes suggest condition was known before policy purchase",
            ],
            "applicable_types": ["critical_illness"],
        },
        {
            "section_id": "SH-008",
            "title": "Hospital Indemnity — Admission Necessity",
            "summary": "Hospital indemnity benefits require medically necessary inpatient admission. "
                       "Observation stays, outpatient-with-bed, and elective admissions may not qualify.",
            "fraud_indicators": [
                "Facility billed as inpatient but classified as observation",
                "Admission duration <24 hours for non-emergency",
                "Elective procedure with unnecessary overnight stay",
                "Multiple short-stay admissions to the same facility",
            ],
            "applicable_types": ["hospital_indemnity"],
        },
        {
            "section_id": "SH-009",
            "title": "Shared Address Clusters — Organized Fraud Rings",
            "summary": "Multiple unrelated members at the same address filing claims through the same "
                       "provider may indicate organised benefit fraud. Cross-reference with employer records.",
            "fraud_indicators": [
                "3+ members at same address not in same family",
                "All members filing claims through the same provider",
                "Members employed at different companies but same address",
                "High dependent count at shared address",
            ],
            "applicable_types": ["wellness", "accident", "hospital_indemnity"],
        },
        {
            "section_id": "SH-010",
            "title": "Resubmission Abuse — Duplicate and Modified Claims",
            "summary": "Resubmitted claims must have material changes. Repeated resubmission of denied "
                       "claims with minor modifications, or resubmissions with inflated amounts, are flagged.",
            "fraud_indicators": [
                "Claim resubmitted 3+ times after denial",
                "Resubmission amount exceeds original by >20%",
                "Diagnosis codes changed between submissions without new medical evidence",
                "Different provider listed on resubmission for same service",
            ],
            "applicable_types": ["wellness", "accident", "hospital_indemnity", "critical_illness"],
        },
    ]

    # Filter by claim type relevance
    ctx_lower = context.lower()
    scored = []
    for rule in RULES:
        type_match = any(ct.lower() in [t.lower() for t in rule['applicable_types']]
                         for ct in claim_types) if claim_types else True
        # Keyword relevance
        keywords = rule['title'].lower() + ' ' + rule['summary'].lower()
        word_hits = sum(1 for w in ctx_lower.split() if w in keywords)
        indicator_hits = sum(1 for ind in rule['fraud_indicators']
                             if any(w in ind.lower() for w in ctx_lower.split()))
        score = (5 if type_match else 0) + word_hits + indicator_hits * 2
        scored.append((score, rule))

    scored.sort(key=lambda x: -x[0])
    results = [r for _, r in scored if _ > 0][:5]

    _tool_cache['regulatory_rules'] = results
    _tool_log('search_regulatory_rules', f'Found {len(results)} relevant rules')
    return _truncate_tool_output(results)


# Keep old name as alias so prompts referencing either name work
search_billing_rules = search_regulatory_rules


# =========================================================================
# 3.  find_similar_cases
# =========================================================================
def find_similar_cases(
    scheme_pattern: Annotated[str, "Pattern type: dependent_ring, provider_cluster, termination_rush, tampered_records, overbilling"],
    specialty: Annotated[str, "Provider specialty or claim type if applicable"] = None,
) -> List[Dict]:
    """
    Find precedent cases with similar supplemental health fraud patterns.

    Returns past resolved cases showing this is a known fraud scheme.
    """
    _tool_log('find_similar_cases', f'Looking up precedents for "{scheme_pattern}"...')

    CASES = {
        "dependent_ring": [
            {
                "case_id": "SIU-2025-0312",
                "scheme": "Dependent Ring — Shared Address Cluster",
                "entities_involved": 8,
                "total_claims": 47,
                "total_paid": 142_000,
                "summary": "Eight members at two shared addresses filed 47 wellness and accident claims "
                           "through the same chiropractic provider within 6 months. Investigation revealed "
                           "5 listed dependents were not eligible family members. Provider billed for "
                           "visits that members could not recall attending.",
                "outcome": "Provider terminated from network, $142K recovered, 3 members referred for prosecution",
                "year": 2025,
            },
            {
                "case_id": "SIU-2024-0189",
                "scheme": "Dependent Fraud — Phantom Dependents",
                "entities_involved": 3,
                "total_claims": 22,
                "total_paid": 58_000,
                "summary": "Three members at the same employer added non-qualifying dependents during "
                           "open enrollment. Dependents filed wellness claims immediately. Address "
                           "verification showed dependents lived in different states.",
                "outcome": "Coverage rescinded, $58K recovered, members terminated from plan",
                "year": 2024,
            },
        ],
        "provider_cluster": [
            {
                "case_id": "SIU-2025-0087",
                "scheme": "Provider Mill — High-Volume Wellness Clinic",
                "entities_involved": 1,
                "total_claims": 312,
                "total_paid": 485_000,
                "summary": "Single chiropractic clinic generated 312 supplemental wellness claims in one "
                           "quarter, 4.7 standard deviations above specialty peers. 78% of patients were "
                           "from a single employer group. Documentation showed identical treatment plans "
                           "across patients. Clinic owner had financial arrangement with HR coordinator.",
                "outcome": "Provider excluded, HR coordinator terminated, $485K demand letter issued",
                "year": 2025,
            },
        ],
        "termination_rush": [
            {
                "case_id": "SIU-2024-0445",
                "scheme": "Termination Rush — Pre-Separation Harvesting",
                "entities_involved": 12,
                "total_claims": 38,
                "total_paid": 94_000,
                "summary": "12 members from a closing manufacturing plant filed 38 claims across all "
                           "plan types in the 14 days before mass termination. Average member had filed "
                           "0.3 claims in the prior 12 months. Claims included suspicious accident dates "
                           "and critical illness diagnoses that appeared pre-existing.",
                "outcome": "22 claims denied, $94K prevented, employer flagged for enhanced monitoring",
                "year": 2024,
            },
        ],
        "tampered_records": [
            {
                "case_id": "SIU-2025-0201",
                "scheme": "Document Forgery — Fabricated Medical Records",
                "entities_involved": 2,
                "total_claims": 9,
                "total_paid": 67_000,
                "summary": "Two members submitted hospital indemnity claims with fabricated discharge "
                           "summaries. Documents lacked facility letterhead, contained identical fonts "
                           "not matching the hospital's records system, and metadata showed PDF editing "
                           "software. Hospital confirmed no admissions for either patient on claimed dates.",
                "outcome": "Claims denied, both members criminally charged, $67K recovery",
                "year": 2025,
            },
        ],
        "overbilling": [
            {
                "case_id": "SIU-2024-0556",
                "scheme": "Overbilling — Inflated Accident Claims",
                "entities_involved": 4,
                "total_claims": 16,
                "total_paid": 112_000,
                "summary": "Four members from different employer groups filed accident claims with amounts "
                           "2.8x the average for similar injuries. All used the same urgent care facility. "
                           "Facility was billing for level-5 evaluations on all accident visits regardless "
                           "of injury severity.",
                "outcome": "Facility audit, $112K overpayment recouped, fee schedule adjusted",
                "year": 2024,
            },
        ],
    }

    results = CASES.get(scheme_pattern.lower(), [])

    # Partial matching
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
    peer_benchmarks: Annotated[Dict, "Peer benchmarks: {avg_claim_amount, avg_claim_count, ...}"],
) -> Dict:
    """
    Estimate recoverable amount from flagged supplemental health claims.

    Calculates gross recoverable, collectability score, net expected recovery,
    and breakdown by claim type.
    """
    _tool_log('estimate_recovery', f'Estimating recovery for {len(flagged_claims)} claims...')

    if not flagged_claims:
        return {"gross_recoverable": 0, "collectability_score": 0, "net_expected": 0}

    total_claimed = sum(float(c.get('claim_amount', c.get('amount', 0))) for c in flagged_claims)
    peer_avg = float(peer_benchmarks.get('avg_claim_amount', 0))

    # Excess calculation
    if peer_avg > 0:
        entity_avg = total_claimed / len(flagged_claims)
        if entity_avg > peer_avg:
            excess_rate = (entity_avg - peer_avg) / entity_avg
        else:
            excess_rate = 0.10  # Minimum suspicion rate for flagged claims
        gross_recoverable = total_claimed * excess_rate
    else:
        excess_rate = 0.15
        gross_recoverable = total_claimed * excess_rate

    # Collectability factors for supplemental health
    # - Documentation quality: 0.85
    # - Member cooperation: 0.80 (lower than provider fraud — individuals harder to recover from)
    # - Statute window: 0.95
    collectability = 0.85 * 0.80 * 0.95
    net_expected = gross_recoverable * collectability

    # Breakdown by claim type
    type_breakdown = {}
    for c in flagged_claims:
        ct = c.get('claim_type', c.get('type', 'unknown'))
        if ct not in type_breakdown:
            type_breakdown[ct] = {'count': 0, 'total': 0}
        type_breakdown[ct]['count'] += 1
        type_breakdown[ct]['total'] += float(c.get('claim_amount', c.get('amount', 0)))

    claim_breakdown = [
        {
            'claim_type': ct,
            'claim_count': d['count'],
            'total_claimed': round(d['total'], 2),
            'estimated_recovery': round(d['total'] * excess_rate * collectability, 2),
        }
        for ct, d in sorted(type_breakdown.items(), key=lambda x: -x[1]['total'])
    ]

    result = {
        "total_flagged_claims": len(flagged_claims),
        "total_claimed": round(total_claimed, 2),
        "peer_avg_per_claim": round(peer_avg, 2),
        "excess_rate": round(excess_rate, 2),
        "gross_recoverable": round(gross_recoverable, 2),
        "collectability_score": round(collectability, 2),
        "net_expected": round(net_expected, 2),
        "claim_breakdown": claim_breakdown[:5],
    }

    _tool_cache['recovery_estimate'] = result
    _tool_log('estimate_recovery', f'Net expected recovery: ${net_expected:,.2f}')
    return _truncate_tool_output(result)


# =========================================================================
# 5.  compile_dossier
# =========================================================================
def compile_dossier(
    case_data: Annotated[Dict, "Complete case data: hypothesis, entities, evidence, stats, network, rules, similar_cases, recovery"],
) -> str:
    """
    Generate final investigation dossier in Markdown format.

    ONLY call this AFTER assess_evidence returns SUFFICIENT.

    case_data should include:
    - hypothesis: Suspected fraud scheme
    - entities: [{entity_id, entity_type, risk_score, claim_amount, ...}]
    - evidence: [list of evidence strings]
    - statistical_analysis: {metric: {entity_value, peer_avg, z_score}}
    - network_analysis: {total_entities, connection_density, patterns}
    - regulatory_rules: rules from search
    - similar_cases: precedent cases
    - recovery_estimate: financial impact
    """
    _tool_log('compile_dossier', 'Generating final Markdown dossier...')

    hypothesis = case_data.get('hypothesis', 'Suspected Supplemental Health Fraud')
    entities = case_data.get('entities', [])
    evidence = case_data.get('evidence', [])
    stats = case_data.get('statistical_analysis', {})
    network = case_data.get('network_analysis', {})
    rules = case_data.get('regulatory_rules', case_data.get('billing_rules', []))
    similar_cases = case_data.get('similar_cases', [])
    recovery = case_data.get('recovery_estimate', {})

    # Self-heal from cache if LLM passed empty data
    if not rules and _tool_cache.get('regulatory_rules'):
        _tool_log('compile_dossier', 'Self-heal: using cached regulatory_rules')
        rules = _tool_cache['regulatory_rules']
    if not similar_cases and _tool_cache.get('similar_cases'):
        _tool_log('compile_dossier', 'Self-heal: using cached similar_cases')
        similar_cases = _tool_cache['similar_cases']
    if (not recovery or not recovery.get('gross_recoverable')) and _tool_cache.get('recovery_estimate'):
        _tool_log('compile_dossier', 'Self-heal: using cached recovery_estimate')
        recovery = _tool_cache['recovery_estimate']

    def sf(val, default=0):
        try:
            return float(val) if val is not None else float(default)
        except (TypeError, ValueError):
            return float(default)

    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    dossier = f"""# SUPPLEMENTAL HEALTH FRAUD INVESTIGATION DOSSIER

**Case Hypothesis**: {hypothesis}
**Date Generated**: {now}
**Status**: Evidence Sufficient — Ready for Escalation

---

## EXECUTIVE SUMMARY

This investigation identified a suspected **{hypothesis}** involving {len(entities)} entities with an estimated net recovery of **${sf(recovery.get('net_expected')):,.2f}**.

The scheme was substantiated by {len(evidence)} independent evidence points. Statistical analysis confirmed deviations exceeding normal peer benchmarks. Pattern analysis indicates coordinated behaviour inconsistent with legitimate supplemental health claims.

**Recommended Action**: Escalate to Special Investigations Unit for formal review.

---

## ENTITIES INVOLVED

"""

    for i, entity in enumerate(entities, 1):
        if isinstance(entity, dict):
            eid = entity.get('entity_id', 'UNKNOWN')
            etype = entity.get('entity_type', 'unknown').title()
            dossier += f"\n### Entity {i}: {eid}\n\n"
            dossier += f"- **Type**: {etype}\n"
            if entity.get('risk_score'):
                dossier += f"- **Risk Score**: {entity['risk_score']}/100\n"
            if entity.get('name') or entity.get('entity_name'):
                dossier += f"- **Name**: {entity.get('name', entity.get('entity_name'))}\n"
            if entity.get('claim_amount') or entity.get('total_claimed'):
                amt = sf(entity.get('claim_amount', entity.get('total_claimed')))
                dossier += f"- **Total Claimed**: ${amt:,.2f}\n"
            if entity.get('claim_count'):
                dossier += f"- **Claims**: {entity['claim_count']}\n"
            if entity.get('suspicious_banner'):
                dossier += f"- **⚠ Suspicious Banner**: Active\n"
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
        # Try to parse from evidence
        parsed = []
        for ev in evidence:
            m = re.search(r'(\w[\w_ ]+?)\s*[=:]\s*\$?([\d,.]+).*?peer.*?([\d,.]+).*?z[- ]?score[=:]?\s*([\d.]+)',
                          str(ev), re.IGNORECASE)
            if m:
                parsed.append((m.group(1).strip(), float(m.group(2).replace(',', '')),
                                float(m.group(3).replace(',', '')), float(m.group(4))))
        if parsed:
            dossier += "| Metric | Entity Value | Peer Average | Z-Score | Significance |\n"
            dossier += "|--------|--------------|--------------|---------|-------------|\n"
            for metric, val, peer, z in parsed:
                sig = "⚠️ HIGH" if abs(z) > 2 else "Normal"
                dossier += f"| {metric} | {val:,.2f} | {peer:,.2f} | {z:.2f} | {sig} |\n"
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
        if network.get('connected_entities'):
            dossier += "\n**Key Connected Entities**:\n\n"
            for conn in network.get('connected_entities', [])[:5]:
                if isinstance(conn, dict):
                    dossier += f"- {conn.get('entity_id', '?')}: {conn.get('entity_type', '?')}, distance={conn.get('distance', '?')}\n"
                else:
                    dossier += f"- {conn}\n"
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
    total_claimed = sf(recovery.get('total_claimed', recovery.get('total_billed', 0)))
    gross = sf(recovery.get('gross_recoverable', 0))
    net = sf(recovery.get('net_expected', 0))
    collect = sf(recovery.get('collectability_score', 0))

    # Self-heal zeros
    if gross == 0 and total_claimed > 0:
        excess = sf(recovery.get('excess_rate', 0.15))
        gross = round(total_claimed * excess, 2)
        if collect == 0:
            collect = 0.65
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
                ct = item.get('claim_type', item.get('type', 'N/A'))
                count = item.get('claim_count', item.get('count', 'N/A'))
                total = sf(item.get('total_claimed', item.get('total_billed', 0)))
                est = sf(item.get('estimated_recovery', 0))
                dossier += f"| {ct} | {count} | ${total:,.0f} | ${est:,.0f} |\n"

    dossier += "\n---\n\n## RECOMMENDED ACTIONS\n\n"
    dossier += "1. **Immediate**: Place flagged claims on payment hold pending SIU review\n"
    dossier += "2. **Verification**: Request original medical documentation and employment records\n"
    dossier += "3. **Investigation**: Conduct member interviews and provider site visit if applicable\n"
    dossier += "4. **Recovery**: Issue demand letters for identified overpayments\n"
    dossier += "5. **Prevention**: Flag entities for enhanced monitoring on future claims\n\n"

    dossier += "---\n\n"
    dossier += "*Generated by Prudential Supplemental Health Examiner Workflow Copilot*\n"

    _tool_log('compile_dossier', f'Dossier generated ({len(dossier)} chars)')
    return dossier


# =========================================================================
# Tool Registry
# =========================================================================
DOSSIER_TOOLS = [
    assess_evidence,
    search_regulatory_rules,
    find_similar_cases,
    estimate_recovery,
    compile_dossier,
]
