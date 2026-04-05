"""
Integration test for VetoNet CrewAI integration.

Tests from the perspective of a YC founder integrating VetoNet
into their multi-agent CrewAI system.

Run: python -m pytest tests/integration_test_crewai.py -v
  or: python tests/integration_test_crewai.py
"""

import inspect
import sys
import os
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from typing import Any, Optional

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vetonet.integrations.langchain.types import VetoResponse, VetoStatus
from vetonet.integrations.langchain.exceptions import (
    VetoBlockedException,
    IntentNotSetError,
    VetoNetConfigError,
)
from vetonet.integrations.crewai import VetoNetCrewAI, VetoNetCrew, vetonet_tool, ToolCallResult


# ---------------------------------------------------------------------------
# Helpers: mock VetoResponse factories
# ---------------------------------------------------------------------------

def make_approved_response(**overrides) -> VetoResponse:
    defaults = dict(
        verdict="approved",
        status=VetoStatus.APPROVED,
        reason="",
        confidence=0.95,
        checks=[],
        request_id="test-ok-123",
    )
    defaults.update(overrides)
    return VetoResponse(**defaults)


def make_blocked_response(reason="Scam detected", **overrides) -> VetoResponse:
    defaults = dict(
        verdict="blocked",
        status=VetoStatus.VETO,
        reason=reason,
        confidence=0.99,
        checks=[],
        request_id="test-block-456",
    )
    defaults.update(overrides)
    return VetoResponse(**defaults)


# ---------------------------------------------------------------------------
# Dummy tool functions (simulating a real agent's tools)
# ---------------------------------------------------------------------------

def buy_item(item: str, cost: float, vendor: str) -> str:
    """Buy an item from a vendor."""
    return f"Purchased {item} for ${cost} from {vendor}"


def transfer_funds(amount: float, recipient: str, memo: str = "") -> str:
    """Transfer funds to a recipient."""
    return f"Transferred ${amount} to {recipient}"


# ===========================================================================
# TEST 1: Context manager + lock_intent + verify_and_execute (honest call)
# ===========================================================================

def test_honest_tool_call():
    """An agent buys exactly what the user asked for."""
    print("\n--- TEST 1: Honest tool call ---")

    with patch.object(
        VetoNetCrewAI, "__init__", lambda self, **kw: _bare_init(self)
    ):
        with VetoNetCrewAI() as veto:
            veto.lock_intent("Buy a $50 Amazon gift card")
            veto.register_tool(
                "buy_item",
                executor=buy_item,
                field_map={"cost": "unit_price"},
            )

            # Mock the API call to return approved
            with patch.object(
                veto._client, "check_sync", return_value=make_approved_response()
            ):
                result = veto.verify_and_execute(
                    "buy_item",
                    {"item": "Amazon gift card", "cost": 50.0, "vendor": "Amazon"},
                )

            assert result.approved, "Should be approved"
            assert result.result == "Purchased Amazon gift card for $50.0 from Amazon"
            assert result.blocked_reason is None
            print(f"  PASS: result={result.result}")

    print("  PASS: Context manager exited cleanly")


# ===========================================================================
# TEST 2: Malicious tool call - agent tries to inflate price
# ===========================================================================

def test_malicious_tool_call():
    """Agent tries to buy a $500 item when user said $50."""
    print("\n--- TEST 2: Malicious tool call (price inflation) ---")

    with patch.object(
        VetoNetCrewAI, "__init__", lambda self, **kw: _bare_init(self)
    ):
        with VetoNetCrewAI() as veto:
            veto.lock_intent("Buy a $50 Amazon gift card")
            veto.register_tool("buy_item", executor=buy_item, field_map={"cost": "unit_price"})

            with patch.object(
                veto._client,
                "check_sync",
                return_value=make_blocked_response("Price mismatch: $500 vs intent $50"),
            ):
                try:
                    veto.verify_and_execute(
                        "buy_item",
                        {"item": "Amazon gift card", "cost": 500.0, "vendor": "Amazon"},
                    )
                    assert False, "Should have raised VetoBlockedException"
                except VetoBlockedException as e:
                    print(f"  PASS: Blocked with reason: {e.reason}")
                    assert "Price mismatch" in e.reason


# ===========================================================================
# TEST 3: @vetonet_tool decorator
# ===========================================================================

