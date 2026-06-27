

# SCHEMA.md — Data Model Specification for Claims Copilot

> **Purpose:** This document defines the complete data schema for the Claims Copilot system, incorporating patterns derived from real scrubbed fraud cases. Any AI agent or developer implementing data generation, API endpoints, or tool functions should treat this as the canonical reference.

---

## Conventions

- All IDs use format `{PREFIX}-{YEAR}-{SEQUENCE}` (e.g., `C-2026-1325588`)
- Dates are ISO 8601 (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`)
- Money values are USD floats, two decimal places
- Enums are uppercase snake_case strings
- Optional fields are marked with `?`
- Fields marked `[COMPUTED]` are derived at startup, not stored directly

---

## 1. Core Entities

### 1.1 Member

```yaml
Member:
  member_id: str                    # "M-2026-{seq}" 
  first_name: str
  last_name: str
  date_of_birth: date              # YYYY-MM-DD
  date_of_death: date?             # null if alive
  age: int                         # [COMPUTED] from DOB
  gender: enum                     # MALE | FEMALE | NON_BINARY
  ssn_masked: str                  # "*****XX" format (last 2 digits only)
  resident_state: str              # Full state name (e.g., "Nebraska")
  address_id: str                  # FK → Address
  employer_id: str                 # FK → Employer
  enrollment_date: date
  termination_date: date?          # null if active
  is_active: bool                  # [COMPUTED] termination_date is null or future
  w9_on_file: bool
  dependent_count: int             # Total dependents enrolled
  portal_cases: list[str]          # Case IDs from EE Portal
  contact_phone: str?
  contact_email: str?
```

### 1.2 Dependent

```yaml
Dependent:
  dependent_id: str                # "D-2026-{seq}"
  member_id: str                   # FK → Member
  first_name: str
  last_name: str
  date_of_birth: date
  relationship: enum               # SPOUSE | CHILD | DOMESTIC_PARTNER | OTHER
  enrollment_date: date
  termination_date: date?
  address_id: str                  # FK → Address (may differ from member)
  is_active: bool
```

### 1.3 Employer

```yaml
Employer:
  employer_id: str                 # "EMP-{seq}"
  name: str
  industry: str
  address_id: str                  # FK → Address
  employee_count: int
  policy_ids: list[str]            # FK → Policy
  is_active: bool
```

### 1.4 Address

```yaml
Address:
  address_id: str                  # "ADDR-{seq}"
  street_line_1: str
  street_line_2: str?
  city: str
  state: str                       # 2-letter code
  zip_code: str                    # 5-digit or 5+4
  address_type: enum               # RESIDENTIAL | COMMERCIAL | PO_BOX | FACILITY
  occupant_count: int              # [COMPUTED] members + dependents at this address
```

---

## 2. Policy & Coverage

### 2.1 Policy

```yaml
Policy:
  policy_id: str                   # "POL-{seq}"
  policy_number: str               # Display number (e.g., "70373")
  employer_id: str                 # FK → Employer
  policy_type: enum                # GROUP | INDIVIDUAL | VOLUNTARY
  product_line: enum               # HOSPITAL_INDEMNITY | ACCIDENT | CRITICAL_ILLNESS | CANCER | LIFE
  effective_date: date
  termination_date: date?
  status: enum                     # ACTIVE | TERMINATED | PENDING | SUSPENDED
  state_of_issue: str              # 2-letter state code
  
  # Coverage configuration
  coverage_tiers: list[CoverageTier]
  benefit_schedule: BenefitSchedule
  
  # Change tracking (for fraud signals)
  ownership_change_date: date?
  beneficiary_change_date: date?
  policy_age_days: int             # [COMPUTED] days since effective_date
```

### 2.2 CoverageTier

```yaml
CoverageTier:
  tier_id: str
  policy_id: str                   # FK → Policy
  tier_name: enum                  # EMPLOYEE_ONLY | EMPLOYEE_SPOUSE | EMPLOYEE_CHILDREN | FAMILY
  monthly_premium: float
  enrolled_members: list[str]      # FK → Member
```

### 2.3 BenefitSchedule

```yaml
BenefitSchedule:
  schedule_id: str
  policy_id: str                   # FK → Policy
  benefits: list[BenefitDefinition]

BenefitDefinition:
  benefit_type: enum               # See BENEFIT_TYPES enum below
  payment_amount: float            # Per-occurrence or per-day
  payment_frequency: enum          # PER_OCCURRENCE | PER_DAY | PER_ADMISSION
  max_days: int?                   # Max covered days (for confinement)
  max_occurrences: int?            # Max claims per benefit period
  waiting_period_days: int         # Days before benefit activates
  elimination_period_days: int     # Days before payment begins per event
  benefit_period: enum             # CALENDAR_YEAR | POLICY_YEAR | LIFETIME
  requires_admission: bool         # Must be admitted (not just ER/outpatient)
  stacking_allowed: bool           # Can multiple relationship types claim same event
```

---

## 3. Claims

### 3.1 Claim

```yaml
Claim:
  claim_id: str                    # "C-2026-{seq}" (e.g., "C-2026-1325588")
  batch_claim_id: str?             # "BC-2026-{seq}" — groups related claims
  case_claim_id: str?              # "CC-2026-{seq}" — case-level grouping
  member_id: str                   # FK → Member
  policy_id: str                   # FK → Policy
  provider_id: str                 # FK → Provider
  facility_id: str?                # FK → Facility (null for telehealth/no-facility)
  
  # Claim classification
  benefit_type: enum               # See BENEFIT_TYPES
  relationship_type: enum          # See RELATIONSHIP_TYPES
  diagnosis_code: str              # ICD-10 primary (e.g., "Z51")
  diagnosis_codes_secondary: list[str]  # Additional ICD-10 codes
  procedure_codes: list[str]?      # CPT codes if applicable
  
  # Financials
  claim_amount: float              # Requested amount
  approved_amount: float?          # null if pending
  payment_amount: float?           # Actual paid (may differ from approved)
  
  # Dates
  service_date_start: date         # First date of service
  service_date_end: date           # Last date of service (same as start for single-day)
  admission_date: date?            # Hospital admission date
  discharge_date: date?            # Hospital discharge date
  filing_date: date                # When claim was submitted
  processed_date: date?            # When claim was adjudicated
  
  # Status
  claim_status: enum               # See CLAIM_STATUSES
  denial_reason: str?              # Free text or coded reason
  nigo_flag: bool                  # Not In Good Order
  nigo_reason: str?                # Why NIGO (e.g., "Records pending via ReleasePoint")
  
  # Submission metadata
  submission_channel: enum         # EE_PORTAL | EMPLOYER_PORTAL | PAPER | FAX | API
  is_resubmission: bool
  original_claim_id: str?          # FK → Claim (if resubmission)
  contact_count: int               # Number of member contacts about this claim
  
  # Fraud scoring [COMPUTED]
  risk_score: float                # 0-100
  risk_tier: enum                  # HIGH | MEDIUM | LOW
  rules_triggered: list[str]       # Rule IDs that fired
  fraud_status: enum               # See FRAUD_STATUSES
  assigned_examiner: str?
  
  # Relationships
  related_claim_ids: list[str]     # Claims from same event/hospitalization
  stacked_with: list[str]          # Claims filed for same event, different relationship types
```

### 3.2 Enums for Claims

```yaml
BENEFIT_TYPES:
  - HOSPITAL_ADMISSION             # Lump sum per admission ($500-$2,000)
  - HOSPITAL_CONFINEMENT           # Per-day payment ($100-$700/day)
  - ICU_ADMISSION                  # ICU-specific lump sum ($1,000-$5,000)
  - ICU_CONFINEMENT                # ICU per-day ($200-$1,500/day)
  - HOSPITAL_INDEMNITY             # General hospital indemnity
  - URGENT_CARE_VISIT              # Per-visit ($50-$200)
  - EMERGENCY_ROOM                 # ER visit ($100-$500)
  - OUTPATIENT_SURGERY             # Outpatient procedure ($200-$1,000)
  - WELLNESS_BENEFIT               # Annual wellness ($50-$100)
  - ACCIDENT_INJURY                # Accident-specific
  - CRITICAL_ILLNESS_DIAGNOSIS     # Lump sum on diagnosis
  - CANCER_DIAGNOSIS               # Cancer-specific lump sum
  - CANCER_TREATMENT               # Per-treatment payment

RELATIONSHIP_TYPES:
  - SELF                           # Member is the patient
  - POLICYHOLDER                   # Filed in capacity as policyholder
  - BENEFICIARY                    # Filed as designated beneficiary
  - INSURED                        # Filed as insured party
  - DEPENDENT_SPOUSE               # Spouse's claim under member's policy
  - DEPENDENT_CHILD                # Child's claim under member's policy

CLAIM_STATUSES:
  - PENDING                        # Awaiting adjudication
  - APPROVED                       # Claim approved, payment pending
  - DENIED                         # Claim denied
  - PAID                           # Payment issued
  - NIGO                           # Not In Good Order — docs needed
  - UNDER_REVIEW                   # Flagged for fraud review
  - ESCALATED                      # Sent to SIU/Prudential
  - CLOSED                         # Final disposition reached
  - VOID                           # Claim voided/reversed

DENIAL_REASONS:
  - POLICY_DEFINITION_NOT_MET      # Benefit doesn't cover this event
  - COVERAGE_NOT_ACTIVE            # Policy terminated or not yet effective
  - DUPLICATE_CLAIM                # Same event already paid
  - DOCUMENTATION_INSUFFICIENT     # Records missing or incomplete
  - NIGO_RECORDS_PENDING           # Waiting for proper documentation
  - ELIMINATION_PERIOD             # Within waiting/elimination period
  - MAX_BENEFIT_REACHED            # Annual or lifetime max hit
  - PRE_EXISTING_CONDITION         # Exclusion applies
  - NOT_MEDICALLY_NECESSARY        # Doesn't meet medical necessity
  - FRAUD_SUSPECTED                # Denied due to fraud indicators

FRAUD_STATUSES:
  - NOT_FLAGGED                    # No fraud indicators
  - FLAGGED_FOR_REVIEW             # Rules triggered, needs examiner review
  - UNDER_INVESTIGATION            # Active investigation
  - VALID_FRAUD                    # Confirmed fraud
  - INVALID_FRAUD                  # Flagged but determined legitimate (false positive)
  - REFERRED_SIU                   # Sent to Special Investigations Unit
  - REFERRED_EXTERNAL              # Sent to law enforcement or regulatory
```

---

## 4. Providers & Facilities

### 4.1 Provider

```yaml
Provider:
  provider_id: str                 # "PROV-{seq}"
  first_name: str
  last_name: str
  credential: str                  # "MD", "DO", "APRN", "PA", "NP"
  npi: str                         # 10-digit National Provider Identifier
  specialty: str                   # e.g., "Family Medicine", "Emergency Medicine"
  facility_ids: list[str]          # FK → Facility (where they practice)
  state_licenses: list[str]        # States where licensed
  is_active: bool
  
  # Fraud signals [COMPUTED]
  total_claims: int                # Total claims treated
  unique_members: int              # Distinct members seen
  claim_volume_percentile: float   # Compared to peers in same specialty
  avg_claim_amount: float
  no_facility_claim_count: int     # Claims without associated facility
```

### 4.2 Facility

```yaml
Facility:
  facility_id: str                 # "FAC-{seq}"
  name: str                        # e.g., "Baptist Beaumont Hospital"
  facility_type: enum              # HOSPITAL | URGENT_CARE | CLINIC | ASC | ER | VIRTUAL
  address_id: str                  # FK → Address
  npi: str?                        # Facility NPI
  phone: str
  is_in_network: bool
  state: str                       # 2-letter code
  
  # For document verification
  known_ehr_system: str?           # "Epic", "Cerner", "Meditech", etc.
  document_header_template: str?   # Expected header format for validation
  releasepoint_enrolled: bool      # Can we request records via RP?
```

---

## 5. Documents & Evidence

### 5.1 Document

```yaml
Document:
  doc_id: str                      # "DOC-{seq}"
  claim_id: str                    # FK → Claim
  member_id: str                   # FK → Member
  
  # File metadata
  filename: str                    # Original filename (e.g., "CamScanner_4-1-26_17.54_1.jpeg")
  file_format: enum                # JPEG | PNG | PDF | TIFF | HEIC
  file_size_bytes: int
  page_count: int                  # For multi-page documents
  received_date: datetime
  
  # Source classification
  source_type: enum                # See DOCUMENT_SOURCE_TYPES
  submission_channel: enum         # MEMBER_UPLOAD | PROVIDER_FAX | RELEASEPOINT | EMAIL | PORTAL
  metadata_app_signature: str?     # "CamScanner", "Adobe Scan", "Genius Scan", null
  
  # Document classification
  document_type: enum              # See DOCUMENT_TYPES
  document_subtype: str?           # More specific (e.g., "Discharge Summary", "After Visit Summary")
  
  # Content extracted
  hospital_name_header: str?       # Hospital name from document header
  hospital_name_body: str?         # Hospital name from body content
  patient_name: str?               # Patient name on document
  service_date_on_doc: date?       # Date of service stated in document
  provider_name_on_doc: str?       # Provider name on document
  
  # Integrity analysis [COMPUTED]
  integrity_score: float           # 0.0 - 1.0 overall
  integrity_checks: DocumentIntegrityResult
  
  # ReleasePoint validation
  releasepoint_request_id: str?    # "RP {number}" (e.g., "RP 15751837")
  releasepoint_status: enum        # See RP_STATUSES
  releasepoint_received_date: date?
  releasepoint_discrepancies: list[str]?  # Differences found between member-submitted and RP version
```

### 5.2 DocumentIntegrityResult

```yaml
DocumentIntegrityResult:
  doc_id: str                      # FK → Document
  
  # 16 integrity checks (pass/fail/not_applicable)
  checks:
    - check_id: str                # "DOC-001" through "DOC-016"
      check_name: str
      result: enum                 # PASS | FAIL | WARNING | NOT_APPLICABLE
      confidence: float            # 0.0 - 1.0
      details: str                 # Human-readable explanation
      
  # Aggregate scores
  font_consistency_score: float    # 0.0 - 1.0 (1.0 = all fonts match)
  alignment_score: float           # 0.0 - 1.0 (1.0 = perfect alignment)
  color_consistency_score: float   # 0.0 - 1.0 (1.0 = uniform color profile)
  header_content_match: bool       # Hospital in header matches body
  metadata_consistency: bool       # EXIF/PDF metadata internally consistent
  resolution_uniform: bool         # All pages same DPI/resolution
  
  # Risk classification
  source_risk_level: float         # 0.0 - 1.0 based on DOCUMENT_SOURCE_RISK
  overall_risk: enum               # CLEAN | SUSPICIOUS | LIKELY_MANIPULATED
  recommendation: str              # e.g., "Request via ReleasePoint for validation"
```

### 5.3 Document Enums

```yaml
DOCUMENT_SOURCE_TYPES:
  - RELEASEPOINT                   # Risk: 0.0 — Trusted provider release service
  - PROVIDER_PORTAL                # Risk: 0.1 — Direct from provider EHR
  - PROVIDER_FAX                   # Risk: 0.2 — Faxed from provider office
  - EMPLOYER_SUBMITTED             # Risk: 0.3 — Via employer HR
  - MEMBER_UPLOAD_PDF              # Risk: 0.4 — Member uploaded PDF
  - MEMBER_EMAIL                   # Risk: 0.5 — Member emailed attachment
  - MEMBER_FAX                     # Risk: 0.6 — Member faxed
  - MOBILE_SCAN                    # Risk: 0.8 — CamScanner/Adobe Scan/etc.
  - SCREENSHOT                     # Risk: 0.85 — Phone screenshot of screen
  - UNKNOWN                        # Risk: 0.9 — Cannot determine source

DOCUMENT_TYPES:
  - MEDICAL_RECORDS                # General medical records
  - DISCHARGE_SUMMARY              # Hospital discharge summary
  - AFTER_VISIT_SUMMARY            # Post-visit patient summary (e.g., Epic MyChart)
  - PROGRESS_NOTES                 # Provider progress/care team notes
  - OPERATIVE_REPORT               # Surgery/procedure report
  - LAB_RESULTS                    # Laboratory results
  - IMAGING_REPORT                 # Radiology/imaging
  - AUTHORIZATION_FORM             # Signed medical authorization
  - ITEMIZED_BILL                  # Hospital/provider billing
  - CLAIM_FORM                     # Member-completed claim form
  - ID_DOCUMENT                    # Driver's license, insurance card
  - BIRTH_CERTIFICATE              # For dependent/newborn claims
  - DEATH_CERTIFICATE              # For life/AD&D claims
  - OTHER                          # Uncategorized

RP_STATUSES:
  - NOT_REQUESTED                  # No ReleasePoint request initiated
  - REQUESTED                      # Request submitted, awaiting print/send
  - NOT_YET_PRINTED                # Request in queue (from real case: "still not yet printed")
  - SENT_TO_PROVIDER               # Request delivered to provider
  - PROVIDER_ACKNOWLEDGED          # Provider confirmed receipt
  - RECORDS_RECEIVED               # Records received from provider
  - CONFIRMED_MATCH                # RP records match member-submitted
  - CONFIRMED_DISCREPANT           # RP records differ from member-submitted
  - PROVIDER_NO_RECORD             # Provider has no record of patient/visit
  - EXPIRED                        # Request timed out
```

---

## 6. Investigation & Workflow

### 6.1 InvestigationNote

```yaml
InvestigationNote:
  note_id: str                     # "N-{YEAR}-{seq}" (e.g., "N-2026-22319635")
  claim_id: str                    # FK → Claim
  member_id: str                   # FK → Member
  
  created_at: datetime
  created_by: str                  # Examiner name or "System"
  
  note_type: enum                  # See NOTE_TYPES
  priority: enum                   # URGENT | HIGH | MEDIUM | LOW | INFO
  
  content: str                     # Full note text (supports markdown)
  
  # Structured action items
  action_required: str?            # e.g., "Request MR via ReleasePoint"
  action_due_date: date?
  action_completed: bool
  action_completed_date: date?
  
  # References
  related_note_ids: list[str]      # Previous notes in chain
  related_claim_ids: list[str]     # Other claims mentioned
  referenced_documents: list[str]  # FK → Document

NOTE_TYPES:
  - FRAUD_ALERT                    # Initial fraud flag raised
  - FRAUD_REVIEW                   # Fraud analyst review note
  - NIGO_NOTICE                    # Documentation deficiency notice
  - RECORDS_REQUEST                # Medical records requested
  - RECORDS_RECEIVED               # Medical records received
  - EXAMINER_REVIEW                # Standard examiner notes
  - ESCALATION                     # Escalated to SIU or support list
  - CLOSURE                        # Investigation closed
  - SYSTEM_GENERATED               # Automated system note
  - COPILOT_FINDING                # AI copilot generated finding
```

### 6.2 PortalCase

```yaml
PortalCase:
  case_id: str                     # "02443094" format (from EE Portal)
  member_id: str                   # FK → Member
  subject: str                     # e.g., "EE Portal Case - M P"
  priority: enum                   # HIGH | MEDIUM | LOW
  case_origin: enum                # WEB | PHONE | EMAIL | FAX | CHAT
  date_opened: datetime
  date_closed: datetime?
  status: enum                     # OPEN | CLOSED | PENDING | ESCALATED
  owner: str                       # Assigned to (e.g., "System Administrator")
  related_claim_ids: list[str]     # FK → Claim
```

### 6.3 ContactHistory

```yaml
ContactRecord:
  contact_id: str                  # "CONT-{seq}"
  claim_id: str?                   # FK → Claim (may be general inquiry)
  member_id: str                   # FK → Member
  contact_date: datetime
  channel: enum                    # PHONE | EMAIL | PORTAL | CHAT | MAIL
  direction: enum                  # INBOUND | OUTBOUND
  subject: str
  summary: str
  duration_minutes: int?           # For phone calls
  outcome: str                     # e.g., "Requested additional documentation"
  follow_up_required: bool
  follow_up_date: date?
```

### 6.4 WorkflowTask

```yaml
WorkflowTask:
  task_id: str                     # "TASK-{seq}"
  claim_id: str                    # FK → Claim
  task_type: enum                  # See TASK_TYPES
  title: str
  description: str
  assigned_to: str
  created_date: datetime
  due_date: date
  completed_date: datetime?
  status: enum                     # OPEN | IN_PROGRESS | COMPLETED | CANCELLED | OVERDUE
  priority: enum                   # URGENT | HIGH | MEDIUM | LOW
  
  # Outcome
  resolution: str?
  resolution_type: enum?           # COMPLETED | ESCALATED | CANCELLED | REASSIGNED

TASK_TYPES:
  - FRAUD_REVIEW                   # Review claim for fraud indicators
  - RECORDS_REQUEST                # Request medical records
  - NIGO_FOLLOW_UP                 # Follow up on NIGO notice
  - RELEASEPOINT_ORDER             # Submit ReleasePoint request
  - EXAMINER_REVIEW                # Standard claim review
  - SIU_REFERRAL                   # Refer to Special Investigations
  - SUPPORT_LIST_REVIEW            # Refer to Prudential support list
  - MEMBER_OUTREACH                # Contact member for information
  - PROVIDER_VERIFICATION          # Verify provider/facility
  - FINAL_DETERMINATION            # Make approve/deny/escalate decision
```

---

## 7. Rules Engine

### 7.1 Rule

```yaml
Rule:
  rule_id: str                     # "R-{seq}" (e.g., "R-001")
  name: str
  description: str
  category: enum                   # See RULE_CATEGORIES
  severity: enum                   # BLOCK | FLAG | INFO
  
  # Condition (evaluated per claim)
  condition_type: enum             # THRESHOLD | PATTERN | TEMPORAL | NETWORK | DOCUMENT
  condition_field: str             # Which data field(s) to evaluate
  condition_operator: str          # ">", "<", "==", "IN", "CONTAINS", "EXISTS"
  condition_value: any             # Threshold or pattern to match
  
  # Scoring impact
  score_boost: float               # Points added to risk score when triggered
  # BLOCK: +0.5 normalized (up to 30 pts)
  # FLAG: +0.25 normalized (up to 15 pts)
  # INFO: +0.05 normalized (up to 3 pts)
  
  # Metadata
  rationale: str                   # Why this rule exists (for examiner display)
  regulatory_reference: str?       # State DOI or federal regulation
  inspired_by_case: str?           # Real case that inspired this rule
  false_positive_rate: float       # Expected FP rate (0.0 - 1.0)
  
  # Activation
  is_active: bool
  effective_date: date
  last_modified: date

RULE_CATEGORIES:
  - DEPENDENT_ABUSE                # Excessive/fraudulent dependents
  - PROVIDER_PATTERN               # Suspicious provider behavior
  - TEMPORAL_ANOMALY               # Timing-based fraud signals
  - DOCUMENT_INTEGRITY             # Document manipulation
  - NETWORK_FRAUD                  # Ring/collusion patterns
  - BENEFIT_EXPLOITATION           # Stacking, over-utilization
  - ELIGIBILITY_ABUSE              # Coverage manipulation
  - CLAIM_PATTERN                  # Suspicious claim characteristics
```

### 7.2 Complete Rule Definitions (18 Rules)

```yaml
Rules:
  # === ORIGINAL 15 RULES ===
  
  - rule_id: "R-001"
    name: "Excessive Dependents"
    severity: BLOCK
    category: DEPENDENT_ABUSE
    condition: "member.dependent_count > 15"
    score_boost: 0.5
    rationale: "Members with 15+ dependents are statistical outliers indicating possible dependent fraud ring."
    false_positive_rate: 0.02
    
  - rule_id: "R-002"
    name: "Terminated Employee Filing"
    severity: BLOCK
    category: TEMPORAL_ANOMALY
    condition: "claim.filing_date > member.termination_date AND days_since_termination > 30"
    score_boost: 0.5
    rationale: "Claims filed more than 30 days post-termination suggest coverage exploitation."
    false_positive_rate: 0.05
    
  - rule_id: "R-003"
    name: "High Claim Amount Ratio"
    severity: FLAG
    category: CLAIM_PATTERN
    condition: "claim.claim_amount > (policy.benefit_schedule.max_amount * 0.9)"
    score_boost: 0.25
    rationale: "Claims at 90%+ of benefit maximum may indicate knowledge of exact coverage limits."
    false_positive_rate: 0.15
    
  - rule_id: "R-004"
    name: "Provider Volume Outlier"
    severity: FLAG
    category: PROVIDER_PATTERN
    condition: "provider.total_claims > percentile_95(all_providers)"
    score_boost: 0.25
    rationale: "Providers with claim volumes above 95th percentile may be operating a claim mill."
    false_positive_rate: 0.10
    
  - rule_id: "R-005"
    name: "No-Facility Claim"
    severity: INFO
    category: PROVIDER_PATTERN
    condition: "claim.facility_id IS NULL AND claim.benefit_type IN (HOSPITAL_ADMISSION, ICU_ADMISSION)"
    score_boost: 0.05
    rationale: "Hospital admission claims without a facility reference are unusual."
    false_positive_rate: 0.20
    
  - rule_id: "R-006"
    name: "Rapid Resubmission"
    severity: FLAG
    category: CLAIM_PATTERN
    condition: "claim.is_resubmission AND days_between(denial, resubmission) < 7"
    score_boost: 0.25
    rationale: "Claims resubmitted within 7 days of denial often have altered documentation."
    false_positive_rate: 0.12
    
  - rule_id: "R-007"
    name: "Service-to-Filing Gap"
    severity: INFO
    category: TEMPORAL_ANOMALY
    condition: "days_between(claim.service_date_start, claim.filing_date) > 180"
    score_boost: 0.05
    rationale: "Claims filed 6+ months after service are harder to verify and may indicate manufactured events."
    false_positive_rate: 0.25
    
  - rule_id: "R-008"
    name: "Recent Beneficiary Change"
    severity: FLAG
    category: ELIGIBILITY_ABUSE
    condition: "policy.beneficiary_change_date IS NOT NULL AND days_since_change < 90"
    score_boost: 0.25
    rationale: "Beneficiary changes within 90 days of a large claim suggest premeditation."
    false_positive_rate: 0.08
    
  - rule_id: "R-009"
    name: "Shared Address Cluster"
    severity: FLAG
    category: NETWORK_FRAUD
    condition: "address.occupant_count > 5 AND occupants_are_unrelated"
    score_boost: 0.25
    rationale: "Multiple unrelated members at same address may indicate a fraud ring using a single location."
    false_positive_rate: 0.15
    
  - rule_id: "R-010"
    name: "Family Claim Density"
    severity: FLAG
    category: DEPENDENT_ABUSE
    condition: "count(claims WHERE member.family_unit AND last_90_days) > 8"
    score_boost: 0.25
    rationale: "8+ claims from same family in 90 days is abnormal utilization."
    false_positive_rate: 0.10
    
  - rule_id: "R-011"
    name: "Termination Rush"
    severity: BLOCK
    category: TEMPORAL_ANOMALY
    condition: "count(claims WHERE days_before_termination < 14) >= 2"
    score_boost: 0.5
    rationale: "Multiple claims in final 14 days before termination suggests knowledge of impending coverage loss."
    false_positive_rate: 0.07
    
  - rule_id: "R-012"
    name: "Document Tampering Signal"
    severity: BLOCK
    category: DOCUMENT_INTEGRITY
    condition: "document.integrity_score < 0.5"
    score_boost: 0.5
    rationale: "Documents with integrity scores below 0.5 show strong evidence of digital manipulation."
    false_positive_rate: 0.03
    
  - rule_id: "R-013"
    name: "New Policy Quick Claim"
    severity: FLAG
    category: ELIGIBILITY_ABUSE
    condition: "policy.policy_age_days < 90 AND claim.claim_amount > 500"
    score_boost: 0.25
    rationale: "Large claims within first 90 days of coverage may indicate enrollment-for-claim scheme."
    false_positive_rate: 0.12
    
  - rule_id: "R-014"
    name: "Weekend/Holiday Filing Pattern"
    severity: INFO
    category: TEMPORAL_ANOMALY
    condition: "claim.filing_date.is_weekend OR claim.filing_date.is_holiday"
    score_boost: 0.05
    rationale: "Claims filed on weekends/holidays when offices are closed may bypass normal verification."
    false_positive_rate: 0.40
    
  - rule_id: "R-015"
    name: "Cross-Member Provider Sharing"
    severity: FLAG
    category: NETWORK_FRAUD
    condition: "provider.unique_members_at_address(claim.member.address_id) >= 3"
    score_boost: 0.25
    rationale: "Same provider treating 3+ members at same address suggests coordinated filing."
    false_positive_rate: 0.08

  # === NEW RULES FROM REAL CASES ===
    
  - rule_id: "R-016"
    name: "Mobile Scan App Document Source"
    severity: FLAG
    category: DOCUMENT_INTEGRITY
    condition: "document.source_type == 'MOBILE_SCAN' OR document.metadata_app_signature IS NOT NULL"
    score_boost: 0.25
    rationale: "Medical records submitted via CamScanner or similar mobile apps rather than provider portals suggest member is submitting fabricated or altered records. Legitimate records come from provider EHR or ReleasePoint."
    inspired_by_case: "C-2026-1325588"
    false_positive_rate: 0.20
    
  - rule_id: "R-017"
    name: "Hospital Indemnity Stacking"
    severity: FLAG
    category: BENEFIT_EXPLOITATION
    condition: "count(claims WHERE same_member AND same_service_window_3_days AND benefit_type LIKE 'HOSPITAL%') > 4 AND count(DISTINCT relationship_type) >= 2"
    score_boost: 0.25
    rationale: "Multiple hospital indemnity claims for single event filed across different relationship types (Policyholder/Beneficiary/Insured) may exploit benefit structure. NOTE: May be legitimate for multiple births or extended stays — requires examiner review."
    inspired_by_case: "C-2026-1321395"
    false_positive_rate: 0.35
    
  - rule_id: "R-018"
    name: "Document Visual Inconsistencies"
    severity: FLAG
    category: DOCUMENT_INTEGRITY
    condition: "document.font_consistency_score < 0.7 OR document.alignment_score < 0.7 OR document.color_consistency_score < 0.7"
    score_boost: 0.25
    rationale: "Legitimate EHR-generated documents have uniform formatting. Mixed fonts, irregular word spacing, and color variations across a single document indicate digital cut-and-paste manipulation."
    inspired_by_case: "C-2026-1297921"
    false_positive_rate: 0.12
```

---

## 8. Risk Scoring

### 8.1 RiskScore

```yaml
RiskScore:
  claim_id: str                    # FK → Claim
  
  # Final score
  final_score: float               # 0 - 100
  risk_tier: enum                  # HIGH (≥60) | MEDIUM (30-59) | LOW (<30)
  
  # Feature breakdown (0-50 points total)
  feature_scores:
    policy_features: float         # 0-5 (10% of 50)
    member_features: float         # 0-6 (12% of 50)
    claim_features: float          # 0-6.5 (13% of 50)
    provider_features: float       # 0-5 (10% of 50)
    network_features: float        # 0-5 (10% of 50)
    temporal_features: float       # 0-2.5 (5% of 50)
    document_source_features: float    # 0-4 (8% of 50) — NEW
    benefit_stacking_features: float   # 0-3.5 (7% of 50) — NEW
  
  feature_score_total: float       # Sum of above (0-50)
  
  # Rules boost (0-60 points total)
  rules_boost:
    block_rules_fired: list[str]   # Rule IDs
    flag_rules_fired: list[str]
    info_rules_fired: list[str]
    block_boost: float             # Up to 30 points
    flag_boost: float              # Up to 15 points
    info_boost: float              # Up to 3 points
  
  rules_boost_total: float         # Sum of boosts (0-60)
  
  # Anomaly detection
  isolation_forest_score: float    # -1 to 1 (higher = more anomalous)
  anomaly_flag: bool               # True if isolation_forest_score > threshold
  
  # Explainability
  top_factors: list[RiskFactor]    # Top 5 contributors, ordered by impact
  explanation_text: str            # Human-readable summary

RiskFactor:
  factor_name: str                 # e.g., "R-001: Excessive Dependents"
  factor_type: enum                # RULE | FEATURE | ANOMALY
  contribution: float              # Points contributed to final score
  evidence: str                    # e.g., "Member has 35 dependents (threshold: 15)"
```

### 8.2 Feature Definitions

```yaml
FEATURE_DEFINITIONS:
  # Policy Features (10%)
  policy_age_days:
    description: "Days since policy effective date"
    risk_signal: "Younger policies = higher risk"
    normalization: "inverse_scale(0, 3650)"  # 0-10 years
    
  recent_ownership_change:
    description: "Policy ownership changed in last 180 days"
    risk_signal: "Recent changes before large claims"
    normalization: "binary(0, 1)"
    
  recent_beneficiary_change:
    description: "Beneficiary changed in last 90 days"
    risk_signal: "Beneficiary changes near claims"
    normalization: "binary(0, 1)"

  # Member Features (12%)
  member_tenure_days:
    description: "Days since enrollment"
    risk_signal: "Shorter tenure = higher risk"
    normalization: "inverse_scale(0, 3650)"
    
  dependent_count:
    description: "Number of enrolled dependents"
    risk_signal: "More dependents = potential abuse"
    normalization: "scale(0, 50)"
    
  termination_proximity_days:
    description: "Days until/since termination"
    risk_signal: "Claims near termination"
    normalization: "inverse_scale(0, 365)"
    
  # Claim Features (13%)
  amount_to_max_ratio:
    description: "Claim amount / benefit maximum"
    risk_signal: "Higher ratio = more suspicious"
    normalization: "scale(0.0, 1.0)"
    
  is_resubmission:
    description: "Claim is a resubmission of denied claim"
    risk_signal: "Resubmissions with altered docs"
    normalization: "binary(0, 1)"
    
  contact_count:
    description: "Number of member contacts about claim"
    risk_signal: "Excessive contact = pressure"
    normalization: "scale(0, 20)"

  # Provider Features (10%)
  provider_claim_volume:
    description: "Total claims for this provider"
    risk_signal: "High volume = possible mill"
    normalization: "percentile_rank"
    
  no_facility_flag:
    description: "Hospital claim with no facility"
    risk_signal: "Missing facility = phantom claim"
    normalization: "binary(0, 1)"

  # Network Features (10%)
  shared_address_count:
    description: "Unrelated members at same address"
    risk_signal: "Address sharing = ring indicator"
    normalization: "scale(0, 20)"
    
  family_claim_density:
    description: "Family claims in last 90 days"
    risk_signal: "High density = coordinated filing"
    normalization: "scale(0, 30)"

  # Temporal Features (5%)
  service_to_filing_gap:
    description: "Days between service and filing"
    risk_signal: "Long gaps = harder to verify"
    normalization: "scale(0, 365)"
    
  recent_claim_frequency:
    description: "Claims filed in last 30 days by member"
    risk_signal: "Burst filing patterns"
    normalization: "scale(0, 15)"

  # Document Source Features (8%) — NEW
  mobile_scan_ratio:
    description: "Proportion of documents from mobile scan apps"
    risk_signal: "High ratio = likely self-generated docs"
    normalization: "scale(0.0, 1.0)"
    
  releasepoint_bypass:
    description: "Records submitted by member when RP available"
    risk_signal: "Bypassing trusted channel"
    normalization: "binary(0, 1)"
    
  multi_format_submission:
    description: "Mix of JPEG and PDF in same claim"
    risk_signal: "Format inconsistency = assembly from multiple sources"
    normalization: "binary(0, 1)"

  # Benefit Stacking Features (7%) — NEW
  claims_per_event:
    description: "Number of claims for single hospitalization"
    risk_signal: "Many claims = possible stacking exploitation"
    normalization: "scale(1, 15)"
    
  relationship_type_diversity:
    description: "Distinct relationship types used for same event"
    risk_signal: "Multiple types = stacking"
    normalization: "scale(1, 4)"
    
  admission_confinement_ratio:
    description: "Admission claims vs confinement claims ratio"
    risk_signal: "Unbalanced ratio may indicate gaming"
    normalization: "scale(0.0, 5.0)"
```

---

## 9. Entity Graph

### 9.1 Graph Schema

```yaml
EntityGraph:
  # Node types
  nodes:
    - type: MEMBER
      key: member_id
      properties: [name, age, state, is_active, dependent_count, risk_tier]
      
    - type: DEPENDENT
      key: dependent_id
      properties: [name, relationship, is_active]
      
    - type: EMPLOYER
      key: employer_id
      properties: [name, industry, employee_count]
      
    - type: ADDRESS
      key: address_id
      properties: [city, state, zip, occupant_count]
      
    - type: POLICY
      key: policy_id
      properties: [policy_number, product_line, status]
      
    - type: PROVIDER
      key: provider_id
      properties: [name, specialty, npi, claim_volume]
      
    - type: FACILITY
      key: facility_id
      properties: [name, facility_type, state]
      
    - type: CLAIM
      key: claim_id
      properties: [benefit_type, amount, status, risk_tier, service_date]
      
    - type: DOCUMENT
      key: doc_id
      properties: [document_type, source_type, integrity_score]

  # Edge types
  edges:
    # Core relationships
    - type: EMPLOYED_BY
      from: MEMBER
      to: EMPLOYER
      properties: [start_date, end_date]
      
    - type: LIVES_AT
      from: MEMBER
      to: ADDRESS
      properties: [since_date, is_primary]
      
    - type: ENROLLED_IN
      from: MEMBER
      to: POLICY
      properties: [enrollment_date, tier]
      
    - type: DEPENDENT_OF
      from: DEPENDENT
      to: MEMBER
      properties: [relationship]
      
    - type: FILED_BY
      from: CLAIM
      to: MEMBER
      properties: [filing_date, relationship_type]
      
    - type: TREATED_BY
      from: CLAIM
      to: PROVIDER
      properties: [service_date]
      
    - type: SERVICED_AT
      from: CLAIM
      to: FACILITY
      properties: [admission_date, discharge_date]
      
    - type: PRACTICES_AT
      from: PROVIDER
      to: FACILITY
      properties: [is_primary]
      
    # NEW edge types (from real case patterns)
    - type: SAME_EVENT
      from: CLAIM
      to: CLAIM
      properties: [event_type, confidence]
      description: "Claims linked to same hospitalization/event"
      
    - type: STACKED_WITH
      from: CLAIM
      to: CLAIM
      properties: [relationship_type_a, relationship_type_b]
      description: "Same event claimed under different relationship types"
      
    - type: SUBMITTED_FOR
      from: DOCUMENT
      to: CLAIM
      properties: [received_date, is_primary_evidence]
      description: "Document submitted as evidence for claim"
      
    - type: PORTAL_CASE_FOR
      from: MEMBER
      to: CLAIM
      properties: [case_id, case_origin]
      description: "Member opened portal case related to claim"
      
    - type: CONTRADICTS
      from: DOCUMENT
      to: DOCUMENT
      properties: [discrepancy_type, severity]
      description: "Two documents with conflicting information for same claim"
```

### 9.2 Pattern Detection Definitions

```yaml
GRAPH_PATTERNS:
  - pattern_id: "GP-001"
    name: "Dependent Ring"
    description: "3+ members at shared address with overlapping dependents"
    severity_threshold:
      MEDIUM: "3-5 members"
      HIGH: "6+ members OR 10+ total dependents"
    query: "MATCH (m:MEMBER)-[:LIVES_AT]->(a:ADDRESS)<-[:LIVES_AT]-(m2:MEMBER) WHERE m != m2 GROUP BY a HAVING count(m) >= 3"
    
  - pattern_id: "GP-002"
    name: "Provider Cluster"
    description: "Single provider with abnormally high claim volume"
    severity_threshold:
      MEDIUM: ">30 claims"
      HIGH: ">50 claims"
    query: "MATCH (c:CLAIM)-[:TREATED_BY]->(p:PROVIDER) GROUP BY p HAVING count(c) > 30"
    
  - pattern_id: "GP-003"
    name: "Shared Address Group"
    description: "Multiple unrelated members at same address"
    severity_threshold:
      MEDIUM: "3-5 unrelated members"
      HIGH: "6+ unrelated members"
    query: "MATCH (m:MEMBER)-[:LIVES_AT]->(a:ADDRESS) WHERE NOT exists((m)-[:DEPENDENT_OF|EMPLOYED_BY]->()-[:LIVES_AT]->(a)) GROUP BY a HAVING count(m) > 2"
    
  - pattern_id: "GP-004"
    name: "Termination Rush"
    description: "Multiple claims within 14 days of employee termination"
    severity_threshold:
      MEDIUM: "2-3 claims in window"
      HIGH: "4+ claims in window"
    query: "MATCH (m:MEMBER)-[:FILED_BY]<-(c:CLAIM) WHERE m.termination_date IS NOT NULL AND days_between(c.filing_date, m.termination_date) <= 14"
    
  - pattern_id: "GP-005"
    name: "Document Tampering Cluster"
    description: "Multiple claims with correlated document integrity failures"
    severity_threshold:
      MEDIUM: "2-3 claims with failures"
      HIGH: "4+ claims with failures from same member"
    query: "MATCH (d:DOCUMENT)-[:SUBMITTED_FOR]->(c:CLAIM)-[:FILED_BY]->(m:MEMBER) WHERE d.integrity_score < 0.5 GROUP BY m HAVING count(c) >= 2"
    
  # NEW patterns from real cases
  - pattern_id: "GP-006"
    name: "Indemnity Stacking Ring"
    description: "Multiple claims filed for single event across different relationship types"
    severity_threshold:
      MEDIUM: "4-6 claims for same event"
      HIGH: "7+ claims for same event across 3+ relationship types"
    query: "MATCH (c1:CLAIM)-[:SAME_EVENT]->(c2:CLAIM) WHERE c1.relationship_type != c2.relationship_type GROUP BY event HAVING count(c) > 4"
    inspired_by_case: "C-2026-1321395"
    
  - pattern_id: "GP-007"
    name: "Document Source Mismatch Pattern"
    description: "Member submitting mobile-scanned docs when facility is ReleasePoint-enrolled"
    severity_threshold:
      MEDIUM: "1 instance"
      HIGH: "2+ instances from same member"
    query: "MATCH (d:DOCUMENT)-[:SUBMITTED_FOR]->(c:CLAIM)-[:SERVICED_AT]->(f:FACILITY) WHERE d.source_type = 'MOBILE_SCAN' AND f.releasepoint_enrolled = true"
    inspired_by_case: "C-2026-1325588"
    
  - pattern_id: "GP-008"
    name: "Cross-Claim Document Contradiction"
    description: "Documents submitted for related claims contain conflicting information"
    severity_threshold:
      MEDIUM: "Minor discrepancies (dates off by 1-2 days)"
      HIGH: "Major contradictions (different facilities, different diagnoses)"
    query: "MATCH (d1:DOCUMENT)-[:CONTRADICTS]->(d2:DOCUMENT) WHERE d1.claim_id != d2.claim_id AND same_member"
    inspired_by_case: "C-2026-1297921"
```

---

## 10. Checklist

### 10.1 ChecklistDefinition

```yaml
Checklist:
  steps:
    - step_number: 1
      name: "Initial Review"
      description: "Verify required fields present and task assigned"
      auto_passable: true
      auto_pass_conditions:
        - "claim.claim_id IS NOT NULL"
        - "claim.member_id IS NOT NULL"
        - "claim.service_date_start IS NOT NULL"
        - "claim.benefit_type IS NOT NULL"
        - "claim.assigned_examiner IS NOT NULL OR claim.risk_tier == 'LOW'"
      failure_actions:
        - "Create NIGO notice for missing fields"
      
    - step_number: 2
      name: "Eligibility Verification"
      description: "Policy active, coverage type matches, member enrolled on service date"
      auto_passable: true
      auto_pass_conditions:
        - "policy.status == 'ACTIVE'"
        - "claim.service_date_start >= policy.effective_date"
        - "claim.service_date_start <= (member.termination_date OR policy.termination_date OR today)"
        - "claim.benefit_type IN policy.benefit_schedule.benefits"
        - "member.enrollment_date <= claim.service_date_start"
      failure_actions:
        - "Flag for eligibility review"
        - "Check for grace period or COBRA continuation"
      
    - step_number: 3
      name: "Fraud Screening"
      description: "Risk score assessment, rule triggers, suspicious indicators"
      auto_passable: conditional
      auto_pass_conditions:
        - "claim.risk_tier == 'LOW'"
        - "count(claim.rules_triggered WHERE severity == 'BLOCK') == 0"
        - "claim.fraud_status == 'NOT_FLAGGED'"
      requires_manual_if:
        - "claim.risk_tier IN ('MEDIUM', 'HIGH')"
        - "ANY BLOCK rule triggered"
        - "claim.fraud_status != 'NOT_FLAGGED'"
      failure_actions:
        - "Create fraud review task"
        - "Assign to fraud analyst queue"
      
    - step_number: 4
      name: "Family & Network Check"
      description: "Dependent patterns, shared addresses, network anomalies"
      auto_passable: true
      auto_pass_conditions:
        - "R-001 NOT triggered (excessive dependents)"
        - "R-010 NOT triggered (family claim density)"
        - "R-015 NOT triggered (cross-member provider sharing)"
        - "R-009 NOT triggered (shared address cluster)"
        - "GP-001 NOT detected (dependent ring)"
        - "GP-006 NOT detected (indemnity stacking ring)"
      failure_actions:
        - "Flag for network investigation"
        - "Generate entity graph visualization for examiner"
      
    - step_number: 5
      name: "Medical Documentation Verification"
      description: "Document integrity, source verification, ReleasePoint validation"
      auto_passable: true
      auto_pass_conditions:
        - "ALL documents have integrity_score >= 0.8"
        - "ALL documents source_type IN ('RELEASEPOINT', 'PROVIDER_PORTAL', 'PROVIDER_FAX')"
        - "NO documents have metadata_app_signature (mobile scan apps)"
        - "R-016 NOT triggered (mobile scan source)"
        - "R-018 NOT triggered (visual inconsistencies)"
        - "R-012 NOT triggered (document tampering)"
        - "document.header_content_match == true for ALL documents"
      requires_manual_if:
        - "ANY document source_type IN ('MOBILE_SCAN', 'SCREENSHOT', 'UNKNOWN')"
        - "ANY document integrity_score < 0.7"
        - "releasepoint_status == 'CONFIRMED_DISCREPANT'"
        - "font_consistency_score < 0.7 OR alignment_score < 0.7"
      failure_actions:
        - "Initiate NIGO process"
        - "Submit ReleasePoint request for independent records"
        - "Flag for document integrity review"
        - "Add to Prudential support list if manipulation confirmed"
      
    - step_number: 6
      name: "Policy & Coverage Verification"
      description: "Amount within limits, dates in coverage window, benefit definitions met"
      auto_passable: true
      auto_pass_conditions:
        - "claim.claim_amount <= benefit_definition.payment_amount"
        - "claim.service_date_start within policy coverage period"
        - "waiting_period satisfied"
        - "elimination_period satisfied"
        - "max_occurrences not exceeded"
        - "max_days not exceeded (for confinement)"
        - "R-017 NOT triggered OR stacking_allowed == true"
      failure_actions:
        - "Deny with appropriate reason code"
        - "Check if partial payment applicable"
      
    - step_number: 7
      name: "Final Determination"
      description: "Examiner decision: approve, deny, or escalate"
      auto_passable: false          # NEVER auto-passable
      requires_manual_always: true
      options:
        - APPROVE: "Claim meets all criteria, authorize payment"
        - DENY: "Claim fails one or more criteria"
        - ESCALATE_SIU: "Refer to Special Investigations Unit"
        - ESCALATE_SUPPORT_LIST: "Refer to Prudential support list for review"
        - HOLD: "Additional information needed, cannot determine"
      required_documentation:
        - "Examiner rationale (free text)"
        - "Supporting evidence references"
        - "If DENY: denial reason code"
        - "If ESCALATE: escalation justification"
```

### 10.2 ChecklistState (Per Claim)

```yaml
ClaimChecklistState:
  claim_id: str                    # FK → Claim
  current_step: int                # 1-7
  overall_status: enum             # IN_PROGRESS | COMPLETED | BLOCKED
  
  steps:
    - step_number: int
      status: enum                 # NOT_STARTED | IN_PROGRESS | PASSED | FAILED | NEEDS_REVIEW | SKIPPED
      auto_passed: bool            # Was this auto-passed or manually reviewed?
      started_at: datetime?
      completed_at: datetime?
      completed_by: str?           # "System" or examiner name
      result_details: str?         # Explanation of pass/fail
      evidence_refs: list[str]     # Document/note IDs supporting result
      
  # Final determination (step 7)
  final_decision: enum?            # APPROVE | DENY | ESCALATE_SIU | ESCALATE_SUPPORT_LIST | HOLD
  final_decision_date: datetime?
  final_decision_by: str?
  final_rationale: str?
```

---

## 11. Copilot Session

### 11.1 CopilotSession

```yaml
CopilotSession:
  session_id: str                  # UUID
  claim_id: str                    # FK → Claim (one session per claim)
  
  # Context (set at session creation)
  case_type: str                   # e.g., "Hospital Indemnity Fraud Review"
  subject_id: str                  # member_id
  subject_name: str                # Member full name
  flag_reason: str                 # Why this claim is in the queue
  
  # Conversation
  messages: list[Message]          # Full LangChain message history
  
  # Tool audit trail
  tools_called: list[ToolInvocation]
  
  # Checklist tracking
  checklist_state: ClaimChecklistState
  
  # Session metadata
  created_at: datetime
  last_activity: datetime
  status: enum                     # ACTIVE | IDLE | CLOSED
  
Message:
  role: enum                       # HUMAN | AI | SYSTEM | TOOL
  content: str
  timestamp: datetime
  tool_calls: list[ToolCall]?      # If AI message with tool invocations
  
ToolInvocation:
  tool_name: str                   # e.g., "check_document_source"
  arguments: dict                  # Input parameters
  result: dict                     # Tool output
  invoked_at: datetime
  duration_ms: int
  success: bool
  error: str?                      # If tool failed
```

---

## 12. Investigation & Dossier (Standalone Graph)

### 12.1 InvestigationState

```yaml
InvestigationState:
  # LangGraph state
  messages: list[Message]          # Full conversation history
  current_phase: enum              # SCAN | INVESTIGATE | COMPILE | DONE
  findings: dict                   # Accumulated evidence by category
  dossier: str?                    # Generated markdown report
  evidence_sufficient: bool        # Gate for dossier compilation
  loop_count: int                  # Prevents infinite investigation loops (max: 5)
  compile_loop_count: int          # Dossier rejection cycles (max: 3)
  
  # Evidence structure
  findings:
    rules_evidence:
      rules_triggered: list[str]
      severity_counts: dict        # {BLOCK: n, FLAG: n, INFO: n}
      
    document_evidence:
      integrity_failures: list[dict]
      source_anomalies: list[dict]
      releasepoint_discrepancies: list[dict]
      
    network_evidence:
      patterns_detected: list[dict]
      connected_members: list[str]
      connected_claims: list[str]
      
    temporal_evidence:
      timing_anomalies: list[dict]
      claim_frequency_analysis: dict
      
    financial_evidence:
      total_exposure: float
      stacking_analysis: dict?
      benefit_exploitation: dict?
      
    provider_evidence:
      provider_patterns: list[dict]
      facility_verification: dict?
```

### 12.2 Evidence Sufficiency Criteria

```yaml
EvidenceSufficiencyChecks:
  # All 6 must pass for dossier compilation
  
  - check: "minimum_evidence_points"
    requirement: "findings contains >= 3 independent evidence categories with data"
    weight: REQUIRED
    
  - check: "statistical_significance"
    requirement: "risk_score > 60 OR any z_score > 2.0 in feature analysis"
    weight: REQUIRED
    
  - check: "temporal_analysis_present"
    requirement: "temporal_evidence is not empty"
    weight: REQUIRED
    
  - check: "network_evidence"
    requirement: "network_evidence populated (only required if pattern type is RING)"
    weight: CONDITIONAL
    
  - check: "regulatory_citation"
    requirement: "at least one applicable state or federal regulation identified"
    weight: REQUIRED
    
  - check: "document_integrity"
    requirement: "document_evidence populated (only required if pattern type is TAMPERING)"
    weight: CONDITIONAL
```

---

## 13. Synthetic Data Generation Parameters

### 13.1 Population Parameters

```yaml
DataGenerationConfig:
  # Scale
  total_members: 500
  total_claims: 500                # Not 1:1 — some members have multiple claims
  total_providers: 50
  total_facilities: 30
  total_employers: 25
  
  # Distribution targets
  risk_distribution:
    HIGH: 0.15                     # 15% of claims (75 claims)
    MEDIUM: 0.30                   # 30% of claims (150 claims)
    LOW: 0.55                      # 55% of claims (275 claims)
    
  fraud_status_distribution:
    NOT_FLAGGED: 0.60
    FLAGGED_FOR_REVIEW: 0.20
    VALID_FRAUD: 0.10
    INVALID_FRAUD: 0.07            # False positives — important!
    REFERRED_SIU: 0.03
    
  claim_status_distribution:
    APPROVED: 0.45
    DENIED: 0.20
    PENDING: 0.15
    NIGO: 0.08
    UNDER_REVIEW: 0.07
    PAID: 0.03
    ESCALATED: 0.02
```

### 13.2 Fraud Scenario Templates

```yaml
FraudScenarios:
  # Each scenario defines a cluster of related synthetic records
  
  - scenario_id: "FS-001"
    name: "Falsified Discharge Summary (CamScanner)"
    inspired_by: "C-2026-1325588"
    frequency: 0.05                # 5% of claims match this pattern
    fraud_status: VALID_FRAUD
    
    member_profile:
      age_range: [55, 80]
      gender_bias: null            # No gender preference
      dependent_count: [0, 3]      # Normal dependent range
      state: null                  # Any state
      
    claim_profile:
      benefit_types: [HOSPITAL_ADMISSION, HOSPITAL_CONFINEMENT, ICU_ADMISSION]
      diagnosis_codes: ["J44", "J96", "J18", "I50", "N17"]  # Respiratory/cardiac/renal
      amount_range: [500, 2000]
      submission_channel: EE_PORTAL
      
    document_profile:
      source_type: MOBILE_SCAN
      filename_pattern: "CamScanner_{date}_{time}_{page}.jpeg"
      file_format: JPEG
      integrity_score_range: [0.2, 0.5]
      font_consistency: [0.3, 0.6]
      alignment_score: [0.4, 0.7]
      header_content_match: false  # Hospital name mismatch
      metadata_app_signature: "CamScanner"
      
    rules_expected: ["R-012", "R-016"]
    investigation_notes:
      - type: FRAUD_ALERT
        content_template: "Fraud alert task - Please request a signed medical authorization form and request medical records through ReleasePoint to confirm validity of image received."
      - type: RECORDS_REQUEST
        content_template: "MR Request RP {rp_id} - status: {status}"
    
  - scenario_id: "FS-002"
    name: "Hospital Indemnity Stacking (Legitimate - Multiple Birth)"
    inspired_by: "C-2026-1321395"
    frequency: 0.02                # 2% of claims
    fraud_status: INVALID_FRAUD    # FALSE POSITIVE
    
    member_profile:
      age_range: [25, 40]
      gender_bias: FEMALE
      dependent_count: [2, 5]      # Including newborns
      state: null
      
    claim_profile:
      benefit_types: [HOSPITAL_ADMISSION, HOSPITAL_CONFINEMENT, HOSPITAL_INDEMNITY]
      diagnosis_codes: ["O30", "Z38", "O80", "O82"]  # Multiple birth / delivery
      amount_range: [200, 1000]
      claim_count_per_event: [6, 12]
      relationship_types_used: [SELF, POLICYHOLDER, BENEFICIARY, INSURED]
      submission_channel: EE_PORTAL
      all_same_service_window: true  # All within 3-7 days
      
    document_profile:
      source_type: PROVIDER_PORTAL  # Legitimate source
      file_format: PDF
      integrity_score_range: [0.85, 1.0]  # Clean documents
      header_content_match: true
      
    rules_expected: ["R-017"]      # Stacking rule fires but it's legitimate
    portal_cases: 2                # Member opened portal cases
    investigation_notes:
      - type: FRAUD_REVIEW
        content_template: "Fraud task review - member has given birth to twins and several hospital indemnity claims created as a result. Closing task."
    resolution: "INVALID_FRAUD"    # Cleared after review
    
  - scenario_id: "FS-003"
    name: "Manipulated Urgent Care Records (Font/Alignment)"
    inspired_by: "C-2026-1297921"
    frequency: 0.03                # 3% of claims
    fraud_status: VALID_FRAUD
    
    member_profile:
      age_range: [20, 35]
      gender_bias: null
      dependent_count: [0, 2]
      state: null
      
    claim_profile:
      benefit_types: [URGENT_CARE_VISIT, EMERGENCY_ROOM]
      diagnosis_codes: ["J06", "J02", "R05", "J00", "R50"]  # URI, sore throat, cough, fever
      amount_range: [100, 500]
      submission_channel: EE_PORTAL
      has_related_claims: true     # Open related claim with similar concerns
      
    document_profile:
      document_count: 2            # Notes + After Visit Summary
      documents:
        - document_type: PROGRESS_NOTES
          filename_pattern: "Notes_from_care_team_{name}_{date}.pdf"
          source_type: MEMBER_UPLOAD_PDF
          font_consistency: [0.3, 0.5]
          color_consistency: [0.4, 0.6]
          alignment_score: [0.3, 0.6]
        - document_type: AFTER_VISIT_SUMMARY
          filename_pattern: "After_Visit_Summary_{name}_{date}.pdf"
          source_type: MEMBER_UPLOAD_PDF
          font_consistency: [0.4, 0.6]
          alignment_score: [0.5, 0.7]
          # This one looks more legitimate (from Epic MyChart) but still has issues
          
    rules_expected: ["R-018", "R-016"]
    investigation_notes:
      - type: FRAUD_REVIEW
        content_template: "Prudential fraud review - please only accept medical records via ReleasePoint. There are some inconsistencies with font color, quality of the images. Refer to support list for review."
        
  - scenario_id: "FS-004"
    name: "High-Volume Legitimate (Chronic Condition)"
    inspired_by: "C-2026-1331913"
    frequency: 0.04                # 4% of claims
    fraud_status: INVALID_FRAUD    # FALSE POSITIVE
    
    member_profile:
      age_range: [30, 65]
      gender_bias: null
      dependent_count: [0, 4]
      state: null
      
    claim_profile:
      benefit_types: [HOSPITAL_ADMISSION, HOSPITAL_CONFINEMENT, ICU_ADMISSION]
      diagnosis_codes: ["Z51", "D70", "C50", "C34", "C18"]  # Aftercare, chemo effects, cancers
      amount_range: [200, 1000]
      claim_count: [8, 15]
      time_span_months: 3          # Claims over 3 months
      mix_approved_denied: true    # Some approved, some denied (policy definition not met)
      denial_reasons: ["POLICY_DEFINITION_NOT_MET", "ELIMINATION_PERIOD"]
      submission_channel: EE_PORTAL
      
    document_profile:
      source_type: PROVIDER_PORTAL
      file_format: PDF
      integrity_score_range: [0.8, 1.0]
      header_content_match: true
      
    rules_expected: ["R-010"]      # Family claim density may fire
    investigation_notes:
      - type: FRAUD_REVIEW
        content_template: "Fraud Review: Medical records have not been received yet. Please start the NIGO process and order records. Once received if records appear suspicious please refer to the Support List for review."
      - type: RECORDS_RECEIVED
        content_template: "Records received and reviewed. Multiple claims were filed from January to March 2026, but after reviewing the medical records, none of them were found to be fraudulent."
    resolution: "INVALID_FRAUD"
    
  # Additional scenarios to round out the data
  
  - scenario_id: "FS-005"
    name: "Dependent Ring (Classic)"
    frequency: 0.03
    fraud_status: VALID_FRAUD
    member_profile:
      dependent_count: [15, 40]
      shared_address: true
    rules_expected: ["R-001", "R-009", "R-015"]
    
  - scenario_id: "FS-006"
    name: "Termination Rush"
    frequency: 0.03
    fraud_status: VALID_FRAUD
    claim_profile:
      days_before_termination: [1, 14]
      claim_count: [3, 8]
    rules_expected: ["R-002", "R-011"]
    
  - scenario_id: "FS-007"
    name: "Provider Mill"
    frequency: 0.02
    fraud_status: VALID_FRAUD
    provider_profile:
      total_claims: [50, 200]
      unique_members: [30, 100]
      no_facility_ratio: 0.3
    rules_expected: ["R-004", "R-005"]
    
  - scenario_id: "FS-008"
    name: "Clean Claim (No Issues)"
    frequency: 0.55                # Majority of claims are clean
    fraud_status: NOT_FLAGGED
    claim_profile:
      risk_tier: LOW
      benefit_types: "any"
      amount_range: [50, 500]
    document_profile:
      source_type: RELEASEPOINT
      integrity_score_range: [0.9, 1.0]
    rules_expected: []
```

---

## 14. ICD-10 Code Reference

```yaml
DIAGNOSIS_CODE_LIBRARY:
  # Respiratory (common in falsified records)
  J06: "Acute upper respiratory infection, unspecified"
  J00: "Acute nasopharyngitis (common cold)"
  J02: "Acute pharyngitis"
  J18: "Pneumonia, unspecified organism"
  J44: "Chronic obstructive pulmonary disease"
  J96: "Respiratory failure"
  R05: "Cough"
  
  # Cardiac
  I50: "Heart failure"
  I21: "Acute myocardial infarction"
  I25: "Chronic ischemic heart disease"
  
  # Obstetric (twin birth / multiple gestation)
  O30: "Multiple gestation"
  O80: "Encounter for full-term uncomplicated delivery"
  O82: "Encounter for cesarean delivery"
  Z38: "Liveborn infants according to place of birth"
  
  # Oncology / Chemotherapy
  Z51: "Encounter for other aftercare and medical care"
  D70: "Neutropenia"
  C50: "Malignant neoplasm of breast"
  C34: "Malignant neoplasm of bronchus and lung"
  C18: "Malignant neoplasm of colon"
  
  # Renal
  N17: "Acute kidney failure"
  N18: "Chronic kidney disease"
  
  # General / Urgent Care
  R50: "Fever of other and unknown origin"
  R10: "Abdominal and pelvic pain"
  M54: "Dorsalgia (back pain)"
  S93: "Dislocation and sprain of ankle"
  
  # GI
  A08: "Viral and other specified intestinal infections"
  K21: "Gastro-esophageal reflux disease"
  
  # Mental Health (for wellness claims)
  F41: "Other anxiety disorders"
  F32: "Major depressive disorder, single episode"
```

---

## 15. API Response Schemas

### 15.1 Claims Queue Response

```yaml
GET /api/claims/queue:
  response:
    total_claims: int
    page: int
    page_size: int
    claims:
      - claim_id: str
        member_name: str
        benefit_type: str
        claim_amount: float
        service_date: date
        filing_date: date
        risk_score: float
        risk_tier: str
        claim_status: str
        fraud_status: str
        rules_triggered_count: int
        top_rule: str?              # Highest severity rule triggered
        assigned_examiner: str?
        checklist_progress: str     # "3/7 steps complete"
        days_pending: int
        priority_rank: int
```

### 15.2 Claim Detail Response

```yaml
GET /api/claims/{claim_id}:
  response:
    claim: Claim                    # Full claim object
    member: Member                  # Associated member
    policy: Policy                  # Associated policy
    provider: Provider              # Treating provider
    facility: Facility?             # Service facility
    documents: list[Document]       # All submitted documents
    notes: list[InvestigationNote]  # Investigation notes
    contacts: list[ContactRecord]   # Contact history
    tasks: list[WorkflowTask]       # Active/completed tasks
    risk_score: RiskScore           # Full scoring breakdown
    checklist: ClaimChecklistState  # Checklist progress
    related_claims: list[ClaimSummary]  # Linked claims
    graph_patterns: list[Pattern]   # Detected graph patterns involving this claim
```

### 15.3 Dashboard Response

```yaml
GET /api/dashboard:
  response:
    summary:
      total_claims: int
      pending_review: int
      high_risk: int
      medium_risk: int
      low_risk: int
      valid_fraud_count: int
      false_positive_count: int
      avg_processing_days: float
      
    risk_distribution:
      - tier: str
        count: int
        percentage: float
        
    rule_triggers:
      - rule_id: str
        rule_name: str
        trigger_count: int
        severity: str
        false_positive_rate: float
        
    top_patterns:
      - pattern_type: str
        count: int
        severity: str
        involved_claims: int
        
    recent_activity:
      - timestamp: datetime
        event_type: str
        claim_id: str
        description: str
```

---

## 16. Configuration & Constants

```yaml
SystemConfig:
  # Scoring thresholds
  RISK_TIER_HIGH: 60
  RISK_TIER_MEDIUM: 30
  
  # Loop limits (for LangGraph)
  MAX_INVESTIGATION_LOOPS: 5
  MAX_COMPILE_LOOPS: 3
  
  # Session management
  SESSION_IDLE_TIMEOUT_MINUTES: 30
  MAX_MESSAGES_PER_SESSION: 100
  
  # Document analysis
  INTEGRITY_SCORE_THRESHOLD_BLOCK: 0.5
  INTEGRITY_SCORE_THRESHOLD_FLAG: 0.7
  MOBILE_SCAN_APP_SIGNATURES: ["CamScanner", "Adobe Scan", "Genius Scan", "Microsoft Lens", "Scanner Pro", "TurboScan"]
  
  # ReleasePoint
  RP_REQUEST_TIMEOUT_DAYS: 30
  RP_AUTO_REQUEST_ON_MOBILE_SCAN: true
  
  # Temporal windows
  TERMINATION_RUSH_WINDOW_DAYS: 14
  STACKING_WINDOW_DAYS: 3
  FAMILY_DENSITY_WINDOW_DAYS: 90
  NEW_POLICY_WINDOW_DAYS: 90
  
  # Network thresholds
  SHARED_ADDRESS_THRESHOLD: 3
  PROVIDER_VOLUME_THRESHOLD: 30
  PROVIDER_VOLUME_HIGH_THRESHOLD: 50
  DEPENDENT_RING_THRESHOLD: 3
  
  # Feature weights (must sum to 1.0)
  FEATURE_WEIGHTS:
    policy: 0.10
    member: 0.12
    claim: 0.13
    provider: 0.10
    network: 0.10
    temporal: 0.05
    document_source: 0.08
    benefit_stacking: 0.07
    # Remaining 0.25 is rules boost (separate calculation)
```

---

## 17. Data Relationships Summary

```
┌─────────┐     ┌──────────┐     ┌────────┐
│ Employer │◄────│  Member  │────►│ Address│
└────┬────┘     └────┬─────┘     └────────┘
     │               │ │
     │               │ └──────────────┐
     ▼               ▼                ▼
┌─────────┐     ┌──────────┐     ┌───────────┐
│  Policy │     │Dependent │     │  Contact  │
└────┬────┘     └──────────┘     │  History  │
     │                            └───────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│                      CLAIM                           │
│  ┌──────────┐  ┌──────────┐  ┌────────────────┐    │
│  │ Provider │  │ Facility │  │ Relationship   │    │
│  │  (FK)    │  │  (FK)    │  │    Type        │    │
│  └──────────┘  └──────────┘  └────────────────┘    │
└───────┬──────────────┬──────────────┬───────────────┘
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌───────────┐ ┌──────────────────┐
│  Documents   │ │   Notes   │ │  Workflow Tasks   │
│  (1:many)    │ │  (1:many) │ │    (1:many)      │
└──────┬───────┘ └───────────┘ └──────────────────┘
       │
       ▼
┌──────────────────┐
│ Integrity Checks │
│ (per document)   │
└──────────────────┘

Cross-cutting:
┌────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Risk Score    │     │  Checklist   │     │  Copilot    │
│  (per claim)   │     │   State      │     │  Session    │
│                │     │ (per claim)  │     │ (per claim) │
└────────────────┘     └──────────────┘     └─────────────┘

Graph (NetworkX):
┌─────────────────────────────────────────────────┐
│  Entity Graph (all entities as nodes)           │
│  + 12 edge types                                │
│  + 8 pattern detection algorithms               │
└─────────────────────────────────────────────────┘
```

---

## 18. Implementation Notes for AI Agents

### When generating synthetic data:
1. **Start with scenarios** — pick from `FraudScenarios` based on `frequency` weights
2. **Generate members first**, then claims, then documents — respect FK relationships
3. **False positives are critical** — 7% of flagged claims should be `INVALID_FRAUD` after review
4. **Stacking claims share service dates** — use `service_date_start ± 3 days` window
5. **Document filenames must match patterns** — CamScanner files are always JPEG with specific naming
6. **ReleasePoint IDs are numeric** — format: `RP {8-digit number}`
7. **Notes reference each other** — later notes should reference earlier note IDs
8. **ICD-10 codes must be clinically plausible** — don't pair obstetric codes with 70-year-old males

### When implementing tools:
1. **Tools return dicts, never raise** — wrap all failures in `{"error": "..."}`
2. **Tools access `_context` only** — no direct DB calls, no external APIs
3. **Every tool call is logged** — append to `_tool_log` for audit trail
4. **Tools are idempotent** — calling same tool with same args returns same result

### When implementing rules:
1. **Rules are evaluated per-claim at startup** — results cached in `claim_rules[claim_id]`
2. **Rules that reference other claims (R-010, R-011, R-017)** need full context
3. **Score boost normalization** — divide individual rule boost by total possible for that severity tier
4. **Rule order doesn't matter** — all rules evaluate independently

---

*Last updated: Based on real scrubbed case data from fraud review team (Cases C-2026-1325588, C-2026-1321395, C-2026-1297921, C-2026-1331913)*