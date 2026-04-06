# Contributing to VetoNet

Thanks for your interest in contributing to VetoNet! This guide covers how to set up your environment, follow our code conventions, and submit changes.

## Dev Environment Setup

```bash
# Clone and install in editable mode with dev dependencies
git clone https://github.com/takenosuke-code/vetonet.git
cd vetonet
pip install -e ".[dev]"
```

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for both linting and formatting:

```bash
ruff check .          # Lint
ruff format --check . # Check formatting
ruff format .         # Auto-format
```

Line length is 100 characters. Target Python version is 3.10+.

## Running Tests

```bash
pytest tests/
```

All tests must pass before a PR will be reviewed.

## Adding a New Deterministic Check

Deterministic checks live in `vetonet/checks/deterministic.py`. To add one:

1. Write the check function in `vetonet/checks/deterministic.py`. It must accept `(IntentAnchor, AgentPayload)` and return a `CheckResult`.
2. Export it from `vetonet/checks/__init__.py`.
3. Wire it into the check pipeline in `vetonet/engine.py` (add it to the `deterministic_checks` list).
4. Add tests in `tests/` covering both pass and fail cases.

## Reporting Security Issues

Do **not** open a public issue for security vulnerabilities. Instead, follow our [Security Policy](SECURITY.md) and report via:

- **Email:** security@veto-net.org
- **GitHub Security Advisories:** [Report privately](https://github.com/takenosuke-code/vetonet/security/advisories)

## Developer Certificate of Origin (DCO)

All commits must include a `Signed-off-by` line certifying that you have the right to submit the contribution under the project's license. Add it with:

```bash
git commit -s -m "Your commit message"
```

This adds a line like:

```
Signed-off-by: Your Name <your.email@example.com>
```

By signing off, you agree to the [Developer Certificate of Origin](https://developercertificate.org/).

## Submitting a Pull Request

1. Fork the repo and create a feature branch from `main`.
2. Make your changes with clear, focused commits.
3. Ensure `ruff check .` and `pytest tests/` both pass.
4. Open a PR against `main` with a description of what and why.
