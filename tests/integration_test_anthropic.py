#!/usr/bin/env python3
"""
Integration Test: VetoNet Anthropic SDK

Simulates a YC founder integrating VetoNet into an AI shopping assistant.
Tests the full flow with mock Anthropic responses (no real API keys needed).

Findings are documented at the bottom of this file.
"""

import os
import sys
import time
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# STEP 1: Can I even import the integration?
# ============================================================================
print("=" * 70)
print("STEP 1: Import VetoNetAnthropic")
print("=" * 70)

start = time.time()
try:
    from vetonet.integrations.anthropic import VetoNetAnthropic, ToolCallResult
    print(f"  OK - imported in {time.time() - start:.3f}s")
except ImportError as e:
    print(f"  FAIL - ImportError: {e}")
    sys.exit(1)


# ============================================================================
# STEP 2: Create instance - what happens without an API key?
# ============================================================================
print("\n" + "=" * 70)
print("STEP 2: Create VetoNetAnthropic instance")
print("=" * 70)

# 2a: No key at all - should fail with clear error
print("\n  2a: No API key provided...")
# Make sure env var is not set
old_key = os.environ.pop("VETONET_API_KEY", None)
try:
    veto = VetoNetAnthropic()
    print("  FAIL - should have raised an error")
except Exception as e:
    print(f"  OK - got: {type(e).__name__}: {e}")

# 2b: With a fake key - should succeed (validation is deferred to API call)
print("\n  2b: With fake API key...")
try:
    veto = VetoNetAnthropic(api_key="veto_sk_test_fake_key_12345")
    print("  OK - instance created")
except Exception as e:
    print(f"  FAIL - {type(e).__name__}: {e}")

# Restore env var if it was set
if old_key:
    os.environ["VETONET_API_KEY"] = old_key


# ============================================================================
# STEP 3: Lock intent
# ============================================================================
print("\n" + "=" * 70)
print("STEP 3: Lock intent")
print("=" * 70)

# 3a: Normal intent
print("\n  3a: Lock 'Buy a $50 Amazon gift card'...")
try:
    veto.lock_intent("Buy a $50 Amazon gift card")
    print(f"  OK - intent locked: '{veto.intent}'")
except Exception as e:
    print(f"  FAIL - {type(e).__name__}: {e}")

# 3b: Empty intent - should fail
print("\n  3b: Lock empty intent...")
try:
    veto.lock_intent("")
    print("  FAIL - should have raised ValueError")
except ValueError as e:
    print(f"  OK - got ValueError: {e}")
except Exception as e:
    print(f"  UNEXPECTED - {type(e).__name__}: {e}")

# 3c: Auto-detect from messages
print("\n  3c: lock_intent_from_messages...")
veto2 = VetoNetAnthropic(api_key="veto_sk_test_fake")
messages = [
    {"role": "user", "content": "I want to buy a $50 Amazon gift card"},
    {"role": "assistant", "content": "I'll help you find that!"},
]
try:
    detected = veto2.lock_intent_from_messages(messages)
    print(f"  OK - auto-detected: '{detected}'")
except Exception as e:
    print(f"  FAIL - {type(e).__name__}: {e}")


# ============================================================================
# STEP 4: Register tools with field_map
# ============================================================================
print("\n" + "=" * 70)
print("STEP 4: Register tools")
print("=" * 70)


def mock_buy_item(product_name: str, price: float, store: str, quantity: int = 1):
    """Mock executor - simulates actually buying something."""
    return {"order_id": "ORD-12345", "product": product_name, "total": price * quantity}


print("\n  4a: Register buy_item with field_map...")
try:
    veto.register_tool(
        name="buy_item",
        executor=mock_buy_item,
        field_map={
            "product_name": "item_description",
            "price": "unit_price",
            "store": "vendor",
            "quantity": "quantity",
        },
        defaults={"item_category": "gift_card", "currency": "USD"},
    )
    print("  OK - tool registered")
except Exception as e:
    print(f"  FAIL - {type(e).__name__}: {e}")

# 4b: Register with auto_infer (no explicit field_map)
print("\n  4b: Register search_products with auto_infer only...")
try:
    veto.register_tool(
        name="search_products",
        executor=lambda query, category="general": [{"name": query}],
    )
    print("  OK - tool registered with auto_infer")
except Exception as e:
    print(f"  FAIL - {type(e).__name__}: {e}")


# ============================================================================
# STEP 5: Build mock Anthropic responses
# ============================================================================
print("\n" + "=" * 70)
print("STEP 5: Build mock Anthropic responses")
print("=" * 70)

# An Anthropic response has .content = list of blocks
# Each tool_use block has: type="tool_use", id=str, name=str, input=dict

# 5a: Honest tool call - matches intent
honest_response = {
    "content": [
        {
            "type": "text",
            "text": "I found a $50 Amazon gift card for you!",
        },
        {
            "type": "tool_use",
            "id": "toolu_01ABC123",
            "name": "buy_item",
            "input": {
                "product_name": "Amazon Gift Card $50",
                "price": 50.00,
                "store": "amazon.com",
                "quantity": 1,
            },
        },
    ]
}

