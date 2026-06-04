# LinkedIn Post: AI Agents for Fraud Detection

---

**Insurance fraud detection has a bottleneck problem.**

Examiners spend 60-70% of their time assembling evidence and only 30% making decisions. The industry response? Hire more analysts. The result? Still overwhelmed, still reactive.

**We built a different model: autonomous agents that investigate, not just flag.**

Instead of rules engines that create alerts, we deployed a multi-agent system that operates like an SIU team. One agent gathers evidence, including network graph analysis to surface connected entities, referral rings, and coordinated billing patterns that no single claim review would catch. Another evaluates sufficiency. A third compiles prosecution-ready dossiers. The orchestrator coordinates the workflow and enforces quality gates.

The breakthrough isn't just the AI, it's the architecture. Traditional fraud tools treat investigation as linear: detect anomaly → alert analyst → manual review. Our system treats it as an iterative loop: gather evidence → assess quality → loop if insufficient → compile only when prosecution-ready.

In testing, the system rejected its own findings twice before accepting a final dossier. That is not a bug, it's the design. We encoded the exact evidence standards that senior investigators use, then automated the loop to enforce them.

**Three insights from building this:**

1. **Transparency beats accuracy.** Examiners trust systems that show their work. Every tool call, every decision branch, every evidence gap is logged. No black boxes.

2. **Quality gates prevent garbage output.** The dossier agent uses deterministic checks against required evidence fields before it will compile. This constraint forces better investigations, not just faster bad ones.

3. **Autonomy shifts analyst focus.** When the system handles evidence assembly, analysts spend time on judgment calls, not data gathering. Investigation cycle time drops from days to hours.

The real value isn't replacing investigators. It's giving them leverage.

**Built as a proof of concept for insurance claims fraud detection.** Multi-agent orchestration. Claude Sonnet 4.0 for reasoning. AWS Bedrock for vision analysis. LangGraph for workflow coordination. Network graph analysis for entity relationship mapping and fraud ring detection.

Grateful to have presented this work at Accenture's Client Innovation Center and discussed the approach with global delivery leadership. The conversation reinforced that the hardest problems in enterprise AI are not purely technical. They revolve around trust, transparency, and fit with how people actually work.

The final question is no longer whether AI can detect fraud. It is whether we can architect systems that investigators actually trust to do the work.

#ArtificialIntelligence #FraudDetection #InsuranceTech #MultiAgentSystems #AWS
