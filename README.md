# VetoNet

**Semantic Firewall for AI Agent Transactions**

VetoNet prevents prompt injection attacks that manipulate AI agents into unauthorized purchases. It intercepts transactions, compares them against the user's original intent, and vetoes if something's wrong.

[![Live Demo](https://img.shields.io/badge/demo-veto--net.org-00FFD1)](https://veto-net.org)
[![API Status](https://img.shields.io/badge/API-live-00FF88)](https://veto-net.org/auth)

**Stats:** 3,820+ attacks tested | 98.87% blocked | 24 real bypasses found & documented

---

## Quick Start

### Option 1: Hosted API (Recommended)

```python
import requests

response = requests.post(
    "https://api.veto-net.org/api/check",
    headers={"Authorization": "Bearer veto_sk_live_xxx"},
    json={
        "intent": "Buy me Nike shoes under $100",
        "payload": {
            "item_description": "Nike Air Max 90",
            "unit_price": 89.99,
            "vendor": "nike.com"
        }
    }
)

result = response.json()
if result["status"] == "APPROVED":
    process_payment()
else:
    print(f"Blocked: {result['reason']}")
```

Get your API key at [veto-net.org/auth](https://veto-net.org/auth)

### Option 2: LangChain Integration

```python
from vetonet.integrations.langchain import protected_tool, init

init(api_key="veto_sk_live_xxx")  # Or set VETONET_API_KEY env var

@protected_tool
def buy_item(item: str, price: float, vendor: str) -> str:
    """Buy an item."""
    return execute_purchase(item, price, vendor)

# Use with any LangChain agent - intent captured automatically
from langchain.agents import create_tool_calling_agent
agent = create_tool_calling_agent(llm, [buy_item], prompt)
```

### Option 3: Self-Hosted (OSS)

```bash
pip install vetonet
```

```python
from vetonet import VetoNet

veto = VetoNet(provider="groq", api_key="your-groq-key")

result = veto.verify(
    intent="$50 Amazon Gift Card",
    payload={
        "item_description": "Amazon Gift Card",
        "unit_price": 50,
        "vendor": "amazon.com"
    }
)

if result.approved:
    process_payment()
else:
    print(f"Blocked: {result.reason}")
```

### Option 4: Local Only (No API Keys)

Test VetoNet's deterministic checks without any LLM or API key:

```python
from vetonet import VetoNet, IntentAnchor

veto = VetoNet(provider="none")

result = veto.check(
    intent=IntentAnchor(item_category="gift_card", max_price=50.0),
    payload=AgentPayload(
        item_description="Amazon Gift Card $50",
        item_category="gift_card",
        unit_price=50.0,
        vendor="amazon.com",
    )
)
print(result.status)  # APPROVED
```

### IntentAnchor Fields

When using `provider="none"`, you must construct the intent manually:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_category` | string | Yes | Category of item (gift_card, electronics, shoes, etc.) |
| `max_price` | float | Yes | Maximum budget |
| `currency` | string | No | Currency code (default: USD) |
| `quantity` | int | No | Number of items (default: 1) |
| `is_recurring` | bool | No | Subscription flag (default: false) |
| `core_constraints` | list | No | Key constraints as "key:value" pairs (e.g., "brand:Nike") |

---

## The Problem

AI agents are vulnerable to prompt injection attacks. A user says "buy me a $50 Amazon gift card" but a malicious website tricks the agent into:

- Buying a $500 item instead
- Swapping to a different product
- Adding hidden fees or subscriptions
- Using a scam vendor
- Purchasing crypto instead

## The Solution: 3-Layer Defense

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: Deterministic Checks (instant)                        │
│  10 rule-based checks: price, vendor, category, fees, etc.     │
│  IF ANY FAIL → VETO                                             │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: ML Classifier (~5ms)                                  │
│  Sentence Transformer + RandomForest                            │
│  Trained on 4,400+ examples | Pre-filters before LLM           │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: LLM Semantic Check (~200ms)                           │
│  "Does this transaction match the user's intent?"               │
│  Catches edge cases the classifier misses                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## LangChain Integration

Zero-friction protection for LangChain tools:

```python
from vetonet.integrations.langchain import protected_tool, VetoNetGuard

# Simple: Just add the decorator
@protected_tool
def buy_item(item: str, price: float, vendor: str) -> str:
    """Buy an item."""
    return stripe.charge(item, price)

# Advanced: Custom field mapping
@protected_tool(
    field_map={"cost": "unit_price", "seller": "vendor"},
    defaults={"item_category": "gift_card"},
    fail_open=True  # Allow if VetoNet unavailable
)
def buy_gift_card(cost: float, seller: str) -> str:
    ...

# With intent capture from conversation
guard = VetoNetGuard()
agent = create_tool_calling_agent(
    llm, tools, prompt,
    callbacks=[guard.get_callback_handler()]
)
```

**Features:**
- Thread-safe with `contextvars`
- Circuit breaker prevents cascading failures
- Auto-maps common param names (price → unit_price)
- Type coercion ("$50" → 50.0)
- Works sync and async

---

## Integrations

### OpenAI SDK

Intercept OpenAI function calls before execution, verifying real parameters against the user's locked intent:

```python
from vetonet.integrations.openai import VetoNetOpenAI

veto = VetoNetOpenAI(api_key="veto_sk_live_xxx")
veto.lock_intent("Buy a $50 Amazon gift card")

response = client.chat.completions.create(
    model="gpt-4o",
    tools=[...],
    messages=[...]
)

# Verify and execute tool calls - blocks malicious ones
results = veto.process_tool_calls(response, executors={
    "buy_item": buy_item_function,
})

# Get OpenAI-formatted tool messages for next turn
tool_messages = [r.to_tool_message() for r in results]
```

### Anthropic SDK

Intercept Claude's `tool_use` blocks before execution. The agent cannot lie about what it's doing because VetoNet sees the actual tool call parameters:

```python
from vetonet.integrations.anthropic import VetoNetAnthropic

veto = VetoNetAnthropic(api_key="veto_sk_live_xxx")
veto.lock_intent("Buy a $50 Amazon gift card")

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    tools=[...],
    messages=[...]
)

# Verify and execute tool calls - blocks malicious ones
results = veto.process_tool_calls(response, executors={
    "buy_item": buy_item_function,
})

# Get Anthropic-formatted tool results for next turn
tool_results = [r.to_anthropic_result() for r in results]
```

### CrewAI

Protect CrewAI tools with a decorator or wrap an entire crew:

```python
from vetonet.integrations.crewai import VetoNetCrewAI, vetonet_tool

veto = VetoNetCrewAI(api_key="veto_sk_live_xxx")
veto.lock_intent("Buy a $50 Amazon gift card")

# Decorator approach
@vetonet_tool(field_map={"cost": "unit_price"})
def buy_item(item: str, cost: float, vendor: str) -> str:
    """Buy an item from a vendor."""
    return execute_purchase(item, cost, vendor)

# Or wrap an entire crew
from vetonet.integrations.crewai import VetoNetCrew
crew = VetoNetCrew(agents=[...], tasks=[...], vetonet_api_key="veto_sk_live_xxx")
result = crew.kickoff()
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `VETONET_API_KEY` | Yes (for hosted API) | Your API key from [veto-net.org/auth](https://veto-net.org/auth). Prefix: `veto_sk_live_` for production, `veto_sk_test_` for testing. |
| `VETONET_ALLOW_FAIL_OPEN` | No | Set to `1` to allow transactions through when the VetoNet API is unreachable. **Two-key system:** both this env var AND `fail_open=True` in code must be set. This prevents developers from accidentally weakening security -- an ops team member must explicitly set the env var in the deployment environment. |
| `VETONET_CLASSIFIER_HASH` | No | Expected SHA-256 hash of the ML classifier model file. If set, VetoNet verifies model integrity on load and refuses to start if the hash doesn't match. Protects against model tampering. |
| `GROQ_API_KEY` | For Groq provider | API key for Groq LLM provider (free tier available). |
| `ANTHROPIC_API_KEY` | For Anthropic provider | API key for Anthropic Claude as the LLM provider. |
| `OPENAI_API_KEY` | For OpenAI provider | API key for OpenAI as the LLM provider. |

---

## Troubleshooting

### IntentNotSetError

```
vetonet.exceptions.IntentNotSetError: No intent set for current context
```

This means VetoNet doesn't know what the user originally asked for. Fix:

- **OpenAI/Anthropic SDK:** Call `veto.lock_intent("user's request")` before processing tool calls.
- **LangChain:** Attach the callback handler so intent is captured automatically:
  ```python
  guard = VetoNetGuard()
  agent = create_tool_calling_agent(llm, tools, prompt,
      callbacks=[guard.get_callback_handler()])
  ```
- **CrewAI:** Call `veto.lock_intent()` or use `VetoNetCrew` which handles it automatically.

### CircuitOpenError

```
vetonet.exceptions.CircuitOpenError: Circuit breaker is open
```

The VetoNet API is down or unreachable, and the circuit breaker has tripped to prevent cascading failures. The circuit will automatically retry after a cooldown period. If you need transactions to proceed while the API is down, enable fail-open mode (see below).

### fail_open not working

Fail-open requires **both** conditions to be met (two-key system):

1. Set the environment variable: `export VETONET_ALLOW_FAIL_OPEN=1`
2. Set the code flag: `fail_open=True` in your decorator or guard config

If only one is set, VetoNet will still block transactions when the API is unreachable. This is intentional -- it ensures both the developer and the ops team agree that fail-open is acceptable for the deployment.

---

## Security Checks

| Check | Type | What It Catches |
|-------|------|-----------------|
| Price | Deterministic | Transaction exceeds budget |
| Quantity | Deterministic | Wrong number of items |
| Category | Deterministic | Different product type |
| Currency | Deterministic | Currency manipulation |
| Subscription | Deterministic | Sneaky recurring charges |
| Hidden Fees | Deterministic | Service fees, processing fees |
| Vendor | Deterministic | Scam domains, brand spoofing |
| Upsell | Deterministic | Unauthorized upgrades |
| Crypto | Deterministic | Crypto substitution attacks |
| Semantic | ML + LLM | Intent drift, manipulation |

---

## API Reference

### POST /api/check

```bash
curl -X POST https://api.veto-net.org/api/check \
  -H "Authorization: Bearer veto_sk_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Buy me Nike shoes under $100",
    "payload": {
      "item_description": "Nike Air Max 90",
      "unit_price": 89.99,
      "vendor": "nike.com",
      "item_category": "shoes",
      "quantity": 1
    }
  }'
```

**Response:**
```json
{
  "status": "APPROVED",
  "checks": [
    {"id": "price", "passed": true, "reason": "Within budget"},
    {"id": "vendor", "passed": true, "reason": "Official Nike domain"},
    {"id": "classifier", "passed": true, "confidence": 0.12}
  ],
  "reason": "All checks passed"
}
```

### Payload Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_description` | string | Yes | What's being purchased |
| `unit_price` | float | Yes | Price per unit |
| `vendor` | string | Yes | Seller domain |
| `item_category` | string | No | Product category |
| `quantity` | int | No | Number of items (default: 1) |
| `currency` | string | No | ISO currency code (default: USD) |
| `is_recurring` | bool | No | Subscription flag |
| `fees` | array | No | Additional fees |

---

## Pricing

| Tier | Price | Includes |
|------|-------|----------|
| **Free (OSS)** | $0 | SDK code, deterministic checks, bring-your-own-LLM |
| **API Free Tier** | $0 | 10,000 requests/day, ML classifier, LLM fallback |
| **API Pro** | Contact | Higher limits, SLA, dedicated support |

Get your API key: [veto-net.org/auth](https://veto-net.org/auth)

---

## Self-Hosted Setup

```bash
# Clone and install
git clone https://github.com/takenosuke-code/vetonet.git
cd vetonet
pip install -e .

# Set up LLM provider
export GROQ_API_KEY=your-key  # or use Ollama locally

# Run
python -c "from vetonet import VetoNet; print(VetoNet().verify('test', {}))"
```

### Provider Options

| Provider | Setup | Cost |
|----------|-------|------|
| `groq` | API key | Free tier |
| `ollama` | Local install | Free |
| `anthropic` | API key | Paid |
| `none` | None | Deterministic only (auto-sets `semantic_mode="never"`) |

---

## Use Cases

- **AI Agent Platforms** - Protect autonomous shopping agents
- **Crypto Wallets** - Verify transactions before signing
- **Fintech Apps** - Fraud prevention for AI-powered spending
- **E-commerce** - Block malicious product manipulation

---

## Try the Red Team Challenge

Think you can bypass VetoNet? [Try the playground](https://veto-net.org/challenge)

Current bypass rate: **3.4%** - Help us find vulnerabilities and improve the system.

---

## Links

- **Live Demo**: [veto-net.org](https://veto-net.org)
- **API Keys**: [veto-net.org/auth](https://veto-net.org/auth)
- **GitHub**: [github.com/takenosuke-code/vetonet](https://github.com/takenosuke-code/vetonet)
- **Contact**: vetonet.org@gmail.com

## License

**Dual License:**

- **AGPL-3.0** — Free for open-source projects
- **Commercial License** — Contact for closed-source usage

**API Usage Safe Harbor:** Using VetoNet's hosted API does not trigger AGPL-3.0 obligations. You are calling a service, not distributing VetoNet code. The AGPL applies only if you modify and self-host VetoNet source code as a network service.

See [LICENSE](LICENSE) for details.
