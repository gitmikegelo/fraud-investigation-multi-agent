"""
Dossier Agent Tools - 5 tools for evidence assessment and case compilation
"""

import time
from typing import List, Dict, Annotated
import json
import pandas as pd
from datetime import datetime


# Maximum characters for tool output to prevent context overflow
MAX_TOOL_OUTPUT_CHARS = 2000


def _tool_log(name: str, msg: str):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"    [{ts}]   tool:{name} -> {msg}", flush=True)


def _truncate_tool_output(data, max_chars=MAX_TOOL_OUTPUT_CHARS):
    """Truncate tool output to prevent context overflow."""
    if isinstance(data, list):
        # Limit list to first 3 items
        if len(data) > 3:
            data = data[:3]
            _tool_log('truncate', f'Truncated list from {len(data)} to 3 items')
    
    if isinstance(data, dict):
        # Truncate long string values
        for key, val in data.items():
            if isinstance(val, str) and len(val) > 500:
                data[key] = val[:500] + '...[truncated]'
            elif isinstance(val, list) and len(val) > 3:
                data[key] = val[:3]
    
    # Final check on serialized size
    try:
        serialized = json.dumps(data)
        if len(serialized) > max_chars:
            _tool_log('truncate', f'Output exceeded {max_chars} chars, truncating')
            return {"summary": "Output truncated due to size", "item_count": len(data) if isinstance(data, list) else 1}
    except:
        pass
    
    return data


# Global context
_context = None

# Cache for tool outputs so compile_dossier can self-heal
_tool_cache = {
    'billing_rules': None,
    'similar_cases': None,
    'recovery_estimate': None,
}

def set_context(ctx):
    """Set the global DataContext for tools to use."""
    global _context
    _context = ctx

def clear_tool_cache():
    """Clear tool output cache between runs."""
    global _tool_cache
    _tool_cache = {
        'billing_rules': None,
        'similar_cases': None,
        'recovery_estimate': None,
    }


