

# Claims Copilot
### Your AI-Powered Partner for Supplemental Health Claims

---

*Built for the people who actually work the claims.*

---

## What Is Claims Copilot?

Imagine starting your morning and instead of logging into five different systems, toggling between screens, and manually checking eligibility — everything you need is already in front of you.

Claims Copilot is a single workspace that brings together your eligibility checks, fraud screening, policy rules, PMR and CBR tracking, and document review — all in one place. It learns the patterns you'd catch if you had unlimited time, and puts them right where you need them.

It's not here to replace your judgment. It's here to make sure you never miss something because you were buried in tabs.

---

## What Does Your Day Look Like With Claims Copilot?

### Before

> *"I check eligibility in one system, pull up the policy in another, cross-reference state rules in a third, then go back to check if there's an open PMR. By the time I'm done with setup, I've spent 10 minutes and haven't even started reviewing the claim."*

### After

You open Claims Copilot. Your queue is ready. Every claim is scored, your open tasks are visible, and when you click into a claim, you can ask the AI copilot a plain-English question like:

> *"Is this member eligible?"*

And get back a clear answer — with the policy details, coverage confirmation, and any issues — in seconds.

---

## The Claims Queue: Your Morning View

When you log in, you see all your claims in one sortable list. Not just the flagged ones — **all of them**.

Each claim shows you at a glance:

- ✅ **Claim type** — Wellness, Accident, Hospital Indemnity, or Critical Illness
- 🔴🟡⚪ **Risk level** — High, Medium, or Low, so you know where to focus
- 🚩 **Why it was flagged** — in plain language, not codes
- 📋 **Open tasks** — PMR due dates, pending CBRs, TAT warnings

You pick what to work first. The platform helps you prioritize, but you're in the driver's seat.

---

## The Copilot: Like Having a Second Set of Eyes

Click into any claim and you're in a conversation with your AI copilot. It's powered by a large language model — the same kind of technology behind ChatGPT — but trained on how supplemental health claims work. Think of it as a really well-informed colleague sitting next to you who's already read the file and knows the policy rules.

**You can ask it anything in plain English:**

- *"Why was this flagged?"*
- *"Show me this member's family claims for the last 100 days."*
- *"Are there any policy changes I should know about?"*
- *"Does this claim match the coverage terms?"*
- *"What state rules apply here?"*
- *"What am I missing? Could this be legitimate?"*

That last question is important. The copilot doesn't just look for problems — it also tells you when something that *looks* suspicious might actually be fine. A blended family adding six dependents after a marriage? That's not fraud. The AI understands context and will tell you.

**You'll also see quick-action buttons** tailored to the claim type you're working, so you don't have to type everything out:

| Claim Type | Quick Actions Available |
|---|---|
| **Wellness** | Dependent Check, Claim History, Auto-Adjudication Review |
| **Accident** | Match to Policy, Accident Details, State Rules |
| **Hospital Indemnity** | Admission/Discharge, Provider Check, Policy Terms |
| **Critical Illness** | Medical Records, Document Analysis, Policy Check |

---

## The Investigation Checklist: Your Process, Automated

For flagged claims, the AI copilot can walk through a 7-step investigation — the same steps you'd do manually, but faster and documented automatically.

| Step | What Happens |
|---|---|
| **1. Initial Review** | Is the claim form complete? Submitted through proper channels? |
| **2. Eligibility** | Policy active? Member verified? Benefit type covered? |
| **3. Fraud Screening** | Any rules triggered? What's the risk score? Document issues? |
| **4. Family & Patterns** | What has this member and their dependents filed recently? Anything unusual? |
| **5. Medical Records** | Do the documents look right? Provider legitimate? Diagnosis match the benefit? |
| **6. Policy Terms** | Which state rules apply? Any exclusions? Any recent policy changes? |
| **7. Your Call** | Approve, deny, pend, or escalate — with everything documented for you |

If a step passes cleanly, it turns green and moves on. If something needs your attention, it turns yellow or red and the AI tells you exactly what to look at and why.

You can run the whole checklist at once, or take it one step at a time. Either way, every finding is captured for your records.

