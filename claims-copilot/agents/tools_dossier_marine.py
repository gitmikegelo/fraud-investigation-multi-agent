"""
Dossier Agent Tools (Marine Cargo) — evidence assessment and case compilation for marine
cargo claims.

Regulatory references cover the Institute Cargo Clauses (A) 2009, the Hague-Visby Rules,
SOLAS VGM, the Marine Insurance Act 1906 / Insurance Act 2015 (English law), and internal
claims guidelines (MC-GL-xx). Precedent cases (MC-SIU-2025-xxxx) are fictional internal
examples for demonstration.
"""

import json
import functools
from typing import List, Dict, Annotated, Optional
from datetime import datetime

from langchain_core.tools import tool


MAX_TOOL_OUTPUT_CHARS = 5000


def _tool_log(name: str, msg: str):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"    [{ts}]   tool:{name} -> {msg}", flush=True)


def _truncate_tool_output(data, max_chars=MAX_TOOL_OUTPUT_CHARS):
    """Keep tool output within budget without dropping whole results."""
    try:
        if len(json.dumps(data, default=str)) <= max_chars:
            return data
    except Exception:
        return data
    if isinstance(data, list):
        slim = []
        for item in data[:8]:
            if isinstance(item, dict):
                item = {k: (v[:2] if isinstance(v, list) else (v[:260] + '...' if isinstance(v, str) and len(v) > 260 else v))
                        for k, v in item.items()}
            slim.append(item)
        return slim
    if isinstance(data, dict):
        return {k: (v[:3] if isinstance(v, list) else (v[:500] + '...' if isinstance(v, str) and len(v) > 500 else v))
                for k, v in data.items()}
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


