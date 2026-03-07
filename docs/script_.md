Reasoning: The user wants me to rewrite their demo script incorporating my improvement suggestions, formatted as markdown, for an 8-minute presentation.



# Claims Investigation Copilot — Demo Script (8 Minutes)
## Final Presentation Script

---

## ROLES

| Section | Speaker | Time |
|---------|---------|------|
| Act 1: Problem | Speaker A | 0:00–1:15 |
| Act 2: Architecture | Speaker A | 1:15–2:00 |
| Act 3: Live Demo (Beats 1-3) | Speaker B | 2:00–5:00 |
| Act 4: Dossier + Legitimate Case | Speaker A | 5:00–6:30 |
| Act 5: Close | Speaker A | 6:30–7:15 |
| Buffer / Overrun | — | 7:15–8:00 |
| Q&A | All 4 | After |

Speakers C and D: Running the demo behind the scenes. Clicking, switching screens, recovering if something breaks. You take technical questions in Q&A.

---

## ACT 1: THE PROBLEM (0:00 – 1:15)

**[SCREEN: Black.]**

**SPEAKER A:**

"Quick question — anyone here ever gotten a medical bill that made absolutely no sense?"

**[Pause. Let people react.]**

"Now imagine you're the insurance company on the other end of that bill, and you're getting 10 million of them a month. Some are legitimate. Some are... creative."

"Healthcare fraud is a $100 billion a year problem in the US. And look — the industry has good tools. Anomaly detection, machine learning models — they flag suspicious claims all day long."

**[SCREEN: Screenshot of dense alert dashboard — 500+ rows]**

"This is what a fraud analyst sees on a Monday morning. Five hundred alerts. Each one is a Post-it note that says 'hey, this looks weird.' And then the actual work starts."

"Each alert takes 2 to 4 hours of manual investigation — pulling claims, checking billing codes, mapping connections between providers, cross-referencing guidelines, writing a case file."

"Five hundred alerts a week. Three analysts on the team. They can investigate maybe 15. That means **97% of potential fraud is never investigated.** Not because the models missed it — because there aren't enough humans to look at it."

**[Beat.]**

"Every alert that sits in that queue for six months? That's $47,000 in average unrecovered billing. Multiply that by the 485 nobody gets to. That's $22 million a year walking out the door. Per health plan."

"So we asked a simple question: what if we didn't build a better flag? What if we built the investigator?"

---

## ACT 2: ARCHITECTURE (1:15 – 2:00)

**[SCREEN: Three agent cards — Lead Investigator, Detective, Case Writer]**

**SPEAKER A:**

"We built three AI agents. And I want to be clear — this is not a pipeline. There's no step 1, step 2, step 3. These agents reason, delegate, and challenge each other."

**[Point to each card:]**

"The Lead Investigator — decides what's worth looking into and how deep to go. Delegates everything. Does no actual work. So basically, management."

**[Pause for laugh.]**

"The Detective — does the digging. Scans claims, profiles providers, maps connections, discovers fraud rings."

"And the Case Writer — compiles everything into a formal investigation dossier. But here's the thing. If the evidence is weak, she refuses to write the report. She sends the Detective back to get more. We call this the **Evidence Gate** — no output without verified inputs."

"We actually tried this with one agent first. It would find something suspicious, get excited, and write a case file confirming its own hypothesis. Classic confirmation bias. When we split investigation from review, the quality changed immediately. The Case Writer catches things the Detective misses. One agent won't argue with itself. Two will."

"Let me show you what this looks like live."

---

## ACT 3: THE LIVE DEMO (2:00 – 5:00)

**[SCREEN: Demo UI. Agent reasoning stream on the left. Visualization panel on the right (empty). Timer overlay (large, 72pt font) in the corner. Evidence confidence panel below the stream.]**

**SPEAKER A:**
"I'm handing this to [Speaker B], who built the agent system."

**SPEAKER B:**

"Alright. We've got a batch of new claims. I'm going to do exactly one thing — click this button. Everything from here is the agents deciding what to do on their own."

**[Click. Timer starts at 00:00. Agent stream begins.]**

---

### BEAT 1 — DISCOVERY (2:15 – 2:50)

**[Stream shows:]**
```
🤖 LEAD: New claims batch received. Asking the Detective to scan for anomalies.
   → Detective: scan latest claims for anomalies.

🔍 DETECTIVE: Scanned 847 claims. 23 flagged as anomalous.
   Top finding: Provider P-4482
   Specialty: Orthopedic Surgery
   Anomaly score: 0.92
   Primary signal: Suspected upcoding on knee procedures
   Billed $487K in 90 days — peer average is $142K
```

