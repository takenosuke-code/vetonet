"""
Integration test: OpenAI SDK integration from a YC founder's perspective.

Tests VetoNetOpenAI with mock OpenAI responses (no real API calls).
Mocks the VetoNet API client to isolate the integration layer.
"""

import json
import sys
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

# ============================================================================
# Test infrastructure
# ============================================================================

PASS = 0
FAIL = 0
ERRORS: List[str] = []


def test(name: str):
    """Decorator to register and run a test."""
    def decorator(fn):
        fn._test_name = name
        return fn
    return decorator


def run_test(fn):
    global PASS, FAIL
    name = getattr(fn, '_test_name', fn.__name__)
    try:
        fn()
        PASS += 1
        print(f"  PASS: {name}")
    except AssertionError as e:
        FAIL += 1
        msg = f"  FAIL: {name} -- {e}"
        print(msg)
        ERRORS.append(msg)
    except Exception as e:
        FAIL += 1
        msg = f"  ERROR: {name} -- {type(e).__name__}: {e}"
        print(msg)
        ERRORS.append(msg)
        traceback.print_exc()


# ============================================================================
# Mock OpenAI response objects (mimics real SDK objects, NOT dicts)
# ============================================================================

@dataclass
class MockFunction:
    name: str
    arguments: str  # JSON STRING, exactly how OpenAI returns it


@dataclass
class MockToolCall:
    id: str
    type: str
    function: MockFunction


@dataclass
class MockMessage:
    role: str = "assistant"
    content: Optional[str] = None
    tool_calls: Optional[List[MockToolCall]] = None


@dataclass
class MockChoice:
    index: int
    message: MockMessage
    finish_reason: str = "tool_calls"


@dataclass
class MockChatCompletion:
    id: str
    choices: List[MockChoice]
    model: str = "gpt-4o"


def make_openai_response(tool_calls: List[dict]) -> MockChatCompletion:
    """Build a mock OpenAI ChatCompletion with tool calls.

    Args:
        tool_calls: List of {"id": str, "name": str, "arguments": dict}
                    arguments will be JSON-serialized (like real OpenAI).
    """
    mock_calls = []
    for tc in tool_calls:
        args = tc["arguments"]
        # OpenAI returns arguments as a JSON STRING
        args_str = json.dumps(args) if isinstance(args, dict) else args
        mock_calls.append(MockToolCall(
            id=tc["id"],
            type="function",
            function=MockFunction(name=tc["name"], arguments=args_str),
        ))

    return MockChatCompletion(
        id="chatcmpl-test123",
        choices=[MockChoice(
            index=0,
            message=MockMessage(tool_calls=mock_calls),
        )],
    )


# ============================================================================
# Mock VetoNet API responses
# ============================================================================

def make_approved_response():
    """Return a VetoResponse that approves the transaction."""
    from vetonet.integrations.langchain.types import VetoResponse, VetoStatus
    return VetoResponse(
        verdict="approved",
        status=VetoStatus.APPROVED,
        reason="All checks passed",
        confidence=0.95,
        checks=[],
        request_id="test-req-001",
    )


def make_blocked_response(reason="Intent mismatch: price deviation detected"):
    """Return a VetoResponse that blocks the transaction."""
    from vetonet.integrations.langchain.types import VetoResponse, VetoStatus
    return VetoResponse(
        verdict="blocked",
        status=VetoStatus.VETO,
        reason=reason,
        confidence=0.92,
        checks=[],
        request_id="test-req-002",
    )


# ============================================================================
# Mock executor functions (what a YC founder would write)
# ============================================================================

def buy_item(item: str, price: float, vendor: str) -> str:
    return f"Purchased {item} for ${price} from {vendor}"


def send_money(recipient: str, amount: float) -> str:
    return f"Sent ${amount} to {recipient}"


# ============================================================================
# TESTS
# ============================================================================

# ---------- Test 1: Basic honest tool call (approved) ----------

