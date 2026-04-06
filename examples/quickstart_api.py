#!/usr/bin/env python3
"""VetoNet API Quickstart - Uses the public demo endpoint (no auth needed)."""

import requests

API_URL = "https://api.veto-net.org/api/demo"

for mode in ("honest", "compromised"):
    resp = requests.post(API_URL, json={"mode": mode}, timeout=10)
    data = resp.json()

    print(f"Mode: {mode}")
    print(f"  Verdict: {data.get('status', 'N/A')}")
    print(f"  Reason:  {data.get('reason', 'N/A')}")

    checks = data.get("checks", [])
    for check in checks:
        passed = "PASS" if check.get("passed") else "FAIL"
        print(f"  [{check.get('name')}] {passed}: {check.get('reason')}")

    print()
