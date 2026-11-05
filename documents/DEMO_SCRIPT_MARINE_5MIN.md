
My name is Mike Arsolon. I'm an AI Engineer under Data+AI, and today I'll be showing you Claims Copilot. Claims Copilot is an AI assistant that helps claims handlers check documents, spot fraud and build a case faster — so people spend their time on decisions, not on paperwork.


*[Business introduction — no screen needed]*

Let me start with the problem. When a cargo claim comes in, the claims handler gets a stack of documents from different companies: an invoice from the seller, a packing list, a bill of lading from the shipping line, container weights from the port, a survey report, and a set of photos. Each one usually looks fine on its own.

The trouble is between the documents. To know if a claim is real, someone has to check them against each other — does the weight match the invoice, is the price normal, is the surveyor independent, has this photo been seen before. Done by hand, that takes days per claim. So in practice, teams can't do it for every claim. Many get paid on the paperwork alone.

That costs money in three ways. Bad claims get paid. Good claims wait too long, and the customer feels it. And time limits get missed — for example, the shipping line has to be told about damage within days, or the chance to get money back from them is gone.

So the question we asked was simple: what if every claim got the full cross-check, in minutes, with a person still making the call?


Today's example is a marine cargo claim. One container going from Singapore to Manila touches almost every company in this room: someone sells it, someone ships it, someone moves it, someone finances it, someone insures it. Everyone holds one piece of the paperwork. Let's see what happens when an AI reads all the pieces together. All the companies and people you'll see are made up.


*[Queue]*

This is a claims handler's morning. Forty-two claims, already sorted by risk before anyone opens a file. At the top is MC-3107 — a breakage claim for about US$204,000 on six containers of insulated glass. That's 71% of what the shipment was insured for. On the right, the system already tells us why it's flagged, in plain English. We didn't go looking for this. It came to the top on its own.


*[Open claim — checklist runs]*

When I open the claim, the checklist runs by itself. These are the same seven steps a claims handler would normally do by hand, opening one system after another: the shipping documents, the cover dates, the document images, the surveyor, the policy clauses. It takes a few seconds, and every result says where it came from.

Look at Step 2, Shipping Documents. This is the key moment. The invoice, the packing list and the bill of lading all say 135 tonnes of glass. They agree with each other — because they all carry the shipper's own numbers. But the terminal weighed the containers, and that weight says 77 tonnes. That's 43% less. The weight can only hold about 2,580 square metres of glass. The invoice charges for 4,320. Part of the glass that was "broken" may never have been loaded. And the price is US$58 per square metre, against a market price of 28 to 38. About 1.8 times the market.

Step 4 is the Document AI Review. The AI checks every document image against 13 forensic checks. The invoice and the bill of lading look completely genuine — and that's the point. Good fraud has clean paperwork. But one survey photo has been used before, on a claim we already paid back in April.

Step 5 is the surveyor. The damage was surveyed 17 days after the ship arrived, at the claimant's own warehouse, by a surveyor the claimant picked. And that surveyor shares a director and an office address with the claimant.


*[Ask Copilot]*

I can also just ask. "Explain the VGM gap." Plain question, plain answer — no spreadsheets, no cross-checking by hand.


*[Start investigation]*

The checklist found the red flags. Normally, the handler would now spend days pulling claim history, checking companies and writing it all up. Instead, we start the investigation.

There are three AI agents working together. The Orchestrator is the lead — it decides what to look at next. The Investigator does the digging: claim history, company links, the surveyor's past work. The Case Writer has to be satisfied before anything reaches a person. It has six checks it needs to see met.

And it pushes back. Watch — the case writer holds the file. Three checks aren't met yet: the documents haven't been matched up, the price hasn't been checked, the photos haven't been checked. So it goes back for more digging. Then it holds it again: breakage is covered by the policy, so a decline has to rest on the policy clauses, and on proof that the surveyor isn't independent.

Then the agents find it. The claimant, the surveyor and the freight forwarder all share one director. The same surveyor signed off five earlier claims — about US$645,000 already paid — across three companies.

Every step is in the activity log on the right. Nothing is a black box.


*[Dossier]*

This is what the claims handler gets. A clear recommendation, every finding with its source next to it, and the point in the claimant's favour too — breakage is a covered risk — so the picture is fair. The recommendation: decline the US$204,000, refer it for investigation, and review the US$645,000 already paid. And because no one told the shipping line in time, there's no money to get back from the carrier either.

The AI doesn't make the call. I do. When I decline, I have to write down why. The AI did days of cross-checking in about forty seconds. The person still signs off.


*[Close]*

Look at what actually caught this claim: a container weight, a shipping-line receipt, an invoice, a photo and a company record. None of that is special to insurance. The same engine can read trade finance documents for a bank, cargo records for a shipping line, or warranty claims for a manufacturer. Different documents — same question: do the pieces agree?

A simple fraud score just says yes or no. But fraud hides in the gap between the paperwork and the real world, and in links between companies that look unrelated until you map them. What we built works more like a good investigator: gather the evidence, challenge it, build the case. The machine does that tirelessly and at scale. The person makes the decision.


*[Business summary]*

So let's go back to the problem we started with.

Before: a stack of documents from different companies, checked by hand when there's time, and often paid on the paperwork. After: every claim gets the full cross-check in minutes — weights, prices, photos, surveyors, company links, policy clauses — the same way, every time.

What that means for the business:

- **Less money paid on bad claims.** On this one claim, US$204,000 not paid, and US$645,000 of past payments flagged for review.
- **Faster payment on good claims.** Clean claims are cleared quickly, so honest customers aren't stuck waiting behind the suspicious ones.
- **Problems caught while they can still be fixed.** Missed deadlines and recovery chances show up early, not months later.
- **Better use of skilled people.** Handlers spend their time on judgement and decisions, not on copying numbers between screens.
- **Every decision can be explained.** Each finding points to its source, which matters for auditors, regulators and customers.

And none of it replaces the person. The AI gathers and checks the evidence. The claims handler decides.

Thank you.
