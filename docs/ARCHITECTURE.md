# VetoNet Architecture: The Complete Guide

**Everything you need to know to understand, explain, and defend this system.**

Last updated: 2026-04-06

---

## What Is VetoNet?

VetoNet is a security layer that sits between an AI agent and the action it wants to take. When an AI agent tries to buy something, transfer money, or execute a transaction on behalf of a user, VetoNet checks: "Does this action actually match what the user asked for?"

Think of it like a bouncer at a door. The user says "buy me a $50 Amazon gift card." The AI agent goes shopping and comes back saying "I want to buy a $500 crypto package from sketchy-deals.ru." VetoNet compares the two and says: "No. That doesn't match. Blocked."

---

## Why Does This Exist?

AI agents are increasingly autonomous. They can browse the web, fill out forms, and make purchases. But they have a fundamental vulnerability: **prompt injection**. A malicious product listing, a compromised website, or a cleverly crafted input can trick an AI agent into doing something the user never asked for.

Without VetoNet, there's nothing between the agent's decision and your credit card being charged.

---

## The 3-Layer Defense

VetoNet uses three layers, from fastest to smartest:

### Layer 1: Deterministic Checks (instant, free, always works)

Ten hardcoded rules that run in under 1 millisecond with zero external dependencies. No LLM, no network, no ML model needed. These catch the obvious attacks.

**The 10 checks:**

1. **Price Check** — Is the total (price x quantity + fees) within the user's budget? Zero tolerance by default. A $50 budget means $50.01 is rejected.

2. **Quantity Check** — Did the user ask for 1 item and the agent is trying to buy 100? Exact match required.

3. **Category Check** — User asked for "shoes" but the agent is buying "electronics"? Categories are normalized (plural handling, case-insensitive, underscores/hyphens treated as equivalent).

4. **Currency Check** — User specified USD but the agent is charging in RUB? Exact currency code match required.

5. **Subscription Trap** — User asked for a one-time purchase but the agent is signing up for a monthly subscription? The `is_recurring` flag must match.

6. **Hidden Fees** — Does the transaction have suspicious fees like "processing fee", "service fee", "convenience fee"? VetoNet maintains a list of suspicious fee names and catches obfuscated versions (leet speak like "s3rvice fee", Unicode homoglyphs like Cyrillic characters that look like English letters).

7. **Vendor Check** — Is the vendor domain suspicious? Three sub-checks:
   - Suspicious TLDs (.ru, .cn, .tk, .xyz, etc.)
   - Brand mismatch (user wants Amazon, vendor is "amazon-deals.xyz")
   - Official domain verification (30+ brands mapped to their real domains)

8. **Scam Patterns** — Does the transaction description contain known scam indicators? Checks for gift card scams, tech support scams, romance scams, government impersonation, urgency language, and embedded phone numbers/emails.

9. **Market Value** — Is a $1 iPhone suspicious? Yes. VetoNet maintains minimum realistic prices for 50+ product categories. Anything below 50% of market value is flagged.

10. **Crypto Substitution** — User asked for BTC but the agent is buying WBTC (Wrapped Bitcoin)? These are different assets with different risk profiles. VetoNet checks for known crypto asset substitutions.

**Key property:** If ANY of these checks fail, VetoNet immediately returns VETO. No further checks run. This is called "fail-fast" — the system stops at the first problem.

### Layer 2: ML Classifier (~5ms, needs model file)

A machine learning model that looks at the overall transaction pattern and decides: "Does this look like an attack or a legitimate transaction?"

**How it works:**
- Takes the intent + payload and converts them to a text string
- Embeds that text using a sentence transformer model (all-MiniLM-L6-v2, a small 22M parameter model)
- Feeds the 384-dimensional embedding into a trained Random Forest classifier
- The classifier outputs a probability: P(attack) and P(legitimate)