**[Evidence confidence panel updates:]**
```
Evidence Strength: ██░░░░░░░░ 18%
├── Statistical anomaly:  ✅ Confirmed (score: 0.92)
├── Peer comparison:      ⬜ Pending
├── Network structure:    ⬜ Pending
├── Temporal pattern:     ⬜ Pending
└── Billing rule match:   ⬜ Pending
```

**SPEAKER B:**
"847 claims scanned, 23 flagged. But watch the Lead. It doesn't just go down the list by score. It's reasoning about which finding matters most."

**[Stream continues:]**
```
🤖 LEAD: P-4482 has the highest anomaly score and biggest dollar exposure.
   But I need to check — is this person acting alone, or part of something bigger?
   → Detective: map connections for P-4482, depth 2
```

"See that? It's asking: is this the whole story, or the tip of something?"

---

### BEAT 2 — THE RING (2:50 – 3:45)

**[Stream shows:]**
```
🔍 DETECTIVE: P-4482 connected to 3 referring providers:
   P-1190 (Family Medicine), P-3387 (Internal Medicine), P-5521 (Pain Management)
   12 shared patients across all four providers
   Referral concentration: 78% — peer group average: 18%
   Combined suspicious billing: $2.3 million
   Network density: 4.2x expected
```

**[RIGHT PANEL: PyVis ring visualization fades in. Red provider nodes. Blue patient nodes. Lines with dollar amounts.]**

**[Evidence confidence panel updates:]**
```
Evidence Strength: █████░░░░░ 48%
├── Statistical anomaly:  ✅ Confirmed (score: 0.92)
├── Peer comparison:      ✅ Confirmed (4.2x density)
├── Network structure:    ✅ Ring detected (4 providers, 12 members)
├── Temporal pattern:     ⬜ Pending
└── Billing rule match:   ⬜ Pending
```

**SPEAKER B:**

**[Stand up. Walk to screen. Point at the visualization.]**

"We started with one provider. The agent pulled the thread and found *this*."

"Four doctors. Twelve patients. These three family docs and internists are sending 78% of their knee patients to one surgeon. Their peers send 18% to any single surgeon. That's a 4x concentration."

"$2.3 million in suspicious billing."

**[Stream continues:]**
```
🤖 LEAD: This is not an individual case. This is a coordinated referral ring.
   Escalating to critical priority.
   → Case Writer: compile investigation dossier for this ring.
```

"The Lead just escalated from 'one weird provider' to 'coordinated fraud ring.' On its own. Nobody told it to do that. That's agentic reasoning — the investigation path isn't scripted, it's decided in real time based on what it finds."

---

### BEAT 3 — THE PUSHBACK ⭐ (3:45 – 5:00)

**[This is your moment. Slow down. Do not rush.]**

**[Stream shows:]**
```
📋 CASE WRITER: Reviewing evidence package.

   I have billing data for P-4482 and the ring structure.
   The referral concentration is striking. However...

   ⚠️ EVIDENCE ASSESSMENT: INSUFFICIENT

   The referral concentration alone is circumstantial. I need to see
   HISTORICAL referral patterns for these three referring providers.
   If they have ALWAYS referred heavily to P-4482, this could be a
   legitimate long-standing practice relationship.

   I need to see that this pattern CHANGED. Without temporal evidence,
   I cannot compile a defensible case file.

   Requesting: 18-month referral history for P-1190, P-3387, P-5521.
```

**[Evidence confidence panel shows:]**
```
Evidence Strength: █████░░░░░ 48%  ⚠️ BLOCKED — Insufficient for dossier
├── Statistical anomaly:  ✅ Confirmed
├── Peer comparison:      ✅ Confirmed
├── Network structure:    ✅ Ring detected
├── Temporal pattern:     ❌ MISSING — "Need historical comparison"
└── Billing rule match:   ⬜ Pending
```

**[PAUSE. Full 3-4 seconds of silence. Let judges read it. Step back slightly from the screen.]**

**SPEAKER B:**

"She said no."

**[Another beat of silence.]**

"The Case Writer just looked at $2.3 million in suspicious billing and said 'I'm not writing this up. The evidence isn't good enough.'"