@test("Honest tool call gets approved and executed")
def test_honest_tool_call():
    from vetonet.integrations.openai import VetoNetOpenAI

    with patch.dict("os.environ", {"VETONET_API_KEY": "veto_sk_test_xxx"}):
        veto = VetoNetOpenAI(api_key="veto_sk_test_xxx")

    veto.lock_intent("Buy a $50 Amazon gift card")
    veto.register_tool("buy_item", buy_item, field_map={
        "item": "item_description",
        "price": "unit_price",
        "vendor": "vendor",
    })

    response = make_openai_response([{
        "id": "call_abc123",
        "name": "buy_item",
        "arguments": {"item": "Amazon gift card", "price": 50.0, "vendor": "Amazon"},
    }])

    # Mock the API client's check_sync to return approved
    with patch.object(veto._client, "check_sync", return_value=make_approved_response()):
        results = veto.process_tool_calls(response)

    assert len(results) == 1, f"Expected 1 result, got {len(results)}"
    r = results[0]
    assert r.approved is True, f"Expected approved, got blocked: {r.blocked_reason}"
    assert r.tool_call_id == "call_abc123"
    assert r.tool_name == "buy_item"
    assert "Purchased" in str(r.result), f"Unexpected result: {r.result}"
    assert r.error is None

    # Test to_tool_message format
    msg = r.to_tool_message()
    assert msg["role"] == "tool"
    assert msg["tool_call_id"] == "call_abc123"
    assert "Purchased" in msg["content"]


# ---------- Test 2: Malicious tool call (blocked) ----------

@test("Malicious tool call gets blocked")
def test_malicious_tool_call():
    from vetonet.integrations.openai import VetoNetOpenAI

    veto = VetoNetOpenAI(api_key="veto_sk_test_xxx")
    veto.lock_intent("Buy a $50 Amazon gift card")
    veto.register_tool("send_money", send_money)

    # Attacker tries to redirect to wire transfer
    response = make_openai_response([{
        "id": "call_evil456",
        "name": "send_money",
        "arguments": {"recipient": "attacker@evil.com", "amount": 5000.0},
    }])

    with patch.object(veto._client, "check_sync", return_value=make_blocked_response()):
        results = veto.process_tool_calls(response)

    r = results[0]
    assert r.approved is False, "Malicious call should be blocked"
    assert r.blocked_reason is not None
    assert "Intent mismatch" in r.blocked_reason
    assert r.result is None

    # Check tool message format for blocked call
    msg = r.to_tool_message()
    assert "[BLOCKED by VetoNet]" in msg["content"]


# ---------- Test 3: No intent locked ----------

@test("Tool call without locked intent gets blocked with clear error")
def test_no_intent():
    from vetonet.integrations.openai import VetoNetOpenAI

    veto = VetoNetOpenAI(api_key="veto_sk_test_xxx")
    # Intentionally NOT calling lock_intent

    veto.register_tool("buy_item", buy_item)

    response = make_openai_response([{
        "id": "call_no_intent",
        "name": "buy_item",
        "arguments": {"item": "test", "price": 10.0, "vendor": "test"},
    }])

    results = veto.process_tool_calls(response)
    r = results[0]
    assert r.approved is False, "Should be blocked without intent"
    assert "intent" in r.blocked_reason.lower() or "lock_intent" in r.blocked_reason


# ---------- Test 4: Malformed JSON in arguments ----------

@test("Malformed JSON in function.arguments fails closed")
def test_malformed_json():
    from vetonet.integrations.openai import VetoNetOpenAI

    veto = VetoNetOpenAI(api_key="veto_sk_test_xxx")
    veto.lock_intent("Buy a $50 Amazon gift card")
    veto.register_tool("buy_item", buy_item)

    # Create response with raw malformed JSON string
    bad_response = MockChatCompletion(
        id="chatcmpl-bad",
        choices=[MockChoice(
            index=0,
            message=MockMessage(tool_calls=[
                MockToolCall(
                    id="call_badjson",
                    type="function",
                    function=MockFunction(
                        name="buy_item",
                        arguments="{invalid json: ???}",
                    ),
                ),
            ]),
        )],
    )

    results = veto.process_tool_calls(bad_response)
    r = results[0]
    assert r.approved is False, "Malformed JSON should be blocked (fail-closed)"
    assert "parse" in r.blocked_reason.lower() or "Failed" in r.blocked_reason


# ---------- Test 5: Unregistered tool ----------

@test("Unregistered tool (no executor) gets blocked")
def test_unregistered_tool():
    from vetonet.integrations.openai import VetoNetOpenAI

    veto = VetoNetOpenAI(api_key="veto_sk_test_xxx")
    veto.lock_intent("Buy something")
    # NOT registering any tools

    response = make_openai_response([{
        "id": "call_unknown",
        "name": "totally_unknown_tool",
        "arguments": {"foo": "bar"},
    }])

    results = veto.process_tool_calls(response)
    r = results[0]
    assert r.approved is False, "Unregistered tool should be blocked"
    assert "executor" in r.blocked_reason.lower() or "registered" in r.blocked_reason.lower()


