# VetoNet Privacy Policy

**Last updated:** 2026-04-04

VetoNet is an open-source transaction safety layer. This document explains what data VetoNet collects, how it is used, and your rights regarding that data.

---

## 1. What Data VetoNet Collects

### Hosted API

When you use the VetoNet hosted API, the following data is collected:

- **Transaction intents** — scrubbed of personally identifiable information (PII)
- **Agent payloads** — scrubbed of PII
- **Verdicts** — the allow/deny decision for each transaction
- **Check results** — individual check outcomes (e.g., scam detection, market value)
- **Timestamps** — when the request was received and processed
- **API key prefix** — the first characters of your API key for request attribution (never the full key)

### SDK Telemetry (Opt-In Only)

SDK telemetry is **disabled by default**. If you opt in, anonymous mode stores:

- Hashed intent (one-way hash, not reversible to original text)
- Category
- Price bucket (range, not exact amount)
- Verdict

### Playground

The VetoNet Playground collects the same data as the hosted API, but **no authentication is required**. Playground requests are not attributed to any user or API key.

---

## 2. What VetoNet Does NOT Collect

VetoNet never collects:

- Payment credentials (credit card numbers, bank accounts, wallet keys)
- Passwords or authentication tokens
- Billing addresses or physical addresses
- Browser fingerprints
- Cookies
- Tracking pixels

---

## 3. How Data Is Used

Collected data is used for:

- **Security monitoring** — detecting abuse, debugging issues, and improving safety checks
- **ML model training** — improving detection accuracy using PII-scrubbed transaction data
- **Aggregate statistics** — understanding usage patterns (e.g., total attacks blocked, bypass rates)

Data is never sold to third parties or used for advertising.

---

## 4. Data Retention

| Data Type | Retention Period |
|---|---|
| Transaction logs | 90 days |
| Telemetry | 30 days |
| Audit logs | 1 year |

After the retention period, data is permanently deleted.

---

## 5. Right to Deletion

You may request deletion of your data at any time by:

- Emailing **security@veto-net.org** with your request
- Using the VetoNet API deletion endpoint (coming soon)

Deletion requests are processed within 30 days.

---

## 6. Sub-Processors

VetoNet uses the following third-party services to operate:

| Sub-Processor | Purpose |
|---|---|
| [Supabase](https://supabase.com) | Database |
| [Railway](https://railway.app) | Hosting |
| [Groq](https://groq.com) | LLM inference |

---

## 7. Contact

For privacy questions, data requests, or security concerns:

**Email:** security@veto-net.org