"And she's right. If you took this to a real fraud investigator and said 'these doctors refer to each other a lot,' they'd say 'so what? Maybe they're in the same hospital. Maybe they've known each other for 20 years. Show me that something *changed*.'"

"That's what she's asking for. We call this the **Evidence Gate** — the system has quality standards built into the agent architecture. The investigator has a bias toward finding things. The case writer has a bias toward rigor. That tension is by design."

"So watch — the Lead listens."

**[Stream continues:]**
```
🤖 LEAD: The Case Writer makes a valid point. We need temporal evidence
   to confirm a pattern shift.
   → Detective: pull 18-month referral history for P-1190, P-3387, P-5521

🔍 DETECTIVE: Referral history retrieved.
   All three providers show a synchronized shift approximately 8 months ago.

   BEFORE (18–8 months ago):
   - Referrals distributed across 6-8 orthopedic surgeons
   - No single surgeon received more than 15%

   AFTER (last 8 months):
   - 78% of referrals concentrated on P-4482
   - Other surgeons dropped almost entirely
   - Change was abrupt — not gradual
   - All three shifted within the same 3-week window
```

**SPEAKER B:**

**[Step forward toward screen.]**

"Three doctors. Same 3-week window. All suddenly sending their patients to the same surgeon. That's not a coincidence. That's a phone call."

"This pattern — coordinated referral rings with upcoding — is exactly what the DOJ prosecuted in the 2023 South Florida Medicare fraud takedown. $1.1 billion in false claims. That scheme ran for four years before anyone caught it."

**[Stream continues:]**
```
📋 CASE WRITER: Updated evidence reviewed.

   ✅ EVIDENCE ASSESSMENT: SUFFICIENT
   Confidence: HIGH

   The synchronized referral shift confirms coordinated behavior change.
   Compiling dossier now.
```

**[Evidence confidence panel:]**
```
Evidence Strength: █████████░ 91%  ✅ SUFFICIENT — Compiling dossier
├── Statistical anomaly:  ✅ Confirmed (score: 0.92)
├── Peer comparison:      ✅ Confirmed (z-score: 3.7)
├── Network structure:    ✅ Ring detected (4 providers, 12 members)
├── Temporal pattern:     ✅ Synchronized shift confirmed (8 months ago)
└── Billing rule match:   ✅ CMS guidelines cited
```

"*Now* she writes it."

**[Glance at timer. It should read ~70-90 seconds.]**

"Check the clock."

**[Let the number speak for itself. Pause.]**

---

## ACT 4: THE DOSSIER + LEGITIMATE CASE (5:00 – 6:30)

**SPEAKER A takes back over.**

### The Dossier (5:00 – 5:50)

**[SCREEN: Dossier view — clean, formatted document]**

**SPEAKER A:**

"So what came out the other end? A complete investigation dossier."

