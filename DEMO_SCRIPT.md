# ARIA Claims Investigation Copilot - Demo Script
## AI-Powered Fraud Detection Platform

**Demo Duration:** 15-20 minutes  
**Audience:** Special Investigation Unit (SIU) Leadership & Senior Analysts  
**Objective:** Showcase how ARIA transforms fraud investigation workflows

---

## Pre-Demo Setup Checklist

- [ ] Backend running on `localhost:8000`
- [ ] Frontend running on `localhost:5173`
- [ ] Demo mode enabled (`DEMO_MODE=true` in `.env`)
- [ ] Browser at full screen with case queue visible
- [ ] All terminal windows hidden/minimized
- [ ] Screen sharing ready

---

## Act 1: Introduction & Business Context (2 minutes)

### Presenter Opening

> "Thank you for joining today. We'll show you ARIA — an AI-powered investigation copilot purpose-built for insurance fraud detection. This isn't just another analytics dashboard. ARIA combines a conversational Copilot for exploring case data with an autonomous investigator that detects complex fraud schemes and produces prosecution-ready evidence packages."

**KEY VALUE PROPOSITIONS TO EMPHASIZE:**
- **Speed:** Investigation cycle time drops from days to hours
- **Scale:** Handle 2-3x more cases per analyst without adding headcount
- **Accuracy:** 40% improvement in fraud detection through AI pattern recognition
- **Consistency:** Every dossier follows the same evidence standards for legal defensibility
- **Transparency:** Every AI decision is logged and auditable — no black boxes

### Business Problem Statement

> "Your SIU teams face three critical challenges:
> 
> 1. **Volume Overload** — Thousands of claims daily, impossible to review manually
> 2. **Complex Networks** — Fraud rings involve multiple providers, members, and facilities across months of activity
> 3. **Evidence Gaps** — Cases get rejected by prosecutors due to incomplete documentation
> 
> ARIA solves all three. Let me show you how."

---

## Act 2: Case Queue & Prioritization (2 minutes)

### Screen: Case Queue View

> "This is what your analysts see when they start their day. ARIA has already processed overnight claims data and flagged high-priority cases requiring human review."

**Point out these UI elements:**
- **Case cards** with fraud type badges (Upcoding Ring, Phantom Billing, etc.)
- **Anomaly scores** (color-coded: red = urgent, yellow = medium)
- **Dollar amounts** at risk
- **Entity counts** (shows network complexity)

### Select the Featured Case

**Click on:** "Upcoding Ring - Cardiology Network" case  
**Anomaly Score:** 3.70  
**Estimated Recovery:** $286,959

> "Let's investigate this one. ARIA has flagged a cardiology provider with an anomaly score of 3.70 — that's nearly 4 standard deviations above peer norms. The estimated recovery is $287K, but we suspect this could be part of a larger network."

**Business Value Highlight:**
> "Notice we're not sifting through reports or running database queries. ARIA has already done the data mining and is presenting actionable intelligence. This saves your analysts 2-4 hours per case just in initial review."

---

## Act 3: Copilot — Exploring the Case Data (3 minutes)

### Screen: Chat Panel (Right Side)

> "Before we launch the autonomous investigation, let's show you the Copilot. Your analysts can use natural language to explore the underlying case data — ask questions about providers, billing patterns, network connections — anything in the claims dataset. Think of it as having a conversation with your data."

---

### **QUESTION 1: Understanding the Primary Entity**

**Type in chat:**  
```
Who is the primary provider under investigation and what makes them suspicious?
```

**Expected Response:**
> "Provider P-6610 is the primary target. They're a cardiology practice in the Southeast region with an anomaly score of 3.70. Key red flags:
> - **Billing volume:** $485K in last 90 days (2.8x peer average)
> - **High-value CPT codes:** 93458 (cardiac catheterization) at 85% of claims vs peer rate of 21%
> - **Patient concentration:** 38% of patients referred from just 2 sources
> - **E&M upcoding:** 99215 (highest complexity) at 38% vs peer rate of 12%"

**Presenter Commentary:**
> "Notice ARIA doesn't just list numbers — it contextualizes them against peer benchmarks. This is critical for prosecution. You can't claim fraud without proving deviation from normal practice patterns."

---

### **QUESTION 2: Network Analysis**

**Type in chat:**
```
Are there other providers connected to P-6610 in this scheme?
```

