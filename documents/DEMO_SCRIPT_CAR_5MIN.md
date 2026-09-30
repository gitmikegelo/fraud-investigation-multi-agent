
My name is Mike Arsolon. I'm an AI Engineer under Data+AI and I'll me doing a demo for Claims Copilot. Claims Copilot is an AI-powered assistant that helps insurance examiners investigate, analyze, and resolve claims faster by automating fraud detection, document review, and dossier generation. 


This is the examiner's morning queue. Claims are already sorted by risk before anyone opens a file. COL-107 is at the top — a collision claim flagged with a watchlisted repair shop, a serial claimant pattern, and a repair estimate that's 1.4 times the vehicle's actual cash value. We didn't hunt for that. The system surfaced it automatically."


Plain-English question, immediate answer. No spreadsheets, no manual cross-referencing. The copilot pulls the risk factors, rule triggers, and prior claim history in seconds.

Notice: three rules fired — a BLOCK on the repair shop watchlist, a flag for claim amount exceeding vehicle ACV, and a serial claimer flag for six prior claims. That combination alone would take an examiner 20–30 minutes to piece together manually."

Now we run an automated workflow through the same steps your examiners follow. In a manual process, they'd open different tools one by one:  It's pulling policy data, running damage analysis against the photo, cross-referencing the repair shop against watchlists, and scanning all submitted documents through computer vision. Each step is independently validated and logged, so every finding is traceable back to a specific data source. By the time it completes, you'll have a full structured audit trail — not just a score."

Watch Step 2: Damage Documentation. This is where DECREE™ comes in — our integrated damage assessment engine. It analyzes the actual vehicle photo and returns a structured repair cost estimate. The shop submitted **$25,877**. DECREE™ puts the realistic range at **$8,750–$12,450**. That's a $13,000–$17,000 gap on a single claim. Caught in seconds.

As discussed prior to thius DECREE™ is a standalone API — it's not locked inside Claims Copilot. That same damage assessment capability can be plugged directly into your existing claims platforms, adjuster portals, or any downstream system. So the business value scales beyond this workflow.

Step 4 is Document AI Review — computer vision scanning the evidence photos for tampering indicators, metadata anomalies, and authenticity signals across 13 forensic checks. Every document, every time, same standard. In our Zurich instance, we have AI vision check on legitimacy damage luggage. And in Prudential instance it's also a high pressure point because we have viosion AI inspecting a medical document instead of manually inspected by an examiner. Our current prototype for that one was prompted through actual number of red flags base on fraudulent history.


The checklist found four red flags on this claim. In a normal workflow, an examiner would now spend hours manually pulling claim history, profiling the repair shop, mapping connections, and writing up findings.

Instead, we launch the autonomous investigation. ARIA — the AI investigation engine — orchestrates the analysis: scans for suspicious entities, profiles the insured and the shop, compares them to statistical peers, and traverses the entity network looking for a repair-shop ring pattern.

There are three agents working in concert here. The **Orchestrator** acts as the lead investigator — it doesn't touch data directly, it decides what to investigate next and routes work to the right agent. The **Investigation Agent** is the detective — it has access to seven tools and does the heavy lifting: scanning entities, pulling claim history, profiling the shop, and mapping network connections. Once the evidence is sufficient, the **Dossier Agent** takes over as the case writer — it assesses the findings, fills any gaps, and compiles everything into the structured report you'll see next.

It's also important for you to understand this is adversarial agentic process, what it means is that sometimes the Investigation Agent will find a lead, but the Orchestrator will say "not enough evidence yet" and send it back for more digging. The agents are constantly challenging each other to ensure the findings are robust and defensible.

You can see every step in the event timeline on the right — this is fully explainable, not a black box. Real agent IDs, real data, real reasoning."


"This is the finished output: executive summary, DECREE™ damage assessment with the cost gap highlighted, entity profiles for the insured and the shop, rule and policy references, and a recommended action.

Matthew Garcia, INS-0001, six prior claims, repair shop on the fraud watchlist, $25K estimate on a car worth $18K. The recommendation: escalate to SIU.

An examiner didn't write this — they'll review it, validate it, and sign off. That's the right use of their time."


**Talk track:**
"One last step — and this is one examiners actually dread. Writing to the claimant. Whether it's a request for more information, a denial notice, or a referral for further review, the wording has to be clear, compliant, and professional.

The system drafts that letter automatically, in plain language, based on the findings from this exact claim. The examiner reads it, adjusts if needed, and sends. No boilerplate hunting, no blank-page paralysis.


"That's the complete operating model: risk-ranked queue, instant Q&A, automated 7-step checklist with live damage assessment, autonomous fraud analysis, a prosecution-ready dossier, and a claimant letter — all generated from a single claim. Every touchpoint in the claim lifecycle — from intake to communication — in one workflow. Analysts spend less time assembling evidence and more time making decisions.

A traditional fraud model sees a claim and returns a verdict: fraud or not fraud. But fraud doesn't announce itself. It hides in the gap between a shop's estimate and a car's real value. It hides in a network of entities that look unrelated until you map them. A binary score misses all of that — and when it's wrong, a real claim gets denied, or a real fraudster gets paid. What we built is closer to how a good investigator actually thinks: gather evidence, challenge assumptions, build a case. The machine does that relentlessly and at scale. The examiner closes it.
