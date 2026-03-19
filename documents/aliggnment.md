Alignment Check: KT Notes vs. Final Plan
Verdict: ~80% aligned. A few real gaps to fix.
What's Well Aligned
KT Note	Plan Coverage
Claim types: wellness, accident, hospital indemnity, critical illness	✅ Exact match
Wellness is auto-adjudicated	✅ Captured, key fraud vector
35 dependents case, $100/person max, auto-adj let them through	✅ Fraud scenario #1
Eligibility requires 3 tools → we consolidate to 1	✅ check_eligibility tool
ET supersedes policy, state-based exclusions (Florida intoxication)	✅ check_state_rules tool
Suspicious banner is primary fraud detection method	✅ Referenced in rules and member data
Manual inspection of medical records is other method	✅ Document analysis engine (DOC-001 to DOC-013)
Family check last 100 days	✅ check_family_claims tool
DOB → expiration date → eligibility chain	✅ In check_eligibility
Accident claims = most examiner effort	✅ Reflected in effort levels and tool design
OneNote fraud checklist → initial claim review, medical review	✅ 7-step checklist framework
Coverage ended Sept 2025 (employment termination)	✅ Termination rush scenario #2
Policy changes, state-based inclusion	✅ Policy alerts (PA-001 surgical repair)
Owner change as fraud signal	✅ Rule R-006, policy change history
Gaps That Need Fixing
1. Daily Volume Mismatch (Important for Demo Realism)
Your notes say: 20-25 claims per day

Plan says: 500 claims in queue

The problem: Showing 500 claims at once doesn't match an examiner's reality. They see 20-25 per day, not a backlog of 500.

Fix for the schematic:

The 500 claims are the TOTAL DATASET (roughly a month of work).
The Claims Queue default view should show TODAY'S claims (~25).

ClaimsQueue.jsx needs a date filter defaulting to "Today":
  [Today (23)] [This Week (112)] [All (500)]

This makes the demo feel real. The examiner opens the app,
sees 23 claims for today, sorted by risk. Not a wall of 500.

The 500 total still exists for dashboard stats, pattern detection,
and network analysis — but the working queue is 20-25.
Action: Modify ClaimsQueue.jsx spec to default to daily view. Modify generate_supplemental.py to distribute claims across ~20 business days with ~25/day.

2. "3 Family Members" Threshold Misread
Your notes say: "3 family member last 100 days"

Plan says: check_family_claims returns all family claims in 100 days

What this likely means: The examiner checks if 3 or more family members have filed claims in the last 100 days — that's a flag, not just a lookup.

Fix:

# In check_family_claims tool output, add:
"family_members_with_claims_100d": int,  # count of family members who filed
"threshold_exceeded": bool,               # True if >= 3

# In rules_engine.py, add or clarify:
# This may warrant a new rule or modification to existing family check:
Rule("R-015", "Family Claim Cluster",
     "3+ family members filed claims in 100-day window",
     "family_members_with_claims >= 3 in 100 days",
     Severity.FLAG,
     "{count} family members filed claims in last 100 days")
3. Proactive vs. Reactive Framing Missing
Your notes clearly distinguish:

Proactive (FIRST CASE): Checklist-based. Claim comes in → task created → assigned to support team → RT team requests medical records → checklist runs
Reactive (SECOND CASE): Email notification. Someone notices something wrong (like 35 dependents) after the fact.
Plan captures both but doesn't frame them explicitly. This matters for the demo because it shows the platform handles both modes.

Fix for copilot prompt and demo script:

Add to SUPPLEMENTAL_COPILOT_PROMPT:

"Investigation modes:
- PROACTIVE: Every claim triggers the checklist. Most claims pass 
  automatically. Flagged claims get examiner review. This is the 
  daily workflow — you're catching things BEFORE they pay.
- REACTIVE: Patterns detected across claims after the fact. 
  The 35-dependent case, provider mills, dependent rings. 
  The dashboard and network view surface these. This catches 
  what individual claim review misses."

Add to demo script:
[X:XX] "Two modes. Proactive: the checklist catches individual 
claim issues before payment. Reactive: the dashboard and network 
catch patterns across claims that no individual review would find. 
Today you have proactive (the checklist in OneNote) but no reactive. 
We give you both."
4. Claim Source/Channel Not Captured
Your notes say: Claims come from: company claim creation site, telephonic, web-based, disability

Plan has: document submission method (portal, fax, email) but not claim SOURCE

Fix:

# Add to Claim dataclass:
claim_source: str  # "company_site", "telephonic", "web", "disability_portal"

# This is minor but adds realism to the synthetic data.
# Could also feed into risk scoring — telephonic claims 
# might have different risk profile than web-submitted.
5. Specific System Names for Realism
Your notes mention: Prudential 360, Power BI, Compass, FIS/PAS

Plan says: "3 systems" generically

Fix: Reference these by name in the copilot prompt and demo:

Add to SUPPLEMENTAL_COPILOT_PROMPT:

"System context: Examiners currently check eligibility across 
Prudential 360, Power BI, and FIS/PAS. The check_eligibility 
tool consolidates what they'd find across all three into one response."

In the demo, when showing check_eligibility:
"This one tool replaces checking Prudential 360, then Power BI, 
then falling back to FIS/PAS. One answer instead of three screens."
6. "Banner" Logic Not Detailed Enough
Your notes say: If a claim has a banner → check if there's a review at Prudential. If no banner → different path.

Plan captures: Suspicious banner as a boolean on member. But the branching logic (banner vs. no-banner investigation paths) isn't explicit.

Fix:

# The checklist should branch based on banner status:

# In checklist.py, Step 3 (Fraud Screening):
"""
Step 3 behavior depends on suspicious_banner:

IF member.suspicious_banner == True:
  - This claim already has institutional suspicion
  - Run ALL fraud checks regardless of risk score
  - Flag for senior examiner review
  - Check: is there an existing review/investigation at Prudential?

IF member.suspicious_banner == False:
  - Run standard rules engine + risk scoring
  - Only escalate if risk score > threshold or rules trigger
  - This is where the platform adds NEW detection capability
    beyond what the banner catches
"""
7. RT Team / Task Assignment Workflow
Your notes say: "if a claim is created, there's a task, will be assigned to support team, RT team ask for medical record"

Plan has: Workflow tasks (PMR, CBR) but doesn't capture the claim creation → task → RT team → medical record request flow.

Fix: This is the examiner's actual workflow. Add it:

# In WorkflowTask, add task_type options:
# "PMR", "CBR", "TAT_ESCALATION", "MEDICAL_RECORD_REQUEST", "INITIAL_REVIEW"

# In generate_supplemental.py:
# Every claim should have an INITIAL_REVIEW task
# Claims requiring medical records should have MEDICAL_RECORD_REQUEST task
# This reflects the real flow: claim created → task assigned → 
# RT requests records → examiner reviews

# In check_workflow_tasks output:
"medical_record_status": {
    "requested": bool,
    "received": bool,
    "request_date": str,
    "days_waiting": int
}
What's NOT in the Notes but IS in the Plan
These are things you inferred or added that weren't explicitly in the KT. They're reasonable additions but flag them as assumptions:

Plan Feature	Status
DOC-001 through DOC-013 (specific document checks)	Inferred from "manual inspection of medical records" — the specific checks came from the OneNote checklist you partially saw. Reasonable but unvalidated.
14 rules with specific thresholds	Invented thresholds. Rules are reasonable but numbers (>5 deps in 30 days, >10 claims/quarter) are guesses.
Risk scoring with weighted features	Your design, not from KT. Good architecture but weights are unvalidated.
Network/graph analysis	Your design. Prudential doesn't do this today. It's additive value.
Policy alert PA-001 (surgical repair)	From KT notes ("change ng policies") but specific wording may be imprecise.
State rules framework	From KT ("ET supersedes policy") but implementation details are your interpretation.
10 specific fraud scenarios	Scenario #1 (35 deps) is from KT. Others are industry-standard patterns you inferred.
Revised Items for Schematic
Here's what to tell the coding agent to adjust:

ADJUSTMENTS TO SCHEMATIC:

1. CLAIMS QUEUE: Default to daily view (20-25 claims).
   500 total claims distributed across ~20 business days.
   Queue shows [Today (23)] [This Week] [All] tabs.

2. NEW RULE R-015: Family Claim Cluster
   "3+ family members filed claims in 100-day window" → FLAG
   Add to rules_engine.py.

3. CLAIM MODEL: Add claim_source field
   Options: "company_site", "telephonic", "web", "disability_portal"

4. WORKFLOW TASKS: Add "MEDICAL_RECORD_REQUEST" and "INITIAL_REVIEW"
   task types. Every claim gets INITIAL_REVIEW task.
   
5. CHECKLIST STEP 3: Branch on suspicious_banner
   Banner=True → full fraud review regardless of score
   Banner=False → standard scoring path

6. COPILOT PROMPT: Add system names (Prudential 360, Power BI, 
   FIS/PAS, Compass) for realism. Add proactive vs reactive framing.

7. DEMO SCRIPT: Add "one check replaces Prudential 360 + Power BI + 
   FIS/PAS" callout. Add proactive/reactive explanation.

Everything else in the schematic remains as designed.
Bottom Line
Your notes are sparse but the important stuff is there. The plan captures the core of what Prudential needs. The gaps are mostly about workflow realism (daily volume, task assignment flow, banner branching) rather than architecture — which means the coding agent can build the right thing and you adjust details in the data and prompts later.

The biggest risk isn't missing a note — it's that you saw the OneNote fraud checklist but couldn't capture all the specific checks. Your DOC-001 through DOC-013 are reasonable but may not match their actual list. Be transparent about that in the demo: "These checks are based on what we captured. We'd calibrate to your full checklist during implementation."