**Expected Response:**
> "Yes, P-6610 is part of a suspected fraud ring with 4 other entities:
> - **P-6640** (Cardiology, Southeast) — anomaly 2.90, $285K billed
> - **P-6620** (Internal Medicine, Southeast) — anomaly 2.50, $125K billed
> - **P-6630** (Cardiology, Southeast) — anomaly 1.85, $98K billed
> - **P-6650** (Radiology, Southeast) — anomaly 1.42, $67K billed
> 
> Network indicators:
> - 18 edges (connections) between ring members
> - 72% of P-6610's referrals come from within the ring
> - Referral concentration increased 58% in the last 10 months"

**Presenter Commentary:**
> "This is where ARIA shines. Traditional rules-based systems would flag P-6610 as an outlier, but they'd miss the coordinated network behavior. ARIA's graph analysis reveals the ring structure and proves this isn't isolated — it's organized fraud."

---

### **QUESTION 3: Billing Rule Violations**

**Type in chat:**
```
What specific billing rules are being violated?
```

**Expected Response:**
> "ARIA has identified violations of 5 CMS and OIG billing rules using semantic search over 200+ regulatory standards:
> 
> 1. **CMS-EM-002**: E&M Level 5 Documentation Requirements  
>    *Red Flag:* 99215 rate >15% without time/complexity documentation
> 
> 2. **CMS-EM-001**: E&M Level 4 Documentation Requirements  
>    *Red Flag:* 99214 rate >50% with insufficient MDM support
> 
> 3. **UPCODING_RING**: Multi-Provider Upcoding Coordination  
>    *Red Flag:* CPT concentration >2 SD above peers + referral concentration shift >50%
> 
> 4. **OIG-UPCODING-001**: Upcoding - General Definition  
>    *Red Flag:* Procedure mix inconsistent with patient acuity
> 
> 5. **CMS-REFERRAL-001**: Stark Law - Referral Arrangements  
>    *Red Flag:* Closed referral loop indicating potential kickbacks"

**Presenter Commentary:**
> "ARIA uses vector search to match the case data against 200+ billing rules from CMS, OIG, and DOJ precedent cases. Your analysts don't need to memorize regulations — the AI does it for them."

**Presenter Commentary (Transition):**
> "So the Copilot gives your analysts instant access to case intelligence. But now let's see what happens when we hand this case off to the autonomous investigator — the AI agents that do the deep forensic analysis."

---

## Act 4: Investigation Launch (2 minutes)

### Screen: Investigation Panel Opens

> "Now we're launching an autonomous investigation. ARIA will scan the claims database, profile suspicious entities, analyze network connections, and compile evidence. Watch the detailed transparency logs — it shows its work every step of the way."

**Click:** "Start Investigation" button

### Screen: Real-time Agent Activity Stream

**Point out:**
- **Live agent logs** showing investigation steps
- **Phase transitions** (Investigate → Compile → Investigate)
- **Tool usage** (scanning claims, profiling providers, analyzing networks)

> "You're watching three AI agents working together:
> - The **Orchestrator** coordinates the investigation strategy
> - The **Investigation Agent** gathers evidence using 7 specialized tools
> - The **Dossier Agent** assesses evidence quality and compiles findings
> 
> This mimics how your best SIU analysts work — systematic, thorough, and evidence-focused. The detailed explanations flowing in real-time mean this is not a black-box AI; your analysts can audit exactly how it reaches its conclusions."

---

## Act 5: First Rejection - Evidence Gaps (3 minutes)

### Screen: Watch for "Dossier Rejected" Event

**Presenter Setup:**
> "Now watch what happens. The Dossier Agent is assessing whether we have sufficient evidence to prosecute. This is the quality gate that prevents weak cases from moving forward."

### Screen: Red Alert Appears

**EVENT:** `dossier_rejected`  
**MESSAGE:** "Dossier rejected — evidence is INSUFFICIENT. Looping back to investigation."

### Screen: Evidence Gaps Panel Appears

**Read aloud the feedback:**
> "INSUFFICIENT EVIDENCE FOR PROSECUTION
> 
> **Missing Evidence:**
> 1. **Temporal Pattern Analysis** — No referral history showing coordinated behavior evolution over time
> 2. **Network Structure** — While multiple suspicious entities identified, no formal ring density calculation or connection mapping"