# ---------- Test 6: Multiple tool calls in one response ----------

@test("Multiple tool calls processed correctly (one approved, one blocked)")
def test_multiple_tool_calls():
    from vetonet.integrations.openai import VetoNetOpenAI

    veto = VetoNetOpenAI(api_key="veto_sk_test_xxx")
    veto.lock_intent("Buy a $50 Amazon gift card")
    veto.register_tool("buy_item", buy_item)
    veto.register_tool("send_money", send_money)

    response = make_openai_response([
        {
            "id": "call_good",
            "name": "buy_item",
            "arguments": {"item": "Amazon gift card", "price": 50.0, "vendor": "Amazon"},
        },
        {
            "id": "call_bad",
            "name": "send_money",
            "arguments": {"recipient": "attacker", "amount": 9999.0},
        },
    ])

    call_count = [0]
    def mock_check_sync(intent, payload):
        call_count[0] += 1
        if call_count[0] == 1:
            return make_approved_response()
        else:
            return make_blocked_response()

    with patch.object(veto._client, "check_sync", side_effect=mock_check_sync):
        results = veto.process_tool_calls(response)

    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    assert results[0].approved is True
    assert results[1].approved is False


# ---------- Test 7: get_tool_messages convenience method ----------

@test("get_tool_messages returns OpenAI-formatted tool messages")
def test_get_tool_messages():
    from vetonet.integrations.openai import VetoNetOpenAI

    veto = VetoNetOpenAI(api_key="veto_sk_test_xxx")
    veto.lock_intent("Buy a $50 Amazon gift card")
    veto.register_tool("buy_item", buy_item)

    response = make_openai_response([{
        "id": "call_msg",
        "name": "buy_item",
        "arguments": {"item": "Amazon gift card", "price": 50.0, "vendor": "Amazon"},
    }])

    with patch.object(veto._client, "check_sync", return_value=make_approved_response()):
        messages = veto.get_tool_messages(response)

    assert len(messages) == 1
    msg = messages[0]
    assert msg["role"] == "tool"
    assert msg["tool_call_id"] == "call_msg"
    assert isinstance(msg["content"], str)


# ---------- Test 8: lock_intent_from_messages ----------

@test("lock_intent_from_messages auto-detects user intent")
def test_lock_intent_from_messages():
    from vetonet.integrations.openai import VetoNetOpenAI

    veto = VetoNetOpenAI(api_key="veto_sk_test_xxx")

    messages = [
        {"role": "system", "content": "You are a shopping assistant."},
        {"role": "user", "content": "Buy a $50 Amazon gift card"},
        {"role": "assistant", "content": "I'll help you with that."},
    ]

    result = veto.lock_intent_from_messages(messages)
    assert result == "Buy a $50 Amazon gift card"
    assert veto.intent == "Buy a $50 Amazon gift card"


# ---------- Test 9: Empty intent rejected ----------

@test("Empty intent raises ValueError")
def test_empty_intent():
    from vetonet.integrations.openai import VetoNetOpenAI

    veto = VetoNetOpenAI(api_key="veto_sk_test_xxx")

    try:
        veto.lock_intent("")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "empty" in str(e).lower()

    try:
        veto.lock_intent("   ")
        assert False, "Should have raised ValueError for whitespace"
    except ValueError as e:
        assert "empty" in str(e).lower()


# ---------- Test 10: No API key raises config error ----------

@test("Missing API key raises clear VetoNetConfigError")
def test_no_api_key():
    from vetonet.integrations.openai import VetoNetOpenAI
    from vetonet.integrations.langchain.exceptions import VetoNetConfigError

    import os
    old = os.environ.pop("VETONET_API_KEY", None)
    try:
        veto = VetoNetOpenAI()
        assert False, "Should have raised VetoNetConfigError"
    except VetoNetConfigError as e:
        assert "api_key" in str(e).lower() or "API key" in str(e)
    finally:
        if old:
            os.environ["VETONET_API_KEY"] = old


# ---------- Test 11: Auto-infer field mapping ----------