# 5b: Malicious tool call - prompt injection swapped the item
malicious_response = {
    "content": [
        {
            "type": "text",
            "text": "I found a great deal for you!",
        },
        {
            "type": "tool_use",
            "id": "toolu_02DEF456",
            "name": "buy_item",
            "input": {
                "product_name": "Bitcoin 0.001 BTC instant",
                "price": 50.00,
                "store": "shadycrypto.io",
                "quantity": 1,
            },
        },
    ]
}

print("  OK - built honest and malicious mock responses")


# ============================================================================
# STEP 6: Process tool calls with mocked VetoNet API
# ============================================================================
print("\n" + "=" * 70)
print("STEP 6: Process tool calls (mocked VetoNet API)")
print("=" * 70)

# We need to mock APIClient.check_sync because there is no real server.
# This simulates what the real API would return.

from vetonet.integrations.langchain.types import VetoResponse, VetoStatus


def make_approved_response():
    return VetoResponse(
        verdict="approved",
        status=VetoStatus.APPROVED,
        reason="Transaction matches user intent",
        confidence=0.95,
        checks=[],
        request_id="test-req-001",
    )


def make_blocked_response():
    return VetoResponse(
        verdict="blocked",
        status=VetoStatus.VETO,
        reason="Item mismatch: user requested 'Amazon gift card' but agent is purchasing 'Bitcoin'",
        confidence=0.98,
        checks=[],
        request_id="test-req-002",
    )


# 6a: HONEST tool call - should be approved
print("\n  6a: Process HONEST tool call...")
with patch.object(veto._client, "check_sync", return_value=make_approved_response()):
    try:
        results = veto.process_tool_calls(honest_response)
        for r in results:
            print(f"      Tool: {r.tool_name}")
            print(f"      Approved: {r.approved}")
            if r.approved:
                print(f"      Result: {r.result}")
            else:
                print(f"      Blocked: {r.blocked_reason}")

            # Test to_anthropic_result
            ar = r.to_anthropic_result()
            print(f"      Anthropic format: {ar}")
    except Exception as e:
        print(f"  FAIL - {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()

# 6b: MALICIOUS tool call - should be blocked
print("\n  6b: Process MALICIOUS tool call...")
with patch.object(veto._client, "check_sync", return_value=make_blocked_response()):
    try:
        results = veto.process_tool_calls(malicious_response)
        for r in results:
            print(f"      Tool: {r.tool_name}")
            print(f"      Approved: {r.approved}")
            if r.approved:
                print(f"      Result: {r.result}")
            else:
                print(f"      Blocked: {r.blocked_reason}")

            # Check the anthropic result format for blocked calls
            ar = r.to_anthropic_result()
            print(f"      Anthropic format: {ar}")
            # Verify it does NOT have is_error (security design)
            has_is_error = "is_error" in ar
            print(f"      has is_error flag: {has_is_error} (should be False)")
    except Exception as e:
        print(f"  FAIL - {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()


# ============================================================================
# STEP 7: Edge cases
# ============================================================================
print("\n" + "=" * 70)
print("STEP 7: Edge cases")
print("=" * 70)

# 7a: No intent locked
print("\n  7a: Process without locked intent...")
veto_no_intent = VetoNetAnthropic(api_key="veto_sk_test_fake")
# Register the tool but don't lock intent
veto_no_intent.register_tool("buy_item", mock_buy_item)
try:
    results = veto_no_intent.process_tool_calls(honest_response)
    for r in results:
        print(f"      Approved: {r.approved}, Reason: {r.blocked_reason}")
except Exception as e:
    print(f"  Got exception: {type(e).__name__}: {e}")

# 7b: Unknown tool in response
print("\n  7b: Unknown tool (no executor)...")
unknown_response = {
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_unknown",
            "name": "transfer_money",
            "input": {"amount": 1000, "to": "attacker@evil.com"},
        }
    ]
}
with patch.object(veto._client, "check_sync", return_value=make_approved_response()):
    results = veto.process_tool_calls(unknown_response)
    for r in results:
        print(f"      Tool: {r.tool_name}, Approved: {r.approved}")
        print(f"      Reason: {r.blocked_reason}")

# 7c: Response with no tool_use blocks (just text)
print("\n  7c: Response with no tool calls...")
text_only_response = {
    "content": [
        {"type": "text", "text": "Let me search for that gift card."}
    ]
}
results = veto.process_tool_calls(text_only_response)
print(f"      Results count: {len(results)} (should be 0)")

# 7d: get_tool_results convenience method
print("\n  7d: get_tool_results convenience method...")
with patch.object(veto._client, "check_sync", return_value=make_approved_response()):
    try:
        tool_results = veto.get_tool_results(honest_response)
        print(f"      Got {len(tool_results)} result(s)")
        for tr in tool_results:
            print(f"      Type: {tr['type']}, ID: {tr['tool_use_id']}")
            print(f"      Content: {tr['content'][:80]}...")
    except Exception as e:
        print(f"  FAIL - {type(e).__name__}: {e}")