def _safe(fallback=None):
    """Never raise: return an error payload (or a fallback factory's result) instead."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                try:
                    _tool_log(fn.__name__, f"ERROR: {str(e)[:150]}")
                except Exception:
                    pass
                if fallback:
                    return fallback(e)
                return {"error": f"{fn.__name__} failed: {str(e)[:200]}"}
        return wrapper
    return deco


# =========================================================================
# 1.  assess_evidence
# =========================================================================
@tool
@_safe()
def assess_evidence(
    hypothesis: Annotated[str, "Suspected scheme (e.g. 'over-valued, part-phantom cargo with colluding surveyor')"],
    evidence: Annotated[List[str], "List of evidence points gathered"],
    scheme_pattern: Annotated[str, "Pattern: overvalued_phantom_cargo, overvaluation, phantom_cargo, surveyor_collusion, surveyor_ring, reused_photos, repeat_claimant, coverage_exclusion"],
) -> Dict:
    """
    Check whether the gathered evidence meets the sufficiency criteria for escalation.
    MUST be called BEFORE compile_dossier.
    """
    evidence = [str(e) for e in (evidence or [])]
    _tool_log('assess_evidence', f'Assessing "{hypothesis}" ({len(evidence)} points)...')
    checks_passed, checks_failed, missing = [], [], []
    all_text = ' '.join(e.lower() for e in evidence)
    pattern = (scheme_pattern or '').lower()

    if len(evidence) >= 3:
        checks_passed.append("multiple_evidence_points")
    else:
        checks_failed.append("multiple_evidence_points")
        missing.append(f"Need >= 3 independent evidence points (have {len(evidence)}). Profile the claimant, "
                       "surveyor and forwarder, and cross-check the shipping documents.")

    stat_kw = ['z-score', 'z_score', 'z=', 'peer', 'benchmark', 'average', 'mean', 'ratio', 'x the',
               'risk score', 'risk_score', 'claim rate', '%', 'vgm', 'kg']
    if any(kw in all_text for kw in stat_kw):
        checks_passed.append("statistical_significance")
    else:
        checks_failed.append("statistical_significance")
        missing.append("Need a quantitative comparison: unit price vs market benchmark, VGM vs declared weight, "
                       "or compare_to_peers() z-score on claim_amount / claim_rate.")

    temporal_kw = ['date', 'day', 'month', 'timeline', 'after discharge', 'history', 'incorporated',
                   'filed', 'prior', 'survey', 'notice', 'period', 'trend']
    if any(kw in all_text for kw in temporal_kw):
        checks_passed.append("temporal_pattern")
    else:
        checks_failed.append("temporal_pattern")
        missing.append("Need timing analysis: survey date vs discharge date, notice to carrier, seller's "
                       "incorporation date, or the claimant's claim history over time.")

    if any(kw in pattern for kw in ['ring', 'collusion', 'network', 'surveyor']):
        net_kw = ['director', 'address', 'network', 'ring', 'linked', 'shared', 'connection', 'watchlist',
                  'panel', 'common control']
        if any(kw in all_text for kw in net_kw):
            checks_passed.append("network_evidence")
        else:
            checks_failed.append("network_evidence")
            missing.append("Need network evidence for a collusion pattern. Call find_connections() on the "
                           "claimant and find_ring() to surface shared directors and addresses.")

    rule_kw = ['rule', 'r-0', 'icc', 'hague', 'mia', 'clause', 'mc-gl', 'solas', 'exclusion', 'triggered']
    if any(kw in all_text for kw in rule_kw):
        checks_passed.append("regulatory_citation")
    else:
        checks_failed.append("regulatory_citation")
        missing.append("Need rule / clause context. Call search_regulatory_rules() for the applicable ICC, "
                       "Hague-Visby, MIA and internal guideline references.")

    if any(kw in pattern for kw in ['phantom', 'valu', 'photo', 'short']):
        doc_kw = ['vgm', 'b/l', 'bill of lading', 'invoice', 'packing list', 'photo', 'eir', 'seal',
                  'weight', 'unit price', 'survey report', 'hash']
        if any(kw in all_text for kw in doc_kw):
            checks_passed.append("document_evidence")
        else:
            checks_failed.append("document_evidence")
            missing.append("Need document evidence: B/L vs invoice vs packing list vs VGM cross-check, seals / EIR, "
                           "or evidence-photo forensics.")

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
# 2.  search_regulatory_rules  (marine cargo references)
# =========================================================================
ALL_TYPES = ["breakage", "wet_damage", "contamination", "shortage", "theft_pilferage"]

RULES = [
    # ── Institute Cargo Clauses (A) 2009 ────────────────────────────────────
    {
        "section_id": "ICC-1",
        "source": "Institute Cargo Clauses (A) 2009, cl. 1",
        "title": "Risks Covered — All Risks",
        "summary": "Covers all risks of loss of or damage to the subject-matter insured, except as excluded by "
                   "cl. 4, 5, 6 and 7. The assured must show an accidental loss during the period of cover; "
                   "it need not prove the precise cause.",
        "fraud_indicators": ["Loss not shown to have occurred during the insured transit",
                             "Loss explained by a non-fortuitous cause (e.g. goods never shipped)"],
        "keywords": ["all risks", "coverage", "fortuity", "cover"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "ICC-4.1",
        "source": "ICC (A) 2009, cl. 4.1",
        "title": "Exclusion — Wilful Misconduct of the Assured",
        "summary": "No cover for loss, damage or expense attributable to the wilful misconduct of the assured "
                   "(see also MIA 1906 s.55(2)(a)).",
        "fraud_indicators": ["Claimed loss staged or fabricated by the assured",
                             "Goods deliberately short-shipped or over-declared"],
        "keywords": ["wilful", "misconduct", "fraud", "phantom", "staged", "collusion"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "ICC-4.3",
        "source": "ICC (A) 2009, cl. 4.3",
        "title": "Exclusion — Inadequate or Unsuitable Packing",
        "summary": "Excludes loss caused by insufficiency or unsuitability of packing or preparation of the goods "
                   "to withstand the ordinary incidents of the insured transit, where the packing is carried out "
                   "by the assured or their employees or before this insurance attaches. 'Packing' includes "
                   "stowage in a container; 'employees' excludes independent contractors.",
        "fraud_indicators": ["Surveyor attributes loss to crating, bracing, dunnage or lashing",
                             "Goods packed / container stuffed by the assured or before cover attached"],
        "keywords": ["packing", "crate", "crating", "stowage", "dunnage", "lashing", "exclusion"],
        "applicable_types": ["breakage", "wet_damage", "contamination"],
    },
    {
        "section_id": "ICC-4.4",
        "source": "ICC (A) 2009, cl. 4.4",
        "title": "Exclusion — Inherent Vice or Nature",
        "summary": "Excludes loss caused by inherent vice or nature of the subject-matter insured (see also "
                   "MIA 1906 s.55(2)(c)).",
        "fraud_indicators": ["Deterioration arising from the goods' own nature without an external cause",
                             "Moisture from the cargo itself rather than water ingress"],
        "keywords": ["inherent", "vice", "nature", "deterioration", "moisture", "exclusion"],
        "applicable_types": ["wet_damage", "contamination"],
    },
    {
        "section_id": "ICC-4.5",
        "source": "ICC (A) 2009, cl. 4.5",
        "title": "Exclusion — Delay",
        "summary": "Excludes loss caused by delay, even if the delay is caused by an insured risk (except "
                   "general average expenses under cl. 2).",
        "fraud_indicators": ["Market loss or deterioration caused by late arrival"],
        "keywords": ["delay", "late arrival", "exclusion"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "ICC-5",
        "source": "ICC (A) 2009, cl. 5",
        "title": "Exclusion — Unseaworthiness and Unfitness of Container",
        "summary": "Cl. 5.1.2 excludes loss from unfitness of a container for safe carriage where it was loaded "
                   "before cover attached or by the assured or their employees and they were privy to the "
                   "unfitness at the time of loading. A defective carrier container does not by itself defeat "
                   "the claim and may support recovery against the carrier.",
        "fraud_indicators": ["Assured stuffed a visibly damaged container"],
        "keywords": ["container", "holed", "unfit", "unseaworthy", "roof", "water ingress"],
        "applicable_types": ["wet_damage", "contamination", "breakage"],
    },
    {
        "section_id": "ICC-8",
        "source": "ICC (A) 2009, cl. 8 (Transit Clause)",
        "title": "Duration — Warehouse to Warehouse, 60-Day Limit",
        "summary": "Cover attaches when the goods are first moved in the warehouse for immediate loading and ends, "
                   "whichever occurs first, on unloading at the final warehouse (8.1.1), at another warehouse "
                   "used for storage or distribution (8.1.2), when a carrying conveyance or container is used for storage "
                   "outside the ordinary course of transit (8.1.3), or 60 days after discharge from the ocean "
                   "vessel at the final port (8.1.4).",
        "fraud_indicators": ["Loss discovered more than 60 days after discharge",
                             "Damage arising during storage at the consignee's premises after delivery"],
        "keywords": ["transit", "60 days", "after discharge", "storage", "delivery", "duration", "late"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "ICC-16",
        "source": "ICC (A) 2009, cl. 16 (Duty of Assured)",
        "title": "Duty to Minimise Loss and Preserve Rights against Carriers",
        "summary": "The assured must take reasonable measures to avert or minimise the loss (16.1) and ensure all "
                   "rights against carriers, bailees or other third parties are properly preserved and "
                   "exercised (16.2). Insurers reimburse the reasonable costs of doing so.",
        "fraud_indicators": ["No notice of claim served on the carrier",
                             "Cargo unstuffed and disposed of before the carrier could inspect"],
        "keywords": ["notice", "carrier", "recovery", "preserve", "subrogation", "minimise"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "ICC-17",
        "source": "ICC (A) 2009, cl. 17 (Waiver)",
        "title": "Waiver — Protective Measures Do Not Prejudice Rights",
        "summary": "Measures taken by the assured or insurers to save, protect or recover the goods are not a "
                   "waiver or acceptance of abandonment and do not otherwise prejudice either party's rights. "
                   "Insurers can appoint surveyors and investigate without conceding liability.",
        "fraud_indicators": [],
        "keywords": ["waiver", "reservation", "without prejudice", "investigate"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "ICC-IMP",
        "source": "ICC 2009 — 'Important' notice (procedure in the event of loss)",
        "title": "Claims Procedure — Survey, Seals and Notice",
        "summary": "The assured should claim immediately on carriers for missing packages, not give clean receipts "
                   "for goods in doubtful condition except under written protest, examine containers and seals "
                   "on delivery, apply immediately for survey by the carrier's representative, give written "
                   "notice to the carrier within 3 days where loss was not apparent, and notify the insurer's "
                   "survey agent immediately.",
        "fraud_indicators": ["Clean receipt given, damage reported later",
                             "Surveyor appointed by the assured rather than the insurer's agent",
                             "Seals not checked or not retained"],
        "keywords": ["survey", "surveyor", "seal", "receipt", "notice", "agent", "appointed"],
        "applicable_types": ALL_TYPES,
    },
    # ── Carriage ────────────────────────────────────────────────────────────
    {
        "section_id": "HVR-III-6",
        "source": "Hague-Visby Rules, Art. III r.6",
        "title": "Notice of Loss and One-Year Time Bar",
        "summary": "Unless written notice of loss is given at delivery (or within 3 days where the loss is not "
                   "apparent), removal of the goods is prima facie evidence of delivery as described in the B/L. "
                   "No notice is needed if the goods were jointly surveyed at receipt. The carrier is discharged "
                   "unless suit is brought within one year of delivery (extendable by agreement).",
        "fraud_indicators": ["No notice to carrier; clean delivery recorded",
                             "No joint survey with the carrier", "Time bar approaching without extension"],
        "keywords": ["notice", "carrier", "time bar", "joint survey", "recovery", "delivery", "eir"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "HVR-III-4",
        "source": "Hague-Visby Rules, Art. III r.3-4",
        "title": "Bill of Lading as Evidence of Goods Received",
        "summary": "The B/L is prima facie evidence of receipt of the goods as described, and conclusive once "
                   "transferred to a third party in good faith. Qualifying words such as 'said to contain' or "
                   "'shipper's load, stow and count' are commonly relied on to limit its evidential effect as to "
                   "contents, so the quantity stated rests on the shipper's declaration.",
        "fraud_indicators": ["B/L claused 'said to contain' with no independent tally",
                             "Declared quantity inconsistent with the VGM weight"],
        "keywords": ["bill of lading", "b/l", "said to contain", "shipper's load", "quantity", "phantom"],
        "applicable_types": ["shortage", "breakage", "theft_pilferage"],
    },
    {
        "section_id": "HVR-IV-5",
        "source": "Hague-Visby Rules, Art. IV r.5",
        "title": "Carrier's Limitation of Liability",
        "summary": "Unless the nature and value of the goods were declared and inserted in the B/L, the carrier's "
                   "liability is limited to the higher of 666.67 SDR per package or unit and 2 SDR per kg of "
                   "gross weight lost or damaged. Packages enumerated in the B/L as packed in a container count "
                   "as packages.",
        "fraud_indicators": [],
        "keywords": ["limitation", "recovery", "sdr", "package", "subrogation"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "SOLAS-VI-2",
        "source": "SOLAS Chapter VI, Regulation 2 (in force 1 July 2016)",
        "title": "Verified Gross Mass (VGM) of Packed Containers",
        "summary": "The shipper must provide a verified gross mass for every packed container before loading, by "
                   "weighing the packed container (Method 1) or weighing all contents and adding the tare "
                   "(Method 2). A container without a VGM must not be loaded.",
        "fraud_indicators": ["VGM cargo weight far below the weight implied by the invoice and packing list",
                             "Invoiced quantity physically impossible within the verified weight"],
        "keywords": ["vgm", "weight", "phantom", "short", "gross mass", "kg"],
        "applicable_types": ALL_TYPES,
    },
    # ── Insurance law (English law and practice, ICC cl. 19) ────────────────
    {
        "section_id": "MIA-17",
        "source": "Marine Insurance Act 1906, s.17 (as amended by Insurance Act 2015)",
        "title": "Utmost Good Faith",
        "summary": "A contract of marine insurance is based on the utmost good faith. For contracts made on or after "
                   "12 August 2016 the Insurance Act 2015 removed avoidance as the remedy under s.17; remedies "
                   "now come from the duty of fair presentation and the fraudulent-claims provisions.",
        "fraud_indicators": ["Misstatement of value, quantity or loss circumstances"],
        "keywords": ["good faith", "misrepresentation", "valu", "fraud"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "MIA-18",
        "source": "Marine Insurance Act 1906, s.18; Insurance Act 2015, ss.3-8",
        "title": "Disclosure / Duty of Fair Presentation",
        "summary": "Originally the assured had to disclose every material circumstance before the contract was "
                   "concluded (s.18). For non-consumer contracts since August 2016 this is replaced by the duty of "
                   "fair presentation; remedies are proportionate, and a deliberate or reckless breach allows "
                   "insurers to avoid the contract and keep the premium.",
        "fraud_indicators": ["Undisclosed links between assured, surveyor and forwarder",
                             "Undisclosed prior loss history"],
        "keywords": ["disclosure", "fair presentation", "material", "history", "director", "linked"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "MIA-27",
        "source": "Marine Insurance Act 1906, s.27(3)",
        "title": "Valued Policy — Agreed Value Conclusive Absent Fraud",
        "summary": "Where the policy states an agreed value, that value is conclusive between insurer and assured "
                   "in the absence of fraud. Over-valuation therefore has to be addressed through fraud or "
                   "fair-presentation grounds, which makes evidence of the true value important.",
        "fraud_indicators": ["Invoice unit price far above the market benchmark",
                             "Seller recently incorporated with no production facility"],
        "keywords": ["valu", "over-valu", "invoice", "price", "benchmark", "insured value"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "MIA-55",
        "source": "Marine Insurance Act 1906, s.55",
        "title": "Proximate Cause and Statutory Exclusions",
        "summary": "Insurers are liable for loss proximately caused by an insured peril (s.55(1)), and not liable "
                   "for loss attributable to the wilful misconduct of the assured (s.55(2)(a)), or, unless the "
                   "policy provides otherwise, for delay, ordinary wear and tear, ordinary leakage and breakage, "
                   "or inherent vice (s.55(2)(b)-(c)).",
        "fraud_indicators": ["Cause of loss not established by an independent survey"],
        "keywords": ["proximate", "cause", "wilful", "misconduct", "breakage", "leakage"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "MIA-79",
        "source": "Marine Insurance Act 1906, s.79",
        "title": "Subrogation",
        "summary": "On paying a loss, insurers are subrogated to the assured's rights and remedies against third "
                   "parties such as the carrier, to the extent of the payment.",
        "fraud_indicators": [],
        "keywords": ["subrogation", "recovery", "carrier"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "IA2015-12",
        "source": "Insurance Act 2015, s.12",
        "title": "Remedies for Fraudulent Claims",
        "summary": "If the assured makes a fraudulent claim, insurers are not liable to pay it, may recover sums "
                   "already paid in respect of it, and may by notice treat the contract as terminated from the "
                   "time of the fraudulent act.",
        "fraud_indicators": ["Exaggerated quantum", "Fabricated evidence or colluding surveyor"],
        "keywords": ["fraud", "fraudulent", "exaggerat", "phantom", "collusion", "recover"],
        "applicable_types": ALL_TYPES,
    },
    # ── Internal claims guidelines ──────────────────────────────────────────
    {
        "section_id": "MC-GL-01",
        "source": "Internal marine claims guideline",
        "title": "Surveyor Appointment and Independence",
        "summary": "Surveys are appointed by the insurer or its claims agent from the approved panel, within 7 days "
                   "of discharge, jointly with the carrier for breakage, shortage and theft. Assured-appointed or "
                   "non-panel surveys require re-inspection by a panel surveyor before settlement.",
        "fraud_indicators": ["Surveyor not on panel or on watchlist", "Survey more than 7 days after discharge",
                             "Surveyor shares directors or address with the claimant"],
        "keywords": ["surveyor", "survey", "panel", "appointed", "watchlist", "late", "collusion"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "MC-GL-02",
        "source": "Internal marine claims guideline",
        "title": "Valuation Verification",
        "summary": "Where the invoiced unit price exceeds 1.4x the market benchmark, obtain proof of payment, the "
                   "seller's export declaration and the import customs declaration before agreeing quantum; "
                   "reconcile quantity against the VGM.",
        "fraud_indicators": ["Unit price > 1.4x benchmark", "VGM weight below invoiced quantity"],
        "keywords": ["valu", "price", "benchmark", "invoice", "vgm", "customs"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "MC-GL-03",
        "source": "Internal marine claims guideline",
        "title": "Recovery Preservation",
        "summary": "Confirm notice of claim to the carrier within 3 days, retain seals and damaged containers, and "
                   "obtain a time extension or issue proceedings before the one-year time bar.",
        "fraud_indicators": ["No notice to carrier", "Clean EIR despite a major loss"],
        "keywords": ["recovery", "notice", "carrier", "time bar", "seal", "eir"],
        "applicable_types": ALL_TYPES,
    },
    {
        "section_id": "MC-GL-04",
        "source": "Internal marine claims guideline",
        "title": "Settling Authority and SIU Referral",
        "summary": "Claims above USD 50,000 or above 40% of insured value are referred to the senior marine claims "
                   "handler. Any BLOCK-severity indicator of fraud (weight discrepancy, surveyor conflict, reused "
                   "evidence) is referred to SIU with payment on hold.",
        "fraud_indicators": ["Major loss above authority", "BLOCK rule triggered"],
        "keywords": ["authority", "referral", "siu", "major loss", "hold", "block"],
        "applicable_types": ALL_TYPES,
    },
]


@tool
@_safe(fallback=lambda e: [{"error": f"search_regulatory_rules failed: {str(e)[:200]}"}])
def search_regulatory_rules(
    claim_types: Annotated[List[str], "Loss types (breakage, wet_damage, contamination, shortage, theft_pilferage)"],
    context: Annotated[str, "Description of the suspected scheme or coverage issue"],
) -> List[Dict]:
    """
    Search marine cargo rule references relevant to the case: Institute Cargo Clauses (A) 2009,
    Hague-Visby Rules, SOLAS VGM, Marine Insurance Act 1906 / Insurance Act 2015 and internal
    guidelines (MC-GL-xx). Returns up to 8 rules with section_id, source, title, summary,
    fraud_indicators and applicable_types.
    """
    claim_types = [str(c).lower() for c in (claim_types or [])]
    _tool_log('search_regulatory_rules', f'Searching rules for types={claim_types}...')
    ctx_lower = (context or '').lower()
    words = [w.strip('.,;:()') for w in ctx_lower.split() if len(w) > 3]

    scored = []
    for rule in RULES:
        type_match = (not claim_types) or any(ct in rule['applicable_types'] for ct in claim_types)
        kw_hits = sum(2 for kw in rule['keywords'] if kw in ctx_lower)
        text = (rule['title'] + ' ' + rule['summary']).lower()
        word_hits = sum(1 for w in set(words) if w in text)
        score = (3 if type_match else 0) + kw_hits * 2 + min(word_hits, 6)
        scored.append((score, rule))
    scored.sort(key=lambda x: -x[0])

    # Diversify: at most 2 references per family (ICC / carriage / SOLAS / insurance law / internal).
    def family(sid: str) -> str:
        head = sid.split('-')[0]
        return {"HVR": "carriage", "MIA": "law", "IA2015": "law", "MC": "internal"}.get(head, head)
    picked, per_family = [], {}
    for s, r in scored:
        if s <= 3 or len(picked) >= 8:
            continue
        fam = family(r['section_id'])
        if per_family.get(fam, 0) < 2:
            picked.append(r)
            per_family[fam] = per_family.get(fam, 0) + 1
    results = [{k: v for k, v in r.items() if k != 'keywords'} for r in picked]
    _tool_cache['regulatory_rules'] = results
    _tool_log('search_regulatory_rules', f'Found {len(results)} relevant rules')
    return _truncate_tool_output(results)


# alias for prompt compatibility
search_billing_rules = search_regulatory_rules


# =========================================================================
# 3.  find_similar_cases  (fictional internal precedents)
# =========================================================================
CASES = {
    "overvalued_phantom_cargo": [{
        "case_id": "MC-SIU-2025-0117",
        "scheme": "Over-valued, Part-phantom Glass Shipment",
        "entities_involved": 4, "total_claims": 3, "total_paid": 412_000,
        "summary": "Consignee claimed 68% breakage on insulated glass invoiced at 1.8x market price by a newly "
                   "incorporated trading company. Terminal VGM showed 40% less cargo than the packing list. "
                   "Survey by an assured-appointed firm sharing a director with the forwarder.",
        "outcome": "Claim declined for fraud; two prior payments recovered; surveyor removed from all panels",
        "year": 2025,
    }],
    "surveyor_collusion": [{
        "case_id": "MC-SIU-2025-0142",
        "scheme": "Colluding Surveyor Network",
        "entities_involved": 6, "total_claims": 7, "total_paid": 655_000,
        "summary": "A non-panel surveyor was appointed by the assured on seven breakage claims for three "
                   "consignees over 18 months. All surveys took place at consignee premises after unstuffing, "
                   "none jointly with the carrier.",
        "outcome": "Referred to SIU; surveyor watchlisted; open claims re-surveyed by panel surveyors",
        "year": 2025,
    }],
    "phantom_cargo": [{
        "case_id": "MC-SIU-2025-0088",
        "scheme": "Short-shipped Cargo Declared as Transit Loss",
        "entities_involved": 2, "total_claims": 1, "total_paid": 0,
        "summary": "Shortage claim on a 'said to contain' B/L. VGM and the load-port weighbridge ticket showed the "
                   "container was loaded with about 55% of the invoiced weight; seals were intact at discharge.",
        "outcome": "Claim declined — loss not shown to have occurred during the insured transit",
        "year": 2025,
    }],
    "reused_photos": [{
        "case_id": "MC-SIU-2025-0163",
        "scheme": "Reused Survey Photographs",
        "entities_involved": 2, "total_claims": 2, "total_paid": 96_000,
        "summary": "Breakage photographs in a new survey report matched, by perceptual hash, images filed on an "
                   "earlier claim by a different consignee handled by the same surveyor.",
        "outcome": "Second claim declined; first claim reopened for recovery",
        "year": 2025,
    }],
    "repeat_claimant": [{
        "case_id": "MC-SIU-2024-0231",
        "scheme": "High Claim Rate on Low Shipment Volume",
        "entities_involved": 1, "total_claims": 5, "total_paid": 388_000,
        "summary": "Importer with about 15 shipments a year filed five breakage claims in 24 months (17% claim "
                   "rate against a portfolio average below 3%).",
        "outcome": "Open cover not renewed; outstanding claims settled only after panel re-survey",
        "year": 2024,
    }],
    "coverage_exclusion": [{
        "case_id": "MC-CLM-2025-0412",
        "scheme": "Genuine Loss Outside Cover (Packing / Transit Clause)",
        "entities_involved": 1, "total_claims": 1, "total_paid": 0,
        "summary": "Genuine breakage of float glass in unbraced crates; panel survey found the packing unsuitable "
                   "for the ordinary incidents of transit (ICC cl. 4.3). Handled as a coverage decision, not fraud.",
        "outcome": "Declined with a reasoned coverage letter; no fraud referral; broker advised on packing standards",
        "year": 2025,
    }],
}
CASE_ALIASES = {
    "overvaluation": "overvalued_phantom_cargo", "over_valuation": "overvalued_phantom_cargo",
    "surveyor_ring": "surveyor_collusion", "short_shipment": "phantom_cargo", "shortage": "phantom_cargo",
    "duplicate_photo": "reused_photos", "serial_claimer": "repeat_claimant",
    "packing": "coverage_exclusion", "transit": "coverage_exclusion",
}


@tool
@_safe(fallback=lambda e: [{"error": f"find_similar_cases failed: {str(e)[:200]}"}])
def find_similar_cases(
    scheme_pattern: Annotated[str, "overvalued_phantom_cargo, phantom_cargo, surveyor_collusion, reused_photos, repeat_claimant, coverage_exclusion"],
    specialty: Annotated[Optional[str], "Loss type if applicable (e.g. breakage)"] = None,
) -> List[Dict]:
    """Find internal precedent marine cargo cases with a similar fraud or coverage pattern."""
    _tool_log('find_similar_cases', f'Looking up precedents for "{scheme_pattern}"...')
    key = (scheme_pattern or '').lower().strip()
    key = CASE_ALIASES.get(key, key)
    results = list(CASES.get(key, []))
    if not results:
        tokens = [t for t in key.replace('-', '_').split('_') if len(t) > 3]
        for k, val in CASES.items():
            if any(t in k for t in tokens) or any(t in v['scheme'].lower() for v in val for t in tokens):
                results.extend(val)
    if not results and key:
        results = CASES["overvalued_phantom_cargo"] + CASES["surveyor_collusion"]
    seen = set()
    results = [c for c in results if c['case_id'] not in seen and not seen.add(c['case_id'])]
    _tool_cache['similar_cases'] = results[:3]
    _tool_log('find_similar_cases', f'Found {len(results)} precedent cases')
    return _truncate_tool_output(results[:3])


# =========================================================================
# 4.  estimate_recovery
# =========================================================================
def _supported_loss(claim) -> Optional[float]:
    """Loss supported by the evidence: VGM-implied quantity at a benchmark-capped price × surveyed damage."""
    if _context is None:
        return None
    try:
        from data.generate_marine import COMMODITIES
    except Exception:
        return None
    shp = _context.get_shipment(claim.shipment_id)
    pol = _context.get_policy(claim.policy_id)
    svr = _context.get_survey(claim.survey_id) if claim.survey_id else None
    if not shp or not pol or not shp.invoice_value:
        return None
    com = next((c for c in COMMODITIES.values() if c["name"] == shp.commodity), None)
    if not com:
        return None
    qty = min(shp.quantity, shp.vgm_cargo_kg / com["kg_per_unit"]) if com["kg_per_unit"] else shp.quantity
    price = min(shp.unit_price, com["price"][1])
    uplift = pol.insured_value / shp.invoice_value
    dmg = (svr.damage_pct / 100) if svr else claim.claim_amount / pol.insured_value
    return min(claim.claim_amount, qty * price * uplift * dmg)


@tool
@_safe()
def estimate_recovery(
    flagged_claims: Annotated[List[Dict], "List of suspicious claims [{claim_id, claim_amount, claim_type}, ...]"],
    peer_benchmarks: Annotated[Optional[Dict], "Optional benchmarks: {avg_claim_amount, prior_paid_total}"] = None,
) -> Dict:
    """
    Estimate the financial impact of flagged marine claims: payment avoided on the open claims
    (claimed amount minus the loss supported by VGM weight and benchmark value), plus prior paid
    claims linked to the same network that may be recoverable (Insurance Act 2015 s.12).
    """
    flagged_claims = flagged_claims or []
    peer_benchmarks = peer_benchmarks or {}
    _tool_log('estimate_recovery', f'Estimating recovery for {len(flagged_claims)} claims...')
    if not flagged_claims:
        return {"total_flagged_claims": 0, "gross_recoverable": 0, "collectability_score": 0, "net_expected": 0}

    breakdown, total_claimed, avoided = [], 0.0, 0.0
    prior_ids, prior_total = set(), 0.0
    for fc in flagged_claims:
        if not isinstance(fc, dict):
            continue
        cid = fc.get('claim_id')
        claim = _context.get_claim(cid) if (_context and cid) else None
        amount = float(claim.claim_amount if claim else fc.get('claim_amount', fc.get('amount', 0)) or 0)
        total_claimed += amount
        supported = _supported_loss(claim) if claim else None
        if supported is None:
            supported = amount * 0.85      # no evidence model — assume modest exaggeration
        excess = max(0.0, amount - supported)
        avoided += excess
        breakdown.append({"claim_id": cid or "N/A",
                          "claim_type": (claim.claim_type if claim else fc.get('claim_type', fc.get('type', 'unknown'))),
                          "claim_amount": round(amount, 2), "supported_loss": round(supported, 2),
                          "payment_avoided": round(excess, 2)})
        # Prior paid claims linked through the claimant or a non-panel / watchlisted surveyor.
        if claim and _context:
            svy = _context.get_surveyor(claim.surveyor_id) if claim.surveyor_id else None
            linked = _context.get_prior_claims(party_id=claim.consignee_id)
            if svy and (svy.on_watchlist or not svy.insurer_panel):
                linked += _context.get_prior_claims(surveyor_id=svy.surveyor_id)
            for p in linked:
                if p.claim_id not in prior_ids:
                    prior_ids.add(p.claim_id)
                    prior_total += p.amount_paid
    if not prior_ids and peer_benchmarks.get('prior_paid_total'):
        prior_total = float(peer_benchmarks['prior_paid_total'])

    prior_collectability = 0.35          # clawback of paid claims is slow and uncertain
    gross = avoided + prior_total
    net = avoided * 0.95 + prior_total * prior_collectability
    result = {
        "total_flagged_claims": len(breakdown),
        "total_claimed": round(total_claimed, 2),
        "payment_avoided_open_claims": round(avoided, 2),
        "prior_paid_claims_under_review": sorted(prior_ids),
        "prior_paid_total": round(prior_total, 2),
        "gross_recoverable": round(gross, 2),
        "collectability_score": round(net / gross, 2) if gross else 0,
        "net_expected": round(net, 2),
        "claim_breakdown": breakdown[:5],
        "method": "Open claims: claimed minus evidence-supported loss (VGM-implied quantity at benchmark-capped "
                  "price × surveyed damage), 95% realisation. Prior paid claims: 35% collectability.",
    }
    _tool_cache['recovery_estimate'] = result
    _tool_log('estimate_recovery', f'Net expected: ${net:,.2f}')
    return _truncate_tool_output(result)


# =========================================================================
# 5.  compile_dossier  (marine-themed)
# =========================================================================
def _dossier_error(e) -> str:
    return ("# MARINE CARGO CLAIM INVESTIGATION DOSSIER\n\n"
            f"Dossier generation failed: {str(e)[:200]}. Please retry.\n")


@tool
@_safe(fallback=_dossier_error)
def compile_dossier(
    case_data: Annotated[Dict, "Complete case data: hypothesis, entities, evidence, statistical_analysis, network_analysis, regulatory_rules, similar_cases, recovery_estimate, claim_id"],
) -> str:
    """
    Generate the final marine cargo investigation dossier in Markdown.
    ONLY call this AFTER assess_evidence returns SUFFICIENT.
    """
    _tool_log('compile_dossier', 'Generating final Markdown dossier...')
    case_data = case_data or {}
    hypothesis = case_data.get('hypothesis', 'Suspected marine cargo claim fraud')
    entities = case_data.get('entities', []) or []
    evidence = case_data.get('evidence', []) or []
    stats = case_data.get('statistical_analysis', {}) or {}
    network = case_data.get('network_analysis', {}) or {}
    rules = case_data.get('regulatory_rules', case_data.get('billing_rules', [])) or []
    similar_cases = case_data.get('similar_cases', []) or []
    recovery = case_data.get('recovery_estimate', {}) or {}
    claim_id = case_data.get('claim_id')

    if not rules and _tool_cache.get('regulatory_rules'):
        rules = _tool_cache['regulatory_rules']
    if not similar_cases and _tool_cache.get('similar_cases'):
        similar_cases = _tool_cache['similar_cases']
    if (not isinstance(recovery, dict) or not recovery.get('gross_recoverable')) and _tool_cache.get('recovery_estimate'):
        recovery = _tool_cache['recovery_estimate']
    if not isinstance(recovery, dict):
        recovery = {}

    def sf(val, default=0):
        try:
            return float(val) if val is not None else float(default)
        except (TypeError, ValueError):
            return float(default)

    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    dossier = f"""# MARINE CARGO CLAIM INVESTIGATION DOSSIER