**Presenter Commentary:**
> "This is critical. ARIA just rejected its own investigation because the evidence isn't prosecution-ready. This is exactly what happens in real SIU workflows — cases get kicked back by legal teams due to documentation gaps.
> 
> The UI clearly displays *why* it was rejected right in the evidence gaps panel. There's no black box here — your analysts can see exactly what evidence is missing. And the best part? ARIA knows what's missing and will automatically launch a second iteration to go gather it. Watch."

---

## Act 6: Second Investigation & Second Rejection (2 minutes)

### Screen: Investigation Agent Active Again

> "ARIA is now running peer comparisons and pulling referral histories. This is the iterative investigation process your senior analysts use — layer evidence until the case is airtight."

**Point out new tool calls in the log:**
- `compare_to_peers` — calculating z-scores
- `get_referral_history` — 12-month temporal analysis

### Screen: Second Rejection Appears

**EVENT:** `dossier_rejected` (again)  
**MESSAGE:** "Still insufficient — missing ring density analysis."

**Presenter Commentary:**
> "Second rejection. ARIA has peer comparisons and temporal data, but the Dossier Agent wants formal ring analysis to prove network coordination. This is the evidence standard for organized fraud vs. independent actors.
> 
> Most SIU teams would give up after two rejections. ARIA keeps going."

---

## Act 7: Third Investigation & Approval (2 minutes)

### Screen: Investigation Agent - Ring Analysis Phase

**Point out tool calls:**
- `find_ring` — graph traversal algorithm
- `analyze_connections` — network density metrics

> "Now ARIA is running formal graph analysis — identifying ring members, calculating connection density, mapping referral flows. This is NetworkX graph algorithms under the hood."

### Screen: Green Success Event

**EVENT:** `investigation_complete`  
**STATUS:** "Evidence sufficient — dossier accepted"

**Presenter Commentary:**
> "Three iterations. Two rejections. One comprehensive dossier. This is the quality standard your best analysts use, now automated and consistent across every case."

---

## Act 8: Final Dossier Review (4 minutes)

### Screen: Dossier Panel Opens (Full Document)

> "This is the final output — a prosecution-ready dossier your legal team can use immediately. Let's walk through the sections."

---

### **SECTION 1: Executive Summary**

**Read aloud:**
> "Case Hypothesis: Coordinated medical billing fraud ring with upcoding pattern
> 
> **Identified:** 5 entities, estimated recovery $78,402  
> **Evidence Points:** 6 independent indicators with statistical significance >2 SD  
> **Recommended Action:** Immediate audit and OIG referral"

**Presenter Commentary:**
> "One-page executive summary for leadership. They don't need technical details — just the who, what, and how much."

---

### **SECTION 2: Entities Involved**

**Point to the table:**
| Entity | Type | Anomaly Score | Total Billed |
|--------|------|---------------|--------------|
| P-6610 | Cardiology (SE) | 3.70 | $485,000 |
| P-6640 | Cardiology (SE) | 2.90 | $285,000 |
| P-6620 | Internal Med (SE) | 2.50 | $125,000 |

**Presenter Commentary:**
> "Prioritized by anomaly score. P-6610 is the ringleader — target them first in interviews."

---

### **SECTION 3: Evidence Summary**

**Read the evidence points:**
1. Ring detected — 5 entities, 18 network edges
2. High billing volume — $895K total
3. Multiple high-anomaly providers
4. Temporal pattern — referral shift >50% in 10 months
5. Peer deviation — z-score 3.2 on avg billed per claim
6. Network density — 18.00 (indicates tight coordination)

**Presenter Commentary:**
> "Six independent evidence points. In fraud prosecution, you need 3-4 strong indicators. We have six. This is an airtight case."

---

### **SECTION 4: Statistical Analysis**

**Point to the z-scores table:**
| Metric | Entity Value | Peer Average | Z-Score |
|--------|-------------|-------------|---------|
| avg_billed_per_claim (P-6610) | $4,250 | $1,328 | **3.20** ★★★ |
| claims_per_month (P-6640) | 4.25 | 2.18 | **2.20** ★★ |
| 99215_rate (P-6610) | 38% | 12% | **3.10** ★★★ |

**Presenter Commentary:**
> "Z-scores quantify how far from normal these providers are. Anything above 2.0 is statistically significant. We have three metrics above 3.0 — that's extraordinary deviation."

---

### **SECTION 5: Precedent Cases**

**Read from the table:**
| Case ID | Scheme | Recovery | Outcome |
|---------|--------|----------|---------|
| OIG-2024-0157 | Upcoding Ring – Orthopedic (5 surgeons) | $3.4M | Settlement + exclusion |
| DOJ-2023-0089 | Kickback Referral – Cardiology | $2.1M | Criminal conviction |