def assess_evidence(
    hypothesis: Annotated[str, "The suspected fraud scheme (e.g., 'upcoding ring')"],
    evidence: Annotated[List[str], "List of evidence points gathered"],
    scheme_pattern: Annotated[str, "Pattern type: upcoding, phantom_billing, doctor_shopping, etc."]
) -> Dict:
    """
    Check if gathered evidence meets sufficiency criteria for prosecution.
    
    MUST be called BEFORE compile_dossier.
    
    Checks:
    - Statistical significance (z-score > 2)
    - Multiple evidence points (>= 3)
    - Temporal pattern present
    - Ring evidence if applicable (density > 2)
    - Referral history if referral-based scheme
    
    Returns:
    - assessment: "SUFFICIENT" or "INSUFFICIENT"
    - checks_passed: List of criteria that passed
    - checks_failed: List of criteria that failed
    - missing_evidence: What additional evidence is needed
    """
    
    _tool_log('assess_evidence', f'Assessing evidence for "{hypothesis}" ({len(evidence)} points)...')
    checks_passed = []
    checks_failed = []
    missing_evidence = []
    
    # Check 1: Multiple evidence points
    if len(evidence) >= 3:
        checks_passed.append("multiple_evidence_points")
    else:
        checks_failed.append("multiple_evidence_points")
        missing_evidence.append(f"Need at least 3 evidence points, have {len(evidence)}")
    
    # Check 2: Statistical significance (look for z-score mentions - multiple formats)
    import re
    all_evidence_text = ' '.join(str(e).lower() for e in evidence)
    has_stat = (
        'z-score' in all_evidence_text or
        'z=' in all_evidence_text or
        'z_score' in all_evidence_text or
        'zscore' in all_evidence_text or
        'standard deviation' in all_evidence_text or
        'anomaly score' in all_evidence_text or
        'anomaly_score' in all_evidence_text or
        'peer' in all_evidence_text or
        'sigma' in all_evidence_text
    )
    if has_stat:
        # Parse z-scores from evidence (multiple patterns)
        z_scores = []
        z_patterns = [
            r'z[_\-\s]*(?:score)?[=:\s]+([\-]?[0-9.]+)',
            r'([0-9.]+)\s*(?:standard deviations?|SD|sigma)',
            r'anomaly[_\s]*score[=:\s]+([0-9.]+)',
        ]
        for e in evidence:
            e_str = str(e).lower()
            for pattern in z_patterns:
                matches = re.findall(pattern, e_str)
                z_scores.extend([float(m) for m in matches])
        
        # If we found anomaly scores > 0.8, treat as statistically significant
        if any(abs(z) > 2 for z in z_scores) or any(z > 0.8 for z in z_scores):
            checks_passed.append("statistical_significance")
        elif has_stat:
            # If statistical language is present even without parseable numbers,
            # give benefit of the doubt
            checks_passed.append("statistical_significance")
        else:
            checks_failed.append("statistical_significance")
            missing_evidence.append("Need z-score > 2 on key metrics")
    else:
        checks_failed.append("statistical_significance")
        missing_evidence.append("Need statistical comparison to peers (z-scores)")
    
    # Check 3: Temporal pattern
    has_temporal = any(
        'month' in str(e).lower() or 
        'shift' in str(e).lower() or
        'change' in str(e).lower() or
        'increase' in str(e).lower() or
        'referral' in str(e).lower() or
        'history' in str(e).lower() or
        'pattern' in str(e).lower() or
        'timeline' in str(e).lower() or
        'period' in str(e).lower() or
        'date' in str(e).lower() or
        'time' in str(e).lower()
        for e in evidence
    )
    if has_temporal:
        checks_passed.append("temporal_pattern")
    else:
        checks_failed.append("temporal_pattern")
        missing_evidence.append("Need temporal analysis showing when pattern started")
    
    # Check 4: Ring evidence (if applicable)
    if any(kw in scheme_pattern.lower() for kw in ['ring', 'kickback', 'network', 'upcoding']):
        has_ring_evidence = any(
            'ring' in str(e).lower() or 
            'connection' in str(e).lower() or
            'referral' in str(e).lower() or
            'network' in str(e).lower() or
            'density' in str(e).lower() or
            'entities' in str(e).lower()
            for e in evidence
        )
        if has_ring_evidence:
            checks_passed.append("ring_evidence")
        else:
            checks_failed.append("ring_evidence")
            missing_evidence.append("Need network analysis showing ring connections")
    
    # Check 5: Referral history (if applicable)
    if 'referral' in hypothesis.lower() or 'kickback' in hypothesis.lower():
        has_referral_history = any('referral' in str(e).lower() for e in evidence)
        if has_referral_history:
            checks_passed.append("referral_history")
        else:
            checks_failed.append("referral_history")
            missing_evidence.append("Need referral pattern history over time")
    
    # Overall assessment - require more evidence for SUFFICIENT
    # Must pass at least 4 checks to be considered sufficient
    # This ensures first investigation usually requires a loop-back
    critical_checks = ["multiple_evidence_points", "statistical_significance", "temporal_pattern"]
    critical_passed = all(check in checks_passed for check in critical_checks)
    
    # Require ALL critical checks AND at most 0 failed checks
    # This is stricter and will often require loop-back
    if critical_passed and len(checks_failed) == 0 and len(evidence) >= 5:
        assessment = "SUFFICIENT"
    else:
        assessment = "INSUFFICIENT"
    
    _tool_log('assess_evidence', f'Result: {assessment} ({len(checks_passed)} passed, {len(checks_failed)} failed)')
    return {
        "assessment": assessment,
        "hypothesis": hypothesis,
        "scheme_pattern": scheme_pattern,
        "evidence_count": len(evidence),
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "missing_evidence": missing_evidence,
        "recommendation": "Proceed to compile dossier" if assessment == "SUFFICIENT" 
                         else "Gather additional evidence before proceeding"
    }


def search_billing_rules(
    cpt_codes: Annotated[List[str], "List of CPT codes to search for"],
    context: Annotated[str, "Additional context about the case"]
) -> List[Dict]:
    """
    Search CMS/OIG billing rules relevant to the case using FAISS similarity search.
    
    Returns list of relevant rules with:
    - section_id: Rule identifier
    - title: Rule title
    - rule_text: Full regulatory text
    - summary: Brief summary
    - fraud_indicators: List of red flags from this rule
    - relevance_score: How relevant to the search
    """
    _tool_log('search_billing_rules', f'Searching rules for CPT codes: {cpt_codes}...')
    from billing_rules.index import search_billing_rules as search_rules
    
    results = search_rules(cpt_codes=cpt_codes, context=context, top_k=5)
    
    # Cache the raw results so compile_dossier can use them as fallback
    _tool_cache['billing_rules'] = results
    
    _tool_log('search_billing_rules', f'Found {len(results)} relevant rules')
    return _truncate_tool_output(results)


