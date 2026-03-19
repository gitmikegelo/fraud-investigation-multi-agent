# Claims Copilot — Prudential Executive Demo Script
### Two Cases. Real Pain. Real Answers.

**Audience:** C-Suite / VP of Claims / Chief Actuary / Head of SIU  
**Duration:** 20–25 minutes  
**Systems Running:** Backend on `localhost:8000` · Frontend on `localhost:5173`

---

> **Presenter mindset before you walk in:**  
> You are not selling software. You are showing them a problem they already have — and the answer to it. Let the system speak. The silence after a reveal is your most powerful moment. Don't fill it.

---

## THE OPENING — 90 Seconds. No Slides.

Walk in. Stand still. Let the room settle.

---

> **"Every morning, your examiners open a queue. Each one sees somewhere between 0 and 20 claims
> They have no idea which ones are real.
> They open Prudential 360. They toggle to Power BI. They check FIS/PAS. They reference Compass.
> Ten minutes later — they've reviewed one claim.
> And the wellness claims? Those never reach an examiner.
> They auto-adjudicate. The money's already gone."**

Pause. Let that last line sit.

> **"Today I'm going to show you two things that happened in your claims data this week.
> One you might catch eventually.
> One you would never see coming.
> Let me show you."**

Open the browser. Full screen. Queue visible.

---

---

# CASE ONE — "The 35 Ghost Dependents"
### WC-247 · Risk Score: 🔴 94 · Wellness Claim · Flagged Before Auto-Adjudication

---

## ACT 1 — The Queue (60 seconds)

*[The queue is visible — date tab on "Today", risk chips visible.]*

> **"This is the morning queue. Around 10 claims today — an examiner's personal slice of the shared pool.
> Already sorted. Not by timestamp — by risk. The system ran overnight analysis on every single one.**
>
> **WC-247. Risk score: 74.1 out of 100. HIGH tier.**
> **This would have auto-adjudicated. It didn't.**
> **Here's why."**

*[Click WC-247. Claim detail opens.]*

---

## ACT 2 — The Copilot Conversation (4 minutes)

*[Copilot panel on the right. Checklist begins auto-loading.]*

> **"Before I show you what the system found, I want you to see HOW it works.
> This is the Copilot. It's not a search bar.
> It's an examiner's second brain — one that has read every policy rule,
> every fraud case, and every filing this member has ever made."**

**Type into Copilot:**
> `"Why was WC-247 flagged?"`

*[Response streams back.]*

> **"There it is. Rule R-001: Dependent Spike.**
> **Member MBR-0247 has 35 dependents enrolled.**
> **Standard threshold is 10. They have 35."**

Pause. Let that number register.

> **"And look at the claim amount.**
> **$12,500. The average claim in this pool is $341.**
> **This claim is 36.6 times normal.**

> **Then there's this: the policy type is Accident.
> The claim type is Wellness.
> They're filing a Wellness claim under an Accident policy.**

> **That's not a mistake.
> That's a script."**

**Type into Copilot:**
> `"What's the total exposure if this had paid out?"`

*[Response streams: $12,500 current claim + $11,951 dependent exposure = $24,451 base. If fraudulent at 2–3x multiplier: $73,355. Plus $5,500–$12,500 in investigative and legal costs.]*

> **"$24,451 base exposure. Up to $73,355 if the ring fully executes.**
> **Plus investigation and legal costs on top.**

> **And that's one claim. One member. One morning.**

> **At this rate, if one person in your book discovered this playbook,
> you're looking at ring behavior scaling across your employer groups —
> and your wellness auto-adjudication has no pre-pay scoring whatsoever.**

> **This claim was stopped. The next 50 might not be."**

---

## ACT 3 — The Network in the Copilot (2 minutes)

**Type into Copilot:**
> `"Are there other members or dependents connected to this case?"`

*[Response surfaces shared-address dependents, cross-claim matches.]*

> **"The system didn't just flag the claim.
> It traced the network — right here, in plain English.**

> **Multiple dependents sharing the same address.
> Dependent IDs that appear on a separate claim — filed by a different member
> at a different employer.**

> **They're related. This is a ring.**

> **One examiner, opening one claim in one tab, would never see that.
> The Copilot sees the entire book simultaneously."**

---

