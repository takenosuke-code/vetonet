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
- Railway: Backend API (needs GROQ_API_KEY env var)
- Frontend: React playground in `/playground`

## Private Docs (gitignored)
- `docs/STRATEGY.md` - Funding/investor strategy
- `docs/SECURITY_AUDIT.md` - Vulnerability report
- `docs/INVESTOR_BRIEF.md` - Pitch materials