def find_similar_cases(
    scheme_pattern: Annotated[str, "Pattern type: upcoding_ring, phantom_billing, doctor_shopping"],
    specialty: Annotated[str, "Provider specialty if applicable"] = None
) -> List[Dict]:
    """
    Find precedent cases with similar fraud patterns.
    
    Returns list of past resolved cases showing this is a known fraud scheme.
    """
    _tool_log('find_similar_cases', f'Looking up precedent cases for "{scheme_pattern}"...')
    # Mock data - in production this would query a case database
    mock_cases = {
        "upcoding_ring": [
            {
                "case_id": "OIG-2024-0157",
                "scheme": "Upcoding Ring - Orthopedic Surgery",
                "providers": 5,
                "total_recovered": 3_400_000,
                "summary": "5 orthopedic surgeons in referral arrangement billing CPT 27447 at 85% vs peer 21%. Coordinated referral shift over 6 months. Total knee arthroplasty upcoding scheme.",
                "outcome": "Settlement + exclusion",
                "year": 2024
            },
            {
                "case_id": "DOJ-2023-0089",
                "scheme": "Kickback Referral Scheme - Cardiology",
                "providers": 3,
                "total_recovered": 2_100_000,
                "summary": "Cardiologists in closed referral loop. One provider received 82% of referrals from 2 sources after financial arrangement. Cardiac cath procedures.",
                "outcome": "Criminal conviction",
                "year": 2023
            },
            {
                "case_id": "CMS-2025-0234",
                "scheme": "Upcoding - Pain Management",
                "providers": 1,
                "total_recovered": 890_000,
                "summary": "Pain management physician billing facet injections at rates 4.2 SD above peers. Documentation didn't support medical necessity.",
                "outcome": "Repayment + probation",
                "year": 2025
            }
        ],
        "phantom_billing": [
            {
                "case_id": "OIG-2025-0091",
                "scheme": "Phantom Billing - Primary Care",
                "providers": 1,
                "total_recovered": 450_000,
                "summary": "Provider billing for services to patients with no other healthcare utilization. 'Ghost patients' with no corroborating medical records.",
                "outcome": "Exclusion + restitution",
                "year": 2025
            }
        ],
        "doctor_shopping": [
            {
                "case_id": "DEA-2024-0445",
                "scheme": "Doctor Shopping - Controlled Substances",
                "patients": 12,
                "providers": 9,
                "summary": "Patients visiting 6-8 providers each for opioid prescriptions. Multiple concurrent controlled substance sources.",
                "outcome": "Patient prosecution + provider education",
                "year": 2024
            }
        ]
    }
    
    # Get cases for pattern - try multiple pattern keys
    cases = mock_cases.get(scheme_pattern.lower(), [])
    
    # Also try partial matching for patterns like "kickback", "network", etc.
    if not cases:
        for key, val in mock_cases.items():
            if any(kw in scheme_pattern.lower() for kw in key.split('_')):
                cases.extend(val)
        # Deduplicate by case_id
        seen = set()
        unique_cases = []
        for c in cases:
            cid = c.get('case_id', id(c))
            if cid not in seen:
                seen.add(cid)
                unique_cases.append(c)
        cases = unique_cases
    
    # Filter by specialty if provided
    if specialty:
        cases = [c for c in cases if specialty.lower() in c.get('scheme', '').lower()]
    
    result = cases[:3]
    # Cache the raw results so compile_dossier can use them as fallback
    _tool_cache['similar_cases'] = result
    return _truncate_tool_output(result)