---

## What the Platform Catches (That's Hard to Spot Manually)

Here's the thing about fraud — the really sophisticated patterns don't show up when you're looking at one claim at a time. Claims Copilot connects the dots across your entire book.

**Some real examples from the prototype:**

🚩 **The 35 Dependents**
A member adds 35 dependents in two weeks and files a wellness claim for each one — all at exactly $100, the benefit maximum. Individually, each claim looks like a routine wellness filing. Together, it's a pattern.

🚩 **The Dependent Ring**
Three members from three different employers all list the same eight "dependents" at the same address. You'd never see this reviewing claims one by one. The AI's network analysis connects the entities and surfaces the overlap.

🚩 **The Provider Mill**
One provider submits 15 hospital indemnity claims in a single month with near-identical documentation across different patients.

🚩 **The Tampered Records**
Medical records with mixed fonts, erasure marks, typed dates over handwritten originals, submitted as an editable Word document via email. In production, an AI vision model examines the actual document images to detect these anomalies — font inconsistencies, evidence of digital alteration, signatures that appear stamped rather than handwritten. Five red flags on one document.

🚩 **The Policy Change Exploit**
Four claims for outpatient surgical repair filed the day after a policy change expanded coverage. All from the same employer group.

**But equally important — what it *doesn't* flag as fraud:**

✅ A new employee who had a genuine accident 60 days after their policy started — bad timing, not bad intent.

✅ A member who called four times in two weeks — because their claim was genuinely complex and they needed updates.

✅ A rural clinic that sends records in black and white — because their scanner is from 2005, not because they're hiding something.

✅ A family that added six dependents in a month — because a marriage happened and stepchildren came with it.

The AI copilot presents both sides. It flags the concern *and* gives you the innocent explanation. You decide.

---

## Document Review: 13 Things to Look For, Checked on Every Claim

Every claim's supporting documentation runs through a standardized review. Think of it as the document checklist you carry in your head — but applied consistently to every single claim. In production, an AI vision model analyzes the actual document images, while an OCR layer extracts and verifies the text content.

**High-priority flags:**
- Mixed font styles within the same document
- Evidence of erasures or white-out
- Typed text layered over handwritten dates
- Medical records submitted as editable Word files
- Signatures that look stamped or don't match known specimens

**Medium-priority flags:**
- Entirely handwritten reports from a modern facility
- Missing standard medical record headers
- Multiple font sizes in a uniform document
- Medical terminology misspelled
- No vitals or medication list in full records

**Lower-priority flags (worth noting, not alarming alone):**
- Black and white records
- Records submitted via email instead of portal
- Records from a different provider than the requesting one

No single flag means fraud. But when you see five flags on one document? That's worth a closer look. The copilot surfaces all of this and lets you weigh it.

---

## Policy Intelligence: Changes You Need to Know About

Policy changes happen. The platform knows about them before you do and tells you when they're relevant to the claim you're reviewing.

**Current example:**

> *Effective September 18, 2025: Surgical repair benefits are now paid regardless of hospital confinement. Outpatient surgery is now covered under Hospital Indemnity.*

When you open a hospital indemnity claim for outpatient surgery, the AI copilot proactively tells you: *"Note — this claim is affected by a recent policy change. Here's what changed and how it applies."*

It also watches for claims that seem to *exploit* a policy change — like four claims filed the day after the change from the same employer group. Worth looking at.

**State rules and ET resolution** are handled the same way. The copilot tells you which state's rules apply, resolves extra-territorial questions, and flags relevant exclusions — all in plain language.

---

## The Risk Dashboard: Your Morning Briefing

Before you dive into individual claims, the dashboard gives you the big picture:

**📊 Auto-Adjudication Intercepts**
How many claims the platform held for review that would have auto-paid. In the prototype: 8 claims, $12,400.

**📈 Risk Distribution**
How many claims fall into High, Medium, and Low risk tiers across your book.

**🔍 Patterns Detected**
Network-level findings — dependent rings, provider clusters, termination rushes, document tampering clusters. Each one is clickable to take you straight to the relevant claims.

