# Marine Cargo Claims Copilot — 10-Minute Demo Script
**Audience:** Singapore Mitsubishi-Kai — senior executives across trading, shipping, logistics, banking, insurance and manufacturing
**Presenter:** Mike Arsolon, AI Engineer, Data & AI
**Claim:** MC-3107 · all companies, people and vessels are fictional

---

## Before you start (checklist)
- [ ] `start_marine.bat` (DEMO_MODE=true). Open http://localhost:5173
- [ ] `/api/health` shows `domain_mode: marine`, `demo_mode: true`
- [ ] Vision cache is warm: open MC-3107 once during rehearsal (`claims-copilot/vision_cache/` has files; the checklist should finish in ~3 s)
- [ ] Survey photo: `images/mc2988.png` and `images/mc3107_2.png` are the same photo. They are a generated placeholder today — swap in a real broken-glass photo (save it under both names), then delete `claims-copilot/data_cache_v1_marine.pkl` and restart
- [ ] Browser zoom 110–125% so the back row can read it
- [ ] Backup video open in another window
- [ ] Wi-Fi off test passed (the whole flow runs without any live API)

---

## 0:00–1:00 · Hook (no screen)

> "One container crosses Singapore to Manila, and the people in this room touch it five times. A trading company sells it. A shipping line carries it. A logistics firm moves it. A bank finances it. An insurer covers it.
>
> Each of you holds one piece of the paperwork. Today I'll show what happens when an AI reads all the pieces together — using one claim."

---

## 1:00–2:00 · The queue

**Screen:** Claims queue, **All** (the default). MC-3107 is already selected, with "Why it's flagged" in the preview on the right.

> "This is a marine cargo claims handler's morning. Forty-two claims, already ranked by risk before anyone opens a file.
>
> At the top: **MC-3107** — a breakage claim for **US$204,000** on six containers of insulated glass. Below it are two more HIGH claims — not fraud, but coverage issues: one loss was discovered after cover ended, one was caused by poor packing. The system separates *who needs a decision* from *who needs an investigation*."

Click **Open claim**.

---

## 2:00–5:00 · The checklist — reading every document together

**Screen:** the checklist starts on its own when the claim opens; the seven steps fill in within a few seconds. Click **See results**, then click a red step to expand its evidence.

**Step 2 — Shipping Documents** *(the key moment — expand it: the weights are laid out line by line)*
> "The invoice, the packing list and the bill of lading all say 135 tonnes. They agree — because they're all the shipper's own numbers.
>
> But the container weights recorded at the terminal — the VGM — say **77 tonnes**. That's 43% less. The weight can hold at most about **2,580 square metres** of glass. The invoice charges for **4,320**.
>
> The glass that was 'broken' may never have been loaded."

> "And the price: **US$58 per square metre**, against a market range of **US$28–38**. 1.76 times the market."

**Step 4 — Document AI Review**
> "The AI inspects every document image. The invoice and the bill of lading look completely genuine — and that's the point. A good fraud has clean paperwork. It only falls apart against the physical evidence.
>
> And one of the survey photos has been used before — on a claim we **already paid** in April, for a different company."

**Step 5 — Survey & Surveyor**
> "The survey happened **17 days** after discharge, at the claimant's own warehouse, after the cargo was unpacked. It was done by a surveyor the claimant chose — not us. That surveyor shares a **director and an office address** with the claimant."

**Step 6 — ICC Coverage**
> "Breakage is covered under ICC (A). But the claimant never notified the shipping line, and took delivery with a clean receipt. So even if the loss were real, our right to recover from the carrier is gone."

---

## 5:00–7:30 · Autonomous investigation

**Screen:** on the results page, click **Start investigation** (purple strip under the checklist). The run takes about 40 seconds.

> "Now the investigation. Three AI agents: an **orchestrator** that decides what to look at, an **investigator** that pulls the evidence, and a **case writer** that must be satisfied before anything reaches me. The fourth box is me — I make the decision.
>
> Watch the case writer **hold** the file." *(first hold appears, amber)* "Three of its six required checks aren't met — the documents haven't been reconciled and the photos haven't been checked. Back it goes."
>
> *(second hold)* "Held again — breakage *is* covered, so a decline has to rest on the policy clauses and on proof the surveyor isn't independent."
>
> *(network found)* "Here: the claimant, the surveyor and the freight forwarder share one director. The same surveyor signed off **five earlier claims — US$645,000 already paid** — across three companies."

> "Every step is in the activity log on the right, and the required checks fill in on the left. Nothing is a black box."

---

## 7:30–9:00 · The dossier

**Screen:** click **Review** on the "Dossier ready" notification (or **Dossier** in the sidebar). Scroll slowly: recommendation → findings (strong first, each with its source) → recommended actions. Open **Full investigation report** only if there is time.

> "This is what the claims handler receives. Every finding says where it came from. And it lists the point in the claimant's favour — breakage is an insured peril — so the decision is balanced.
>
> Recommendation: **decline US$204,000**, refer for investigation, and review **US$645,000** already paid."

Click **Decline claim** → the note field is required → type one line → **Decline**.

> "A person still makes the decision, and has to write down why. The AI did the three days of cross-checking in about forty seconds."

---

## 9:00–10:00 · Close — same engine, other documents

> "Look at what caught this claim: a terminal weight, a shipping-line receipt, an invoice, a photo, a company registry. None of it is insurance-specific.
>
> The same engine reads **trade-finance documents** for a bank, **warranty claims** for a manufacturer, **lease-asset claims** for a leasing company, **cargo exceptions** for a carrier. Different documents — same question: *do the pieces agree?*
>
> Thank you."

---

## If something goes wrong
| Problem | Recovery |
|---|---|
| Checklist step 4 shows "vision analysis unavailable" | Keep going — steps 2, 5 and 6 carry the story. Say: "The image check runs in the background." |
| Investigation stalls | Refresh the browser, reopen MC-3107, **See results** → **Start investigation** again (the demo replay is deterministic) |
| Copilot chat answer is slow or fails | Skip the chat — it is the only live AI call in the flow, and nothing else depends on it |
| Anything else | Switch to the backup video at the same timestamp |

## Numbers to remember
| | |
|---|---|
| Claimed | US$204,493 (71% of insured value US$288,019) |
| Declared vs weighed cargo | 135,000 kg vs 77,466 kg (43% short) |
| Invoiced vs weight-supported quantity | 4,320 m² vs ~2,580 m² |
| Price vs market | US$58/m² vs US$28–38/m² (1.76×) |
| Survey delay | 17 days after discharge |
| Surveyor's prior paid claims | 5 claims, 3 companies, US$644,700 |
