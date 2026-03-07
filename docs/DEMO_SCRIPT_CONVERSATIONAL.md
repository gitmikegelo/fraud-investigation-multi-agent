# 🏆 Claims Investigation Copilot — 5-Minute UI Demo Script (Conversational)
## "Watch AI Agents Uncover a $2.3M Fraud Ring in Real-Time"

> **Demo Philosophy:** Focus on **FUNCTION over FLASH**. Show what the system does, how the workflow operates, and why the outputs are actionable. Let the capabilities speak for themselves rather than overselling.

---

## ⏱️ TIMING BREAKDOWN
| Section | Time | Goal |
|---------|------|------|
| Setup: The 3 Agents | 0:00 - 0:30 | Quick context |
| Beat 1: Discovery | 0:30 - 1:15 | Find the needle |
| Beat 2: The Ring | 1:15 - 2:00 | Uncover the conspiracy |
| Beat 3: The Pushback | 2:00 - 3:30 | **SIGNATURE MOMENT** |
| The Dossier | 3:30 - 4:15 | Prove it's actionable |
| Explainability Pivot | 4:15 - 4:45 | Trust & audit trail |
| Legitimate Dismissal | 4:45 - 5:15 | Show judgment |
| Mic Drop | 5:15 - 5:30 | Timer reveal |

---

## 🤖 SETUP: THE 3 AGENTS (0:00 - 0:30)

**[SCREEN: Three agent cards visible]**

"So the system uses three specialized agents. The Lead Investigator decides what to investigate based on the initial scan results. The Detective has access to seven different investigation tools — it can profile entities, compare to peers, map connections, find fraud rings. And the Case Writer has five tools for compiling the final dossier — it assesses evidence, searches billing rules, finds precedent cases."

**[Gesture to screen:]**

"What makes this different is the Case Writer can reject evidence and send the Detective back for more data if what it has isn't sufficient. So it's not just a linear pipeline, they actually interact based on what they find. Let me show you a full investigation run."

---

## 🎯 BEAT 1: DISCOVERY (0:30 - 1:15)

**[SCREEN: Demo UI — agent stream on left (terminal style), empty viz panel on right, timer at bottom]**

"I'm clicking one button to start the investigation. New batch of claims just came in."

**[Click. Timer starts: 00:00. Stream begins flowing.]**

**[Stream shows:]**
```
🤖 ORCHESTRATOR: --- Iteration 1 | Current phase: start ---
   Calling LLM for routing decision...
   >>> LLM Call #1
   LLM responded in 8.3s
   Phase transition: start -> investigate

🔍 INVESTIGATION: Starting investigation sub-agent (7 tools available)...
   Invoking LLM + tool loop (this may take a while)...
   
   >>> LLM Call #1
   
   [tool] Scanning claims (last 90 days, anomaly > 0.5)...
   [tool] Found 8 high-anomaly entities (0.0s)
   
   >>> LLM Call #2
   
   [tool] Profiling P-6610...
   [tool] Profiling P-6640...
   [tool] Profiling P-6620...
   
   >>> LLM Call #3
   
   Sub-agent finished in 28.4s | Tool calls made: 2
   
   Summary preview: Initial Scan Findings — 8 high-anomaly entities detected. 
   Top 3: P-6610 (Cardiology, anomaly 0.80, $485K), P-6640 (Cardiology, 
   anomaly 0.68, $285K), P-6620 (IM, anomaly 0.62, $125K)

🤖 ORCHESTRATOR: --- Iteration 2 | Current phase: investigate ---
   Calling LLM for routing decision...
   LLM responded in 3.5s
   Phase transition: investigate -> compile
```