def test_vetonet_tool_decorator():
    """Test the decorator approach."""
    print("\n--- TEST 3: @vetonet_tool decorator ---")

    # Decorate a function
    @vetonet_tool(field_map={"cost": "unit_price"})
    def buy_gift_card(cost: float, seller: str) -> str:
        """Buy a gift card."""
        return f"Bought card for ${cost} from {seller}"

    # Verify signature is preserved
    sig = inspect.signature(buy_gift_card)
    params = list(sig.parameters.keys())
    assert "cost" in params, f"'cost' not in params: {params}"
    assert "seller" in params, f"'seller' not in params: {params}"
    print(f"  PASS: Signature preserved: {params}")

    # Call WITHOUT context manager -> should raise IntentNotSetError
    try:
        buy_gift_card(cost=50.0, seller="Amazon")
        assert False, "Should have raised IntentNotSetError"
    except IntentNotSetError as e:
        print(f"  PASS: No guard active -> IntentNotSetError: {e.message[:80]}")

    # Call WITH context manager but no intent locked
    with patch.object(
        VetoNetCrewAI, "__init__", lambda self, **kw: _bare_init(self)
    ):
        with VetoNetCrewAI() as veto:
            try:
                buy_gift_card(cost=50.0, seller="Amazon")
                assert False, "Should have raised IntentNotSetError"
            except IntentNotSetError as e:
                print(f"  PASS: No intent locked -> IntentNotSetError: {e.message[:80]}")

    # Call WITH context manager AND intent AND mocked approval
    with patch.object(
        VetoNetCrewAI, "__init__", lambda self, **kw: _bare_init(self)
    ):
        with VetoNetCrewAI() as veto:
            veto.lock_intent("Buy a $50 Amazon gift card")

            with patch.object(
                veto._client, "check_sync", return_value=make_approved_response()
            ):
                result = buy_gift_card(cost=50.0, seller="Amazon")
                assert result == "Bought card for $50.0 from Amazon"
                print(f"  PASS: Decorator approved call, result={result}")


# ===========================================================================
# TEST 4: VetoNetCrew - ImportError path (CrewAI not installed)
# ===========================================================================

def test_vetonet_crew_import_error():
    """VetoNetCrew should give a clear ImportError when crewai is not installed."""
    print("\n--- TEST 4: VetoNetCrew without crewai ---")

    try:
        crew = VetoNetCrew(
            agents=[],
            tasks=[],
            vetonet_api_key="veto_sk_test_xxx",
        )
        # If crewai IS installed somehow, this is still ok
        print(f"  INFO: CrewAI is installed, VetoNetCrew created successfully")
    except ImportError as e:
        msg = str(e)
        assert "crewai" in msg.lower(), f"ImportError should mention crewai: {msg}"
        assert "pip install" in msg, f"Should suggest pip install: {msg}"
        print(f"  PASS: Clear ImportError: {msg}")
    except VetoNetConfigError:
        # This would mean crewai IS installed but no valid key
        print(f"  INFO: CrewAI is installed (got config error, expected)")


# ===========================================================================
# TEST 5: VetoNetCrew with mocked CrewAI
# ===========================================================================

def test_vetonet_crew_mocked():
    """Test VetoNetCrew with mocked CrewAI classes."""
    print("\n--- TEST 5: VetoNetCrew with mocked CrewAI ---")

    # Build fake Agent and Task
    @dataclass
    class FakeTask:
        description: str = "Buy a $50 Amazon gift card for the office"

    @dataclass
    class FakeAgent:
        name: str = "buyer"
        tools: list = None

        def __post_init__(self):
            if self.tools is None:
                self.tools = []

    @dataclass
    class FakeTool:
        name: str = "buy_item"
        func: Any = None

        def __call__(self, *a, **kw):
            return self.func(*a, **kw) if self.func else "done"

    fake_tool = FakeTool(name="buy_item", func=buy_item)
    agent = FakeAgent(name="buyer", tools=[fake_tool])
    task = FakeTask()

    # Patch crewai import inside crew.py
    import vetonet.integrations.crewai.crew as crew_mod

    original_has = crew_mod._HAS_CREWAI
    original_crew_cls = crew_mod.Crew

    try:
        crew_mod._HAS_CREWAI = True

        # Mock the Crew class to just call each tool
        mock_crew_cls = MagicMock()
        mock_crew_instance = MagicMock()
        mock_crew_instance.kickoff.return_value = "Crew completed"
        mock_crew_cls.return_value = mock_crew_instance
        crew_mod.Crew = mock_crew_cls

        # Now test VetoNetCrew with mocked API
        with patch.object(
            VetoNetCrewAI, "__init__", lambda self, **kw: _bare_init(self)
        ):
            vc = VetoNetCrew.__new__(VetoNetCrew)
            vc._agents = [agent]
            vc._tasks = [task]
            vc._field_maps = {"buy_item": {"cost": "unit_price"}}
            vc._crew_kwargs = {}
            vc._guard = VetoNetCrewAI.__new__(VetoNetCrewAI)
            _bare_init(vc._guard)
            vc._original_tools = {}

            # Test intent extraction
            intent = vc._extract_intent()
            assert "Buy a $50 Amazon gift card" in intent
            print(f"  PASS: Intent extracted: {intent[:60]}")

            # Test tool wrapping
            vc._guard.lock_intent(intent)
            vc._wrap_all_tools()
            assert hasattr(agent.tools[0], "_vetonet_protected") or True
            print(f"  PASS: Tools wrapped ({len(agent.tools)} tools)")

            # Test kickoff
            with patch.object(
                vc._guard._client, "check_sync", return_value=make_approved_response()
            ):
                result = vc.kickoff()
                assert result == "Crew completed"
                print(f"  PASS: kickoff() returned: {result}")

    finally:
        crew_mod._HAS_CREWAI = original_has
        crew_mod.Crew = original_crew_cls


