
# SCHEMA.md — Claims Copilot Data Schema

> Canonical reference for data generation and tool implementation. Derived from real scrubbed fraud cases.

---

## 1. Core Entities

### Member
```yaml
member_id: str              # "M-2026-{seq}"
first_name: str
last_name: str
date_of_birth: date
age: int                    # [COMPUTED]
gender: enum                # MALE | FEMALE
ssn_masked: str             # "*****XX"
resident_state: str
address_id: str             # FK → Address
employer_id: str            # FK → Employer
enrollment_date: date
termination_date: date?
is_active: bool
dependent_count: int
```

### Dependent
```yaml
dependent_id: str           # "D-2026-{seq}"
member_id: str              # FK → Member
first_name: str
last_name: str
date_of_birth: date
relationship: enum          # SPOUSE | CHILD | DOMESTIC_PARTNER
address_id: str
```

### Provider
```yaml
provider_id: str            # "PROV-{seq}"
name: str
credential: str             # "MD", "DO", "APRN", "NP"
npi: str
specialty: str
facility_ids: list[str]
total_claims: int           # [COMPUTED]
```

### Facility
```yaml
facility_id: str            # "FAC-{seq}"
name: str                   # e.g., "Baptist Beaumont Hospital"
facility_type: enum         # HOSPITAL | URGENT_CARE | CLINIC | ER
address_id: str
known_ehr_system: str?      # "Epic", "Cerner"
releasepoint_enrolled: bool
```

---

## 2. Claim

```yaml
claim_id: str               # "C-2026-{seq}" (e.g., "C-2026-1325588")
batch_claim_id: str?        # "BC-2026-{seq}" — groups related claims
member_id: str
policy_id: str
provider_id: str
facility_id: str?

# Classification
benefit_type: enum          # HOSPITAL_ADMISSION | HOSPITAL_CONFINEMENT | ICU_ADMISSION
                            # | HOSPITAL_INDEMNITY | URGENT_CARE_VISIT | EMERGENCY_ROOM
relationship_type: enum     # SELF | POLICYHOLDER | BENEFICIARY | INSURED
diagnosis_code: str         # ICD-10 (e.g., "Z51", "J44", "O30")

# Financials
claim_amount: float
approved_amount: float?

# Dates
service_date_start: date
service_date_end: date
filing_date: date

# Status
claim_status: enum          # APPROVED | DENIED | PENDING | NIGO | UNDER_REVIEW | CLOSED
denial_reason: str?         # "Policy definition not met", etc.
nigo_flag: bool

# Fraud [COMPUTED]
risk_score: float           # 0-100
risk_tier: enum             # HIGH (≥60) | MEDIUM (30-59) | LOW (<30)
rules_triggered: list[str]
fraud_status: enum          # NOT_FLAGGED | FLAGGED_FOR_REVIEW | VALID_FRAUD | INVALID_FRAUD

# Relationships
related_claim_ids: list[str]    # Same event/hospitalization
stacked_with: list[str]         # Same event, different relationship types
```

---

## 3. Document

```yaml
doc_id: str                 # "DOC-{seq}"
claim_id: str
filename: str               # e.g., "CamScanner_4-1-26_17.54_1.jpeg"
file_format: enum           # JPEG | PDF | PNG
source_type: enum           # RELEASEPOINT (0.0 risk) | PROVIDER_PORTAL (0.1)
                            # | PROVIDER_FAX (0.2) | MEMBER_UPLOAD_PDF (0.4)
                            # | MEMBER_EMAIL (0.5) | MOBILE_SCAN (0.8) | UNKNOWN (0.9)
document_type: enum         # DISCHARGE_SUMMARY | AFTER_VISIT_SUMMARY | PROGRESS_NOTES
                            # | MEDICAL_RECORDS | CLAIM_FORM | AUTHORIZATION_FORM
metadata_app_signature: str?    # "CamScanner", "Adobe Scan", null

# Integrity [COMPUTED]
integrity_score: float          # 0.0 - 1.0
font_consistency_score: float   # 0.0 - 1.0
alignment_score: float          # 0.0 - 1.0
color_consistency_score: float  # 0.0 - 1.0
header_content_match: bool      # Hospital in header matches body

# ReleasePoint validation
releasepoint_request_id: str?   # "RP 15751837"
releasepoint_status: enum       # NOT_REQUESTED | REQUESTED | NOT_YET_PRINTED
                                # | RECORDS_RECEIVED | CONFIRMED_MATCH | CONFIRMED_DISCREPANT
```

---

## 4. Investigation Note

```yaml
note_id: str                # "N-{YEAR}-{seq}" (e.g., "N-2026-22319635")
claim_id: str
created_at: datetime
created_by: str
note_type: enum             # FRAUD_ALERT | FRAUD_REVIEW | NIGO_NOTICE | RECORDS_REQUEST | CLOSURE
content: str                # Full text (supports markdown)
action_required: str?       # e.g., "Request MR via ReleasePoint"
```