**Case Hypothesis**: {hypothesis}
{f'**Claim**: {claim_id}' + chr(10) if claim_id else ''}**Date Generated**: {now}
**Status**: Evidence Sufficient — Ready for Referral

---

## EXECUTIVE SUMMARY

This investigation examined a suspected **{hypothesis}** involving {len(entities)} entities. The findings rest on {len(evidence)} independent evidence points drawn from the shipping documents, the terminal VGM record, the survey and the entity network. Estimated financial impact (payment avoided plus recoverable prior payments): **${sf(recovery.get('net_expected')):,.2f}**.

**Recommended Action**: Hold payment and refer to the Special Investigations Unit; appoint an independent panel surveyor for re-inspection.

---

## ENTITIES INVOLVED

"""
    for i, entity in enumerate(entities, 1):
        if isinstance(entity, dict):
            eid = entity.get('entity_id', 'UNKNOWN')
            etype = str(entity.get('entity_type', 'unknown')).title()
            dossier += f"\n### Entity {i}: {eid}\n\n- **Role**: {etype}\n"
            if entity.get('name') or entity.get('entity_name'):
                dossier += f"- **Name**: {entity.get('name', entity.get('entity_name'))}\n"
            if entity.get('risk_score'):
                dossier += f"- **Risk Score**: {entity['risk_score']}/100\n"
            if entity.get('claim_amount') or entity.get('total_claimed'):
                amt = sf(entity.get('claim_amount', entity.get('total_claimed')))
                dossier += f"- **Amount Claimed**: ${amt:,.2f}\n"
            if entity.get('claim_count'):
                dossier += f"- **Claims**: {entity['claim_count']}\n"
            for k in ('director', 'registered_address', 'notes'):
                if entity.get(k):
                    dossier += f"- **{k.replace('_', ' ').title()}**: {entity[k]}\n"
            dossier += "\n"
        else:
            dossier += f"\n### Entity {i}: {entity}\n\n"

    dossier += "\n---\n\n## EVIDENCE SUMMARY\n\n"
    for i, ev in enumerate(evidence, 1):
        dossier += f"{i}. {ev}\n"

    dossier += "\n---\n\n## STATISTICAL ANALYSIS\n\n"
    if stats and isinstance(stats, dict):
        dossier += "| Metric | Entity Value | Peer / Benchmark | Z-Score | Significance |\n"
        dossier += "|--------|--------------|------------------|---------|-------------|\n"
        for metric, data in stats.items():
            if isinstance(data, dict):
                ev = sf(data.get('entity_value', data.get('value', 0)))
                pa = sf(data.get('peer_avg', data.get('peer_average', data.get('benchmark', 0))))
                zs = sf(data.get('z_score', data.get('z', 0)))
                sig = "HIGH" if abs(zs) > 2 else "Normal"
                dossier += f"| {metric} | {ev:,.2f} | {pa:,.2f} | {zs:.2f} | {sig} |\n"
            else:
                dossier += f"| {metric} | {data} | | | |\n"
    else:
        dossier += "_No structured statistical data provided._\n"

    dossier += "\n---\n\n## NETWORK ANALYSIS\n\n"
    if network and isinstance(network, dict):
        dossier += f"- **Connected Entities**: {network.get('total_entities', 0)}\n"
        dossier += f"- **Connection Density**: {sf(network.get('connection_density')):,.2f}\n"
        if network.get('relationship_summary'):
            dossier += f"- **Relationships**: {network['relationship_summary']}\n"
        if network.get('shared_directors'):
            dossier += f"- **Shared Directors**: {network['shared_directors']}\n"
        if network.get('patterns'):
            dossier += "\n**Detected Patterns**:\n"
            for p in (network['patterns'] if isinstance(network['patterns'], list) else [network['patterns']]):
                if isinstance(p, dict):
                    dossier += f"- [{p.get('severity', 'MEDIUM')}] {p.get('pattern_type', '')}: {p.get('description', '')}\n"
                else:
                    dossier += f"- {p}\n"
    else:
        dossier += "_No network analysis data provided._\n"

    dossier += "\n---\n\n## APPLICABLE CLAUSES, LAW AND GUIDELINES\n\n"
    if rules:
        for rule in rules:
            if isinstance(rule, dict):
                dossier += f"### {rule.get('section_id', 'RULE')}: {rule.get('title', 'Unknown')}\n\n"
                if rule.get('source'):
                    dossier += f"_{rule['source']}_\n\n"
                dossier += f"{rule.get('summary', 'N/A')}\n\n"
                if rule.get('fraud_indicators'):
                    dossier += "**Relevant indicators**:\n"
                    for ind in rule.get('fraud_indicators', [])[:3]:
                        dossier += f"- {ind}\n"
                dossier += "\n"
            else:
                dossier += f"- {rule}\n"
    else:
        dossier += "_No rule references cited._\n"

    dossier += "\n---\n\n## PRECEDENT CASES\n\n"
    if similar_cases:
        for case in similar_cases:
            if isinstance(case, dict):
                dossier += f"### {case.get('case_id', 'CASE')}: {case.get('scheme', 'Unknown')}\n\n"
                dossier += f"- **Summary**: {case.get('summary', 'N/A')}\n"
                paid = sf(case.get('total_paid', case.get('total_recovered', 0)))
                dossier += f"- **Total Paid**: ${paid:,.0f}\n"
                dossier += f"- **Outcome**: {case.get('outcome', 'Unknown')}\n"
                dossier += f"- **Year**: {case.get('year', 'N/A')}\n\n"
            else:
                dossier += f"- {case}\n"
    else:
        dossier += "_No precedent cases found._\n"

    dossier += "\n---\n\n## FINANCIAL IMPACT\n\n"
    total_claimed = sf(recovery.get('total_claimed', 0))
    gross = sf(recovery.get('gross_recoverable', 0))
    net = sf(recovery.get('net_expected', 0))
    collect = sf(recovery.get('collectability_score', 0))
    dossier += f"- **Claims Reviewed**: {recovery.get('total_flagged_claims', len(entities))}\n"
    dossier += f"- **Total Claimed**: ${total_claimed:,.2f}\n"
    if recovery.get('payment_avoided_open_claims') is not None:
        dossier += f"- **Payment Avoided (open claims)**: ${sf(recovery.get('payment_avoided_open_claims')):,.2f}\n"
    if recovery.get('prior_paid_total'):
        dossier += (f"- **Prior Paid Claims Under Review**: ${sf(recovery.get('prior_paid_total')):,.2f} "
                    f"({', '.join(recovery.get('prior_paid_claims_under_review', [])[:6])})\n")
    dossier += f"- **Gross Impact**: ${gross:,.2f}\n"
    dossier += f"- **Collectability**: {collect:.0%}\n"
    dossier += f"- **Net Expected**: **${net:,.2f}**\n\n"
    if recovery.get('claim_breakdown'):
        dossier += "| Claim | Type | Claimed | Supported Loss | Payment Avoided |\n"
        dossier += "|-------|------|---------|----------------|-----------------|\n"
        for item in recovery.get('claim_breakdown', [])[:5]:
            if isinstance(item, dict):
                dossier += (f"| {item.get('claim_id', 'N/A')} | {item.get('claim_type', 'N/A')} | "
                            f"${sf(item.get('claim_amount')):,.0f} | ${sf(item.get('supported_loss')):,.0f} | "
                            f"${sf(item.get('payment_avoided')):,.0f} |\n")

    dossier += "\n---\n\n## INNOCENT EXPLANATIONS CONSIDERED\n\n"
    dossier += ("- Unit price above benchmark: special specification or small-lot premium — to be tested against "
                "proof of payment and customs declarations.\n"
                "- VGM below declared weight: calculation error under SOLAS Method 2 — to be tested against the "
                "terminal weighbridge record.\n"
                "- Assured-appointed, late survey: surveyor availability or customs delay — independent "
                "re-inspection resolves this.\n"
                "- Shared directors or address: serviced offices or family businesses — company registry "
                "records resolve this.\n")

    dossier += "\n---\n\n## RECOMMENDED ACTIONS\n\n"
    dossier += "1. **Immediate**: Hold payment on the flagged claim(s) pending SIU review, under a reservation of rights (ICC cl. 17)\n"
    dossier += "2. **Verification**: Obtain the terminal weighbridge / VGM records, proof of payment, export and import customs declarations\n"
    dossier += "3. **Survey**: Appoint an independent insurer panel surveyor to re-inspect the cargo and review the original photographs\n"
    dossier += "4. **Network**: Obtain company registry extracts for the claimant, surveyor and forwarder\n"
    dossier += "5. **Recovery**: Review linked prior paid claims; protect any rights against the carrier before the one-year time bar\n"
    dossier += "6. **Prevention**: Place the surveyor and forwarder on enhanced monitoring for future claims\n\n"
    dossier += "---\n\n"
    dossier += "*Generated by the Marine Cargo Claims Copilot*\n"

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
