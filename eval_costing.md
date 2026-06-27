# Updated Rating With Architecture Context

## Revised Overall: **8/10** — This is actually quite well-matched to your architecture. But the gap between "what the POC is" and "what the cost calculator estimates" needs bridging.

---

## What Changes With This Context

### The Cost Calculator Makes More Sense Now

Reading your architecture, I can see the calculator's assumptions map to real design decisions:

| Calculator Assumption | Architecture Reality | Alignment |
|---|---|---|
| 8-15 LLM calls per investigation | 3-node graph with self-healing loop (investigate → reject → investigate deeper) | ✅ Reasonable — could easily be 8-15 tool calls |
| Chat messages = 1.5-3K input tokens | Session-per-claim with full message history growing over conversation | ✅ History accumulates |
| Document vision costs | Document analysis is a real feature (13 checks per doc) | ✅ Mapped correctly |
| Separate chat vs. investigation costs | You literally have two LLM paths: `create_react_agent` for chat, `StateGraph` for deep investigation | ✅ Good separation |

### But Here's the Disconnect

Your POC is architecturally sophisticated but **operationally simple**:

| Architecture Says | Cost Calculator Assumes |
|---|---|
| Pickle cache, in-memory | RDS PostgreSQL Multi-AZ ($121/mo) |
| NetworkX in-process | (No graph DB cost, correct) |
| Single FastAPI process | ECS Fargate with auto-scaling ($144/mo) |
| No auth, single user | 50 concurrent examiners |
| Synthetic 500 claims pre-generated | 500 claims/day incoming |
| `_context` global | Redis-backed sessions ($25/mo) |

**The calculator is costing a system you haven't built yet.** Your POC probably runs on a single `t3.medium` EC2 instance (or even locally) plus Bedrock API calls.

---

## What I'd Add: A Phased Cost View

### Phase 0: Current POC (Where You Are)
| Component | Monthly Cost |
|---|---|
| Bedrock (dev/demo usage) | $20-80 |
| EC2 or local dev | $0-50 |
| S3 (if any) | $1 |
| **Total** | **$50-130/month** |

### Phase 1: Pilot (5-10 real examiners, real claims)
| Component | Monthly Cost |
|---|---|
| Bedrock (real usage, small scale) | $100-300 |
| ECS Fargate (single task) | $70 |
| RDS PostgreSQL (single-AZ, t3.small) | $50 |
| ElastiCache (t3.micro) | $13 |
| S3 + networking | $20 |
| **Total** | **$250-450/month** |

### Phase 2: Production (your calculator's scenario)
| Component | Monthly Cost |
|---|---|
| Everything in the calculator | $1,000-2,300 |

---

## Specific Feedback Given Your Architecture

### 1. The Investigation Cost Is Your Biggest Unknown 🔴

Your self-healing dossier loop is brilliant architecturally, but it's a **cost wildcard**:

```
investigate → assess → REJECT → investigate deeper → assess → REJECT → investigate deeper → accept → compile
```

Each loop iteration is multiple tool calls, each tool call sends the full `messages` history to Claude. By the 3rd loop, your input tokens could be 10-15K per call (accumulated history).

**What to instrument in POC:**
- Average loop count before dossier acceptance
- Token count growth per loop iteration
- How often `evidence_sufficient` flips on first pass vs. requiring re-investigation

### 2. Message History Accumulation Will Dominate Chat Costs 🟡

Your `CopilotSession` keeps full `messages: List[BaseMessage]`. By message 10 in a session, you're sending the entire conversation history (including all prior tool results) with every new message.

**Back-of-envelope:**
- Message 1: ~1K input tokens
- Message 5: ~5-8K input tokens (prior messages + tool results)
- Message 15: ~15-25K input tokens

The calculator assumes "1.5K-3K input per message" — this is probably the **average** but the **marginal cost per message increases** as the session grows. This is correct modeling if sessions are short (5-10 messages), but could underestimate if examiners have long sessions.

**What to instrument:** Average session length and token count at session end.

### 3. The "Rules First" Design Saves You Money 💰

This is undersold in the cost calculator. Because your architecture is:
```
Rules (free) → Risk Score (free) → LLM only for investigation/chat
```

Only 25% of claims hit the LLM for investigation. The other 75% are handled by deterministic rules + examiner review of pre-computed results. **This is a major cost advantage** over architectures that throw every claim at an LLM.

Worth calling out explicitly: *"Our architecture ensures 75% of claims never touch Bedrock, keeping AI costs proportional to complexity, not volume."*

### 4. Model Choice Discrepancy ⚠️

- Architecture says: **Claude 3.5 Haiku**
- Cost calculator says: **Claude Haiku 4.5** ($1.00/$5.00)

These are different models at different price points. Claude 3.5 Haiku (what you're actually using) is currently $0.25/$1.25 — **4x cheaper** than what the calculator assumes.

This means either:
- Your actual POC costs are **4x lower** than calculated (good news for budget)
- The calculator is forward-planning for model migration (valid, since Claude 3.x retirement is mentioned)

**Clarify this in the document.** It's confusing to have the architecture reference one model and the calculator price another.

### 5. The "What Would Change for Production" Table Is Gold

Your architecture doc already has this table. The cost calculator should **directly map to it**:

| Production Change | Cost Implication | Calculator Line Item |
|---|---|---|
| Pickle → PostgreSQL + Redis | +$146/mo | RDS + ElastiCache ✅ |
| Single user → RBAC/SSO | Cognito ~$5/mo | Not in calculator ❌ |
| NetworkX → Neptune | +$100-400/mo | **Missing** ❌ |
| Claude Haiku → Model routing (Haiku + Sonnet) | +30-50% on Bedrock | Partially captured ⚠️ |
| No encryption → HIPAA-compliant | KMS + compliance tooling | Partially captured ⚠️ |

---

## Top 3 Recommendations

### 1. Add a "POC Instrumentation Plan" to validate cost assumptions

```python
# Add to your agent callbacks
@tool_call_logger
def log_bedrock_usage(response):
    log({
        "claim_id": session.case_id,
        "path": "chat" | "investigation" | "vision",
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "loop_iteration": state.get("loop_count"),
        "tool_called": tool_name,
        "timestamp": now()
    })
```

Run 50 claims through the full pipeline. You'll have real data to replace every assumption.

### 2. Reconcile the model pricing

Either update the architecture to say "we'll migrate to Haiku 4.5" or update the calculator to show current 3.5 Haiku pricing alongside future pricing. Both are valid — just be explicit.

### 3. Add Neptune/graph DB costs if that's the production plan

Your entity graph is a core differentiator. If production means Neptune, that's $100-400/month that's currently invisible in the calculator.

---

## Summary

| Aspect | Rating | Comment |
|---|---|---|
| Accuracy of assumptions | 7/10 | Reasonable but unvalidated |
| Architecture alignment | 8/10 | Calculator maps well to real design |
| Stage-appropriateness | 6/10 | Costs a system 2 phases ahead |
| Usefulness for stakeholders | 8/10 | Good for "what will production cost" conversations |
| Actionability | 6/10 | Needs instrumentation plan to become real |

**It's a good artifact for the conversation you'll have with leadership about production investment. Just frame it as "projected production costs pending POC validation" — not "our budget."**