---

## 5. Rules Engine (18 Rules)

### Original 15 + 3 New From Real Cases

| ID | Name | Severity | Category | Condition |
|----|------|----------|----------|-----------|
| R-001 | Excessive Dependents | BLOCK | DEPENDENT_ABUSE | dependent_count > 15 |
| R-002 | Terminated Employee Filing | BLOCK | TEMPORAL | filing > 30 days post-term |
| R-003 | High Claim Amount Ratio | FLAG | CLAIM_PATTERN | amount > 90% of max |
| R-004 | Provider Volume Outlier | FLAG | PROVIDER | claims > 95th percentile |
| R-005 | No-Facility Claim | INFO | PROVIDER | hospital claim, no facility |
| R-006 | Rapid Resubmission | FLAG | CLAIM_PATTERN | resubmit < 7 days |
| R-007 | Service-to-Filing Gap | INFO | TEMPORAL | gap > 180 days |
| R-008 | Recent Beneficiary Change | FLAG | ELIGIBILITY | change < 90 days |
| R-009 | Shared Address Cluster | FLAG | NETWORK | 5+ unrelated at address |
| R-010 | Family Claim Density | FLAG | DEPENDENT_ABUSE | 8+ family claims in 90 days |
| R-011 | Termination Rush | BLOCK | TEMPORAL | 2+ claims within 14 days of term |
| R-012 | Document Tampering Signal | BLOCK | DOCUMENT | integrity_score < 0.5 |
| R-013 | New Policy Quick Claim | FLAG | ELIGIBILITY | policy < 90 days + amount > $500 |
| R-014 | Weekend/Holiday Filing | INFO | TEMPORAL | filed on weekend/holiday |
| R-015 | Cross-Member Provider Sharing | FLAG | NETWORK | same provider, 3+ members at address |
| **R-016** | **Mobile Scan App Source** | **FLAG** | **DOCUMENT** | **source=MOBILE_SCAN or app_signature present** |
| **R-017** | **Hospital Indemnity Stacking** | **FLAG** | **BENEFIT_EXPLOIT** | **4+ claims same event, 2+ relationship types** |
| **R-018** | **Document Visual Inconsistencies** | **FLAG** | **DOCUMENT** | **font/alignment/color score < 0.7** |

**Score boost:** BLOCK = +0.5 (up to 30pts), FLAG = +0.25 (up to 15pts), INFO = +0.05 (up to 3pts)

---

## 6. Risk Scoring Formula

```
Final Score = Feature Score (0-50) + Rules Boost (0-60)

Feature Score weights:
  policy_features:          10%
  member_features:          12%
  claim_features:           13%
  provider_features:        10%
  network_features:         10%
  temporal_features:         5%
  document_source_features:  8%   ← NEW (mobile_scan_ratio, releasepoint_bypass)
  benefit_stacking_features: 7%   ← NEW (claims_per_event, relationship_type_diversity)

Tiers: HIGH (≥60) | MEDIUM (30-59) | LOW (<30)
```

---

## 7. Entity Graph Edges

```yaml
# Core (existing)
Member ──EMPLOYED_BY──► Employer
Member ──LIVES_AT──► Address
Member ──ENROLLED_IN──► Policy
Dependent ──DEPENDENT_OF──► Member
Claim ──FILED_BY──► Member
Claim ──TREATED_BY──► Provider
Claim ──SERVICED_AT──► Facility

# New (from real cases)
Claim ──SAME_EVENT──► Claim          # Same hospitalization
Claim ──STACKED_WITH──► Claim        # Same event, different relationship types
Document ──SUBMITTED_FOR──► Claim
Document ──CONTRADICTS──► Document   # Conflicting info
```

### Pattern Detection (8 Patterns)

| ID | Pattern | Severity Threshold |
|----|---------|-------------------|
| GP-001 | Dependent Ring | HIGH: 6+ members or 10+ dependents at shared address |
| GP-002 | Provider Cluster | HIGH: >50 claims from single provider |
| GP-003 | Shared Address Group | HIGH: 6+ unrelated members |
| GP-004 | Termination Rush | HIGH: 4+ claims in 14-day window |
| GP-005 | Document Tampering Cluster | HIGH: 4+ integrity failures, same member |
| GP-006 | **Indemnity Stacking Ring** | HIGH: 7+ claims, 3+ relationship types |
| GP-007 | **Document Source Mismatch** | HIGH: 2+ mobile scans when facility has RP |
| GP-008 | **Cross-Claim Contradiction** | HIGH: Major facility/diagnosis conflicts |

---

## 8. Fraud Scenario Templates

