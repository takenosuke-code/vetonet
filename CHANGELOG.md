# Changelog

All notable changes to VetoNet will be documented in this file.

This project follows [Semantic Versioning](https://semver.org/).

## [0.1.4] - 2025-06-01

Initial public release.

### Features

- **3-layer defense system:** deterministic checks, ML classifier, and LLM semantic verification
- **LangChain integration:** `@protected_tool` decorator for automatic intent capture and verification
- **OpenAI integration:** drop-in middleware for OpenAI function calling agents
- **Anthropic integration:** tool-use interception for Claude-based agents
- **CrewAI integration:** task-level verification for multi-agent workflows
- **ML classifier:** local CPU-based model for fast pre-filtering of suspicious transactions
- **Text sanitization:** prompt injection detection and neutralization in transaction fields
- **Fail-open safety system:** configurable behavior when checks encounter errors
- **Suspicion scoring:** weighted scoring across all checks for nuanced decision-making
- **Deterministic checks:** price, category, quantity, currency, subscription trap, hidden fees, vendor, scam patterns, market value, and crypto substitution
- **Provider support:** Ollama (local), Groq, Anthropic, OpenAI, and `none` (deterministic-only)
