"""
VetoNet OpenAI Agents SDK Integration - @vetonet_function_tool Decorator

Wraps a function with VetoNet verification for use with OpenAI's Agents SDK.
Preserves __signature__ so @function_tool schema extraction works correctly.
"""

import functools
import inspect
import logging
from vetonet.integrations.fail_open import should_allow_fail_open
from typing import Any, Callable, Dict, Optional, TypeVar

from vetonet.integrations.langchain.exceptions import (
    VetoBlockedException,
    IntentNotSetError,
    CircuitOpenError,
    MappingError,
    SignatureError,
    VetoNetError,
)
from vetonet.integrations.langchain.registry import (
    ToolSignatureConfig,
    get_registry,
)

logger = logging.getLogger("vetonet.openai")

T = TypeVar("T")

# Thread/async-safe locked intent using ContextVar (not a plain global)
from contextvars import ContextVar

_locked_intent: ContextVar[Optional[str]] = ContextVar("vetonet_openai_intent", default=None)


def set_locked_intent(intent: str) -> None:
    """Set the locked intent for the current execution context.

    Thread-safe and async-safe via ContextVar.

    Args:
        intent: Natural language intent (e.g., "Buy a $50 Amazon gift card")
    """
    if not intent or not intent.strip():
        raise ValueError("Intent cannot be empty")
    _locked_intent.set(intent.strip())


def get_locked_intent() -> Optional[str]:
    """Get the current locked intent for this execution context."""
    return _locked_intent.get()


def clear_locked_intent() -> None:
    """Clear the locked intent for this execution context."""
    _locked_intent.set(None)


# Try to import OpenAI Agents SDK
try:
    from agents import function_tool as openai_function_tool

    _HAS_AGENTS_SDK = True
except ImportError:
    _HAS_AGENTS_SDK = False
    openai_function_tool = None


def vetonet_function_tool(
    func: Optional[Callable] = None,
    *,
    field_map: Optional[Dict[str, str]] = None,
    defaults: Optional[Dict[str, Any]] = None,
    auto_infer: bool = True,
    name: Optional[str] = None,
    fail_open: bool = False,
) -> Callable:
    """Decorator that wraps a function with VetoNet verification for OpenAI Agents SDK.

    Preserves __signature__ so @function_tool can extract the schema correctly.
    If the OpenAI Agents SDK is available, applies @function_tool after wrapping.

    Simple usage:
        @vetonet_function_tool
        def buy_item(item: str, price: float, vendor: str) -> str:
            '''Buy an item.'''
            return execute_purchase(item, price, vendor)

    With mapping:
        @vetonet_function_tool(
            field_map={"cost": "unit_price", "seller": "vendor"},
            defaults={"item_category": "gift_card"}
        )
        def buy_gift_card(cost: float, seller: str) -> str:
            '''Buy a gift card.'''
            ...

    Args:
        func: Function to decorate (if used without parens)
        field_map: Map tool params to AgentPayload fields
        defaults: Default values for AgentPayload fields
        auto_infer: Auto-map params with matching names
        name: Tool name (default: function name)
        fail_open: Allow transaction if VetoNet unavailable

    Returns:
        Wrapped function (with @function_tool applied if Agents SDK available)
    """

    def decorator(fn: Callable) -> Callable:
        tool_name = name or fn.__name__

        # Build signature config and register
        config = ToolSignatureConfig(
            field_map=field_map or {},
            defaults=defaults or {},
            auto_infer=auto_infer,
            fail_open=fail_open,
        )
        registry = get_registry()
        registry.register(tool_name, config)

        is_async = inspect.iscoroutinefunction(fn)

        if is_async:

            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs) -> Any:
                return await _verify_and_execute_async(fn, args, kwargs, tool_name, config)

            async_wrapper.__signature__ = inspect.signature(fn)
            wrapper = async_wrapper
        else:

            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs) -> Any:
                return _verify_and_execute_sync(fn, args, kwargs, tool_name, config)

            sync_wrapper.__signature__ = inspect.signature(fn)
            wrapper = sync_wrapper

        # Apply OpenAI Agents SDK @function_tool if available
        if _HAS_AGENTS_SDK and openai_function_tool is not None:
            return openai_function_tool(wrapper)

        return wrapper

    # Handle @vetonet_function_tool vs @vetonet_function_tool()
    if func is not None:
        return decorator(func)
    return decorator