## ACT 4 — The Dossier (90 seconds)

*[Click "Generate Dossier" button.]*

> **"In a normal workflow, if your examiner caught this,
> they'd spend 45 minutes writing up the evidence package —
> pulling screenshots, drafting the timeline, summarizing the rules.**

> **Watch this."**

*[95-second autonomous generation. Progress indicators animate.]*

> **"Done. 95 seconds.**
> **Timeline, evidence summary, rules violated, network diagram, dollar exposure,
> recommended action — all pre-formatted for your Legal and SIU teams.**

> **The examiner didn't write a single word.
> They reviewed it. They hit 'Approve for Escalation'.**
> **That's the workflow."**

---

*[Pause. Let the room absorb.]*

> **"That's Case One. Simple fraud. Brute force. Stopped before payment.**

> **Case Two is different. Case Two is someone who read your policy manual."**

---
---

# CASE TWO — "The Day-After Game"
### HI-089 · Risk Score: 🟡 71 · Hospital Indemnity · Policy Change Exploit

---

## ACT 1 — The Setup (60 seconds)

*[Return to queue. Click HI-089.]*

> **"This is a Hospital Indemnity claim. Risk score 71 — Medium.**
> **On the surface, nothing unusual.**
> **Outpatient surgical repair. Provider is real. Diagnosis is legitimate.
> Documentation is complete.**

> **Most examiners would approve this in under three minutes.**

> **But the system flagged it under Rule R-014.**
> **Let me show you why."**

---

## ACT 2 — The Policy Intelligence Layer (3 minutes)

**Type into Copilot:**
> `"Why was HI-089 flagged? Focus on policy changes."`

*[Response streams in, citing PA-001.]*

> **"Policy Alert PA-001.**
> **Effective September 18th, 2025.**
> **Surgical repair is now covered under Hospital Indemnity
> regardless of inpatient confinement —
> outpatient surgery now qualifies."**

> **"This claim was filed…"**

*[Point to the date on screen.]*

> **"September 19th."**

Pause. Let the room do the math.

> **"One day after the policy change.**

> **Coincidence? Maybe.**
> **Now let me show you who else filed this week."**

---

## ACT 3 — The Pattern Reveal (3 minutes)

**Type into Copilot:**
> `"Are there other claims that match this pattern — same employer group, same claim type, filed in the 7 days after PA-001?"`

*[Response: 3 additional claims — HI-091, HI-094, HI-097. Same employer group. Same claim type. Filed September 19–23.]*

> **"Four claims. Same employer. Same claim type. Same 5-day window.**
> **Filed within 120 hours of a policy change
> that most policyholders didn't even know existed yet.**

> **This is insider-timing fraud.**
> **Someone in that employer group — or someone advising that group —
> read your policy update bulletin before the ink was dry."**

**Type into Copilot:**
> `"What are the document analysis results for these four claims?"`