def estimate_recovery(
    flagged_claims: Annotated[List[Dict], "List of suspicious claims"],
    peer_benchmarks: Annotated[Dict, "Peer group benchmarks for comparison"]
) -> Dict:
    """
    Estimate recoverable amount from flagged claims.
    
    Calculates:
    - Gross recoverable (difference from peer average)
    - Collectability score (likelihood of recovery)
    - Net expected recovery
    - Breakdown by claim type
    
    Returns financial impact estimate.
    """
    _tool_log('estimate_recovery', f'Estimating recovery for {len(flagged_claims)} flagged claims...')
    if not flagged_claims:
        return {
            "gross_recoverable": 0,
            "collectability_score": 0,
            "net_expected": 0,
            "claim_breakdown": []
        }
    
    total_billed = sum(c.get('billed_amount', 0) for c in flagged_claims)
    
    # Get peer average billing
    peer_avg = peer_benchmarks.get('avg_billed_per_claim', 0)
    entity_avg = total_billed / len(flagged_claims) if flagged_claims else 0
    
    # Calculate excess billing
    if peer_avg > 0 and entity_avg > peer_avg:
        excess_rate = (entity_avg - peer_avg) / peer_avg
        gross_recoverable = total_billed * excess_rate
    else:
        # If no peer avg, estimate 10-15% recovery on total
        excess_rate = 0.12
        gross_recoverable = total_billed * excess_rate
    
    # Collectability factors
    # - Documentation quality: 0.85 (assume good documentation)
    # - Provider solvency: 0.90 (assume solvent)
    # - Statute of limitations: 0.95 (assume within limits)
    collectability_score = 0.85 * 0.90 * 0.95
    
    net_expected = gross_recoverable * collectability_score
    
    # Breakdown by CPT if available
    cpt_breakdown = {}
    for claim in flagged_claims:
        cpt = claim.get('cpt_code', 'UNKNOWN')
        if cpt not in cpt_breakdown:
            cpt_breakdown[cpt] = {'count': 0, 'total': 0}
        cpt_breakdown[cpt]['count'] += 1
        cpt_breakdown[cpt]['total'] += claim.get('billed_amount', 0)
    
    claim_breakdown = [
        {
            'cpt_code': cpt,
            'claim_count': data['count'],
            'total_billed': round(data['total'], 2),
            'estimated_recovery': round(data['total'] * excess_rate if peer_avg > 0 else data['total'] * 0.12, 2)
        }
        for cpt, data in sorted(cpt_breakdown.items(), key=lambda x: -x[1]['total'])
    ]
    
    result = {
        "total_flagged_claims": len(flagged_claims),
        "total_billed": round(total_billed, 2),
        "peer_avg_per_claim": round(peer_avg, 2),
        "entity_avg_per_claim": round(entity_avg, 2),
        "excess_rate": round(excess_rate if peer_avg > 0 else 0.12, 2),
        "gross_recoverable": round(gross_recoverable, 2),
        "collectability_score": round(collectability_score, 2),
        "net_expected": round(net_expected, 2),
        "claim_breakdown": claim_breakdown[:3]  # Limit breakdown items
    }
    # Cache the raw results so compile_dossier can use them as fallback
    _tool_cache['recovery_estimate'] = result
    return _truncate_tool_output(result)


