# VetoNet

**Semantic Firewall for AI Agent Transactions**

VetoNet prevents prompt injection attacks that manipulate AI agents into unauthorized purchases. It intercepts transactions, compares them against the user's original intent, and vetoes if something's wrong.

[![Live Demo](https://img.shields.io/badge/demo-veto--net.org-00FFD1)](https://veto-net.org)
[![API Status](https://img.shields.io/badge/API-live-00FF88)](https://veto-net.org/auth)

**Stats:** 4,200+ attacks tested | 96.6% blocked | 99.58% ML accuracy

---

## Quick Start

### Option 1: Hosted API (Recommended)

```python
import requests

response = requests.post(
    "https://web-production-fec907.up.railway.app/api/check",
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
from vetonet.langchain import protected_tool, init

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
│  Trained on 1,500+ real attacks | 99.58% F1 score              │
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
from vetonet.langchain import protected_tool, VetoNetGuard

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
curl -X POST https://web-production-fec907.up.railway.app/api/check \
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
| `none` | None | Deterministic only |

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

See [LICENSE](LICENSE) for details.