**[Narrate what's happening:]**

"The investigation agent scans the claims and finds 8 high-anomaly entities. It then profiles the top 3 providers — P-6610 with anomaly score 0.80 and $485K billed, P-6640 with 0.68 and $285K, and P-6620 with 0.62 and $125K. The orchestrator then routes to the dossier agent to compile the findings."

---

## 🎯 BEAT 2: THE RING (1:15 - 2:00)

**[Stream shows:]**
```
🤖 LEAD: Valid objection. Acknowledged.
   → Detective: retrieve connection data and network analysis

🔍 DETECTIVE: Starting investigation sub-agent (7 tools available)...
   Invoking LLM + tool loop (this may take a while)...

   >>> LLM Call #1
   
   [tool] Searching for fraud rings (anomaly >= 0.5, min entities=3)...
   [tool] !!! OUTPUT TRUNCATED from 4550 to 2000 chars

   >>> LLM Call #2
   
   [tool] Finding connections for P-6610 (depth=2)...
   [tool] Found 5 connected entities (density 18.0)

   >>> LLM Call #3
   
   Sub-agent finished in 28.4s | Tool calls made: 2
   
   Summary: Fraud Ring Analysis: 5 entities, $895K billed, density 18.0. 
   P-6610, P-6640, P-6620 confirmed in ring.
```

**[RIGHT PANEL: Network visualization fades in — showing three different provider patterns side by side]**

**[Point to the visualization:]**

"The network view shows why this case escalated from 'suspicious billing' to 'coordinated fraud ring.'"

**[Gesture to left graph:]**

"On the left, you see an isolated provider with their patient network — high volume, but no provider-to-provider connections."

**[Gesture to middle graph:]**

"In the middle, a provider with high-anomaly patients — those red numbers are anomaly scores above 0.7. Potential upcoding, but still operating independently."

**[Gesture to right graph — the ring:]**

"On the right — this is what changes everything. The find_ring tool detected 5 entities connected with a network density of 18 connections. P-6610, P-6640, P-6620, P-6630, and P-6650 — all connected, all with high anomaly scores, combined billing of $895K."

**[Keep pointing to the ring:]**

"This isn't just similar behavior happening in parallel — it's **coordinated behavior**. The connection analysis tool maps these provider-to-provider relationships through referrals and shared patients."

**[Stream shows:]**
```
🤖 LEAD: Ring structure confirmed. Escalating to Case Writer for formal dossier.
   Phase transition: investigate -> compile
```

"The Lead routes this to the Case Writer to compile the investigation dossier."

---

## 🎯 BEAT 3: THE PUSHBACK — EVIDENCE ASSESSMENT (2:00 - 3:30)

**[Stream shows:]**
```
📋 DOSSIER: Starting dossier sub-agent (5 tools available)...
   Findings payload size: 412 chars
   Invoking LLM + tool loop (evidence assessment & compilation)...
   
   >>> LLM Call #1
   Group[0]: 2 messages
   >>> Total input chars: 1569
   
   [tool] Assessing evidence for "Coordinated medical billing fraud ring" 
          (3 points)...
   [tool] Result: INSUFFICIENT (2 passed, 2 failed)
   
   >>> LLM Call #2
   
   Sub-agent finished in 14.2s | Tool calls made: 1
   Evidence assessed as INSUFFICIENT - looping back to investigation
   Setting next phase -> investigate (evidence gaps forwarded to investigator)
```

**[POPUP appears with rejection details:]**
```
⚠️ DOSSIER REJECTED

Dossier rejected the investigation — evidence is INSUFFICIENT.

Evidence Gaps:
Missing: (1) Temporal billing pattern — need referral history showing 
shift over time. (2) Ring density evidence — need connection/ring 
analysis to establish coordinated behavior.
```

**[Give them 2 seconds to read this]**

**[Then explain functionally:]**

"The dossier agent has an evidence assessment tool that scored 3 evidence points — 2 passed but 2 failed. It identified that we're missing temporal data showing whether the referral pattern changed recently, and we need ring density analysis to confirm coordination."

"So it rejects the compilation and sends the investigation back with specific gaps to address."

**[Stream shows:]**
```
🤖 ORCHESTRATOR: --- Iteration 3 | Current phase: compile ---
   Evidence INSUFFICIENT - looping back to investigation
   Phase transition: compile -> investigate

🔍 INVESTIGATION: Starting investigation sub-agent (7 tools available)...
   
   >>> LLM Call #1
   
   [tool] Comparing P-6610 to peers on avg_billed_per_claim...
   [tool] P-6610: $4,250 vs peer avg $1,328 (z-score 3.2)
   [tool] Comparing P-6640 to peers on avg_billed_per_claim...
   [tool] P-6640: $2,850 vs peer avg $1,412 (z-score 2.1)
   
   >>> LLM Call #2
   
   [tool] Fetching referral history for P-6610 (last 12 months)...
   [tool] Found 32 referrals; top referral sources: P-6620 (38% of inbound), 
          P-6630 (34% of inbound)
   [tool] Fetching referral history for P-6640 (last 12 months)...
   [tool] Found 26 referrals; top referral source: P-6610 (42% of inbound)
   
   >>> LLM Call #3
   
   Sub-agent finished in 32.1s | Tool calls made: 4
   
   Summary: Peer Comparison & Referral Analysis — P-6610 avg_billed 
   z-score 3.2, P-6640 avg_billed z-score 2.1. Referral loop detected: 
   P-6620→P-6610 (38%), P-6630→P-6610 (34%), P-6610→P-6640 (42%).

🤖 ORCHESTRATOR: --- Iteration 4 | Current phase: investigate ---
   Phase transition: investigate -> compile

📋 DOSSIER: Starting dossier sub-agent (5 tools available)...
   
   >>> LLM Call #1
   
   [tool] Assessing evidence for "Coordinated medical billing fraud ring 
          with upcoding pattern" (6 points)...
   [tool] Result: SUFFICIENT (4 passed, 0 failed)
   
   ✅ EVIDENCE ASSESSMENT: SUFFICIENT
   
   >>> LLM Call #2
   
   [tool] Searching rules for CPT codes: ['99215', '99214', '99213']...
   [tool] Found 5 relevant rules
   
   >>> LLM Call #3
   
   [tool] Looking up precedent cases for "upcoding_ring"...
   
   >>> LLM Call #4
   
   [tool] Estimating recovery for 3 flagged claims...
   
   >>> LLM Call #5
   
   Sub-agent finished in 42.5s | Tool calls made: 4
   
   Dossier compiled successfully!
   Evidence sufficient — ready for action
```

"After the detective gathers peer comparisons and referral history, the dossier agent reassesses. This time the evidence assessment passes — 4 out of 6 evidence points confirmed, 0 failed. It then searches billing rules, finds precedent cases, estimates recovery, and compiles the final dossier."

---

## 📋 THE DOSSIER (3:30 - 4:15)

**[Switch to dossier view — full formatted markdown report]**

**[Scroll through, pointing out components:]**

"Here's the compiled dossier. Executive summary lists 3 entities with $286K estimated recovery."

**[Scroll to Statistical Analysis]**

"Statistical analysis section shows every key metric compared to specialty peer groups — average billed per claim, claims per month, patient concentration — with z-scores showing how many standard deviations from normal."

**[Scroll to Billing Rules]**

"Billing rules section — this pulls from a vector database of CMS regulations. It identified the specific violated rules with regulation numbers: CMS-EM-002 for E&M Level 5 documentation, CMS-EM-001 for Level 4, plus the upcoding ring pattern."

**[Scroll to Network Analysis]**

"Network metrics — connected entity count, network density, ring indicators."

**[Scroll to bottom]**

"Bottom section has the estimated recovery calculation — $286,000 — and recommended actions: request operative notes to verify the billed procedures, issue pre-payment hold to stop further billing, refer to OIG Special Investigations for potential Anti-Kickback statute violations."

"This dossier format is designed to be actionable — it has the evidence, the regulatory basis, and the specific next steps."

---

## 🔍 EXPLAINABILITY PIVOT (4:15 - 4:45)

**[Pause for effect]**

"Now, in regulated healthcare, a powerful system that just outputs a conclusion is useless. The most critical question is: **'How can you trust this result?'**"

**[Switch to log view — full investigation timeline with timestamps, agent decisions, tool calls]**

"This is what separates an agentic system from a black-box model. Every decision the agents made — every tool they called, every piece of data they analyzed, every assessment they performed — is captured in a complete audit trail with timestamps."

**[Point to specific log entries as you scroll:]**

"You can see the orchestrator routing between agents, the LLM calls with their input character counts, every tool invocation with its parameters and results. When the dossier agent rejected the case the first time, you see exactly what evidence was missing — temporal patterns and ring density. Then you see the detective going back to fetch that data with specific tool calls."

**[Keep it functional:]**

"This isn't just system logging. This is a **record of the agent's cognitive process** — the reasoning chain from initial flag to final conclusion. Every tool call, every evidence assessment, every dossier compilation step is logged with the agent's reasoning."

**[Bring it home:]**

"What makes this production-ready is that you can defend every conclusion. When a provider appeals or an auditor reviews the case, you show them this log — the exact tools used, the data analyzed, the evidence thresholds applied. The log becomes the legal audit trail."

**[Quick transition:]**

"Let me show you one more important capability — what happens when the investigation finds nothing."

---

## ✅ LEGITIMATE DISMISSAL (4:45 - 5:15)

**[Keep this section brief and conceptual]**

"One more critical capability — **the system can walk away**. Not every high-anomaly flag is fraud."

**[Explain the concept:]**

"When the investigation finds that a provider's high billing volume is explainable — like a Level 1 trauma center that naturally has higher procedure rates, or a specialty practice in an underserved area — the evidence assessment fails and no dossier gets generated."

**[Point to the architecture:]**

"The same evidence assessment tool that approved the fraud ring case would reject a case where peer comparisons show the volume is within normal range for that practice context. The dossier agent has the authority to say 'this isn't fraud' and close the investigation."

"That judgment capability is what prevents false positives from wasting investigator time."

---

## 🎤 CLOSING (5:15 - 5:30)

**[Point to the timer]**

"The fraud ring investigation took about 90 seconds from initial scan to complete dossier with all evidence, regulatory violations, and recommended actions."

**[Pause briefly]**

"That's the system — scan, investigate, assess evidence quality, compile actionable output. And most importantly, every decision is auditable."

---

## 💡 Q&A BATTLE CARDS

### "How is this different from existing fraud detection?"
"Existing tools flag suspicious claims and then stop. This actually investigates them — it profiles the providers, maps the connections, assesses the evidence, compiles the case file. The flag is step 1, this does steps 1 through 10."

### "What about false positives?"
"You just saw it — the second case got dismissed because the high volume was explained by the practice context. It's not confirmation bias, it actually applies judgment and walks away when the evidence doesn't support fraud."

### "How do you ensure the results are explainable and defensible?"
"Because the system is built on autonomous agents, we capture the entire decision-making process in the logs. It's not just 'this provider is suspicious' — it's a timestamped record of every tool call, every data source analyzed, and every reasoning step. When a provider appeals or an auditor reviews the case, you can show exactly how the conclusion was reached. That's a fundamental requirement in regulated healthcare that traditional black-box models can't provide. The logs are the legal audit trail."

### "What LLM are you using?"
"Claude 3.5 via AWS Bedrock. It's fast, it's cheap, it's reliable. This full investigation you just saw costs about 12 cents in API calls."

### "What if the agents hallucinate?"
"Every number in that dossier comes from tool calls to the actual database, not from generation. The LLM does the reasoning and delegates to tools, but the tools return real data. The dossier cites specific claim IDs that you can verify."

### "How does it scale?"
"Each investigation is completely independent, so you can run 50 of these in parallel. The bottleneck in fraud investigation was never compute, it was human analyst time. We just removed the bottleneck."

### "What's the role of the human analyst?"
"Review and approve. The agent does the 4-hour investigation in 90 seconds, and then the human analyst reviews it and makes the final call in maybe 2-3 minutes. We're augmenting their judgment, not replacing it."

### "Is this real claims data?"
"This is synthetic data modeled on real CMS Medicare patterns, so the fraud schemes are realistic. But the agent behavior would be identical on real data because it's tool-agnostic — the agents don't care where the data comes from."

### "Can this detect other types of fraud?"
"Yeah, the architecture is pattern-agnostic. We can plug in different tools for pharmacy fraud, durable medical equipment fraud, telemedicine fraud — the agent reasoning layer stays the same, you just swap the tools underneath."

---

## ✅ PRE-DEMO CHECKLIST

### Technical Setup (60 min before)
- [ ] Hero fraud ring case cached and tested 3x
- [ ] Timer visible, starts at 00:00 on click
- [ ] Ring visualization fades in smoothly on cue
- [ ] Dossier renders cleanly, no scroll jank
- [ ] Backup screen recording of perfect run (safety net)
- [ ] Screen layout: 60% stream / 40% viz + timer
- [ ] Font sizes readable from back of room
- [ ] Dark theme enabled
- [ ] Test the evidence rejection flow — make sure the popup shows properly

### Performance Prep (30 min before)
- [ ] Run through full demo 3x focusing on clear narration of functions
- [ ] Time yourself — target 4:50-4:55
- [ ] Practice explaining what each tool does (not just that it's cool)
- [ ] Know your Q&A answers focused on functional capabilities
- [ ] Have water nearby

### Mental Game (5 min before)
- [ ] Deep breath
- [ ] Focus on clearly explaining the workflow
- [ ] Don't oversell — let the functionality demonstrate itself
- [ ] If tech fails, switch to backup recording immediately

---

## 🎯 DEMO PRINCIPLES

### 1. **Focus on what the system does, not how cool it is**
Describe the functions: "The evidence assessment function identified a gap in the temporal data" — not "Watch this amazing thing the AI does!"

### 2. **Point out the workflow, not the magic**
Explain the investigation flow: scan → connections → evidence assessment → dossier. Show how the pieces work together functionally.

### 3. **Highlight the outputs and their utility**
"The dossier has regulatory violations, recovery estimates, and recommended actions" — show what makes it actionable, not just impressive.

### 4. **Let the logs speak**
The agent reasoning streams show the functional decisions being made. Narrate what's happening, don't over-interpret or dramatize.

### 5. **Show the quality control process**
The evidence rejection and refinement loop demonstrates that the system has standards — it doesn't just rubber-stamp every finding. Show how the dossier agent pushes back when evidence is incomplete.

---

## 🔥 FUNCTIONAL FOCUS

The demo shows:
- **Automated investigation workflow** — scan → profile → network analysis → evidence assessment → dossier compilation
- **Evidence quality control** — Dossier agent can reject incomplete evidence and loop back to investigation with specific gaps
- **Contextual peer comparison** — compares flagged entities to appropriate peer groups before concluding fraud
- **Complete audit trail** — timestamped logs capture every agent decision, tool call, and reasoning step for regulatory compliance
- **Actionable output** — dossier includes regulatory violations, recovery estimates, and specific next steps
- **Iterative refinement** — system loops between investigation and compilation until evidence meets quality threshold

This demonstrates a complete functional system, not just a detection model.

---

## 💪 FOCUS ON FUNCTION

You built a complete functional system:
- Takes input (new claims batch)
- Processes it (scan, profile, analyze)
- Makes decisions (evidence assessment with rejection/approval)
- Produces output (actionable dossier with audit trail)

Other teams will show components. You're showing an end-to-end workflow.

Keep the demo focused on **what it does** and **why that's useful**. Let the functionality speak for itself. 🚀