**[Scroll slowly. Don't read everything. Hit highlights:]**

"Executive summary — four providers, twelve patients, forty-seven flagged claims, coordinated referral ring with upcoding."

**[Scroll]**

"Every provider benchmarked against their peer group. P-4482 billing 3.7 standard deviations above average. That's not noise."

**[Scroll]**

"Specific CMS billing rule citations — pulled from actual guidelines via our billing rules index. Not generated. Retrieved."

**[Scroll to bottom]**

"Estimated recovery: $252,600. Recommended next steps: request operative notes for flagged procedures, issue pre-payment hold on P-4482, refer the referral pattern to the Special Investigations Unit for potential Anti-Kickback Statute violations."

"This isn't a dashboard. This isn't an alert. This is a case file that an investigator can pick up and act on this afternoon."

"And every single number in this dossier is traceable. The LLM never generates data — it reasons and delegates. Every figure came from a tool call. A pandas query. A model score. A graph traversal. You can audit every line back to its source."

---

### The Legitimate Case (5:50 – 6:30)

**[Pause. Shift tone.]**

"But here's the question that separates a real investigation tool from a paranoid alarm system."

**[Beat.]**

"Can it clear the innocent?"

**[SCREEN: Second case — pre-loaded]**

```
🤖 LEAD: Provider P-2891 flagged for high billing volume.
   Sending Detective to investigate.

🔍 DETECTIVE: P-2891 is a trauma surgeon at a Level 1 trauma center
   in Houston. High volume is consistent with facility type and peer
   group. No referral anomalies. No coding irregularities. Weekend
   billing is high but expected for trauma.

🤖 LEAD: This is a legitimate high-volume practice. Pattern is
   consistent with peers in the same setting.

   CLOSING INVESTIGATION. No case generated.
```

**[Evidence panel shows:]**
```
Evidence Strength: N/A — Investigation closed
Result: ✅ LEGITIMATE — No case generated
Reason: Pattern consistent with peer group (Level 1 Trauma)
```

"It looked at it. Checked the data. Compared to peers. And said 'this person is doing exactly what you'd expect a trauma surgeon to do. Close the case.'"

"We call this the **Acquittal Path**. An investigation tool that can't clear the innocent is just a witch hunt with a nice UI."

---

## ACT 5: THE CLOSE (6:30 – 7:15)

**[SCREEN: Before/After comparison]**

```
BEFORE                                 AFTER
───────                                ──────
500 alerts in a Monday queue           Prioritized, investigated, closed or escalated
2-4 hours per investigation            90 seconds
97% of alerts die uninvestigated       Every alert gets a full investigation
Analyst writes the case file           Agent writes, analyst reviews and approves
Ring schemes buried in noise           Rings discovered and mapped automatically
Evidence gaps found in court           Evidence gaps found by the agent itself
```

**SPEAKER A:**

"Let me give you the math. A full week's alert queue — 500 investigations — runs in about 75 minutes parallelized, for $60 in API costs. That's less than one hour of one analyst's salary. To investigate everything."

"We didn't build a better fraud scorer. There are plenty of those. We built the thing that happens *after* the score."

"Three agents. One investigates. One writes the case. One refuses to cut corners."

"From a suspicious bill to a complete case file in ninety seconds."

"Thanks."

**[Stop. Don't add anything. Silence is confidence.]**

---

## Q&A ANSWER BANK

**Every answer under 20 seconds. No rambling.**

---

**"How is this different from what's already out there?"**

> "Everything out there stops at the flag. We start at the flag. The investigation — pulling claims, profiling providers, mapping connections, comparing to peers, writing the case file — that's all manual work today. We automated the entire investigation workflow, not just the detection."

---

**"Is this real data?"**

> "Synthetic, modeled on CMS Medicare public datasets. Realistic distributions, realistic fraud patterns. But the agents don't know where the fraud is — they start from a raw scan and work forward. The investigation path, the ring discovery, the pushback — that's all emergent behavior. Swap this for a real claims database and the agents run identically."

---

**"What model are you using?"**

> "Claude 3.5 Haiku through AWS Bedrock. The full investigation you just saw — all the back-and-forth between agents — cost about 12 cents."
>
> [If they react:] "Twelve cents to investigate a $2.3 million fraud ring. The ROI math is kind of absurd."

---

**"What if it hallucinates?"**

> "The LLM never generates data. It reasons and delegates. Every number in that dossier came from a tool call — a pandas query, a model score, a graph traversal. The claim IDs are real IDs from the database. You can trace every number to its source. The LLM decides what to ask for. The tools provide the answers."

---

**"What about false positives?"**

> "You saw it. P-2891 — flagged, investigated, cleared. The system isn't designed to confirm fraud. It investigates and reaches a conclusion. Sometimes that conclusion is 'nothing here.' That's by design."

---

**"What's the human's role?"**

> "Review and approve. The agent compresses a 4-hour investigation into 90 seconds of work product. The analyst reads the dossier, checks the evidence, and makes the call. We didn't remove the human. We gave them their afternoon back."

---

**"Why three agents instead of one?"**

> "We tried one agent first. It found something suspicious, got excited, and confirmed its own hypothesis every time. Classic confirmation bias. By separating investigation from review, we get adversarial collaboration — you saw it. The Case Writer pushed back on the Detective's findings. One agent won't argue with itself. Two will."

---

**"Could this work on real claims data?"**

> "The tools are Python functions that query data sources. We're already querying a database in the demo. Swap the connection string to Snowflake or Redshift and it works the same way. The agent layer doesn't care where the data lives."

---

**"How does it scale?"**

> "The anomaly scan is a batch job — runs nightly on the full claims table. The agent investigations are per-case and independent, so they parallelize trivially. 500 cases, 10 parallel workers, about 75 minutes, $60 in API costs. That covers a full week's queue for the cost of a lunch."

---

**"How does it handle novel fraud patterns?"**

> "The anomaly detection is unsupervised — Isolation Forest — so it catches things that are statistically unusual, not just known patterns. The agents then investigate to determine *why* it's unusual. A model tells you something is anomalous. The agents figure out whether it's fraud or just unusual."

---

**"What about HIPAA / privacy?"**

> "In production, the entire system runs within the health plan's infrastructure. Bedrock runs in the customer's AWS account — no data leaves the environment. The LLM sees claims data, but it's the same data fraud analysts already access. No data goes to Anthropic."

---

**"What's your competitive advantage?"**

> "Existing tools score claims. We investigate them. The scoring part is a solved problem — there are great models out there. Nobody has automated the 4 hours that happen after the score. That's the gap we fill."

---

**"What if a provider is flagged unfairly?"**

> "You saw that happen. P-2891 was flagged and cleared. Every dossier is a recommendation, not a verdict. A human reviews it, checks the evidence, and makes the call. We'd rather over-investigate and clear than under-investigate and miss."

---

**"What's next?"**

> "Three things. Real claims data integration with a health plan partner. A human-in-the-loop approval workflow so investigators can accept, reject, or request more on any case. And expanding the pattern library — pharmacy fraud, DME schemes, telehealth abuse. The architecture is pattern-agnostic."

---

**"How long did this take to build?"**

> "About 17 hours of focused work across four people. The agent framework handles orchestration. Most of our time went into the tools, the data layer, and the evidence assessment logic — not the agent wiring itself."

---

## EMERGENCY PROTOCOLS

### If the live demo freezes or crashes:

**SPEAKER B:** "The demo gods aren't cooperating — let me show you the run we recorded earlier. Same system, same data, same behavior."

**[Switch to backup video immediately. Do NOT try to debug on stage. One apology max. Move on.]**

### If the agent takes an unexpected path:

**SPEAKER B:** "Interesting — it's going a different direction than rehearsal. That's actually the point. It's not a script, it's reasoning in real time. Let's see where it goes."

**[This is a FEATURE, not a bug. Lean into it hard.]**

### If the agent loops too many times:

**SPEAKER B:** "It's being thorough — we have a loop cap to prevent runaway investigation costs in production. Let me show you where it ends up."

**[If needed, switch to pre-loaded final state.]**

### If a judge asks something you don't know:

"Honestly, I don't know. Great question — I'd love to dig into it after. What I can tell you is [pivot to something you DO know]."

**Never bluff. Judges can tell. "I don't know" said with confidence is 10x better than a rambling guess.**

---

## TIMING CHEAT SHEET

| Timestamp | What Should Be Happening | If Behind |
|-----------|-------------------------|-----------|
| 1:00 | Finishing problem statement | Cut the alert list description |
| 2:00 | Starting live demo | Skip "we tried one agent" story |
| 3:00 | Ring discovered, visualization showing | Summarize detective findings verbally |
| 4:00 | Pushback moment happening | Do NOT rush this. Cut time from dossier walkthrough instead |
| 5:00 | Dossier on screen | Skim — hit 3 highlights max |
| 6:00 | Legitimate case showing | Do NOT skip this. It's crucial |
| 7:00 | Close / before-after screen | Deliver final lines |
| 7:15 | Done | |

**Golden rule: If you're running long, protect the pushback moment and the legitimate case. Cut architecture explanation and dossier walkthrough. The demo speaks for itself.**

---

## THE THREE THINGS JUDGES WILL REMEMBER

1. **The pushback** — the Case Writer saying no
2. **The timer** — 90 seconds
3. **The ring visualization** — the picture

Everything else serves these three moments. If you nail them, you're in the finals.

---

## THE FOUR NAMED CONCEPTS TO DROP NATURALLY

1. **Evidence Gate** — the Case Writer's refusal mechanism
2. **Adversarial Review** — investigation and review separated to prevent confirmation bias
3. **Acquittal Path** — the system's ability to clear legitimate providers
4. **Investigation Loop** — agents iterating until evidence meets quality threshold

Don't define these formally. Just use them like they're obvious. Judges remember named patterns.

---

## ENERGY NOTES

- **Speaker A:** Warm, confident, storytelling. You're explaining why this matters.
- **Speaker B:** Technical, genuine, slightly amazed by what the agents do. You built this and you think it's cool — let that show without being cocky.
- **Nobody reads.** If you catch yourself reciting, stop and just talk.
- **The pushback pause is everything.** Rehearse those 4 seconds of silence 10 times. Silence on stage feels eternal. That's why it works.