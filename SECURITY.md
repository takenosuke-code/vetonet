# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| v0.1.4  | Yes       |
| < v0.1.4 | No      |

## Reporting a Vulnerability

If you discover a security vulnerability in VetoNet, please report it responsibly:

- **Email:** security@veto-net.org
- **GitHub Security Advisories:** Use the [Security Advisories](https://github.com/takenosuke-code/vetonet/security/advisories) tab to report privately.

Please do **not** open a public GitHub issue for security vulnerabilities.

## Response Timeline

- **Acknowledgment:** Within 48 hours of receiving your report.
- **Fix timeline:** Within 7 days of acknowledgment, we will provide a timeline for a fix or mitigation.

## Scope

The following are considered in-scope vulnerabilities:

- Bypassing VetoNet checks (deterministic, ML, or LLM layers)
- Authentication bypass (API key validation, session handling)
- Data leakage (exposure of API keys, user data, or internal state)

## Out of Scope

The following are **not** considered vulnerabilities:

- Red team challenge playground bypasses (these are expected and tracked as part of the challenge)
- Denial of Service (DoS) attacks

## Credit Policy

Security researchers who report valid vulnerabilities will be credited in our release notes and security advisories, unless they prefer to remain anonymous. Let us know your preference when reporting.