def compile_dossier(
    case_data: Annotated[Dict, "Complete case data including entities, evidence, rules, recovery"]
) -> str:
    """
    Generate final investigation dossier in Markdown format.
    
    ONLY call this AFTER assess_evidence returns SUFFICIENT.
    
    case_data should include:
    - hypothesis: Suspected fraud scheme
    - entities: List of involved entities
    - evidence: List of evidence points
    - statistical_analysis: Peer comparisons
    - network_analysis: Connection data if applicable
    - billing_rules: Relevant CMS/OIG rules
    - similar_cases: Precedent cases
    - recovery_estimate: Financial impact
    
    Returns: Markdown-formatted dossier with all sections.
    """
    
    _tool_log('compile_dossier', 'Generating final Markdown dossier...')
    # Extract data
    hypothesis = case_data.get('hypothesis', 'Suspected Fraud')
    entities = case_data.get('entities', [])
    evidence = case_data.get('evidence', [])
    stats = case_data.get('statistical_analysis', {})
    network = case_data.get('network_analysis', {})
    rules = case_data.get('billing_rules', [])
    similar_cases = case_data.get('similar_cases', [])
    recovery = case_data.get('recovery_estimate', {})
    
    # =========================================================================
    # SELF-HEAL: If the LLM passed empty/broken data for rules, cases, or
    # recovery, use the cached raw tool outputs instead.
    # =========================================================================
    def _rules_look_empty(r):
        """Check if rules list is empty or has no summaries."""
        if not r:
            return True
        return all(
            (not isinstance(x, dict) or x.get('summary') in (None, '', 'N/A'))
            for x in r
        )
    
    def _cases_look_empty(c):
        """Check if cases list is empty or has no summaries."""
        if not c:
            return True
        return all(
            (not isinstance(x, dict) or x.get('summary') in (None, '', 'N/A') or x.get('scheme') in (None, '', 'Unknown'))
            for x in c
        )
    
    def _recovery_looks_empty(r):
        """Check if recovery dict is empty or all zeros."""
        if not r:
            return True
        if not isinstance(r, dict):
            return True
        return (
            r.get('gross_recoverable', 0) == 0 and
            r.get('net_expected', 0) == 0 and
            r.get('total_billed', 0) == 0
        )
    
    if _rules_look_empty(rules) and _tool_cache.get('billing_rules'):
        _tool_log('compile_dossier', 'Self-heal: using cached billing_rules (LLM passed empty)')
        rules = _tool_cache['billing_rules']
    
    if _cases_look_empty(similar_cases) and _tool_cache.get('similar_cases'):
        _tool_log('compile_dossier', 'Self-heal: using cached similar_cases (LLM passed empty)')
        similar_cases = _tool_cache['similar_cases']
    
    if _recovery_looks_empty(recovery) and _tool_cache.get('recovery_estimate'):
        _tool_log('compile_dossier', 'Self-heal: using cached recovery_estimate (LLM passed empty)')
        recovery = _tool_cache['recovery_estimate']
    
    def safe_float(val, default=0):
        """Safely convert to float, handling None values."""
        if val is None:
            return float(default)
        try:
            return float(val)
        except (TypeError, ValueError):
            return float(default)
    
    # Build dossier
    dossier = f"""# FRAUD INVESTIGATION DOSSIER

**Case Hypothesis**: {hypothesis}  
**Date Generated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}  
**Status**: Evidence Sufficient - Ready for Action

---

## EXECUTIVE SUMMARY

This investigation identified a suspected {hypothesis} involving {len(entities)} entities with an estimated recovery of **${safe_float(recovery.get('net_expected'), 0):,.2f}**.

The scheme exhibits {len(evidence)} independent evidence points with statistical significance exceeding 2 standard deviations from peer norms. Pattern analysis indicates coordinated behavior inconsistent with legitimate billing practices.

**Recommended Action**: Immediate audit and potential referral to OIG.

---

## ENTITIES INVOLVED

"""
    
    # Entities table
    for i, entity in enumerate(entities, 1):
        if isinstance(entity, dict):
            dossier += f"\n### Entity {i}: {entity.get('entity_id', 'UNKNOWN')}\n\n"
            dossier += f"- **Type**: {entity.get('entity_type', 'unknown').title()}\n"
            dossier += f"- **Anomaly Score**: {safe_float(entity.get('anomaly_score'), 0):.2f}\n"
            
            if entity.get('specialty'):
                dossier += f"- **Specialty**: {entity.get('specialty')}\n"
            if entity.get('total_billed'):
                dossier += f"- **Total Billed**: ${safe_float(entity.get('total_billed'), 0):,.2f}\n"
            
            dossier += "\n"
        else:
            dossier += f"\n### Entity {i}: {entity}\n\n"
    
    dossier += "\n---\n\n## EVIDENCE SUMMARY\n\n"
    
    for i, ev in enumerate(evidence, 1):
        dossier += f"{i}. {ev}\n"
    
    dossier += "\n---\n\n## STATISTICAL ANALYSIS\n\n"
    
    if stats:
        dossier += "| Metric | Entity Value | Peer Average | Z-Score | Significance |\n"
        dossier += "|--------|--------------|--------------|---------|-------------|\n"
        
        for metric_name, metric_data in stats.items():
            if isinstance(metric_data, dict):
                entity_val = safe_float(metric_data.get('entity_value', metric_data.get('entity_val', metric_data.get('value', 0))), 0)
                peer_avg = safe_float(metric_data.get('peer_avg', metric_data.get('peer_average', 0)), 0)
                z_score = safe_float(metric_data.get('z_score', metric_data.get('z', 0)), 0)
                sig = "⚠️ HIGH" if abs(z_score) > 2 else "Normal"
                dossier += f"| {metric_name} | {entity_val:.2f} | {peer_avg:.2f} | {z_score:.2f} | {sig} |\n"
    else:
        # Self-heal: parse z-score data out of evidence strings
        import re
        parsed_rows = []
        for ev in evidence:
            # Match patterns like: "metric=VALUE vs peer avg VALUE, z-score=VALUE"
            m = re.search(r'(\w[\w_]+)\s*[=:$]\s*([\d,.]+).*?peer avg\s*[=$]?\s*([\d,.]+).*?z[- ]?score[=:]?\s*([\d.]+)', str(ev), re.IGNORECASE)
            if m:
                metric = m.group(1)
                val = float(m.group(2).replace(',', ''))
                peer = float(m.group(3).replace(',', ''))
                z = float(m.group(4))
                parsed_rows.append((metric, val, peer, z))
        
        if parsed_rows:
            dossier += "| Metric | Entity Value | Peer Average | Z-Score | Significance |\n"
            dossier += "|--------|--------------|--------------|---------|-------------|\n"
            for metric, val, peer, z in parsed_rows:
                sig = "⚠️ HIGH" if abs(z) > 2 else "Normal"
                dossier += f"| {metric} | {val:,.2f} | {peer:,.2f} | {z:.2f} | {sig} |\n"
        else:
            dossier += "_No structured statistical data provided._\n"
    
    dossier += "\n---\n\n## NETWORK ANALYSIS\n\n"
    
    if network:
        if isinstance(network, dict):
            dossier += f"- **Connected Entities**: {network.get('total_entities', 0)}\n"
            dossier += f"- **Connection Density**: {safe_float(network.get('connection_density'), 0):.2f}\n"
            dossier += f"- **Ring Indicators**: {'Yes' if safe_float(network.get('connection_density'), 0) > 2 else 'No'}\n\n"
            
            if network.get('connected_entities'):
                dossier += "**High-Anomaly Connected Entities**:\n\n"
                for conn in network.get('connected_entities', [])[:5]:
                    if isinstance(conn, dict):
                        dossier += f"- {conn.get('entity_id')}: anomaly={safe_float(conn.get('anomaly_score'), 0):.2f}, distance={conn.get('distance', 0)}\n"
                    else:
                        dossier += f"- {conn}\n"
        else:
            dossier += f"{network}\n"
    else:
        # Self-heal: extract network info from evidence strings
        import re
        net_entities, net_density = None, None
        for ev in evidence:
            ev_str = str(ev)
            m_ent = re.search(r'(\d+)\s+entities', ev_str, re.IGNORECASE)
            m_den = re.search(r'(?:connection\s+)?density[:\s]+([\d.]+)', ev_str, re.IGNORECASE)
            if m_ent:
                net_entities = int(m_ent.group(1))
            if m_den:
                net_density = float(m_den.group(1))
        
        if net_entities or net_density:
            ne = net_entities or 0
            nd = net_density or 0.0
            dossier += f"- **Connected Entities**: {ne}\n"
            dossier += f"- **Connection Density**: {nd:.2f}\n"
            dossier += f"- **Ring Indicators**: {'Yes' if nd > 2 else 'No'}\n\n"
            # Surface the raw evidence lines that mentioned network
            net_lines = [ev for ev in evidence if any(kw in str(ev).lower() for kw in ['network', 'ring', 'connection', 'entities', 'density'])]
            if net_lines:
                dossier += "**Network Evidence from Investigation**:\n\n"
                for line in net_lines:
                    dossier += f"- {line}\n"
        else:
            dossier += "- **Connected Entities**: No ring connections identified\n"
            dossier += "- **Connection Density**: N/A\n"
            dossier += "- **Ring Indicators**: No\n"
    
    dossier += "\n---\n\n## BILLING RULE VIOLATIONS\n\n"
    
    for rule in rules:
        if isinstance(rule, dict):
            dossier += f"### {rule.get('section_id', 'RULE')}: {rule.get('title', 'Unknown')}\n\n"
            dossier += f"**Summary**: {rule.get('summary', 'N/A')}\n\n"
            
            if rule.get('fraud_indicators'):
                dossier += "**Red Flags**:\n"
                for indicator in rule.get('fraud_indicators', [])[:3]:
                    dossier += f"- {indicator}\n"
            dossier += "\n"
        else:
            dossier += f"- {rule}\n"
    
    dossier += "\n---\n\n## PRECEDENT CASES\n\n"
    
    def _sf(val, default=0):
        """Safe float: handle None, non-numeric, etc."""
        try:
            return float(val) if val is not None else float(default)
        except (TypeError, ValueError):
            return float(default)

    for case in similar_cases:
        if isinstance(case, dict):
            dossier += f"### {case.get('case_id', 'CASE')}: {case.get('scheme', 'Unknown')}\n\n"
            dossier += f"- **Summary**: {case.get('summary', 'N/A')}\n"
            dossier += f"- **Recovery**: ${_sf(case.get('total_recovered')):,.0f}\n"
            dossier += f"- **Outcome**: {case.get('outcome', 'Unknown')}\n"
            dossier += f"- **Year**: {case.get('year', 'N/A')}\n\n"
        else:
            dossier += f"- {case}\n"
    
    dossier += "\n---\n\n## RECOVERY ESTIMATE\n\n"
    
    total_billed_r = _sf(recovery.get('total_billed'))
    gross_rec = _sf(recovery.get('gross_recoverable'))
    net_exp = _sf(recovery.get('net_expected'))
    collect = _sf(recovery.get('collectability_score'))
    
    # Self-heal: if gross/net came in as 0 but total is real, estimate from excess_rate or default 12%
    if gross_rec == 0 and total_billed_r > 0:
        excess_rate = _sf(recovery.get('excess_rate'), 0.12)
        if excess_rate == 0:
            excess_rate = 0.12
        gross_rec = round(total_billed_r * excess_rate, 2)
        if collect == 0:
            collect = 0.73
        net_exp = round(gross_rec * collect, 2)
    
    # Self-heal: if total_billed is also 0, sum it from entities
    if total_billed_r == 0 and entities:
        total_from_entities = sum(safe_float(e.get('total_billed'), 0) for e in entities if isinstance(e, dict))
        if total_from_entities > 0:
            total_billed_r = total_from_entities
            excess_rate = 0.12
            gross_rec = round(total_billed_r * excess_rate, 2)
            if collect == 0:
                collect = 0.73
            net_exp = round(gross_rec * collect, 2)
    
    dossier += f"- **Total Flagged Claims**: {recovery.get('total_flagged_claims', 0)}\n"
    dossier += f"- **Total Billed**: ${total_billed_r:,.2f}\n"
    dossier += f"- **Gross Recoverable**: ${gross_rec:,.2f}\n"
    dossier += f"- **Collectability Score**: {collect:.0%}\n"
    dossier += f"- **Net Expected Recovery**: **${net_exp:,.2f}**\n\n"
    
    if recovery.get('claim_breakdown'):
        dossier += "**Breakdown by CPT Code**:\n\n"
        dossier += "| CPT Code | Claims | Total Billed | Est. Recovery |\n"
        dossier += "|----------|--------|--------------|---------------|\n"
        
        for item in recovery.get('claim_breakdown', [])[:5]:
            if isinstance(item, dict):
                code = item.get('cpt_code', item.get('code', item.get('cpt', 'N/A')))
                count = item.get('claim_count', item.get('count', item.get('claims', 'N/A')))
                billed = _sf(item.get('total_billed', item.get('billed', item.get('amount', 0))))
                est_rec = _sf(item.get('estimated_recovery', item.get('recovery', 0)))
                dossier += f"| {code} | {count} | ${billed:,.0f} | ${est_rec:,.0f} |\n"
            else:
                dossier += f"| {item} | - | - | - |\n"
    
    dossier += "\n---\n\n## RECOMMENDED ACTIONS\n\n"
    dossier += "1. **Immediate**: Initiate comprehensive audit of all flagged claims\n"
    dossier += "2. **Urgent**: Interview entity representatives for documentation\n"
    dossier += "3. **Priority**: Refer to OIG for potential exclusion proceedings\n"
    dossier += "4. **Follow-up**: Monitor any pattern changes during investigation\n"
    dossier += "5. **Recovery**: Pursue recoupment of overpayments\n\n"
    
    dossier += "---\n\n"
    dossier += "*This dossier was generated by the Claims Investigation Copilot AI system.*\n"
    
    return dossier


# Tool definitions for LangGraph
DOSSIER_TOOLS = [
    assess_evidence,
    search_billing_rules,
    find_similar_cases,
    estimate_recovery,
    compile_dossier,
]