*[Response: HI-089 — mixed font detected in medical record (DOC-001). HI-091 — typed date over handwritten content (DOC-003). HI-094 — Word document submitted instead of PDF (DOC-007). HI-097 — records arrived via email to examiner's inbox, not through the portal (DOC-013).]*

> **"Now we have four claims, filed in a 5-day window, after a policy change,
> each with independent document anomalies.**

> **Individually? Any one of these gets through.
> Together? This is a referral."**

---

## ACT 4 — The Escalation Package (90 seconds)

*[Click "Generate Dossier" for HI-089 group.]*

> **"The system just built the package your Legal team needs.**
> **Four claims. Coordinated timeline. Document integrity findings.
> Rule violations. Employer group cross-reference.**
> **Recommended action: Pend all four. Request original records from provider directly.
> Notify SIU."**

> **"This took 90 seconds to produce.**
> **And your examiner — who was about to approve HI-089 in three minutes —
> just escalated a four-claim fraud ring."**

---
---

# THE CLOSE — 3 Minutes. No Hedging.

*[Close the browser. Stand up. Face the room.]*

---

> **"Let me tell you what just happened.**

> **Case One: brute-force dependent fabrication.
> Caught before a single dollar was paid.
> Under any other workflow — it auto-adjudicates and you never know.**

> **Case Two: sophisticated policy-timing exploit.
> Four claims filed by people who knew your coverage changed
> before your examiners did.
> Caught because the system reads every claim, every rule, and every policy alert — simultaneously.**

> **Your examiners are not the problem.
> They're working in a system designed for a world
> where fraud was simpler and slower.**
> **That world is gone."**

Pause.

> **"Here is what we are replacing:**

> **Ten tabs → one workspace.**
> **45-minute report writing → 90-second dossier.**
> **One claim reviewed at a time → 500 claims analyzed overnight.**
> **Zero pre-pay fraud scoring → every wellness claim scored before auto-adjudication.**

> **The Copilot doesn't make the call. Your examiner does.**  
> **That never changes. The AI surfaces the truth.
> The human decides what to do with it.**

> **That's not just a better tool.**
> **That's a better defense."**

---

### THE ASK

> **"We can have this running against your real claims environment
> — read-only, no system changes, no integration risk —
> in four weeks.**

> **Four weeks from today, your SIU lead sees a queue like the one I just showed you.
> Real claims. Real flags. Real answers.**

> **If it doesn't change the way your team works,
> you walk away. Zero obligation.**

> **If it does — and it will —
> we talk about what full deployment looks like."**

---

---

## ANTICIPATED QUESTIONS — AND HOW TO ANSWER THEM

**Q: "How is this different from what our current rules engine already does?"**
> "Your current rules engine fires a banner. It tells examiners something might be wrong.
> It doesn't tell them what, why, or what to do next.
> And it applies zero network analysis — it looks at one claim at a time.
> This system looks at 500 claims simultaneously and connects the dots across them.
> That's the difference between a smoke detector and a fire marshal."

**Q: "What about false positives? We don't want examiners investigating legitimate claims."**
> "This is the exact right question — and the brochure documents four real false positives we handle correctly.
> A new employee with a genuine accident filed 60 days after policy start — cleared.
> A rural clinic submitting B&W scans because their scanner is from 2005 — cleared.
> A member who called four times because her claim was genuinely complicated — cleared.
> The system distinguishes bad timing from bad intent.
> When in doubt, it surfaces the evidence and lets the examiner decide.
> The examiner always has the final word."

**Q: "How does it integrate with our existing systems?"**
> "The Copilot reads from your existing data through a read-only API layer.
> No rip-and-replace. No changes to Prudential 360, FIS/PAS, or Compass.
> We sit on top. The queue you saw IS your claims queue — just with intelligence applied to it."

**Q: "Is this AI making decisions?"**
> "No. Full stop. The determination is always manual.
> What the AI does is preparation — it reads the file, checks the rules, checks the network,
> checks the documents, and puts the evidence in front of the examiner in plain English.
> The examiner approves, denies, pends, or escalates. Every time. No exceptions."

**Q: "What's the ROI?"**
> "We're cautious about projections without your actual numbers.
> What the benchmark data shows: mature carriers using AI-assisted review
> intercept 40% more fraud than rules-only systems,
> reduce average case time by 85%,
> and process 3x more claims per examiner per week.
> But the number I'd ask your SIU lead: how much did you pay out to wellness claims
> last year before any fraud screening was applied?
> That number is your baseline. And right now, it has a floor of zero."

---

## TECHNICAL APPENDIX — If Asked to Go Deeper

| Layer | What It Does | Why It Matters |
|---|---|---|
| Rules Engine (L1) | 15 deterministic rules fire at intake | Catches known patterns instantly — no ML needed |
| Risk Scoring (L2) | 7-category composite score, 0–100 | Every claim ranked; wellness claims scored BEFORE auto-adj |
| Entity Graph (L3) | NetworkX graph — shared addresses, provider clusters, dependent rings | Sees fraud rings one claim at a time is blind to |
| Document Analysis | 13 checks — fonts, metadata, format, origin | Catches tampering without needing forensics lab |
| Copilot Agent | LangGraph + AWS Bedrock Claude — 16 tools | Natural language investigation; no system-switching |
| Dossier Generator | Autonomous 5-step evidence pipeline | SIU-ready package in 90 seconds |

**The examiner was toggling 5 systems to answer 3 questions per claim.**  
**This system answers 50 questions in the time it used to take to answer 3.**

---

*Claims Copilot · Built for Prudential Supplemental Health · March 2026*  
*"The determination is always yours."*