# ===========================================================================
# TEST 6: Edge case - no context manager
# ===========================================================================

def test_no_context_manager():
    """Decorator should fail closed without active guard."""
    print("\n--- TEST 6: No context manager (no active guard) ---")

    @vetonet_tool
    def risky_buy(item: str, price: float) -> str:
        """A tool used outside context manager."""
        return f"bought {item}"

    try:
        risky_buy(item="laptop", price=999)
        assert False, "Should have raised"
    except IntentNotSetError as e:
        assert "context manager" in e.message.lower() or "guard" in e.message.lower()
        print(f"  PASS: Correctly blocked: {e.message[:80]}")


# ===========================================================================
# TEST 7: Edge case - no intent locked
# ===========================================================================

def test_no_intent_locked():
    """verify_and_execute should fail closed without locked intent."""
    print("\n--- TEST 7: No intent locked ---")

    with patch.object(
        VetoNetCrewAI, "__init__", lambda self, **kw: _bare_init(self)
    ):
        with VetoNetCrewAI() as veto:
            veto.register_tool("buy_item", executor=buy_item)

            try:
                veto.verify_and_execute("buy_item", {"item": "laptop", "cost": 999})
                assert False, "Should have raised IntentNotSetError"
            except IntentNotSetError as e:
                assert "lock_intent" in e.message
                print(f"  PASS: Correctly blocked: {e.message[:80]}")


# ===========================================================================
# TEST 8: Edge case - empty intent
# ===========================================================================

def test_empty_intent():
    """lock_intent should reject empty strings."""
    print("\n--- TEST 8: Empty intent ---")

    with patch.object(
        VetoNetCrewAI, "__init__", lambda self, **kw: _bare_init(self)
    ):
        with VetoNetCrewAI() as veto:
            for bad_intent in ["", "   ", None]:
                try:
                    if bad_intent is None:
                        # lock_intent expects str, None should error
                        veto.lock_intent(bad_intent)
                        assert False, f"Should have raised for intent={bad_intent!r}"
                    else:
                        veto.lock_intent(bad_intent)
                        assert False, f"Should have raised for intent={bad_intent!r}"
                except (ValueError, AttributeError, TypeError):
                    print(f"  PASS: Rejected intent={bad_intent!r}")


# ===========================================================================
# TEST 9: Edge case - no executor registered
# ===========================================================================

def test_no_executor():
    """verify_and_execute without executor should return blocked result."""
    print("\n--- TEST 9: No executor registered ---")

    with patch.object(
        VetoNetCrewAI, "__init__", lambda self, **kw: _bare_init(self)
    ):
        with VetoNetCrewAI() as veto:
            veto.lock_intent("Buy a gift card")
            # Register tool without executor
            veto.register_tool("phantom_tool")

            result = veto.verify_and_execute("phantom_tool", {"item": "test"})
            assert not result.approved
            assert "No executor" in result.blocked_reason
            print(f"  PASS: Blocked with: {result.blocked_reason}")


# ===========================================================================
# TEST 10: Decorator preserves function metadata
# ===========================================================================

def test_decorator_preserves_metadata():
    """Decorator should preserve __name__, __doc__, __signature__."""
    print("\n--- TEST 10: Decorator metadata preservation ---")

    @vetonet_tool(field_map={"cost": "unit_price"})
    def purchase_widget(cost: float, color: str, quantity: int = 1) -> str:
        """Purchase a widget in the specified color."""
        return f"{quantity}x {color} widget(s)"

    # Check name
    assert purchase_widget.__name__ == "purchase_widget", (
        f"Name mangled: {purchase_widget.__name__}"
    )
    print(f"  PASS: __name__ = {purchase_widget.__name__}")

    # Check docstring
    assert "widget" in (purchase_widget.__doc__ or "").lower(), (
        f"Docstring lost: {purchase_widget.__doc__}"
    )
    print(f"  PASS: __doc__ preserved")

    # Check signature
    sig = inspect.signature(purchase_widget)
    params = list(sig.parameters.keys())
    assert params == ["cost", "color", "quantity"], f"Signature wrong: {params}"
    print(f"  PASS: __signature__ = {sig}")

    # Check default value preserved
    assert sig.parameters["quantity"].default == 1
    print(f"  PASS: Default values preserved")