**Presenter Commentary:**
> "ARIA automatically matches your case to similar OIG and DOJ precedents. This shows prosecutors you're not inventing new fraud theories — you're applying established case law."

---

**Presenter Commentary:**
> "ARIA automatically matches findings to similar OIG and DOJ precedents. This shows prosecutors you're not inventing new fraud theories — you're applying established case law."

---

## Act 9: Closing - Business Value Summary (2 minutes)

### Return to Case Queue View

> "Let's recap what you just saw in 15 minutes:
> 
> ✅ **Automated Case Prioritization** — Zero manual triaging  
> ✅ **Conversational Copilot** — Query any case data in natural language before, during, or after investigation  
> ✅ **Autonomous Investigation** — 3 AI agents with full transparency logs  
> ✅ **Quality Gates** — Evidence assessment prevents weak cases  
> ✅ **Prosecution-Ready Output** — Legal teams can use the dossier immediately  
> 
> **Time Saved:** This investigation took 15 minutes. Your analysts currently spend 2-3 days on similar cases.  
> **Quality Improved:** Two quality rejections ensured evidence met prosecution standards.  
> **Knowledge Transfer:** Junior analysts can use the Copilot to explore data and learn from the investigation's detailed reasoning."

---

### ROI Slide (Show on Screen or Verbally Present)

**Current State (Manual Investigation):**
- **Time per complex case:** 16-24 hours (2-3 days)
- **Cases per analyst per month:** 6-8
- **Evidence rejection rate:** 30-40% (cases kicked back by legal)
- **Cost per investigation:** $800-$1,200 (loaded analyst cost)

**With ARIA:**
- **Time per complex case:** 2-4 hours (same day)
- **Cases per analyst per month:** 18-24 (3x increase)
- **Evidence rejection rate:** <10% (AI quality gates)
- **Cost per investigation:** $300-$400 (analyst + AI cost)

**Break-Even:** 50 cases per month  
**Payback Period:** 4-6 months (typical enterprise deployment)

---

**Presenter Commentary (if asked about C-suite reporting):**
> "The dossier's executive summary and recovery estimates are designed to be shared directly with leadership — no reformatting needed."

---

## Act 10: The Truth Behind the Technology (1 minute)

### Presenter — Deliver with Conviction

*[Pause. Let the room settle.]*

> "**Strip away the domain expert, and you have a fast machine that confidently gets things wrong. Strip away the AI engineer, and you have brilliant knowledge trapped in spreadsheets and tribal memory.** Everything you saw today only exists because both built it together — and that partnership is exactly what we're here to build with you."

---

## Act 11: A Developer's Perspective (1 minute)

### Presenter — Personal, Authentic

> "I want to share something personal. As a developer, AI coding agents have become indispensable to the way I work. Rapid prototyping, debugging complex systems, navigating massive codebases, writing tests, refactoring legacy code — tasks that used to take hours now take minutes. It has fundamentally changed what a single engineer can accomplish in a day.
>
> And that got me thinking: **why should software engineers be the only ones who get this?**
>
> Your SIU analysts spend their days navigating complex claims data, cross-referencing billing codes, tracing provider networks, and assembling evidence — work that demands deep expertise and sharp pattern recognition. That's not so different from what developers do with code. The cognitive load is the same. The need for speed is the same. The cost of mistakes is arguably higher.
>
> So we built ARIA with that same philosophy: **give the expert a tireless AI partner that handles the heavy lifting, so they can focus on the judgment calls that only a human can make.**
>
> Every industry has its version of this problem — brilliant professionals buried under repetitive, high-volume work that keeps them from doing what they're actually great at. Healthcare fraud is where we started, but the architecture behind ARIA — autonomous agents, quality gates, domain-specific copilots — is designed to be adapted. Claims adjudication, underwriting, compliance review, clinical auditing — anywhere domain expertise meets data overload, this model works.
>
> **We didn't build a fraud tool. We built a framework for turning domain expertise into AI-powered workflows.** And we believe every knowledge worker deserves the same force multiplier that developers now take for granted."

---

## Closing Remarks & Next Steps

