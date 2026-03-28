# VetoNet - Semantic Firewall for AI Agents

Prevents "Intent Drift" in AI agent transactions via prompt injection attacks.

**Target market:** Crypto wallets, AI agent platforms, fintech apps.

## Architecture
```
User Intent → Intent Anchor → Agent shops → VetoNet intercepts → Approve/Veto
```

## Design Decisions
- **Hybrid checks**: Deterministic first (fast, free), then LLM semantic check
- **Fail fast**: First failed check stops evaluation
- **Multi-provider**: Ollama (local), Groq (free hosted), Anthropic, OpenAI
- **Open core**: Free SDK, paid hosted API

## Business Context
MVP for crypto wallets / AI agent companies. Positioning: first-mover, specialized focus.

## Current Deployment
- GitHub: https://github.com/takenosuke-code/vetonet
- Backend: https://web-production-fec907.up.railway.app
- Frontend: https://vetonet-3jz7.vercel.app
- Railway env vars: `GROQ_API_KEY`, `DATABASE_URL`, `VETONET_ADMIN_KEY`

## Testing
- `scripts/fuzzer.py` - 100+ hardcoded attack patterns
- `scripts/attack_agent.py` - AI-generated attacks (needs Groq)

## Private Docs (gitignored)
- `docs/STRATEGY.md` - Funding/investor strategy
- `docs/SECURITY_AUDIT.md` - Vulnerability report
- `docs/INVESTOR_BRIEF.md` - Pitch materials