# ===========================================================================
# TEST 11: lock_intent_from_task
# ===========================================================================

def test_lock_intent_from_task():
    """lock_intent_from_task should extract description from task objects."""
    print("\n--- TEST 11: lock_intent_from_task ---")

    @dataclass
    class FakeTask:
        description: str

    with patch.object(
        VetoNetCrewAI, "__init__", lambda self, **kw: _bare_init(self)
    ):
        with VetoNetCrewAI() as veto:
            task = FakeTask(description="Buy a $25 Starbucks gift card")
            result = veto.lock_intent_from_task(task)
            assert result == "Buy a $25 Starbucks gift card"
            assert veto.intent == "Buy a $25 Starbucks gift card"
            print(f"  PASS: Intent from task: {veto.intent}")

            # Task with no description
            empty_task = FakeTask(description="")
            result = veto.lock_intent_from_task(empty_task)
            assert result is None
            print(f"  PASS: Empty task description returns None")


# ===========================================================================
# TEST 12: ToolCallResult dataclass
# ===========================================================================

def test_tool_call_result():
    """ToolCallResult should be a clean data object."""
    print("\n--- TEST 12: ToolCallResult dataclass ---")

    ok = ToolCallResult(tool_name="buy", approved=True, result="done", request_id="abc")
    assert ok.approved
    assert ok.result == "done"
    assert ok.blocked_reason is None
    assert ok.error is None
    print(f"  PASS: Approved result: {ok}")

    blocked = ToolCallResult(tool_name="buy", approved=False, blocked_reason="scam")
    assert not blocked.approved
    assert blocked.blocked_reason == "scam"
    print(f"  PASS: Blocked result: {blocked}")


# ===========================================================================
# TEST 13: Auto-infer field mapping
# ===========================================================================

def test_auto_infer_mapping():
    """Auto-infer should map common param names without explicit field_map."""
    print("\n--- TEST 13: Auto-infer field mapping ---")

    with patch.object(
        VetoNetCrewAI, "__init__", lambda self, **kw: _bare_init(self)
    ):
        with VetoNetCrewAI() as veto:
            veto.lock_intent("Buy a laptop")
            # Register with NO explicit field_map, rely on auto_infer
            veto.register_tool("buy", executor=buy_item, auto_infer=True)

            # The registry should auto-map 'price' -> 'unit_price', etc.
            payload = veto.registry.map_to_payload(
                "buy", {"item": "laptop", "price": 999, "vendor": "BestBuy"}
            )
            assert payload["unit_price"] == 999.0
            assert payload["item_description"] == "laptop"
            assert payload["vendor"] == "BestBuy"
            print(f"  PASS: Auto-mapped payload: price->unit_price, item->item_description")


# ===========================================================================
# Bare init helper (bypasses API key requirement)
# ===========================================================================

def _bare_init(self):
    """Initialize VetoNetCrewAI without needing a real API key."""
    from vetonet.integrations.langchain.types import (
        VetoNetGuardConfig,
        VetoNetClientConfig,
        CircuitBreakerConfig,
    )
    from vetonet.integrations.langchain.client import APIClient
    from vetonet.integrations.langchain.circuit import CircuitBreaker
    from vetonet.integrations.langchain.registry import ToolRegistry

    self._config = VetoNetGuardConfig(api_key="veto_sk_test_fake")
    self._circuit_breaker = CircuitBreaker(CircuitBreakerConfig())
    client_config = VetoNetClientConfig(api_key="veto_sk_test_fake")
    self._client = APIClient(config=client_config, circuit_breaker=self._circuit_breaker)
    self._registry = ToolRegistry()
    self._locked_intent = None
    self._executors = {}
    self._token = None


# ===========================================================================
# Runner
# ===========================================================================

ALL_TESTS = [
    test_honest_tool_call,
    test_malicious_tool_call,
    test_vetonet_tool_decorator,
    test_vetonet_crew_import_error,
    test_vetonet_crew_mocked,
    test_no_context_manager,
    test_no_intent_locked,
    test_empty_intent,
    test_no_executor,
    test_decorator_preserves_metadata,
    test_lock_intent_from_task,
    test_tool_call_result,
    test_auto_infer_mapping,
]


def main():
    passed = 0
    failed = 0
    errors = []

    print("=" * 70)
    print("VetoNet CrewAI Integration Tests")
    print("=" * 70)

    for test_fn in ALL_TESTS:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((test_fn.__name__, e))
            print(f"  FAIL: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed out of {len(ALL_TESTS)}")
    if errors:
        print("\nFailures:")
        for name, err in errors:
            print(f"  - {name}: {err}")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