def _verify_and_execute_sync(
    fn: Callable,
    args: tuple,
    kwargs: dict,
    tool_name: str,
    config: ToolSignatureConfig,
) -> Any:
    """Execute function with VetoNet verification (sync)."""
    from vetonet.integrations.langchain.guard import get_default_guard

    try:
        guard = get_default_guard()

        # Get intent from ContextVar or LangChain intent system
        intent = _locked_intent.get()
        if intent is None:
            from vetonet.integrations.langchain.intent import get_current_intent

            lc_intent = get_current_intent()
            if lc_intent is not None:
                intent = lc_intent.raw_message

        if intent is None:
            raise IntentNotSetError(tool_name=tool_name)

        # Map kwargs to payload
        registry = get_registry()
        payload = registry.map_to_payload(tool_name, kwargs)

        # Verify with VetoNet
        result = guard.verify_sync(intent, payload)

        if result.blocked:
            raise VetoBlockedException(
                reason=result.reason,
                confidence=result.confidence,
                request_id=result.request_id,
            )

        # Verification passed - execute
        return fn(*args, **kwargs)

    except (VetoBlockedException, IntentNotSetError):
        raise
    except CircuitOpenError:
        if should_allow_fail_open(config.fail_open, tool_name, "circuit_open", logger):
            return fn(*args, **kwargs)
        raise VetoBlockedException(reason="VetoNet unavailable (circuit open)")
    except (MappingError, SignatureError):
        raise
    except VetoNetError:
        if should_allow_fail_open(config.fail_open, tool_name, "vetonet_error", logger):
            return fn(*args, **kwargs)
        raise


async def _verify_and_execute_async(
    fn: Callable,
    args: tuple,
    kwargs: dict,
    tool_name: str,
    config: ToolSignatureConfig,
) -> Any:
    """Execute function with VetoNet verification (async)."""
    from vetonet.integrations.langchain.guard import get_default_guard

    try:
        guard = get_default_guard()

        # Get intent from ContextVar or LangChain intent system
        intent = _locked_intent.get()
        if intent is None:
            from vetonet.integrations.langchain.intent import get_current_intent

            lc_intent = get_current_intent()
            if lc_intent is not None:
                intent = lc_intent.raw_message

        if intent is None:
            raise IntentNotSetError(tool_name=tool_name)

        # Map kwargs to payload
        registry = get_registry()
        payload = registry.map_to_payload(tool_name, kwargs)

        # Verify with VetoNet
        result = await guard.verify_async(intent, payload)

        if result.blocked:
            raise VetoBlockedException(
                reason=result.reason,
                confidence=result.confidence,
                request_id=result.request_id,
            )

        # Verification passed - execute
        return await fn(*args, **kwargs)

    except (VetoBlockedException, IntentNotSetError):
        raise
    except CircuitOpenError:
        if should_allow_fail_open(config.fail_open, tool_name, "circuit_open", logger):
            return await fn(*args, **kwargs)
        raise VetoBlockedException(reason="VetoNet unavailable (circuit open)")
    except (MappingError, SignatureError):
        raise
    except VetoNetError:
        if should_allow_fail_open(config.fail_open, tool_name, "vetonet_error", logger):
            return await fn(*args, **kwargs)
        raise


__all__ = [
    "vetonet_function_tool",
    "set_locked_intent",
    "get_locked_intent",
    "clear_locked_intent",
]
