# Claims Investigation Copilot — Demo Battle Plan
## "From Suspicious Bill to Complete Case File in 90 Seconds"

---

## The Golden Rule of Hackathon Winners

> Judges don't remember architecture diagrams.
> They remember **the moment they felt something.**
>
> Your job is to create THREE emotional beats:
> 1. A problem they feel in their gut
> 2. A moment where the AI does something unexpectedly smart
> 3. A number that makes them lean forward

---

## Pre-Demo Setup (Critical)

### Screen Layout During Demo
```
┌─────────────────────────────────────────────────┐
│  LEFT 60%              │  RIGHT 40%             │
│                        │                        │
│  Agent Reasoning       │  Ring Visualization    │
│  Stream (terminal      │  (PyVis graph,         │
│  style, real-time)     │  hidden until Beat 2)  │
│                        │                        │
│  Dark background       │  Dark background       │
│  Green/amber text      │  Nodes appear live     │
│  Typing effect         │                        │
│                        │                        │
│                        │  ┌──────────────────┐  │
│                        │  │  TIMER: 00:00    │  │
│                        │  │  (counting up)   │  │
│                        │  └──────────────────┘  │
└─────────────────────────────────────────────────┘
```

### What Must Be Ready
- [ ] Cached hero case path (live LLM calls, but tool outputs pre-warmed so it's fast)
- [ ] Timer widget visible on screen (starts when investigation begins)
- [ ] Ring visualization loads hidden, reveals on cue
- [ ] Dossier renders in a clean formatted panel
- [ ] One backup recording of the full run in case of catastrophic failure
- [ ] All team members know exactly when they speak (if co-presenting)

---

## The Script — 6 Minutes Total

---

### ACT 1: THE PROBLEM (0:00–0:45)
**Goal:** Make them care. Don't educate. Make them *feel* the problem.

> **[SLIDE: Black screen. Single stat.]**
>
> "$100 billion."
>
> "That's how much healthcare fraud costs the US every year.
> More than the GDP of most countries. And here's the thing —
> we're actually pretty good at *flagging* suspicious claims.
> The algorithms work. The models work."
>
> **[SLIDE: Screenshot of a typical fraud alert dashboard — a wall of 500 alerts]**
>
> "But a flag is not an investigation."
>
> "This is what a fraud analyst sees Monday morning. 500 alerts.
> Each one takes 2 to 4 hours to investigate manually.
> Pull the claims. Check the billing codes. Compare to peers.
> Map the connections. Write the case file. Cite the regulations."
>
> **[Pause. Let it sink in.]**
>
> "Most of these alerts die in a queue. Not because they're not real —
> because there aren't enough humans."
>
> "We built the humans."

**Why this works:** You didn't explain fraud. You made them feel the bottleneck.
Senior data+AI people already know about models. They know the *real* problem
is what happens after the model flags something.

---

### ACT 2: THE TEAM — NOT THE TECH (0:45–1:15)
**Goal:** 30 seconds max. Frame agents as *people*, not software.

> "Three AI agents. Not a pipeline. A team."
>
> **[SLIDE: Three cards side by side — no diagram, just roles]**
>
> ```
> ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
> │  THE LEAD        │  │  THE DETECTIVE   │  │  THE CASE WRITER│
> │                  │  │                  │  │                 │
> │  Decides what    │  │  Scans claims    │  │  Compiles the   │
> │  to investigate  │  │  Profiles        │  │  case file      │
> │  and how deep    │  │  entities        │  │                 │
> │  to go           │  │  Maps networks   │  │  AND PUSHES     │
> │                  │  │  Finds rings     │  │  BACK if the    │
> │  Delegates.      │  │                  │  │  evidence is    │
> │  Adapts.         │  │  Does the work.  │  │  weak.          │
> │  Stops when done.│  │                  │  │                 │
> └─────────────────┘  └─────────────────┘  └─────────────────┘
> ```
>
> "The Lead decides what to investigate. The Detective does the digging.
> The Case Writer compiles the evidence — but won't sign off on a
> weak case. If the evidence isn't there, she sends the detective
> back for more."
>
> "Let me show you."

**Why this works:** You humanized the agents. Judges now think of them
as a team, not code. The "pushes back" line is foreshadowing — it pays off
in Beat 3.

---

### ACT 3: THE LIVE INVESTIGATION (1:15–4:15)
**Goal:** Three emotional beats. This is the core of your demo.

> "I'm going to hit one button. A new batch of claims just came in.
> Watch what happens."
>
> **[Click. Timer starts. Agent stream begins on screen.]**

---

#### BEAT 1 — DISCOVERY (1:15–1:45) 🎯
**The hook: AI finds the needle in the haystack.**

Let the agent stream show:
```
🤖 ORCHESTRATOR: New claims batch received. Scanning for anomalies...

🔍 DETECTIVE: Scanned 847 claims. 23 flagged.
   Top hit: Provider P-4482 — Orthopedic Surgeon
   Anomaly score: 0.92
   Signal: Upcoding on knee procedures
   Billed $487K in 90 days — peers average $142K
```

> **[You narrate over the stream]**
>
> "23 flags. But watch — the Lead doesn't investigate all 23.
> It *reasons* about which one matters most."

```
🤖 ORCHESTRATOR: P-4482 has the highest anomaly score and the
   largest dollar exposure. But before I escalate, I want to
   check — is this isolated, or connected to something bigger?
   → Sending Detective to map connections.
```

> "It's already thinking like an investigator. Not just sorting by score.
> Asking: is this part of something *bigger*?"

---

#### BEAT 2 — THE RING (1:45–2:45) 🎯🎯
**The wow moment: It discovers a conspiracy.**

```
🔍 DETECTIVE: P-4482 connected to 3 referring providers.
   P-1190, P-3387, P-5521.
   12 shared patients.
   Referral concentration: 78% (expected: 18%)
   Combined suspicious billing: $2.3 million.
```

> **[RIGHT PANEL: Ring visualization fades in. Nodes appear one by one.
> Red nodes for providers. Blue for patients. Lines connecting them.
> Dollar amounts on edges.]**

> **[Point at the screen]**
>
> "It found one suspicious bill. It pulled the thread. And it uncovered
> four doctors funneling patients to each other to overbill $2.3 million."

```
🤖 ORCHESTRATOR: This is not an individual case. This is a coordinated
   ring. Escalating priority. Sending to Case Writer for dossier.
```

> "Now watch what happens next. This is my favorite part."

---

#### BEAT 3 — THE PUSHBACK (2:45–3:45) 🎯🎯🎯
**THE moment that wins you the hackathon. Rehearse this 10 times.**

```
📋 CASE WRITER: I have the billing data and the ring structure.
   But the referral concentration alone is circumstantial.

   ⚠️ EVIDENCE ASSESSMENT: INSUFFICIENT

   MISSING: Historical referral data. I need to see that these
   referring providers CHANGED their behavior. If they always
   referred to P-4482, this could be a legitimate practice
   relationship.

   I will not compile this dossier until I see the evidence.
```

> **[PAUSE. 2 full seconds. Let the audience read it.]**
>
> "The Case Writer just refused to write the report."
>
> **[Let that land.]**
>
> "She's not being difficult. She's being *rigorous*. A human
> investigator would ask the same question — did this pattern
> *change*, or was it always like this?"

```
🤖 ORCHESTRATOR: Valid concern. Sending Detective back for
   18-month referral history.

🔍 DETECTIVE: Confirmed. All three referring providers shifted
   referral patterns 8 months ago.
   Before: distributed across 6-8 surgeons.
   After: 78% concentrated on P-4482.
   Shift was sudden. And synchronized.

📋 CASE WRITER: ✅ EVIDENCE ASSESSMENT: SUFFICIENT
   Confidence: HIGH
   Compiling dossier...
```

> "Synchronized shift. 8 months ago. Three doctors all changed
> behavior at the same time. That's not coincidence.
> That's coordination. *Now* she writes the case."

**Why Beat 3 wins:** Every other team at this hackathon will show an AI
that produces output. You're showing an AI that *refuses to produce output*
until the evidence is right. That's the difference between a pipeline
and an agent. Judges will remember this.

---

#### TIMER CHECK
> **[Glance at timer. It should read ~60-90 seconds.]**
>
> "By the way — look at the clock."

---

### ACT 4: THE DOSSIER (3:45–4:30)
**Goal:** Show the output is real, professional, actionable.

> **[Switch to dossier view. Scroll slowly.]**

> "Complete investigation dossier."

**Don't read the whole thing. Hit these 4 lines only:**

> "Executive summary. Four providers. Twelve patients. Forty-seven claims."
>
> **[Scroll]**
>
> "Statistical comparison — every metric compared to peers with z-scores."
>
> **[Scroll]**
>
> "Billing rule citations — specific CMS sections that were violated."
>
> **[Scroll to bottom]**
>
> "Estimated recovery: $252,600. And recommended actions:
> request operative notes, issue pre-payment hold, refer to
> the Special Investigations Unit for Anti-Kickback review."
>
> "This isn't a summary. This is a case file an investigator
> can act on *today*."

---

### ACT 5: THE SECOND CASE — LEGITIMACY (4:30–5:00)
**Goal:** Prove it's not a fraud-confirmation machine. 30 seconds.**

> "But here's the thing — not every flag is fraud."
>
> **[Trigger second case — pre-cached. Show just the conclusion.]**

```
🤖 ORCHESTRATOR: Provider P-2891 flagged for high billing volume.
   Detective investigated. Volume is high but consistent with
   peer group for trauma surgery in urban setting.
   No referral anomalies. No coding irregularities.

   ASSESSMENT: Legitimate practice pattern. Closing investigation.
   No case generated.
```

> "It investigated. It looked at the evidence. And it walked away.
> That's not a model. That's judgment."

**Why this matters:** This is the answer to the obvious judge question
"what about false positives?" You answered it before they asked.

---

### ACT 6: THE CLOSE (5:00–5:45)
**Goal:** One killer line they remember at judging.**

> "Every tool in healthcare fraud is designed to find the needle
> in the haystack."
>
> **[Pause]**
>
> "We built the investigator who picks up the needle, follows the thread,
> discovers three more needles connected to it, writes the case,
> and tells you exactly what to do about it."
>
> **[SLIDE: Side by side]**
>
> ```
>  BEFORE                          AFTER
>  ──────                          ─────
>  500 alerts in a queue           Prioritized, investigated, documented
>  2-4 hours per case              90 seconds
>  Analyst writes the report       Agent writes, analyst reviews
>  Ring schemes missed             Rings discovered automatically
>  Evidence gaps found in court    Evidence gaps found by the AI itself
> ```
>
> "From suspicious bill to complete case file. Three agents.
> Ninety seconds."

**[Done. Stop talking. Don't over-explain.]**

---

## Q&A Prep — The 8 Questions Judges Will Ask

| Question | Your Answer |
|----------|-------------|
| "How is this different from existing fraud detection?" | "Existing tools flag. We investigate. The flag is step 1 of 10. We do steps 1 through 10." |
| "Is this real data?" | "Synthetic, modeled on CMS Medicare public data. The patterns are realistic. The agent behavior is identical on real data — it's tool-agnostic." |
| "What about false positives?" | "You saw it — the agent investigated P-2891 and walked away. It's not a confirmation machine. It applies judgment." |
| "What LLM are you using?" | "Claude 3.5 Haiku via Bedrock. Fast, cheap, reliable. Full investigation costs about 12 cents in tokens." (Have the number ready) |
| "How does it scale?" | "Each investigation is independent. You can run 50 in parallel. The bottleneck was never compute — it was human analysts." |
| "What's the human role?" | "Review and approve. The agent does the investigation. The human makes the final call. We compressed 4 hours of work into a 2-minute review." |
| "What if the agents hallucinate?" | "Every number in the dossier comes from tool calls, not generation. The LLM reasons and delegates. The tools return real data. The dossier cites specific claim IDs that can be verified." |
| "What's next?" | "Real claims integration, human-in-the-loop approval workflow, and expanding to pharmacy fraud patterns. The architecture is pattern-agnostic." |

---

## Rehearsal Schedule (Next 24 Hours)

| Time | Activity | Who |
|------|----------|-----|
| T-24h | Finalize cached demo path, test 3x | Dev 1 |
| T-24h | Build legitimate dismissal case | Dev 2 |
| T-24h | Polish UI — timer, streaming, visualization | Dev 3 |
| T-24h | Write slides, rehearse solo | Presenter |
| T-18h | Full team run-through #1 | All |
| T-18h | Fix whatever broke | Dev 1+3 |
| T-12h | Full team run-through #2 (record it) | All |
| T-12h | Watch recording, cut anything that drags | All |
| T-6h | Full dress rehearsal #3 (timed, no stops) | All |
| T-6h | Backup: record clean run as safety video | Dev 1 |
| T-2h | Final tech check on demo machine | Dev 1+3 |
| T-1h | Presenter warms up, team relaxes | All |

---

## The 5 Rules

1. **Never say "LangGraph" or "FAISS" or "NetworkX" during the demo.** Judges don't care. Say "our agents" and "our tools." Tech goes in Q&A only.
2. **The timer is your closer.** When it hits 90 seconds and the dossier appears, you win the room.
3. **Beat 3 (the pushback) is your signature moment.** If you rush it, you lose your differentiator.
4. **Stop talking when you're done.** Don't fill silence. Let the dossier sit on screen.
5. **If the live demo fails, show the recording without apology.** Say "let me show you the run we did earlier" and keep moving. Never debug on stage.