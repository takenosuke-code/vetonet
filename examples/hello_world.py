#!/usr/bin/env python3
"""VetoNet Hello World - No API keys, no network, pure deterministic checks."""

from vetonet import VetoNet, IntentAnchor, AgentPayload

veto = VetoNet(provider="none")

# --- Honest transaction: $50 Amazon gift card ---
intent = IntentAnchor(item_category="gift_card", max_price=50.00)
payload = AgentPayload(
    item_description="Amazon Gift Card - $50",
    item_category="gift_card",
    unit_price=49.99,
    vendor="amazon.com",
)

result = veto.check(intent, payload)
print(f"Honest agent:      {result.status.value}")
print(f"  Reason:          {result.reason}")
for c in result.checks:
    print(f"  [{c.name}] {'PASS' if c.passed else 'FAIL'}: {c.reason}")

print()

# --- Price attack: agent inflates the price 3x ---
attack_payload = AgentPayload(
    item_description="Amazon Gift Card - $50",
    item_category="gift_card",
    unit_price=149.99,
    vendor="amazon.com",
)

result = veto.check(intent, attack_payload)
print(f"Price attack:      {result.status.value}")
print(f"  Reason:          {result.reason}")
for c in result.checks:
    print(f"  [{c.name}] {'PASS' if c.passed else 'FAIL'}: {c.reason}")