### FS-001: Falsified Discharge Summary *(from C-2026-1325588)*
```yaml
frequency: 5%
fraud_status: VALID_FRAUD
member: age 55-80
claims: HOSPITAL_ADMISSION, dx J44/J96/I50, amount $500-$2000
documents: source=MOBILE_SCAN, filename="CamScanner_*", integrity 0.2-0.5
            font_consistency 0.3-0.6, header_content_match=false
rules_fire: [R-012, R-016]
note: "Fraud alert - request MR via ReleasePoint to confirm validity"
```

### FS-002: Indemnity Stacking - Legitimate *(from C-2026-1321395)*
```yaml
frequency: 2%
fraud_status: INVALID_FRAUD  ← FALSE POSITIVE
member: age 25-40, female
claims: 6-12 HOSPITAL_INDEMNITY claims, dx O30/Z38, amount $200-$1000
        relationship_types: [SELF, POLICYHOLDER, BENEFICIARY, INSURED]
        all within 3-7 day window
documents: source=PROVIDER_PORTAL, integrity 0.85-1.0 (clean)
rules_fire: [R-017]
note: "Member gave birth to twins. Closing task."
resolution: Cleared after review
```

### FS-003: Manipulated Urgent Care Records *(from C-2026-1297921)*
```yaml
frequency: 3%
fraud_status: VALID_FRAUD
member: age 20-35
claims: URGENT_CARE_VISIT, dx J06/R05, amount $100-$500
documents: 2 files (Notes + After Visit Summary)
           source=MEMBER_UPLOAD_PDF, font_consistency 0.3-0.5
           alignment 0.3-0.6, color_consistency 0.4-0.6
rules_fire: [R-018, R-016]
note: "Inconsistencies with font color, quality. Accept only via ReleasePoint."
```

### FS-004: High-Volume Legitimate - Chronic *(from C-2026-1331913)*
```yaml
frequency: 4%
fraud_status: INVALID_FRAUD  ← FALSE POSITIVE
member: age 30-65
claims: 8-15 claims over 3 months, dx Z51/D70/C50
        mix of APPROVED and DENIED (policy definition not met)
documents: source=PROVIDER_PORTAL, integrity 0.8-1.0 (clean)
rules_fire: [R-010] (maybe)
note: "After reviewing medical records, none found to be fraudulent."
resolution: Cleared after records review
```

### FS-005-008: Standard patterns (existing)
```yaml
FS-005: Dependent Ring         - 3% - VALID_FRAUD - R-001, R-009
FS-006: Termination Rush       - 3% - VALID_FRAUD - R-002, R-011
FS-007: Provider Mill          - 2% - VALID_FRAUD - R-004, R-005
FS-008: Clean Claims           - 55% - NOT_FLAGGED - no rules fire
```

---

## 9. Distribution Targets

```yaml
risk_distribution:
  HIGH: 15% | MEDIUM: 30% | LOW: 55%

fraud_status_distribution:
  NOT_FLAGGED: 60% | FLAGGED_FOR_REVIEW: 20%
  VALID_FRAUD: 10% | INVALID_FRAUD: 7% | REFERRED_SIU: 3%

claim_status_distribution:
  APPROVED: 45% | DENIED: 20% | PENDING: 15%
  NIGO: 8% | UNDER_REVIEW: 7% | CLOSED: 5%
```

---

## 10. ICD-10 Codes Used

```yaml
# Respiratory (falsified records pattern)
J44: COPD | J06: Upper respiratory infection | J96: Respiratory failure

# Obstetric (stacking pattern)
O30: Multiple gestation | Z38: Liveborn infant | O80: Uncomplicated delivery

# Oncology (high-volume legitimate)
Z51: Aftercare | D70: Neutropenia | C50: Breast cancer | C34: Lung cancer

# Urgent Care (manipulated records)
J02: Sore throat | R05: Cough | R50: Fever | A08: Viral GI infection

# Cardiac/Renal
I50: Heart failure | N17: Acute kidney failure
```

---

## 11. Implementation Constraints

1. **IDs follow format** — Claims: `C-2026-{7-digit}`, Notes: `N-2026-{8-digit}`, RP: `RP {8-digit}`
2. **False positives are mandatory** — 7% of flagged claims must resolve as INVALID_FRAUD
3. **Documents from MOBILE_SCAN always get low integrity** — score 0.2-0.6
4. **Stacking claims share service_date ± 3 days** — linked via `stacked_with`
5. **Clinical plausibility** — don't pair obstetric codes with male/elderly members
6. **ReleasePoint only for enrolled facilities** — check `facility.releasepoint_enrolled`
7. **Notes chain** — later notes should reference earlier note_ids when continuing investigation
8. **Tools return dicts, never raise** — wrap failures in `{"error": "..."}`
9. **All scoring is deterministic and pre-computed at startup**