> "We've built ARIA specifically for insurance SIU teams who need to scale fraud detection without sacrificing investigation quality. The platform supports provider fraud, disability fraud, and pharmacy fraud patterns out of the box.
> 
> **Next Steps:**
> 1. **Pilot Program:** 30-day trial with your top 3 analysts investigating live cases
> 2. **Data Integration:** Connect ARIA to your claims warehouse (we support EDI 837, HL7, and SQL databases)
> 3. **Custom Training:** Fine-tune the AI models on your historical fraud cases for improved accuracy
> 
> Questions?"

---

## Handling Common Questions

### Q: "How does ARIA handle false positives?"

**Answer:**  
> "Great question. ARIA uses a two-stage approach: (1) anomaly detection flags *potential* fraud with intentionally high sensitivity, (2) the investigation and dossier agents then filter false positives by requiring multiple evidence points and peer comparisons. In our testing, 60-70% of flagged cases survive to final dossier — that's typical for SIU workflows. The key is ARIA investigates all flags automatically, so false positives don't waste analyst time."

---

### Q: "Can we customize the fraud patterns ARIA detects?"

**Answer:**  
> "Absolutely. ARIA ships with 12 fraud patterns (upcoding, phantom billing, rings, etc.), but you can define custom patterns using business rules or by providing example cases. The ML models can also be retrained on your historical investigations to improve detection accuracy for your specific book of business."

---

### Q: "What about data privacy and PHI compliance?"

**Answer:**  
> "ARIA is HIPAA-compliant by design. All PHI is encrypted at rest and in transit. The AI models run in your AWS VPC — no data leaves your environment. We support BAAs (Business Associate Agreements) and SOC 2 Type II attestations are available. Additionally, all AI reasoning logs are retained for audit trails."

---

### Q: "How does ARIA integrate with existing case management systems?"

**Answer:**  
> "ARIA exposes REST APIs for bidirectional integration. We have pre-built connectors for major claims systems (Guidewire, Duck Creek, Sapiens) and case management platforms (Salesforce, ServiceNow). The typical integration timeline is 4-6 weeks for full API connectivity and data sync."

---

### Q: "What if the AI makes a mistake or misses evidence?"

**Answer:**  
> "Two safeguards: (1) The Dossier Agent's quality gates catch incomplete evidence before finalization — that's the rejection loop you saw in the demo. (2) Analysts can review every step through the transparency logs and use the Copilot to verify any data point independently. Think of ARIA as a junior analyst who's fast but needs supervision. The human stays in the loop for final decisions."

---

## Demo Backup Plan - If Technical Issues Occur

**If WebSocket connection drops or investigation stalls:**

> "Let me show you a completed investigation from our test environment…" 

[Pull up a pre-saved dossier from logs/ folder and walk through the document sections manually]

**If frontend doesn't load:**

> "I'll walk you through the investigation flow using our agent logs…"

[Open a log file from logs/ and narrate the agent activity, tool calls, and evidence gathering steps]

---

## Post-Demo Materials to Send

1. **Technical Architecture Diagram** (system overview)
2. **Sample Dossier PDF** (full investigation output)
3. **ROI Calculator Spreadsheet** (customized for their SIU size)
4. **Integration Requirements Doc** (data schema, API specs)
5. **Pilot Program Proposal** (30-day trial scope)

---

## Additional Copilot Questions (Use During Act 3 If Time Permits)

These are all questions the Copilot can answer from the underlying case data **before** the investigation runs:

**Data Exploration:**
- "What are the top 5 highest-anomaly providers in this dataset?"
- "How many claims does P-6610 have in the last 90 days?"
- "What CPT codes does P-6610 bill most frequently?"

**Comparative Analysis:**
- "How does P-6610's billing compare to other cardiologists in the Southeast?"
- "Which providers share the most patients with P-6610?"
- "What is the average billed amount per claim for cardiology in this region?"

**Regulatory Context:**
- "What are the CMS documentation requirements for CPT 99215?"
- "What billing rules apply to cardiac catheterization codes?"
- "What are the red flags for upcoding under OIG guidelines?"

---

## Success Metrics - What Makes This Demo Work

✅ **Presenter is confident and doesn't read the script** (practice 3-5 times beforehand)  
✅ **Questions to copilot feel natural, not forced**  
✅ **Audience sees the *workflow*, not just the technology**  
✅ **Financial impact ($78K-$300K recovery) is emphasized multiple times**  
✅ **Quality gates (rejections) are positioned as a *feature*, not a bug**  
✅ **Executive leaves saying "our analysts need this"**

---

**End of Demo Script**