**📋 Workflow Health**
Open PMRs (and how many are past TAT), pending CBRs (and how many haven't had callbacks), and claims approaching their deadlines. A quick check to make sure nothing is falling through the cracks.

---

## How the Scoring Works

Every claim gets a risk score from 0 to 100. Here's what goes into it:

| What We Look At | Examples |
|---|---|
| **The policy** | How old is it? Any recent owner or beneficiary changes? |
| **The member** | How many dependents? How often do they file? Were dependents recently added? |
| **The claim itself** | Is the amount exactly at the benefit max? Is the documentation complete? |
| **The provider** | How many patients are they seeing? Is the volume normal for their specialty? |
| **The connections** | Does this member share an address with other claimants? Same provider as flagged members? |
| **The timing** | Filed right before coverage ends? Right after a dependent was added? Right after a policy change? |

| Score | What It Means | What You Do |
|---|---|---|
| 🔴 **65–100** | Significant risk indicators | Priority review — this is at the top of your queue |
| 🟡 **30–64** | Some flags worth investigating | Take a closer look when you get to it |
| ⚪ **0–29** | Likely clean | Fast-track eligible — process normally |

The score is fully transparent. You can always ask the AI *"Why does this claim have a 76?"* and it will break it down factor by factor in plain English.

---

## Network View: Seeing What Connects

Some fraud only becomes visible when you zoom out. The network view uses AI-powered entity analysis to map how members, dependents, providers, and addresses connect to each other — revealing relationships that no amount of individual claim review would surface.

**What it reveals:**

- 🕸️ **Dependent rings** — People who shouldn't know each other sharing the same dependents
- 🏘️ **Address clusters** — Multiple unrelated claimants at the same physical address
- 🏥 **Provider mills** — One provider handling a suspicious volume of similar claims
- 🏢 **Employer-linked spikes** — Unusual claim activity from a single company

When you spot a pattern, you can click into any node to see the claims involved and start your investigation from there.

---

## Escalation: The Package Writes Itself

When a claim needs to go to SIU, the AI copilot generates a complete referral package based on everything uncovered during your investigation:

- 📅 Timeline of events
- 📄 Evidence summary with specific data points
- 🕸️ Network diagram (if applicable)
- 💰 Dollar exposure
- ⚙️ Rules triggered with explanations
- 📝 Recommended action

No more spending 30 minutes writing up what you found. The AI documents everything as you work, and the escalation package pulls it all together.

---

## What This Means for Your Team

| Metric | Impact |
|---|---|
| **Time per claim** | Reduced — one workspace instead of five systems |
| **Claims you can catch** | Increased — AI-powered network analysis reveals patterns invisible to individual review |
| **Documentation** | Automatic — the AI captures every step as you go |
| **Consistency** | Every claim goes through the same checklist, same scoring |
| **False accusations** | Fewer — the AI presents both sides, not just the red flags |
| **TAT compliance** | Visible — overdue tasks surfaced before they become problems |
| **Onboarding** | Faster — new examiners have a guided process and an AI partner from day one |

---

## A Few Things Worth Knowing

**The AI copilot never makes the call.** It presents evidence, explains what it found, and gives you both the concern and the innocent explanation. The determination is always yours.

**It works on every claim, not just suspicious ones.** The eligibility check, the policy matching, the state rules — those save you time on Monday morning's routine stack, not just on the rare fraud case.

**The prototype uses synthetic data.** All 500 claims, all members, all providers — entirely made up for demonstration purposes. The 10 fraud scenarios and 5 false positives are designed to show what the platform can do across a realistic range of situations.

---

## Want to See It in Action?

The prototype is ready for a live walkthrough. In about seven minutes, we can show you:

1. What your morning queue looks like
2. How a routine claim goes from open to done in two minutes
3. What happens when the AI catches something you wouldn't see on your own
4. How the network view reveals connected fraud
5. What a fair investigation looks like — red flags *and* innocent explanations
6. How an escalation package generates itself

We built this for your workflow. We'd love to show you how it fits.

---

*Claims Copilot — built by people who listened to how you actually work.*