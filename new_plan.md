Planning a Fraud Analyst Copilot That Actually Mirrors Real Workflow
Start With How the Analyst Actually Thinks
A seasoned fraud analyst doesn't think in "phases." They think in questions, each answer triggering the next question:

"Who looks weird?"
  → "What specifically is weird about them?"
    → "Is there an innocent explanation?"
      → "What would I need to see to confirm or rule out fraud?"
        → "Is this worth escalating?"
Your system should follow that same chain.

Layer 0: The Hotlist (No Agent Needed)
What the analyst does: Every morning, checks what got flagged overnight.

What you build: A scheduled batch job that runs peer comparisons and spits out a ranked provider list. This is just SQL and statistics. No LLM. No agent.

Output: 
┌──────────┬────────────┬──────────────┬───────────────┬──────────┐
│ Provider │ Specialty  │ Billed (90d) │ Key Deviation │ Priority │
├──────────┼────────────┼──────────────┼───────────────┼──────────┤
│ P-6610   │ Cardiology │ $321K        │ 3.36σ billing │ HIGH     │
│ P-7777   │ Pain Mgmt  │ $360K        │ 74% out-spec  │ HIGH     │
│ P-1520   │ Ortho Surg │ $1.97M       │ same-day dup  │ MEDIUM   │
└──────────┴────────────┴──────────────┴───────────────┴──────────┘
The analyst picks one and starts digging. They choose. Not the system.

Layer 1: The Provider Deep Dive (Light Agent)
What the analyst does: Pulls up the provider's billing history and starts asking questions.

What you build: A single agent that the analyst converses with. Not autonomous. Reactive.

Analyst: "Tell me about P-6610"

Agent: P-6610 is a Cardiologist in Southeast region.
       30 claims in 90 days, $321K total.
       
       What stands out:
       - Bills $10,700/claim. Peers average $2,911. (z=3.36)
       - Only 8 unique patients. That's 0.43/month vs peer avg 4.29.
       - 83% of referrals come from just 4 sources.
       - 100% high-complexity claims. Peers average 47%.
       
       In plain terms: very few patients, very high bills per visit,
       almost all referred by the same small group.

Analyst: "What's the diagnosis mix?"

Agent: [pulls claim details]
       Top diagnoses:
       - I25.10 (Coronary artery disease) — 18 claims
       - I48.91 (Atrial fibrillation) — 7 claims  
       - I50.9 (Heart failure) — 5 claims
       
       These diagnoses can support high-complexity E&M,
       but 100% high-complexity across all visits is unusual.
       Peers with similar diagnosis mix bill high-complexity 
       at 35-50%.

Analyst: "Show me the top patients"

Agent: [pulls patient-level summary]
       Patient M-NET-04: 8 claims, $85K billed
       Patient M-NET-02: 6 claims, $64K billed
       Patient M-NET-01: 5 claims, $53K billed
       
       These 3 patients account for 63% of total billing.

Analyst: "Are these patients seeing other providers?"

Agent: [now network analysis makes sense contextually]
       Yes. M-NET-04 also sees P-6640, P-6630, and P-6650.
       M-NET-02 sees P-6640 and P-6620.
       All five providers share patients and have elevated 
       anomaly scores (0.59-0.79).
Notice what happened: the analyst drove the investigation. Network analysis came in naturally when the analyst asked about shared patients — not because an orchestrator decided it was time for "ring detection."

Layer 2: The Sanity Check (Where AI Actually Helps)
What the analyst does: Before escalating, they ask themselves "is there an innocent explanation?"

This is where an LLM genuinely adds value — playing devil's advocate:

Analyst: "I'm ready to flag P-6610. What am I missing?"

Agent: Possible innocent explanations to consider:

1. SPECIALTY NICHE: If P-6610 focuses on complex cardiac 
   electrophysiology, high billing per claim could be 
   legitimate. Have you checked their sub-specialty?

2. REFERRAL PATTERN: 83% referral concentration from 4 
   sources could indicate a legitimate group practice 
   arrangement rather than kickbacks. Are the referring 
   providers in the same medical group?

3. LOW PATIENT VOLUME: 0.43 patients/month could mean 
   they're semi-retired or part-time. Cross-check with 
   their credentialing status.

4. HIGH-COMPLEXITY PATIENTS: If this provider specifically 
   accepts complex transfers that other cardiologists 
   decline, 100% high-complexity could be legitimate 
   case selection, not upcoding.

Recommendation: Request 5-10 medical records before 
escalating. If documentation supports the billed 
complexity, this may be a legitimate outlier.
This is something a dashboard can't do. This requires reasoning about context, and it's where an LLM earns its place.

Layer 3: The Documentation Review (Future NLP Win)
What the analyst does: Reads medical records and compares to billed codes.

What you'd eventually build: An NLP layer that reads clinical notes and checks:

Does the documented history support the diagnosis codes?
Does the exam documentation meet the E&M level billed?
Are the notes templated/cloned across patients?
Is the time documented consistent with the billed level?
This is the hardest and most valuable part. It's also where most organizations aren't ready yet because their clinical notes are in PDFs, faxes, and scanned images.

But even a simple version helps:

Agent: I reviewed 10 clinical notes for P-6610.

       Concern: 8 of 10 notes contain identical Review of 
       Systems language across different patients. The HPI 
       section varies but the ROS and Physical Exam appear 
       templated.
       
       Specific finding: Notes for M-NET-04 (visit 3/15) 
       and M-NET-02 (visit 3/17) share identical 14-point 
       ROS. Statistically unlikely for different patients 
       with different chief complaints.
How to Plan This With SME + Engineer
Phase 1 (4-6 weeks): The Hotlist + Basic Deep Dive
SME defines:

What metrics matter for their top 5 fraud schemes
What peer groups make sense (specialty + region? specialty + practice size?)
What thresholds trigger review (they'll know from experience)
What data they actually have access to
Engineer builds:

Batch statistical comparison job
Simple ranked output (table, not dossier)
Conversational agent with 4-5 tools (profile, claims, peers, patients, referrals)
Test by: Having the SME use it on 10 known fraud cases and 10 known clean providers. Does it surface the right signals? Does it miss anything they'd normally catch?

Phase 2 (4-6 weeks): The Sanity Check + Context
SME defines:

Common innocent explanations for each fraud pattern
What additional context resolves ambiguity (sub-specialty, practice arrangement, patient population)
Their actual escalation criteria
Engineer builds:

Prompt engineering for the "what am I missing" feature
Integration with provider credentialing data
Integration with practice/group affiliation data
Test by: Having the SME try to break it. Give it edge cases. Rural providers. New practices. Legitimate specialists who look like outliers.

Phase 3 (8-12 weeks): Network + Documentation
SME defines:

When they actually need network analysis (not always)
What they look for in medical records
What "cloned documentation" looks like in their experience
Engineer builds:

On-demand network visualization (not automatic ring detection)
Basic NLP for clinical note comparison
Document similarity detection across a provider's patient notes
Phase 4 (Optional): Autonomous First Pass
Only after Phases 1-3 are solid and trusted, you can add an autonomous mode:

"Run overnight analysis on this quarter's claims. 
In the morning, show me your top 10 concerns with 
your reasoning. I'll decide what to investigate."
This is where the agentic loop makes sense — but only because each component has been validated individually with the SME first.

The Key Principle
Build for the analyst's workflow, not for the AI's architecture.

The current system was designed around what agents can do (scan, profile, compile, loop). The right system is designed around what analysts need to know (who's suspicious, why, what else could explain it, what should I look at next).

The agent architecture becomes invisible plumbing. The analyst just asks questions and gets useful answers. That's the goal.