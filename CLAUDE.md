# VetoNet - Semantic Firewall for AI Agents

## What This Is
VetoNet is a security protocol that prevents "Intent Drift" in AI agent transactions. When an AI agent tries to buy something on your behalf, VetoNet intercepts the transaction, compares it against your original intent, and vetoes if it drifted (e.g., prompt injection attack).

**Target market:** Crypto wallets, AI agent platforms, fintech apps that let AI spend money.

## Architecture

```
User Intent → Intent Anchor (structured) → Agent shops → VetoNet intercepts → Approve/Veto
```

### Key Files

| File | Purpose |
|------|---------|
| `vetonet/models.py` | Pydantic models: IntentAnchor, AgentPayload, Fee, VetoResult |
| `vetonet/normalizer.py` | Extracts structured intent from natural language (uses Ollama/Qwen) |
| `vetonet/checks/deterministic.py` | 8 fast, free security checks (price, quantity, vendor, etc.) |
| `vetonet/checks/semantic.py` | LLM-based semantic similarity check |
| `vetonet/engine.py` | Orchestrates all checks, fails fast |
| `demo/shopping_agent.py` | Mock AI shopping agent (honest/compromised modes) |
| `demo/live_demo.py` | Terminal demo with ASCII art and colors |
| `app.py` | Streamlit web UI (basic) |
| `api.py` | Flask API backend for React playground |
| `playground/` | React + Tailwind interactive playground (the good UI) |
| `tests/scenarios.py` | 8 attack scenarios for testing |

### Security Checks (9 total)
1. **Price** - Is total ≤ max allowed?
2. **Quantity** - Matches requested amount?
3. **Category** - Right product type?
4. **Currency** - No currency manipulation?
5. **Vendor TLD** - Not a scam domain (.xyz, .ru, etc.)?
6. **Price Anomaly** - Not suspiciously cheap (scam indicator)?
7. **Hidden Fees** - No sketchy fees (processing, convenience, etc.)?
8. **Subscription Trap** - Not sneaking in recurring charges?
9. **Semantic Similarity** - LLM checks if item matches intent constraints

## How to Run

### Prerequisites
- Python 3.10+
- Node.js 18+
- Ollama with `qwen2.5:7b` model (for local LLM)

```bash
# Install Python dependencies
pip install -r requirements.txt
pip install flask-cors

# Terminal demo (quick test)
python -m demo.live_demo --attack
python -m demo.live_demo --safe

# Streamlit UI (basic)
streamlit run app.py

# React Playground (the good one)
# Terminal 1: Start API backend
python api.py

# Terminal 2: Start React frontend
cd playground
npm install
npm run dev
# Open http://localhost:5173
```

## React Playground Features

The `/playground` directory contains a polished React + Tailwind UI with:

### Demo Mode
- Visual three-column flow: Intent Lock → Agent Shopping → VetoNet Decision
- Toggle between Honest Agent and Compromised Agent
- Real-time security check animations
- Connects to real VetoNet backend via `/api/demo`

### Red Team Challenge Mode
- **Gamified attack simulation** (like Lakera's Gandalf)
- Users craft their own malicious payloads
- Try to bypass VetoNet's security checks
- Hidden fees, vendor spoofing, subscription traps, etc.
- Connects to `/api/redteam` endpoint

### Data Collection
- All attack attempts logged to `data/attack_attempts.jsonl`
- Stats displayed: Total attempts, Blocked, Bypassed, Bypass rate
- Use this data to improve VetoNet's detection

### Design
- Dark cyberpunk theme (not generic AI slop)
- Cyan/coral/lime accent colors
- JetBrains Mono + Sora fonts
- Animated security check sequence
- Glass card effects, glows, grid background

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Health check |
| `/api/demo` | POST | Run standard demo (honest/compromised mode) |
| `/api/redteam` | POST | Red team mode - user crafts attack payload |
| `/api/stats` | GET | Get attack statistics |
| `/api/attacks` | GET | Get recent attack attempts |

## Current State

### What Works
- Full veto engine with 9 security checks
- Terminal demo (demo/live_demo.py)
- Streamlit web UI (app.py) - basic but functional
- **React playground with Red Team mode** - the polished demo
- Flask API connecting frontend to real VetoNet engine
- Data collection for attack attempts (anonymized)
- **SDK packaged for pip install** - `pip install vetonet`
- **Multi-provider support** - Ollama (local), Groq (free), Anthropic, OpenAI

### SDK Distribution (2026-03-25)

VetoNet is now a pip-installable SDK:

```bash
pip install vetonet              # Core with Ollama
pip install vetonet[groq]        # + Groq provider
pip install vetonet[anthropic]   # + Claude provider
```

```python
from vetonet import VetoNet

veto = VetoNet(provider="groq", api_key="...")
result = veto.verify("$50 Amazon Gift Card", payload)
if not result.approved:
    print(f"Blocked: {result.reason}")
```

### Security Hardening (2026-03-25)

Security audit identified 15 vulnerabilities. **5 Critical FIXED:**

| Vuln | Fix Applied |
|------|-------------|
| Prompt injection in semantic check | Input sanitization, injection pattern filtering |
| JSON parsing manipulation | Balanced brace extraction, single object validation |
| LLM response validation | Range checks, type validation, sanitization |
| Sensitive data logging | Anonymized logs, attack classification, no raw payloads |
| API input validation | Price/quantity limits, request validation |

Additional hardening:
- `/api/attacks` now requires `X-API-Key` header (set `VETONET_ADMIN_KEY`)
- Error messages no longer expose system internals
- Brand-to-domain verification (prevents amazon-giftcards.xyz spoofing)

See `docs/SECURITY_AUDIT.md` for full report.

### Open Issues / Next Steps

1. **Medium vulnerabilities** - 6 medium issues documented in SECURITY_AUDIT.md
2. **Deployment** - Deploy hosted demo with Groq fallback
3. **Funding path** - See `docs/STRATEGY.md` for YC/grants strategy

## Design Decisions

- **100% local AI** - User specifically wanted Ollama/Qwen instead of cloud APIs for integrity/privacy story
- **Hybrid checks** - Deterministic checks run first (fast, free), LLM check only if all pass
- **Fail fast** - First failed check stops evaluation
- **Category normalization** - Handles plurals (gift_cards → gift_card) and formatting
- **Gamified demo** - Red Team challenge mode for engagement and data collection (inspired by Lakera's Gandalf)

## Demo Script

For investor demos:
1. Open React playground (http://localhost:5173)
2. **Demo Mode**: Show legitimate purchase flow (approved)
3. Toggle to "Compromised Agent" - same request now gets VETOED
4. Show which specific checks failed
5. **Red Team Mode**: Let them try to craft an attack
6. Show the stats - blocked vs bypassed attempts

## User Context

Building this as MVP to pitch to crypto wallets / AI agent companies. Concerned about:
- Looking too simple (why wouldn't Apple just build this?)
- Market timing (AI agents aren't mainstream yet)
- Protecting idea before going public with it

Positioning: First-mover advantage, specialized focus, sell to others vs compete.

## Research Notes

Studied how other B2B security companies demo their products:
- **Lakera** - Gandalf game, interactive playgrounds
- **Cloudflare** - Browser-based sandboxes
- **Stripe** - Test cards, sandbox environments
- **Auth0** - Code samples + solution demos

Key insight: "free + gated" funnel works best. Public playground builds awareness, then sales demos close deals.
