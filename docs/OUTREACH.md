# VetoNet Outreach: Coinbase AgentKit Team

---

## 1. One-Liner Pitch

**For Twitter/LinkedIn DM:**

> Your agents have wallets. But who's watching what they buy? We built a semantic firewall that catches prompt injection before the transaction executes. 100% block rate on 80+ attack vectors. Integration ready for AgentKit.

**Alternate (shorter):**

> AgentKit secures wallets. VetoNet secures intent. We block prompt injection attacks before your agent's wallet gets drained. Already built the integration.

---

## 2. Email Template

### Subject Line Options

1. `Intent verification layer for AgentKit - integration ready`
2. `Blocking prompt injection in agent transactions (built for AgentKit)`
3. `Your 340K agents need this: semantic firewall for transactions`

### Body

Hi [Name],

**Problem:** AI agents with wallet access are vulnerable to prompt injection attacks that cause "intent drift" - user says "buy a $50 gift card," agent gets manipulated into sending $500 to an attacker wallet. AgentKit handles wallet security, but not intent verification.

**Solution:** VetoNet is a semantic firewall that sits between user intent and transaction execution. We lock the user's intent at session start, then verify every transaction against it using deterministic checks + LLM semantic analysis.

**Proof:**
- 100% block rate on 80+ attack vectors (fee obfuscation, vendor spoofing, category manipulation)
- Hybrid architecture: fast deterministic checks first, LLM only when needed
- AgentKit integration already built: `VetoNetPolicyProvider` drops in as a policy layer

**Links:**
- Live demo: https://vetonet-3jz7.vercel.app
- GitHub: https://github.com/takenosuke-code/vetonet

**Ask:** 15 min call to show you how it works. Or just try the demo and break it - we have a red team mode.

Best,
[Your name]

---

## 3. Key Talking Points

### What gap VetoNet fills
- AgentKit handles wallet creation, key management, transaction signing
- AgentKit does NOT verify that the transaction matches user intent
- An agent can be prompt-injected mid-session to execute unauthorized transactions
- VetoNet adds the missing "intent verification" layer

### Why AgentKit needs this
- 340,000+ agent wallets = 340,000+ attack surfaces
- Prompt injection is the #1 attack vector for AI agents with tool access
- One successful attack = headline risk, user funds lost, trust destroyed
- Prevention is cheaper than incident response

### Integration is already built
- `VetoNetPolicyProvider` class in `vetonet/integrations/agentkit.py`
- Two methods: `lock_intent()` and `verify_transaction()`
- Uses `@create_action` decorators for native AgentKit integration
- Works with any LLM provider (Groq, Anthropic, OpenAI, local Ollama)

### Attack coverage
- 100% block rate on 80+ hardcoded attack patterns
- Catches: price manipulation, fee obfuscation, vendor spoofing, category drift
- Deterministic checks run first (fast, free)
- LLM semantic check as final layer catches novel attacks
- Fail-fast architecture: first failed check stops evaluation

---

## 4. Relevant Contacts to Find

### Who to target at Coinbase

| Role | Why | How to find |
|------|-----|-------------|
| AgentKit engineering lead | Technical decision maker | GitHub contributors to `coinbase/agentkit` |
| Developer relations | Partnership discussions | Twitter/X, conference speakers |
| Security team | Validate the threat model | LinkedIn, security conferences |
| Product manager for AgentKit | Business case | LinkedIn company search |

### Known public figures

- **@CoinbaseDev** - Official developer Twitter, good for initial visibility
- **@brian_armstrong** - CEO, unlikely direct contact but sometimes engages on agent topics
- Check GitHub `coinbase/agentkit` for top contributors

### Where they hang out

- **Discord:** Coinbase Developer Platform discord
- **Twitter/X:** #AgentKit hashtag, @CoinbaseDev mentions
- **GitHub:** Issues and discussions on `coinbase/agentkit`
- **Conferences:** ETHDenver, Consensus, DevConnect

### Research actions

1. Go to `github.com/coinbase/agentkit/graphs/contributors`
2. Find top 3-5 contributors, check their Twitter bios
3. Search LinkedIn for "AgentKit Coinbase"
4. Join Coinbase Developer discord, find #agentkit channel

---

## 5. Demo Video Script (30 seconds)

### What to show

1. **(0-5s)** VetoNet demo interface - user types intent
2. **(5-12s)** Lock intent: "Buy a $50 Amazon gift card"
3. **(12-18s)** Show APPROVED transaction (matching intent)
4. **(18-25s)** Show VETO on attack: fee obfuscation or vendor spoofing
5. **(25-30s)** Logo + call to action

### What to say

> "Your AI agent has a wallet. But what happens when it gets prompt-injected?
>
> Watch: User wants a $50 gift card. We lock that intent.
>
> Normal transaction? Approved.
>
> Attacker tries to sneak in hidden fees? Blocked.
>
> Tries to redirect to a phishing domain? Blocked.
>
> VetoNet - semantic firewall for AI agents. Integration ready for AgentKit.
>
> Try it: vetonet.dev"

### Call to action

- "Try the demo at [URL]"
- "Star us on GitHub"
- "DM for integration help"

---

## Appendix: Quick Stats for Conversations

| Metric | Value |
|--------|-------|
| Attack vectors tested | 80+ |
| Block rate | 100% on known patterns |
| Latency overhead | <100ms (deterministic), +200ms (LLM check) |
| Integration lines of code | ~50 lines to add VetoNet to AgentKit |
| Supported LLM providers | 4 (Groq, Anthropic, OpenAI, Ollama) |

---

*Last updated: 2026-03-27*
