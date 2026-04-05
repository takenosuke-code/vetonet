"""
VetoNet CrewAI Integration - @vetonet_tool Decorator

Wraps a function with VetoNet verification, then optionally applies
CrewAI's @tool decorator for seamless integration.
"""

import functools
import inspect
import logging
import os
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from vetonet.integrations.langchain.exceptions import (
    VetoBlockedException,
    IntentNotSetError,
    CircuitOpenError,
    VetoNetError,
)
from vetonet.integrations.langchain.registry import ToolSignatureConfig, get_registry

logger = logging.getLogger("vetonet.crewai")

T = TypeVar("T")

# Try to import CrewAI's tool decorator
try:
    from crewai.tools import tool as crewai_tool

    _HAS_CREWAI = True
except ImportError:
    _HAS_CREWAI = False
    crewai_tool = None


def vetonet_tool(
    func: Optional[Callable] = None,
    *,
    # Tool metadata
    name: Optional[str] = None,
    # Signature mapping
    field_map: Optional[Dict[str, str]] = None,
    defaults: Optional[Dict[str, Any]] = None,
    auto_infer: bool = True,
    # VetoNet behavior
    on_veto: Optional[Callable[[VetoBlockedException], Any]] = None,
) -> Union[Callable, Any]:
    """Create a CrewAI tool with VetoNet protection.

    Wraps the function with VetoNet verification, preserves __signature__
    for CrewAI schema extraction, and applies CrewAI's @tool if available.

    Simple usage:
        @vetonet_tool
        def buy_item(item: str, price: float, vendor: str) -> str:
            '''Buy an item from a vendor.'''
            return execute_purchase(item, price, vendor)

    With mapping:
        @vetonet_tool(
            name="Buy Gift Card",
            field_map={"cost": "unit_price", "seller": "vendor"},
            defaults={"item_category": "gift_card"}
        )
        def buy_gift_card(cost: float, seller: str) -> str:
            '''Buy a gift card.'''
            ...

    Args:
        func: Function to decorate (if used without parens)
        name: Tool name for CrewAI (default: function name)
        field_map: Map tool params to AgentPayload fields
        defaults: Default values for AgentPayload fields
        auto_infer: Auto-map params with matching names
        on_veto: Callback when transaction is vetoed

    Returns:
        CrewAI tool with VetoNet protection, or wrapped function if CrewAI not installed
    """

    def decorator(fn: Callable) -> Union[Callable, Any]:
        tool_name = name or fn.__name__

        # Build and register signature config
        config = ToolSignatureConfig(
            field_map=field_map or {},
            defaults=defaults or {},
            auto_infer=auto_infer,
        )
        registry = get_registry()
        registry.register(tool_name, config)

        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def wrapper(*args, **kwargs) -> Any:
                return await _execute_with_verification_async(
                    fn, args, kwargs, tool_name, config, on_veto
                )
        else:
            @functools.wraps(fn)
            def wrapper(*args, **kwargs) -> Any:
                return _execute_with_verification(
                    fn, args, kwargs, tool_name, config, on_veto
                )

        # Preserve __signature__ for CrewAI schema extraction
        wrapper.__signature__ = inspect.signature(fn)

        # Apply CrewAI's @tool decorator if available
        # crewai_tool is applied directly to the function, not as a factory
        if _HAS_CREWAI and crewai_tool is not None:
            wrapper.__name__ = tool_name
            return crewai_tool(wrapper)

        return wrapper

    # Handle @vetonet_tool vs @vetonet_tool()
    if func is not None:
        return decorator(func)
    return decorator


def _execute_with_verification(
    fn: Callable,
    args: tuple,
    kwargs: dict,
    tool_name: str,
    config: ToolSignatureConfig,
    on_veto: Optional[Callable],
) -> Any:
    """Execute function with VetoNet verification."""
    from .guard import get_active_guard

    guard = get_active_guard()

    # Fail closed: no guard = block
    if guard is None:
        raise IntentNotSetError(
            message="No VetoNetCrewAI guard active. Use 'with VetoNetCrewAI(...) as veto:' context manager.",
            tool_name=tool_name,
        )

    # Fail closed: no intent = block
    if guard.intent is None:
        raise IntentNotSetError(
            message="No intent locked. Call lock_intent() before tool execution.",
            tool_name=tool_name,
        )

    try:
        # Map args to payload
        payload = guard.registry.map_to_payload(tool_name, kwargs)

        # Verify with VetoNet
        result = guard._client.check_sync(guard.intent, payload)

        if result.blocked:
            exc = VetoBlockedException(
                reason=result.reason,
                confidence=result.confidence,
                request_id=result.request_id,
            )
            if on_veto:
                logger.warning(
                    "[SECURITY] on_veto callback intercepted block for %s: %s",
                    tool_name,
                    exc.reason,
                )
                return on_veto(exc)
            raise exc

        # Approved - execute
        return fn(*args, **kwargs)

    except (VetoBlockedException, IntentNotSetError):
        raise
    except CircuitOpenError:
        raise VetoBlockedException(
            reason="VetoNet unavailable (circuit open)",
        )
    except VetoNetError as e:
        raise VetoBlockedException(
            reason=f"VetoNet verification error: {e}",
        )


async def _execute_with_verification_async(
    fn: Callable,
    args: tuple,
    kwargs: dict,
    tool_name: str,
    config: ToolSignatureConfig,
    on_veto: Optional[Callable],
) -> Any:
    """Execute async function with VetoNet verification."""
    from .guard import get_active_guard

    guard = get_active_guard()

    if guard is None:
        raise IntentNotSetError(
            message="No VetoNetCrewAI guard active. Use 'with VetoNetCrewAI(...) as veto:' context manager.",
            tool_name=tool_name,
        )

    if guard.intent is None:
        raise IntentNotSetError(
            message="No intent locked. Call lock_intent() before tool execution.",
            tool_name=tool_name,
        )

    try:
        payload = guard.registry.map_to_payload(tool_name, kwargs)
        result = await guard._client.check(guard.intent, payload)

        if result.blocked:
            exc = VetoBlockedException(
                reason=result.reason,
                confidence=result.confidence,
                request_id=result.request_id,
            )
            if on_veto:
                logger.warning(
                    "[SECURITY] on_veto callback intercepted block for %s: %s",
                    tool_name,
                    exc.reason,
                )
                return on_veto(exc)
            raise exc

        return await fn(*args, **kwargs)

    except (VetoBlockedException, IntentNotSetError):
        raise
    except CircuitOpenError:
        raise VetoBlockedException(reason="VetoNet unavailable (circuit open)")
    except VetoNetError as e:
        raise VetoBlockedException(reason=f"VetoNet verification error: {e}")


__all__ = [
    "vetonet_tool",
]