@test("Auto-infer maps 'price' -> 'unit_price', 'item' -> 'item_description'")
def test_auto_infer():
    from vetonet.integrations.openai import VetoNetOpenAI

    veto = VetoNetOpenAI(api_key="veto_sk_test_xxx")
    veto.lock_intent("Buy a $50 Amazon gift card")
    # Register with auto_infer=True (default) and NO field_map
    veto.register_tool("buy_item", buy_item, auto_infer=True)

    response = make_openai_response([{
        "id": "call_auto",
        "name": "buy_item",
        "arguments": {"item": "Amazon gift card", "price": 50.0, "vendor": "Amazon"},
    }])

    captured_payload = {}
    def capture_check_sync(intent, payload):
        captured_payload.update(payload)
        return make_approved_response()

    with patch.object(veto._client, "check_sync", side_effect=capture_check_sync):
        results = veto.process_tool_calls(response)

    assert captured_payload.get("unit_price") == 50.0, f"Auto-infer failed for price: {captured_payload}"
    assert captured_payload.get("item_description") == "Amazon gift card", f"Auto-infer failed for item: {captured_payload}"
    assert captured_payload.get("vendor") == "Amazon", f"Auto-infer failed for vendor: {captured_payload}"


# ---------- Test 12: Dict-format response (not SDK object) ----------

@test("Dict-format response works (raw API response)")
def test_dict_response():
    from vetonet.integrations.openai import VetoNetOpenAI

    veto = VetoNetOpenAI(api_key="veto_sk_test_xxx")
    veto.lock_intent("Buy a $50 Amazon gift card")
    veto.register_tool("buy_item", buy_item)

    # Raw dict response (like from httpx, not openai SDK)
    raw_response = {
        "choices": [{
            "message": {
                "tool_calls": [{
                    "id": "call_dict",
                    "function": {
                        "name": "buy_item",
                        "arguments": '{"item": "Amazon gift card", "price": 50.0, "vendor": "Amazon"}',
                    }
                }]
            }
        }]
    }

    with patch.object(veto._client, "check_sync", return_value=make_approved_response()):
        results = veto.process_tool_calls(raw_response)

    assert len(results) == 1
    assert results[0].approved is True


# ---------- Test 13: Executors passed inline (not pre-registered) ----------

@test("Inline executors override pre-registered ones")
def test_inline_executors():
    from vetonet.integrations.openai import VetoNetOpenAI

    veto = VetoNetOpenAI(api_key="veto_sk_test_xxx")
    veto.lock_intent("Buy a $50 Amazon gift card")

    response = make_openai_response([{
        "id": "call_inline",
        "name": "buy_item",
        "arguments": {"item": "Amazon gift card", "price": 50.0, "vendor": "Amazon"},
    }])

    with patch.object(veto._client, "check_sync", return_value=make_approved_response()):
        results = veto.process_tool_calls(response, executors={"buy_item": buy_item})

    assert results[0].approved is True
    assert "Purchased" in str(results[0].result)


# ---------- Test 14: Decorator (vetonet_function_tool) ----------

@test("@vetonet_function_tool decorator wraps function correctly")
def test_decorator():
    from vetonet.integrations.openai.decorator import (
        vetonet_function_tool,
        set_locked_intent,
        clear_locked_intent,
        _locked_intent,
    )

    @vetonet_function_tool
    def buy_gift_card(item: str, price: float, vendor: str) -> str:
        """Buy a gift card."""
        return f"Bought {item} for ${price} from {vendor}"

    # Check the wrapper preserves the function name and signature
    assert buy_gift_card.__name__ == "buy_gift_card", f"Name lost: {buy_gift_card.__name__}"

    import inspect
    sig = inspect.signature(buy_gift_card)
    params = list(sig.parameters.keys())
    assert "item" in params, f"Signature lost: {params}"
    assert "price" in params, f"Signature lost: {params}"
    assert "vendor" in params, f"Signature lost: {params}"

    # Clean up
    clear_locked_intent()


# ---------- Test 15: Decorator with set_locked_intent ----------

@test("Decorator + set_locked_intent integration")
def test_decorator_with_intent():
    from vetonet.integrations.openai.decorator import (
        vetonet_function_tool,
        set_locked_intent,
        clear_locked_intent,
        _locked_intent,
    )

    @vetonet_function_tool
    def buy_gift_card(item: str, price: float, vendor: str) -> str:
        """Buy a gift card."""
        return f"Bought {item} for ${price} from {vendor}"

    set_locked_intent("Buy a $50 Amazon gift card")
    assert _locked_intent.get() == "Buy a $50 Amazon gift card"

    # The decorator calls get_default_guard() internally which needs setup.
    # Since we're testing integration, we just verify the intent system works.
    clear_locked_intent()
    assert _locked_intent.get() is None