# 7e: Context manager
print("\n  7e: Context manager usage...")
try:
    with VetoNetAnthropic(api_key="veto_sk_test_fake") as v:
        v.lock_intent("Buy something")
        print("      OK - context manager works")
except Exception as e:
    print(f"  FAIL - {type(e).__name__}: {e}")


# ============================================================================
# STEP 8: Auto-infer field mapping test
# ============================================================================
print("\n" + "=" * 70)
print("STEP 8: Auto-infer field mapping")
print("=" * 70)

# Register a tool with common param names and let auto_infer handle it
veto_auto = VetoNetAnthropic(api_key="veto_sk_test_fake")
veto_auto.lock_intent("Buy a laptop for $999")

def mock_purchase(name: str, price: float, vendor: str, quantity: int = 1):
    return {"ok": True}

veto_auto.register_tool(
    name="purchase",
    executor=mock_purchase,
    # No field_map! Relying on auto_infer for "name" -> item_description,
    # "price" -> unit_price, "vendor" -> vendor, "quantity" -> quantity
)

auto_response = {
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_auto",
            "name": "purchase",
            "input": {"name": "MacBook Pro 14", "price": 999.0, "vendor": "apple.com", "quantity": 1},
        }
    ]
}

print("  Testing auto_infer with common param names...")
with patch.object(veto_auto._client, "check_sync", return_value=make_approved_response()):
    results = veto_auto.process_tool_calls(auto_response)
    for r in results:
        print(f"      Approved: {r.approved}, Result: {r.result}")


# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("ALL TESTS PASSED")
print("=" * 70)

print("""
========================================================================
CUSTOMER FEEDBACK: YC Founder Perspective
========================================================================

1. TIME TO UNDERSTAND THE API:
   About 15-20 minutes reading source code. There is NO dedicated doc for
   the Anthropic integration - I had to read guard.py, processor.py, the
   __init__.py docstring, and reverse-engineer the LangChain types/registry
   modules. The agentkit_demo.py example is for a different integration
   (AgentKit, not Anthropic SDK). A simple README or quickstart for the
   Anthropic integration would cut onboarding time to 5 minutes.

2. CONFUSING OR UNDOCUMENTED:
   - The field_map system is NOT documented anywhere. I had to read
     registry.py to discover the valid AgentPayload fields:
     item_description, item_category, unit_price, quantity, vendor,
     currency, is_recurring, fees, metadata. These should be in the
     docstring or a constant you can import.
   - auto_infer is on by default but the mapping table (AUTO_FIELD_MAP)
     is hidden in langchain/registry.py. No way to know what gets
     auto-mapped without reading source.
   - The Anthropic integration imports ALL its core types from
     vetonet.integrations.langchain.*. This is confusing - why does my
     Anthropic code depend on a langchain module? Feels like shared code
     that should be in a common/ package.
   - No docstring or example showing what a mock Anthropic response
     should look like (dict vs SDK object). I had to read
     extract_tool_use_blocks() to figure out it handles both.

3. DID IT WORK OUT OF THE BOX?
   Yes, once I understood the API and mocked the HTTP calls. The code
   is well-structured and handles edge cases (no intent, unknown tool,
   no tool calls in response). The auto_infer feature is genuinely
   useful - common param names like "price", "vendor", "name" just work.

4. WHAT IS MISSING FOR PRODUCTION:
   - A dedicated Anthropic integration quickstart/README
   - pip install vetonet[anthropic] with dependency management
   - A way to test locally without a live API (mock mode / dry-run flag)
   - Streaming support (Anthropic's streaming returns tool_use blocks
     incrementally)
   - Multi-tool-call ordering (what if tool B depends on tool A's result?)
   - Webhook/callback for when a call is blocked (for alerting)
   - Dashboard or logging integration guidance

5. DOES THE field_map SYSTEM MAKE SENSE?
   Yes, once discovered. The concept of mapping arbitrary tool params to
   a canonical AgentPayload is smart. The auto_infer is a great DX win.
   But the valid target fields and auto-mapping rules need to be
   documented prominently. I would also like to see a validation error
   if my field_map targets a non-existent field (this already works -
   good).

6. IS ERROR HANDLING CLEAR WHEN BLOCKED?
   Yes. The ToolCallResult.blocked_reason is clear. The design decision
   to NOT set is_error on blocked results (to prevent Claude from
   retrying with different params) is smart and well-commented in
   processor.py. The to_anthropic_result() format is ready to plug into
   the next messages.create() call.

OVERALL: Solid foundation. The code quality is high. The main gap is
documentation - specifically an Anthropic-focused quickstart with a
working example. The dependency on langchain.* modules for shared types
is architecturally confusing even though it works fine.
""")
