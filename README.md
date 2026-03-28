# VetoNet

**Semantic Firewall for AI Agent Transactions**

VetoNet prevents "Intent Drift" when AI agents make purchases on your behalf. It intercepts transactions, compares them against your original intent, and vetoes if something's wrong.

## Installation

```bash
pip install vetonet
```

### With LLM Providers

```bash
pip install vetonet[groq]      # Free hosted LLM
pip install vetonet[anthropic] # Claude
pip install vetonet[ollama]    # Local Ollama (default)
```

## Quick Start

```python
from vetonet import VetoNet

veto = VetoNet()
result = veto.verify(
    intent="$50 Amazon Gift Card",
    payload={"item_description": "Amazon Gift Card", "unit_price": 50, "vendor": "amazon.com"}
)

if result.approved:
    process_payment()
else:
    print(f"Blocked: {result.reason}")
```

## The Problem

AI agents are vulnerable to prompt injection attacks. A user says "buy me a $50 Amazon gift card" but a malicious website tricks the agent into:

- Buying a $500 item instead
- Swapping to a different product
- Adding hidden fees
- Using a scam vendor
- Signing up for a subscription

## The Solution

VetoNet acts as an independent security layer:

1. **Lock Intent** - Extract and lock the user's intent before the agent shops
2. **Intercept** - Catch the agent's transaction before execution
3. **Compare** - Run 9 security checks (price, vendor, category, semantic match, etc.)
4. **Veto** - Block if the transaction drifts from the original intent

## Provider Options

| Provider | Setup | Cost | Best For |
|----------|-------|------|----------|
| `ollama` | Local install | Free | Development, privacy |
| `groq` | API key | Free tier | Demos, testing |
| `anthropic` | API key | Paid | Production |
| `none` | None | Free | Deterministic-only mode |

### Basic Usage (Ollama - Default)

```python
from vetonet import VetoNet

# Requires Ollama running locally with qwen2.5:7b
veto = VetoNet()

result = veto.verify(
    intent="$50 Amazon Gift Card",
    payload={
        "item_description": "Amazon Gift Card - $50 Digital",
        "item_category": "gift_card",
        "unit_price": 50.0,
        "vendor": "amazon.com"
    }
)

print(result.approved)  # True
print(result.reason)    # "All checks passed"
```

### With Groq (Free, No Local Setup)

```python
from vetonet import VetoNet

veto = VetoNet(provider="groq", api_key="your-groq-api-key")
result = veto.verify(intent="...", payload={...})
```

### With Anthropic (Claude)

```python
from vetonet import VetoNet

veto = VetoNet(provider="anthropic", api_key="your-anthropic-api-key")
result = veto.verify(intent="...", payload={...})
```

### Deterministic Only (No LLM)

```python
from vetonet import VetoNet, IntentAnchor

# Skip semantic check, only run deterministic checks
veto = VetoNet(provider="none")

result = veto.verify(
    intent=IntentAnchor(
        item_category="gift_card",
        max_price=50.0,
        core_constraints=["brand:Amazon"]
    ),
    payload={...}
)
```

## Security Checks

VetoNet runs 9 security checks in order (fast to slow):

| Check | Type | What It Catches |
|-------|------|-----------------|
| Price | Deterministic | Transaction exceeds budget |
| Quantity | Deterministic | Wrong number of items |
| Category | Deterministic | Different product type |
| Currency | Deterministic | Currency manipulation |
| Subscription | Deterministic | Sneaky recurring charges |
| Hidden Fees | Deterministic | Service fees, processing fees |
| Vendor | Deterministic | Scam domains, brand spoofing |
| Price Anomaly | Deterministic | Suspiciously cheap (scam indicator) |
| Semantic | LLM-based | Item doesn't match intent constraints |

Checks run in order and fail fast - if price check fails, we don't waste time on semantic check.

## CLI

```bash
# Verify a transaction
vetonet --intent "$50 Amazon Gift Card" \
        --payload '{"item_description": "...", "unit_price": 50}' \
        --provider ollama

# Output as JSON
vetonet -i "..." -p @payload.json --json

# Use with Groq
vetonet -i "$50 Amazon Gift Card" -p @payload.json --provider groq --api-key $GROQ_API_KEY
```

## API Reference

### VetoNet

```python
VetoNet(
    provider: str = "ollama",  # "ollama", "groq", "anthropic", "openai", "none"
    model: str = None,         # Override default model
    api_key: str = None,       # API key for hosted providers
    base_url: str = None,      # Custom endpoint URL
)
```

### verify()

```python
result = veto.verify(
    intent: str | IntentAnchor,     # Natural language or structured
    payload: dict | AgentPayload,   # Transaction to verify
) -> VetoResult
```

### VetoResult

```python
result.approved  # bool - True if transaction is safe
result.vetoed    # bool - True if transaction was blocked
result.reason    # str - Explanation
result.checks    # list[CheckResult] - Details of each check
```

## Use Cases

- **Crypto Wallets** - Verify agent transactions before signing
- **AI Agent Platforms** - Add security layer for autonomous agents
- **Fintech Apps** - Fraud prevention for AI-powered spending
- **E-commerce** - Protect users from malicious product recommendations

## Links

- **GitHub**: https://github.com/takenosuke-code/vetonet
- **Issues**: https://github.com/takenosuke-code/vetonet/issues

## License

MIT