# ---------- Test 16: Context manager ----------

@test("VetoNetOpenAI works as context manager")
def test_context_manager():
    from vetonet.integrations.openai import VetoNetOpenAI

    with VetoNetOpenAI(api_key="veto_sk_test_xxx") as veto:
        veto.lock_intent("Test")
        assert veto.intent == "Test"
    # Should not raise on exit


# ---------- Test 17: Response with no tool calls ----------

@test("Response with no tool calls returns empty results")
def test_no_tool_calls():
    from vetonet.integrations.openai import VetoNetOpenAI

    veto = VetoNetOpenAI(api_key="veto_sk_test_xxx")
    veto.lock_intent("Buy something")

    # Response with no tool calls (just text)
    response = MockChatCompletion(
        id="chatcmpl-text",
        choices=[MockChoice(
            index=0,
            message=MockMessage(content="Here's what I found...", tool_calls=None),
            finish_reason="stop",
        )],
    )

    results = veto.process_tool_calls(response)
    assert len(results) == 0


# ---------- Test 18: Executor throws exception ----------

@test("Executor exception is captured in result (not raised)")
def test_executor_exception():
    from vetonet.integrations.openai import VetoNetOpenAI

    def broken_executor(**kwargs):
        raise RuntimeError("Database connection failed")

    veto = VetoNetOpenAI(api_key="veto_sk_test_xxx")
    veto.lock_intent("Buy something")
    veto.register_tool("broken_tool", broken_executor)

    response = make_openai_response([{
        "id": "call_broken",
        "name": "broken_tool",
        "arguments": {"item": "test"},
    }])

    with patch.object(veto._client, "check_sync", return_value=make_approved_response()):
        results = veto.process_tool_calls(response)

    r = results[0]
    # The tool was approved but execution failed
    assert r.approved is True, "Should still be marked approved (verification passed)"
    assert r.error is not None, "Error should be captured"
    assert "Database connection failed" in r.error

    msg = r.to_tool_message()
    assert "[ERROR]" in msg["content"]


# ============================================================================
# Bug hunt: Check the decorator's _verify_and_execute_sync for a known issue
# ============================================================================

@test("BUG CHECK: decorator._locked_intent is ContextVar, not plain value")
def test_decorator_intent_bug():
    """
    The decorator code at line 173 does:
        intent = _locked_intent
    But _locked_intent is a ContextVar, not a string!
    It should be:
        intent = _locked_intent.get()
    """
    from vetonet.integrations.openai.decorator import _locked_intent, set_locked_intent, clear_locked_intent
    from contextvars import ContextVar

    # Verify _locked_intent IS a ContextVar
    assert isinstance(_locked_intent, ContextVar), f"Expected ContextVar, got {type(_locked_intent)}"

    # Set a value
    set_locked_intent("test intent")

    # The correct way to read it
    assert _locked_intent.get() == "test intent"

    # The BUG: reading _locked_intent directly gives the ContextVar object, not the value
    # In _verify_and_execute_sync line 173: `intent = _locked_intent`
    # This means intent will ALWAYS be truthy (it's a ContextVar object)
    # and will NEVER be None, so the LangChain fallback at line 175 is dead code.
    # Then at line 189: guard.verify_sync(intent, payload) gets a ContextVar, not a string.
    raw_ref = _locked_intent
    assert raw_ref is not None, "ContextVar is always truthy - this is the bug"
    assert not isinstance(raw_ref, str), "ContextVar is NOT a string - this confirms the bug"

    clear_locked_intent()


# ============================================================================
# Run all tests
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("VetoNet OpenAI Integration Test Suite")
    print("(YC Founder Perspective - Testing from scratch)")
    print("=" * 70)
    print()

    # Collect all test functions
    tests = [v for v in globals().values() if callable(v) and hasattr(v, '_test_name')]

    for t in tests:
        run_test(t)

    print()
    print("=" * 70)
    print(f"Results: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
    print("=" * 70)

    if ERRORS:
        print()
        print("FAILURES:")
        for e in ERRORS:
            print(e)

    sys.exit(1 if FAIL > 0 else 0)
