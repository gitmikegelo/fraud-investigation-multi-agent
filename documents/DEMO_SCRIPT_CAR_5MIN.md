# Claims Copilot — Car Insurance 5-Minute Demo Script

Audience: Business + SIU stakeholders  
Duration: 5:00 hard stop  
Primary case: COL-107 (Matthew Garcia — hero case, risk score 98.4)  
Extended beat: Claimant Letter (in Dossier view)

---

## 0:00–0:20 — Set the frame

"In five minutes I'll show the full loop: prioritized queue, rapid Q&A, automated checklist with live damage assessment, autonomous fraud analysis, a finished dossier ready for escalation, and a claimant communication — all on a single car insurance claim."

---

## 0:20–1:00 — Show queue and pick claim

**Action:**
1. Open Claims Queue.
2. Keep Today view — cases are pre-ranked by risk score.
3. Click **COL-107** — Matthew Garcia, collision claim, risk score **98.4 HIGH**.

**Talk track:**
"This is the examiner's morning queue. Claims are already sorted by risk before anyone opens a file. COL-107 is at the top — a collision claim flagged with a watchlisted repair shop, a serial claimant pattern, and a repair estimate that's 1.4 times the vehicle's actual cash value. We didn't hunt for that. The system surfaced it automatically."

---

## 1:00–1:40 — Ask one fast question (quick win)

**Action:**
1. Click the **Why Flagged?** chip — or type: *Why was this claim flagged? Explain the risk score.*

**Talk track:**
"Plain-English question, immediate answer. No spreadsheets, no manual cross-referencing. The copilot pulls the risk factors, rule triggers, and prior claim history in seconds.

Notice: three rules fired — a BLOCK on the repair shop watchlist, a flag for claim amount exceeding vehicle ACV, and a serial claimer flag for six prior claims. That combination alone would take an examiner 20–30 minutes to piece together manually."

**Optional follow-up if response is short:**
"What's the DECREE damage estimate versus what was submitted?"

---

## 1:40–2:45 — Run checklist and call out key steps

**Action:**
1. Click **▶ Run Full Checklist**.
2. Let the 7-step card animate through statuses in real time.

**Talk track:**
"Now we run the full structured examination — the same seven steps your examiners follow, automated end to end.

Watch Step 2: Damage Documentation. This is where DECREE™ comes in — our integrated damage assessment engine. It analyzes the actual vehicle photo and returns a structured repair cost estimate. The shop submitted **$25,877**. DECREE™ puts the realistic range at **$8,750–$12,450**. That's a $13,000–$17,000 gap on a single claim. Caught in seconds.

Step 4 is Document AI Review — computer vision scanning the evidence photos for tampering indicators, metadata anomalies, and authenticity signals across 13 forensic checks. Every document, every time, same standard.

Step 5 flags the repair shop outright — 'Discount Fender Fix' is on the fraud watchlist. The system doesn't just note it; it blocks approval pending examiner review."

---

## 2:45–3:45 — Launch autonomous fraud analysis

**Action:**
1. When checklist completes, click **Launch AI Fraud Analysis →**.
2. Point at the Agent Flow graph and the live event timeline.

**Talk track:**
"The checklist found four red flags on this claim. In a normal workflow, an examiner would now spend hours manually pulling claim history, profiling the repair shop, mapping connections, and writing up findings.

Instead, we launch the autonomous investigation. ARIA — the AI investigation engine — orchestrates the analysis: scans for suspicious entities, profiles the insured and the shop, compares them to statistical peers, and traverses the entity network looking for a repair-shop ring pattern.

You can see every step in the event timeline on the right — this is fully explainable, not a black box. Real agent IDs, real data, real reasoning."

---

## 3:45–4:30 — Show full dossier output

**Action:**
1. Let auto-navigation open the Dossier view, or click **View Full Dossier →**.
2. Scroll quickly through the sections.

**Talk track:**
"This is the finished output: executive summary, DECREE™ damage assessment with the cost gap highlighted, entity profiles for the insured and the shop, rule and policy references, and a recommended action.

Matthew Garcia, INS-0001, six prior claims, repair shop on the fraud watchlist, $25K estimate on a car worth $18K. The recommendation: escalate to SIU.

An examiner didn't write this — they'll review it, validate it, and sign off. That's the right use of their time."

---

## 4:30–4:50 — Generate the claimant letter

**Action:**
1. Still in Dossier view, click **✉ Claimant Letter**.
2. Let the letter generate — it takes a few seconds.
3. Briefly show the rendered letter; point out plain-language tone.
4. Optionally click **Download PDF** to show the export.

**Talk track:**
"One last step — and this is one examiners actually dread. Writing to the claimant. Whether it's a request for more information, a denial notice, or a referral for further review, the wording has to be clear, compliant, and professional.

The system drafts that letter automatically, in plain language, based on the findings from this exact claim. The examiner reads it, adjusts if needed, and sends. No boilerplate hunting, no blank-page paralysis.

Every touchpoint in the claim lifecycle — from intake to communication — in one workflow."

---

## 4:50–5:00 — Close with workflow summary

**Talk track:**
"That's the complete operating model: risk-ranked queue, instant Q&A, automated 7-step checklist with live damage assessment, autonomous fraud analysis, a prosecution-ready dossier, and a claimant letter — all generated from a single claim. What used to take hours now takes minutes, with the same forensic standard applied every time."

---

## Presenter cheatsheet (if time gets tight)

- **Behind at 2:00:** Skip the follow-up chat question; go straight to checklist.
- **Behind at 3:00:** Shorten checklist narration to "DECREE™ caught a $13K gap on the estimate, shop is watchlisted, moving to fraud analysis."
- **Behind at 4:00:** Show dossier headings only; skip to close — drop the claimant letter beat.
- **Behind at 4:30:** Say "the system also generates the claimant letter automatically" without clicking it.
- **If anything stalls:** Narrate from visible state on screen and jump to the close line above.

---

## Exact UI labels to use on screen

- Claims Queue
- COL-107 / Matthew Garcia
- Why Flagged?
- ▶ Run Full Checklist
- DECREE™ estimate (Step 2)
- Launch AI Fraud Analysis →
- View Full Dossier →
- ✉ Claimant Letter
- Download PDF

---

## Key numbers to know cold

| Data point | Value |
|---|---|
| Claim ID | COL-107 |
| Insured | Matthew Garcia (INS-0001) |
| Claim type | Collision |
| Risk score | **98.4 HIGH** |
| Submitted estimate | **$25,877** |
| DECREE™ estimate | **$8,750–$12,450** |
| Vehicle ACV | **$18,484** |
| Estimate vs. ACV | **1.4× over value** |
| Prior claims | **6 (serial claimer)** |
| Repair shop | Discount Fender Fix — **watchlisted** |
| Rules triggered | BLOCK + 2 FLAGS |