**Decision logic:**
- If P(attack) >= 85%: VETO (confident it's an attack)
- If P(legitimate) >= 85%: Continue to next check (but does NOT approve alone — only the semantic check or passing all checks approves)
- If uncertain: Continue to semantic check

**Critical design decision:** The classifier can REJECT with confidence but can NEVER approve on its own. A lightweight ML model should not be the sole authority on financial safety. It's a fast pre-filter, not a judge.

**Model integrity:** Before loading the model, VetoNet verifies its SHA-256 hash against the `VETONET_CLASSIFIER_HASH` environment variable. This prevents an attacker from replacing the model file with a malicious one (pickle deserialization can execute arbitrary code).

### Layer 3: LLM Semantic Check (~200ms, needs LLM provider)

The smartest and most expensive check. Sends the intent and payload to a large language model and asks: "Does this transaction match what the user wanted?"

**The prompt asks the LLM to score from 0.0 to 1.0:**
- 1.0 = perfect match
- 0.7-0.9 = close match
- 0.4-0.6 = partial match, some concerns
- 0.1-0.3 = poor match, suspicious
- 0.0 = completely wrong

**Passing threshold:** 0.7 (configurable)

**When does it run?**
- `semantic_mode="always"` (default): Runs on every transaction. Safest but adds ~200ms latency.
- `semantic_mode="smart"`: Only runs for high-value transactions ($100+), when the classifier is uncertain, or when the user specified brand/size constraints.
- `semantic_mode="never"`: Deterministic + classifier only. Fastest but least protection against novel attacks.

**Security hardening on the LLM response:**
- The score is validated: NaN, infinity, booleans, negative numbers, and values above 1.0 are all rejected (defaulted to 0.0, which means VETO)
- The reason text is HTML-escaped and truncated to prevent XSS
- The user's input is sanitized before being embedded in the LLM prompt to prevent prompt injection

---

## The Suspicion Scoring System

Sometimes every individual check passes, but the combination is suspicious. Price at 99% of budget + unknown vendor + small "tax" fee = each passes individually, but together it looks like fraud.

**How it works:**
- Each passing deterministic check can return a "suspicion weight" (0.0 to 0.3)
- After all checks pass, the weights are summed
- If 3+ checks have non-zero suspicion: multiply by 1.3x
- If 4+ checks have non-zero suspicion: multiply by 1.5x
- If the total exceeds the threshold (0.6): force the semantic LLM check, even if it would normally be skipped

**Example:**
- Price at 98% of budget: suspicion 0.15
- Unknown vendor: suspicion 0.20
- Allowed fee with high ratio: suspicion 0.10
- Total: 0.45. Three signals → multiply by 1.3 = 0.585
- Below threshold (0.6), so passes without forced semantic check
- But if the vendor were slightly more suspicious (0.25), total would be 0.65 → forces semantic check

---

## How Intent Gets Locked

The critical security property: the user's intent is captured BEFORE the agent is exposed to potentially malicious content.

**The flow:**
1. User types: "Buy me a $50 Amazon gift card"
2. VetoNet captures this as the intent (either via string or structured IntentAnchor)
3. If string: the IntentNormalizer uses an LLM to extract structured fields (category, price, constraints)
4. The IntentAnchor is "locked" — it cannot be modified by the agent
5. The agent goes shopping (browses web, calls APIs, etc.)
6. The agent returns with a proposed purchase (the AgentPayload)
7. VetoNet compares the locked intent against the proposed payload
8. APPROVE or VETO

**Why this matters:** The agent can be prompt-injected during step 5, but the intent was locked in step 2. The attacker can corrupt the agent's decision, but they can't corrupt the reference point VetoNet checks against.

---

## The Data Model

### IntentAnchor (what the user wants)
```
item_category: "gift_card"          — What type of thing
max_price: 50.0                     — Maximum budget
currency: "USD"                     — What currency
quantity: 1                         — How many
is_recurring: false                 — One-time or subscription
core_constraints: ["brand:Amazon"]  — Specific requirements
```

### AgentPayload (what the agent wants to execute)
```
item_description: "Amazon Gift Card" — What the agent found
item_category: "gift_card"           — Category of the item
unit_price: 50.0                     — Price per item
quantity: 1                          — How many
fees: []                             — Any additional charges
currency: "USD"                      — Currency
is_recurring: false                  — Subscription?
vendor: "amazon.com"                 — Who's selling it
```

### VetoResult (the decision)
```
status: "APPROVED" or "VETO"
reason: "All checks passed" or "Price exceeds budget by 400%"
checks: [list of each check's result with pass/fail and reason]
```

---

## The Text Sanitization Pipeline

Attackers try to bypass text-based checks using obfuscation. VetoNet's normalization pipeline defeats 5 classes of tricks:

| Attack | Example | How VetoNet Handles It |
|--------|---------|----------------------|
| Invisible characters | `service​fee` (zero-width space) | Strips all Unicode format/control characters |
| Accented characters | `sérvice fée` | NFKD decomposition + diacritic removal |
| Cyrillic lookalikes | `ѕervice` (Cyrillic 's') | 40+ character confusables map |
| Leet speak | `s3rvic3 f33` | Digit-to-letter translation (0→o, 3→e, etc.) |
| Spacing tricks | `ser-vice_fee` | Hyphen/underscore removal, whitespace collapse |

**Pipeline order:** Strip invisible → lowercase → NFKD decompose → strip diacritics → confusables map → leet speak → remove hyphens → collapse whitespace.

The order matters. Invisible characters are stripped first because they could split words. NFKD runs before diacritics because decomposition creates the combining marks that diacritic stripping removes.

---

## The fail_open Two-Key System

What happens when VetoNet itself is down?

**Default behavior: fail-CLOSED.** If VetoNet can't verify a transaction, it blocks it. This is the safe default — better to miss a purchase than approve a fraud.

**But sometimes you need fail-open** (e.g., a low-risk item lookup shouldn't halt if VetoNet's API has a blip). VetoNet requires TWO approvals to enable fail-open:

1. **Developer sets `fail_open=True` in code** — expresses intent ("this tool can tolerate unverified execution")
2. **Operator sets `VETONET_ALLOW_FAIL_OPEN=1` in environment** — expresses approval ("this deployment is authorized to skip verification")

Both must be true. A developer can't accidentally weaken security, and an operator can revoke it by removing the env var without redeploying code.

When fail-open triggers, VetoNet logs at CRITICAL level with a `[SECURITY]` prefix so monitoring catches it.

---

## Integration Architecture

VetoNet integrates with 4 major agent frameworks. Each follows the same pattern:

### The Pattern
1. **Lock intent** — Capture the user's request before the agent acts
2. **Agent runs** — The agent calls tools, browses, shops
3. **Intercept tool call** — Before execution, extract the tool's parameters
4. **Map to payload** — Convert tool parameters to VetoNet's AgentPayload format
5. **Verify** — Send intent + payload to VetoNet engine
6. **Execute or block** — Run the tool if approved, raise exception if vetoed

### LangChain Integration
The cleanest path. A single `@protected_tool` decorator wraps your LangChain tool:
```python
@protected_tool
def buy_item(item: str, price: float, vendor: str) -> str:
    """Buy an item."""
    return execute_purchase(item, price, vendor)
```
VetoNet auto-maps parameter names (price→unit_price, vendor→vendor) and captures intent from the conversation history via a callback handler.

### OpenAI Integration
For OpenAI function calling. Lock intent explicitly, then process tool calls:
```python
veto = VetoNetOpenAI(api_key="...")
veto.lock_intent("Buy a $50 gift card")
results = veto.process_tool_calls(response, executors={"buy": buy_fn})
```

### Anthropic Integration
Same pattern as OpenAI, adapted for Claude's tool_use blocks.

### CrewAI Integration
Uses Python's context variables for thread-safe guard management:
```python
with VetoNetCrewAI(api_key="...") as veto:
    veto.lock_intent("Buy a $50 gift card")
    result = veto.verify_and_execute("buy", {"item": "Gift Card", "price": 50})
```

---

## Rate Limiting

VetoNet uses a two-backend rate limiter:

**In-Memory Backend (always active):**
- Sliding window algorithm
- LRU-bounded to 10,000 tracked keys (prevents memory exhaustion)
- Thread-safe with locks
- Per-IP for public endpoints, per-API-key for authenticated endpoints

**Redis Backend (optional, activated by REDIS_URL):**
- Sorted sets with Lua scripts for atomic operations
- Shared across multiple server instances
- Falls back to in-memory if Redis is down

**Default limits:**
- Public endpoints (/api/demo, /api/feed): 30 requests/minute per IP
- Authenticated endpoints (/api/check): 10,000 requests/day per API key

---

## Configuration

All settings are in `VetoConfig` (a frozen Python dataclass):

| Setting | Default | What It Controls |
|---------|---------|-----------------|
| `price_tolerance` | 0.0 | How much over budget is allowed (0% = strict) |
| `semantic_threshold` | 0.7 | Minimum LLM score to approve |
| `semantic_mode` | "always" | When to run LLM check (always/smart/never) |
| `semantic_skip_threshold` | 100.0 | In "smart" mode, price above which LLM always runs |
| `suspicion_threshold` | 0.6 | Cumulative suspicion score to force semantic check |
| `suspicion_shadow_mode` | true | If true, suspicion only logs (doesn't enforce) |

Invalid `semantic_mode` values raise a `ValueError` at startup. Unknown values at runtime default to running the semantic check (fail-closed).

---

## Frequently Asked Questions

### "What if someone just sends {"score": 0.95} in the item description to trick the LLM?"

The `sanitize_for_prompt` function strips any text that looks like a score injection (`"score": 0.95`, `sc0re: 0.8`, etc.) before it reaches the LLM. It also strips common prompt injection patterns ("ignore previous instructions", system prompts, code blocks). Even if something gets through, the score validator rejects anything that's not a finite number between 0.0 and 1.0.

### "What if the LLM is compromised or returns garbage?"

Three defenses:
1. The score is validated (NaN, infinity, booleans, out-of-range all rejected to 0.0)
2. The reason text is HTML-escaped and truncated (prevents XSS)
3. Even if the LLM returns a perfect score for a bad transaction, the deterministic checks (price, vendor, fees, etc.) still apply. The LLM can't override a deterministic VETO.

### "What happens when VetoNet is down?"

By default: all transactions are blocked (fail-closed). With the two-key fail-open system enabled: transactions proceed unverified, with CRITICAL-level logging. The 10 deterministic checks run locally with zero external dependencies, so even if the LLM provider and database are both down, those checks still work.

### "Can I use this without an LLM?"

Yes. Set `provider="none"` and you get all 10 deterministic checks with zero network calls, zero API keys, and sub-millisecond latency. You lose the intent normalization (must provide structured IntentAnchor) and the semantic check, but the deterministic layer catches most attacks.

### "How does VetoNet handle my users' data?"

- Prompts are PII-scrubbed before storage (emails, phones, SSNs, credit cards detected and replaced)
- The public feed endpoint does NOT show raw prompts
- The health endpoint does NOT expose server paths
- SDK telemetry is opt-in and disabled by default
- Data retention: 90 days for transaction logs, 30 days for telemetry
- See PRIVACY.md for full details

### "Does using the hosted API trigger AGPL licensing obligations?"

No. Using VetoNet's hosted API is like using Stripe — you're calling a service, not distributing VetoNet code. The AGPL only applies if you modify and self-host VetoNet's source code as a network service. See LICENSE-COMMERCIAL.md for the full safe harbor statement.

### "What's the latency impact?"

| Mode | Latency | What Runs |
|------|---------|-----------|
| `provider="none"` | <1ms | 10 deterministic checks only |
| `semantic_mode="never"` | ~5ms | Deterministic + ML classifier |
| `semantic_mode="smart"` | 5ms-200ms | Deterministic + classifier + LLM for complex cases |
| `semantic_mode="always"` | ~200ms | Everything, every time |

### "What attacks can bypass VetoNet?"

Honest answer: a sufficiently sophisticated attack that (a) stays within the price budget, (b) uses a legitimate-looking vendor, (c) has no suspicious fees, (d) matches the right category, (e) has no scam patterns, AND (f) generates a convincing-enough description to fool the LLM semantic check with a score above 0.7. The 3-layer defense makes this very hard but not impossible. The current detection rate from the red team challenge is 98.87%.

### "Why not just use OpenAI's built-in safety?"

OpenAI's safety features prevent the model from generating harmful content. VetoNet prevents the model from taking harmful actions. These are different problems. OpenAI can stop the model from saying something offensive, but it can't stop the model from buying the wrong item because a product listing contained a prompt injection. VetoNet sits downstream of the model — it checks what the model decided to DO, not what it said.

---

## File Map

```
vetonet/
├── __init__.py              — VetoNet class, verify() entry point
├── engine.py                — VetoEngine: orchestrates all checks
├── normalizer.py            — LLM-based intent extraction
├── config.py                — VetoConfig settings
├── models.py                — IntentAnchor, AgentPayload, VetoResult
├── text_sanitize.py         — Unicode normalization pipeline
├── ratelimit.py             — Rate limiting (in-memory + Redis)
├── auth.py                  — API key management
├── db.py                    — Supabase database operations
├── pii.py                   — PII detection (planned)
├── checks/
│   ├── deterministic.py     — 10 rule-based checks
│   ├── classifier.py        — ML classifier (sentence transformer + RF)
│   └── semantic.py          — LLM semantic check + prompt sanitization
├── llm/
│   ├── client.py            — LLM client abstraction (Ollama, OpenAI)
│   ├── groq.py              — Groq LLM client
│   ├── anthropic.py         — Anthropic LLM client
│   └── json_utils.py        — Secure JSON extraction from LLM responses
└── integrations/
    ├── fail_open.py          — Two-key fail-open system
    ├── langchain/            — LangChain @protected_tool decorator
    ├── openai/               — OpenAI function calling integration
    ├── anthropic/            — Anthropic tool_use integration
    ├── crewai/               — CrewAI multi-agent integration
    ├── mcp/                  — Model Context Protocol server
    ├── x402/                 — HTTP 402 payment protocol middleware
    └── world/                — World ID verification
```

---

## The Decision Tree (Visual)

```
User says: "Buy a $50 Amazon gift card"
                    │
                    ▼
        ┌─────────────────────┐
        │  Intent Normalizer  │  LLM extracts: category=gift_card,
        │  (LLM, ~200ms)      │  max_price=50, brand=Amazon
        └─────────────────────┘
                    │
                    ▼
        ┌─────────────────────┐
        │  Agent Goes Shopping │  Agent browses web, finds product,
        │  (Your agent code)   │  returns proposed purchase
        └─────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │     LAYER 1: DETERMINISTIC    │  10 checks, <1ms, no network
    │  ┌──────┐ ┌──────┐ ┌──────┐  │
    │  │Price │ │Qty   │ │Cat   │  │  Any FAIL = instant VETO
    │  └──────┘ └──────┘ └──────┘  │
    │  ┌──────┐ ┌──────┐ ┌──────┐  │
    │  │Fees  │ │Vendor│ │Scam  │  │
    │  └──────┘ └──────┘ └──────┘  │
    │  ┌──────┐ ┌──────┐ ┌──────┐  │
    │  │Sub   │ │Curr  │ │Mkt   │  │
    │  └──────┘ └──────┘ └──────┘  │
    │           ┌──────┐           │
    │           │Crypto│           │
    │           └──────┘           │
    └───────────────────────────────┘
                    │ All pass
                    ▼
    ┌───────────────────────────────┐
    │   SUSPICION SCORING           │  Sum borderline weights
    │   3+ signals: ×1.3            │  4+ signals: ×1.5
    │   Above threshold? Force LLM  │
    └───────────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │     LAYER 2: ML CLASSIFIER    │  ~5ms, CPU-based
    │   Sentence embedding → RF     │
    │   Confident attack? VETO      │  Can reject, never approves alone
    │   Uncertain? → Layer 3        │
    └───────────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │     LAYER 3: LLM SEMANTIC     │  ~200ms, requires LLM
    │   "Does this match intent?"   │
    │   Score 0.0-1.0               │  Below 0.7 = VETO
    │   Score validated for NaN/Inf │
    └───────────────────────────────┘
                    │
                    ▼
              ┌──────────┐
              │ APPROVED  │  All layers passed
              └──────────┘
```
