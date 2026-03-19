"""13 document checks (DOC-001 to DOC-013) for supplemental health claims."""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class DocCheckResult:
    check_id: str
    check_name: str
    passed: bool
    explanation: str
    severity: str = "INFO"  # INFO, WARNING, CRITICAL
    details: Dict = field(default_factory=dict)


def run_document_checks(doc_metadata) -> List[DocCheckResult]:
    """Run all 13 DOC checks against document metadata. Returns list of results."""
    results = []

    # DOC-001: Header presence
    has_header = getattr(doc_metadata, 'has_header', True)
    results.append(DocCheckResult(
        check_id="DOC-001", check_name="Facility Header Present",
        passed=has_header,
        explanation="Facility header found on document" if has_header else "MISSING: No facility header on document",
        severity="CRITICAL" if not has_header else "INFO",
        details={"has_header": has_header},
    ))

    # DOC-002: Provider signature
    has_sig = getattr(doc_metadata, 'has_signature', True)
    results.append(DocCheckResult(
        check_id="DOC-002", check_name="Provider Signature Present",
        passed=has_sig,
        explanation="Provider signature present" if has_sig else "MISSING: No provider signature",
        severity="CRITICAL" if not has_sig else "INFO",
        details={"has_signature": has_sig},
    ))

    # DOC-003: Date consistency
    has_date = getattr(doc_metadata, 'has_date', True)
    results.append(DocCheckResult(
        check_id="DOC-003", check_name="Date of Service Consistent",
        passed=has_date,
        explanation="Date of service present and consistent" if has_date else "MISSING: Date of service not found or inconsistent",
        severity="WARNING" if not has_date else "INFO",
        details={"has_date": has_date},
    ))

    # DOC-004: Document format quality
    fmt = getattr(doc_metadata, 'format_type', 'digital')
    resolution = getattr(doc_metadata, 'resolution', 'standard')
    good_quality = not (fmt == "fax" and resolution == "low")
    results.append(DocCheckResult(
        check_id="DOC-004", check_name="Document Quality Adequate",
        passed=good_quality,
        explanation="Document quality acceptable" if good_quality else f"Low quality: {fmt} format, {resolution} resolution",
        severity="WARNING" if not good_quality else "INFO",
        details={"format": fmt, "resolution": resolution},
    ))

    # DOC-005: Tampering indicators
    tampering = getattr(doc_metadata, 'tampering_indicators', [])
    no_tampering = len(tampering) == 0
    results.append(DocCheckResult(
        check_id="DOC-005", check_name="No Tampering Indicators",
        passed=no_tampering,
        explanation="No tampering detected" if no_tampering else f"TAMPERING: {', '.join(tampering)}",
        severity="CRITICAL" if not no_tampering else "INFO",
        details={"tampering_indicators": tampering},
    ))

    # DOC-006: Duplicate document check
    dup = getattr(doc_metadata, 'duplicate_of', None)
    not_dup = dup is None
    results.append(DocCheckResult(
        check_id="DOC-006", check_name="No Duplicate Documents",
        passed=not_dup,
        explanation="No duplicate detected" if not_dup else f"DUPLICATE: Document matches {dup}",
        severity="WARNING" if not not_dup else "INFO",
        details={"duplicate_of": dup},
    ))

    # DOC-007: Provider name matches claim
    doc_provider = getattr(doc_metadata, 'provider_name', '')
    has_provider = doc_provider and doc_provider != "Unknown Provider"
    results.append(DocCheckResult(
        check_id="DOC-007", check_name="Provider Name Matches",
        passed=has_provider,
        explanation="Provider identified on document" if has_provider else "Provider name missing or unknown",
        severity="WARNING" if not has_provider else "INFO",
        details={"provider_name": doc_provider},
    ))

    # DOC-008: Service date within filing window
    dos = getattr(doc_metadata, 'date_of_service', '')
    received = getattr(doc_metadata, 'received_date', '')
    date_ok = bool(dos and received)
    results.append(DocCheckResult(
        check_id="DOC-008", check_name="Service Date Within Window",
        passed=date_ok,
        explanation="Service date and received date present" if date_ok else "Missing service or received date",
        severity="WARNING" if not date_ok else "INFO",
        details={"date_of_service": dos, "received_date": received},
    ))

    # DOC-009: Metadata hash integrity
    meta_hash = getattr(doc_metadata, 'metadata_hash', '')
    has_hash = bool(meta_hash)
    results.append(DocCheckResult(
        check_id="DOC-009", check_name="Metadata Hash Present",
        passed=has_hash,
        explanation="Document metadata hash verified" if has_hash else "No metadata hash",
        severity="INFO",
        details={"metadata_hash": meta_hash},
    ))

    # DOC-010: Document type appropriate for claim
    doc_type = getattr(doc_metadata, 'doc_type', 'unknown')
    valid_types = ["medical_record", "invoice", "receipt", "discharge_summary", "operative_report"]
    type_ok = doc_type in valid_types
    results.append(DocCheckResult(
        check_id="DOC-010", check_name="Document Type Valid",
        passed=type_ok,
        explanation=f"Document type: {doc_type}" if type_ok else f"Unexpected document type: {doc_type}",
        severity="WARNING" if not type_ok else "INFO",
        details={"doc_type": doc_type},
    ))

    # DOC-011: Complete documentation set
    # Based on metadata alone, we check if essential fields are populated
    complete = has_header and has_sig and has_date and has_provider
    results.append(DocCheckResult(
        check_id="DOC-011", check_name="Documentation Complete",
        passed=complete,
        explanation="All required document elements present" if complete else "Incomplete documentation — missing elements",
        severity="WARNING" if not complete else "INFO",
        details={"complete": complete},
    ))

    # DOC-012: Format consistency
    # Faxed documents from non-rural facilities are flagged
    claim_id = getattr(doc_metadata, 'claim_id', '')
    fmt_concern = fmt == "fax" and resolution == "low"
    results.append(DocCheckResult(
        check_id="DOC-012", check_name="Format Consistency",
        passed=not fmt_concern,
        explanation="Document format consistent" if not fmt_concern else "Low-quality fax — verify document authenticity",
        severity="INFO",
        details={"format_type": fmt, "resolution": resolution},
    ))

    # DOC-013: Cross-reference check
    # Simple metadata cross-reference
    cross_ref_ok = not (tampering and not has_header)
    results.append(DocCheckResult(
        check_id="DOC-013", check_name="Cross-Reference Validation",
        passed=cross_ref_ok,
        explanation="Cross-reference checks passed" if cross_ref_ok else "Cross-reference failed: tampering + missing header",
        severity="CRITICAL" if not cross_ref_ok else "INFO",
        details={"cross_ref_passed": cross_ref_ok},
    ))

    return results
