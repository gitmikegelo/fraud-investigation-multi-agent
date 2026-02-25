
# Claims Investigation Copilot — Full Demo Script
## The Actual Words You Say Out Loud

---

## Before You Start

- Take a breath
- Don't rush the opening
- You're not presenting a school project. You're showing something you built that actually works.
- Talk TO the judges, not AT the screen

---

## WHO SPEAKS WHEN

| Section | Speaker | Why |
|---------|---------|-----|
| Act 1: Problem + Architecture | Speaker A (strongest storyteller) | Sets the tone |
| Act 2: Live Demo (Beats 1-3) | Speaker B (built the agents) | Knows the system cold, can improvise if something unexpected happens |
| Act 3: Dossier + Legitimate Case | Speaker A | Brings it home |
| Act 4: Close | Speaker A | Bookends the story |
| Q&A | All 4 | Whoever knows the answer best takes it, no stepping on each other |

Speakers C and D: You're not silent. You're running the demo behind the scenes, 
ready to click, switch screens, or recover if something breaks. You answer 
technical questions in Q&A. This is not a demotion — this is how winning teams operate.

---

## ACT 1: THE PROBLEM (0:00 – 1:15)

**[SCREEN: Black. Nothing. You're standing in front of it.]**

**SPEAKER A:**

"So quick question — anyone here ever had a medical bill that made absolutely 
no sense?"

**[Pause. Let people chuckle or nod.]**

"Yeah. Now imagine you're the insurance company on the other end of that bill, 
and you're getting 10 million of them a month. Some of them are legitimate. 
Some of them are... creative."

"Healthcare fraud is a $100 billion a year problem in the US alone. And look — 
the industry isn't asleep. There are models. Good ones. Isolation forests, 
anomaly detection, the whole nine yards. They flag suspicious claims all day long."

**[SCREEN: Screenshot of a dense alert dashboard — 500+ rows of alerts]**

"This is what a fraud analyst sees on a Monday morning. Five hundred alerts. 
Each one is basically a Post-it note that says 'hey, this looks weird.' 
And then the actual work starts."

"You pull the claims. You check the billing codes. You look up the provider. 
You compare them to their peers. You check if they're connected to other 
suspicious providers. You look for patterns over time. You cross-reference 
CMS billing guidelines. Then you write a 3-page case file."

"That's 2 to 4 hours. Per alert. And there are 500 of them."

**[Beat.]**

"Most of these alerts? They die in a queue. Not because they're not real — 
because there literally aren't enough humans to look at them."

"So we asked a pretty simple question: what if we didn't build a better 
flag? What if we built the investigator?"

---

**[SCREEN: Three agent cards — Lead, Detective, Case Writer]**

"We built three AI agents. And I want to be clear — this is not a pipeline. 
There's no step 1, step 2, step 3. These agents talk to each other. They 
argue with each other. One of them is kind of a pain in the ass, honestly, 
and that's by design."

**[Point to each card:]**

"The Lead Investigator — decides what's worth looking into and how deep to go. 
Delegates everything. Does no actual work. So basically, management."

**[Pause for laugh.]**

"The Detective — does the actual digging. Scans claims, profiles providers, 
maps connections, finds fraud rings."

"And the Case Writer — compiles everything into a formal investigation dossier. 
But here's the thing about her. If the evidence is weak, she will refuse to 
write the report. She'll send the Detective back to get more. She has 
standards."

"Let me show you what this looks like."

---

## ACT 2: THE LIVE DEMO (1:15 – 4:00)

**[SCREEN: Demo UI. Agent reasoning stream on the left. Visualization panel 
on the right (empty for now). Timer in the corner.]**

**SPEAKER A:**
"I'm gonna hand this over to [Speaker B], who built the agent system. 
[B], take it away."

**SPEAKER B:**

"Alright. So we've got a batch of new claims that just came in. I'm going to 
do exactly one thing — click this button. Everything else you see from here 
is the agents deciding what to do."

**[Click. Timer starts at 00:00. Agent stream begins.]**

---

### BEAT 1 — DISCOVERY

**[Stream shows:]**
```
🤖 LEAD: New claims batch. Let me get the Detective to scan for anomalies.
   → Detective: scan latest claims for anomalies.

🔍 DETECTIVE: Scanned 847 claims. 23 flagged as anomalous.
   Top finding: Provider P-4482
   Specialty: Orthopedic Surgery
   Anomaly score: 0.92
   Primary signal: Suspected upcoding on knee procedures
   Billed $487K in 90 days — peer average is $142K
```

**SPEAKER B:**
"So right away — 847 claims, 23 flagged. But watch what the Lead does. It 
doesn't just go down the list. It's actually thinking about which one 
matters."

**[Stream continues:]**
```
🤖 LEAD: P-4482 has the highest anomaly score and the biggest dollar 
   exposure. But I don't want to jump to conclusions. Let me check — 
   is this person acting alone, or is there something bigger going on?
   → Detective: map connections for P-4482, depth 2
```

"See that? It's not just sorting by score. It's asking — is this the 
whole story, or is this the tip of something?"

---

### BEAT 2 — THE RING

**[Stream shows:]**
```
🔍 DETECTIVE: P-4482 has connections to 3 referring providers:
   P-1190 (Family Medicine), P-3387 (Internal Medicine), P-5521 (Pain Mgmt)
   12 shared patients across all four providers
   Referral concentration: 78% — expected for this peer group: 18%
   Combined suspicious billing: $2.3 million
   Network density: 4.2x normal
```

**[RIGHT PANEL: PyVis ring visualization fades in. Nodes appear. 
Red provider nodes. Blue patient nodes. Lines with dollar amounts.]**

**SPEAKER B:**
"Okay so this is where it gets interesting."

**[Stand up. Walk to screen. Point at the visualization.]**

"We started with one guy. One suspicious provider. The agent pulled the 
thread and found *this*. Four doctors. Twelve patients. And a referral 
pattern that makes no medical sense."

"These three family docs and internists are sending 78% of their knee 
patients to one specific surgeon. Their peers send maybe 18% to any 
single surgeon. That's a 4x concentration."

"Two point three million dollars in suspicious billing."

**[Stream continues:]**
```
🤖 LEAD: This is not an individual case. This is a coordinated referral 
   ring. Escalating to critical priority. 
   → Case Writer: compile investigation dossier for this ring.
```

"Lead just escalated it from 'one weird provider' to 'coordinated fraud 
ring.' On its own. Nobody told it to do that."

---

### BEAT 3 — THE PUSHBACK ⭐

**[This is the moment. Slow down. Don't talk over it.]**

**[Stream shows:]**
```
📋 CASE WRITER: Reviewing evidence package.

   I have billing data for P-4482 and the ring structure. The referral 
   concentration is striking. However...

   ⚠️ EVIDENCE ASSESSMENT: INSUFFICIENT

   The referral concentration alone is circumstantial. I need to see 
   HISTORICAL referral patterns for these three referring providers. 
   If they have ALWAYS referred heavily to P-4482, this could be a 
   legitimate long-standing practice relationship.

   I need to see that this pattern CHANGED. Without temporal evidence, 
   I cannot compile a defensible case file.

   Requesting: 18-month referral history for P-1190, P-3387, P-5521.
```

**[PAUSE. Let the judges read it. Full 3 seconds of silence.]**

**SPEAKER B:**
"She said no."

**[Another beat.]**

"The Case Writer just looked at $2.3 million in suspicious billing and said 
'I'm not writing this up yet. The evidence isn't good enough.'"

"And honestly? She's right. If you took this to a real investigator and said 
'these doctors refer to each other a lot,' they'd say 'okay, maybe they're 
in the same practice. Maybe they went to med school together. Show me that 
something *changed*.'"

"That's what she's asking for. So watch — the Lead listens."

**[Stream continues:]**
```
🤖 LEAD: Fair point. We need temporal evidence to confirm a pattern shift.
   → Detective: pull 18-month referral history for P-1190, P-3387, P-5521

🔍 DETECTIVE: Referral history retrieved.
   All three providers show a sudden, synchronized shift approximately 
   8 months ago.
   
   BEFORE (18-8 months ago):
   - Referrals distributed across 6-8 orthopedic surgeons
   - No single surgeon received more than 15%
   
   AFTER (last 8 months):
   - 78% of referrals concentrated on P-4482
   - Other surgeons dropped from rotation almost entirely
   - Change was abrupt — not gradual
   - All three providers shifted within the same 3-week window
```

**SPEAKER B:**
"Three doctors. Same 3-week window. All suddenly sending their patients to 
the same surgeon. That's not a coincidence. That's a phone call."

**[Stream continues:]**
```
📋 CASE WRITER: Updated evidence reviewed.

   ✅ EVIDENCE ASSESSMENT: SUFFICIENT
   Confidence: HIGH

   The synchronized referral shift confirms coordinated behavior change.
   Compiling dossier now.
```

"*Now* she writes it."

**[Glance at timer.]**

"Check the clock, by the way."

**[Timer should read somewhere around 60-90 seconds.]**

---

## ACT 3: THE DOSSIER + LEGITIMATE CASE (4:00 – 5:15)

**SPEAKER A takes back over.**

**[SCREEN: Dossier view — clean, formatted document]**

**SPEAKER A:**
"So what came out the other end? A full investigation dossier."

**[Scroll slowly. Don't read everything. Hit the highlights:]**

"Executive summary — four providers, twelve patients, forty-seven flagged 
claims, coordinated referral ring with upcoding."

**[Scroll]**

"Every provider compared to their peer group with z-scores. P-4482 billing 
3.7 standard deviations above peer average. That's not a rounding error."

**[Scroll]**

"Specific CMS billing rule citations — these aren't made up. They're 
pulled from actual guidelines."

**[Scroll to bottom]**

"Estimated recovery: $252,600. And here are the recommended next steps: 
request operative notes for the flagged procedures, issue a pre-payment 
hold on new claims from P-4482, and refer the referral pattern to the 
Special Investigations Unit for potential Anti-Kickback Statute violations."

"This isn't a dashboard. This isn't an alert. This is a case file that 
an investigator can pick up and act on this afternoon."

---

**[Quick transition]**

"But here's a question you should be asking — does it flag everything 
as fraud? Because a system that sees fraud everywhere is useless."

**[SCREEN: Second case — pre-loaded, show just the conclusion]**

```
🤖 LEAD: Provider P-2891 flagged for high billing volume. 
   Sending Detective to investigate.

🔍 DETECTIVE: P-2891 is a trauma surgeon at a Level 1 trauma center 
   in Houston. High volume is consistent with facility type and 
   peer group. No referral anomalies. No coding irregularities. 
   Weekend billing is high but expected for trauma.

🤖 LEAD: This is a legitimate high-volume practice. Pattern is 
   consistent with peers in the same setting. 
   
   CLOSING INVESTIGATION. No case generated.
```

"It looked at it. It checked the data. And it said 'this person is fine. 
Leave them alone.'"

"Because an investigation tool that can't clear the innocent is just a 
witch hunt with a nice UI."

---

## ACT 4: THE CLOSE (5:15 – 5:45)

**[SCREEN: Side by side comparison]**

```
BEFORE                              AFTER
───────                             ──────
500 alerts in a Monday queue        Prioritized, investigated, closed or escalated
2-4 hours per investigation         90 seconds  
Analyst writes the case file        Agent writes, analyst reviews and approves
Ring schemes buried in noise        Rings discovered and mapped automatically
Evidence gaps found in court        Evidence gaps found by the agent itself
```

**SPEAKER A:**

"We didn't build a better fraud scorer. There are plenty of those. 
We built the thing that happens *after* the score."

"Three agents. One investigates. One writes the case. And one refuses 
to cut corners."

"From a suspicious bill to a complete case file in ninety seconds."

"Thanks."

**[Stop. Don't add anything. Don't say "and that's our project" or 
"so yeah." Just stop. Silence is confidence.]**

---

## Q&A — ANSWER BANK

**Keep every answer under 20 seconds. Judges hate rambling.**

---

**"How is this different from what's already out there?"**

> "Everything out there stops at the flag. We start at the flag. The 
> investigation — pulling claims, profiling providers, mapping 
> connections, comparing to peers, writing the case — that's all 
> manual work today. We automated the entire workflow, not just 
> the detection."

---

**"Is this real data?"**

> "Synthetic, but modeled on CMS Medicare public datasets. Realistic 
> distributions, realistic fraud patterns. The agent behavior is 
> identical regardless of the data source — it's calling tools that 
> query whatever data you point them at."

---

**"What model are you using?"**

> "Claude 3.5 Haiku through AWS Bedrock. And the full investigation 
> you just saw — including all the back-and-forth between agents — 
> cost about 12 cents in API calls."
>
> [If they seem impressed:] "Yeah. Twelve cents to investigate a 
> $2.3 million fraud ring. The ROI math is kind of silly."

---

**"What if it hallucinates?"**

> "Great question. The LLM never generates data. It reasons and 
> delegates. Every number in that dossier came from a tool call — 
> a pandas query, a model score, a graph traversal. The claim IDs 
> are real claim IDs from the database. You can trace every number 
> back to its source. The LLM decides what to ask for. The tools 
> provide the answers."

---

**"What about false positives?"**

> "You saw it. P-2891 — flagged, investigated, cleared. The system 
> isn't designed to confirm fraud. It's designed to investigate and 
> reach a conclusion. Sometimes that conclusion is 'nothing here.'"

---

**"What's the human's role?"**

> "Review and approve. The agent compresses a 4-hour investigation 
> into 90 seconds of work product. The analyst reads the dossier, 
> checks the evidence, and makes the call. We didn't remove the 
> human. We gave them their afternoon back."

---

**"Why three agents instead of one?"**

> "Separation of concerns. The investigator has a bias toward finding 
> things — that's their job. The case writer has a bias toward 
> rigor — that's their job. By separating them, we get a natural 
> check and balance. You saw it — the case writer pushed back on 
> the investigator's findings. One agent wouldn't argue with itself."

---

**"Could this work on real claims data?"**

> "The tools are just Python functions that query dataframes. Swap 
> the dataframe for a database connection and it works the same way. 
> The agent layer doesn't care where the data lives."

---

**"How does it handle edge cases / novel fraud patterns?"**

> "The anomaly detection is unsupervised — Isolation Forest — so it 
> catches things that are statistically unusual, not just known 
> patterns. The agents then investigate to determine if the anomaly 
> is actually fraud or just unusual. That's the whole point of 
> having the investigation step — a model can't tell you *why* 
> something is anomalous. The agents figure out the why."

---

**"What's next?"**

> "Three things. Real claims data integration with a health plan 
> partner. A human-in-the-loop approval workflow so investigators 
> can accept, reject, or request more on any case. And expanding 
> the pattern library — pharmacy fraud, durable medical equipment 
> schemes. The architecture is pattern-agnostic."

---

## EMERGENCY PROTOCOLS

### If the live demo freezes or crashes:

**SPEAKER B:** "Alright, the demo gods are not with us today — let me 
show you the run we recorded earlier, same system, same data."

**[Switch to backup video. Do NOT apologize more than once. Do NOT 
try to debug on stage. Move on immediately.]**

### If an agent does something unexpected:

This is actually GOOD. Lean into it.

**SPEAKER B:** "Okay, interesting — it's going a different direction 
than last time. That's actually the point — it's not a script, it's 
reasoning in real time. Let's see where it goes."

### If a judge asks something you don't know:

"Honestly, I don't know. That's a great question and I'd love to 
dig into it after. What I can tell you is [pivot to something you 
DO know]."

**Never bullshit. Judges can tell. "I don't know" said confidently 
is 10x better than a rambling guess.**

---

## FINAL NOTES

### Energy Management
- Speaker A: Warm and confident. You're telling a story.
- Speaker B: Technical and genuine. You built this thing and you're 
  proud of it but not cocky about it.
- Nobody should sound like they're reading. If you catch yourself 
  reciting memorized lines, stop and just *talk*.

### The Three Things Judges Will Remember
1. The pushback moment (the Case Writer saying no)
2. The timer (90 seconds)
3. The ring visualization (the picture)

Everything else is in service of those three moments. If you nail 
those three, you're in the finals.

### The One Thing That Will Lose You Points
Overexplaining. If you see eyes glazing, skip ahead. The demo speaks 
for itself. Trust it.

---

Good luck. You built something real. Now go show it off.
