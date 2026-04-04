"""
VetoNet LangChain Integration - @protected_tool Decorator

Combined decorator that creates a LangChain tool with VetoNet protection.
Eliminates decorator order confusion by handling both in one.
"""

import functools
import inspect
import logging
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from .async_utils import is_async_callable
from .exceptions import (
    VetoBlockedException,
    VetoBlockedToolException,
    IntentNotSetError,
    CircuitOpenError,
    VetoNetError,
    LANGCHAIN_AVAILABLE,
)
from .intent import get_current_intent
from .registry import ToolSignatureConfig, get_registry

logger = logging.getLogger("vetonet.langchain")

T = TypeVar("T")

# Try to import LangChain
try:
    from langchain_core.tools import StructuredTool, tool as langchain_tool
    from langchain_core.tools import ToolException
    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False
    StructuredTool = None
    langchain_tool = None
    ToolException = Exception


def protected_tool(
    func: Optional[Callable] = None,
    *,
    # Signature mapping
    field_map: Optional[Dict[str, str]] = None,
    defaults: Optional[Dict[str, Any]] = None,
    auto_infer: bool = True,

    # Tool metadata (passed to LangChain @tool)
    name: Optional[str] = None,
    description: Optional[str] = None,
    return_direct: bool = False,

    # VetoNet behavior
    fail_open: bool = False,
    on_veto: Optional[Callable[[VetoBlockedException], Any]] = None,
) -> Union[Callable, "StructuredTool"]:
    """Create a LangChain tool with VetoNet protection.

    This is a combined decorator that:
    1. Creates a LangChain StructuredTool
    2. Registers signature mapping with VetoNet
    3. Wraps execution with VetoNet verification

    Simple usage:
        @protected_tool
        def buy_item(item: str, price: float, vendor: str) -> str:
            '''Buy an item.'''
            return execute_purchase(item, price, vendor)

    With mapping:
        @protected_tool(
            field_map={"cost": "unit_price", "seller": "vendor"},
            defaults={"item_category": "gift_card"}
        )
        def buy_gift_card(cost: float, seller: str, recipient: str) -> str:
            '''Buy a gift card.'''
            ...

    Args:
        func: Function to decorate (if used without parens)
        field_map: Map tool params to AgentPayload fields
        defaults: Default values for AgentPayload fields
        auto_infer: Auto-map params with matching names
        name: Tool name (default: function name)
        description: Tool description (default: docstring)
        return_direct: Return tool output directly to user
        fail_open: Allow transaction if VetoNet unavailable
        on_veto: Callback when transaction is vetoed

    Returns:
        LangChain StructuredTool with VetoNet protection
    """
    def decorator(fn: Callable) -> Union[Callable, "StructuredTool"]:
        # Get function metadata
        tool_name = name or fn.__name__
        tool_desc = description or fn.__doc__ or f"Execute {tool_name}"

        # Build signature config
        config = ToolSignatureConfig(
            field_map=field_map or {},
            defaults=defaults or {},
            auto_infer=auto_infer,
            fail_open=fail_open,
        )

        # Register with registry
        registry = get_registry()
        registry.register(tool_name, config)

        # Detect if async
        is_async = is_async_callable(fn)

        if is_async:
            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs) -> Any:
                return await _execute_with_verification(
                    fn, args, kwargs, tool_name, config, on_veto, is_async=True
                )

            # Preserve signature for LangChain
            async_wrapper.__signature__ = inspect.signature(fn)
            wrapper = async_wrapper
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs) -> Any:
                return _execute_with_verification_sync(
                    fn, args, kwargs, tool_name, config, on_veto
                )

            # Preserve signature for LangChain
            sync_wrapper.__signature__ = inspect.signature(fn)
            wrapper = sync_wrapper

        # Create LangChain tool if available
        if _HAS_LANGCHAIN:
            lc_tool = StructuredTool.from_function(
                func=wrapper,
                name=tool_name,
                description=tool_desc,
                return_direct=return_direct,
                handle_tool_error=True,  # Handle VetoBlockedToolException gracefully
            )
            return lc_tool

        # No LangChain - return wrapped function
        return wrapper

    # Handle @protected_tool vs @protected_tool()
    if func is not None:
        return decorator(func)
    return decorator


async def _execute_with_verification(
    fn: Callable,
    args: tuple,
    kwargs: dict,
    tool_name: str,
    config: ToolSignatureConfig,
    on_veto: Optional[Callable],
    is_async: bool
) -> Any:
    """Execute function with VetoNet verification (async version)."""
    # Import here to avoid circular import
    from .guard import get_default_guard

    try:
        guard = get_default_guard()

        # Get intent
        intent = get_current_intent()
        if intent is None:
            if config.fail_open:
                logger.warning(f"No intent captured for {tool_name}, allowing (fail_open)")
            else:
                raise IntentNotSetError(tool_name=tool_name)

        # Map args to payload
        registry = get_registry()
        payload = registry.map_to_payload(tool_name, kwargs)

        # Verify with VetoNet
        if intent is not None:
            result = await guard.verify_async(intent.raw_message, payload)

            if result.blocked:
                exc = VetoBlockedToolException(
                    reason=result.reason,
                    confidence=result.confidence,
                    request_id=result.request_id
                ) if LANGCHAIN_AVAILABLE else VetoBlockedException(
                    reason=result.reason,
                    confidence=result.confidence,
                    request_id=result.request_id
                )

                if on_veto:
                    return on_veto(exc)
                raise exc

        # Verification passed - execute
        return await fn(*args, **kwargs)

    except (VetoBlockedException, VetoBlockedToolException):
        raise
    except IntentNotSetError:
        raise
    except CircuitOpenError:
        if config.fail_open:
            logger.warning(f"Circuit open for {tool_name}, allowing (fail_open)")
            return await fn(*args, **kwargs)
        raise VetoBlockedToolException(
            reason="VetoNet unavailable (circuit open)"
        ) if LANGCHAIN_AVAILABLE else VetoBlockedException(
            reason="VetoNet unavailable (circuit open)"
        )
    except VetoNetError as e:
        if config.fail_open:
            logger.warning(f"VetoNet error for {tool_name}: {e}, allowing (fail_open)")
            return await fn(*args, **kwargs)
        raise


def _execute_with_verification_sync(
    fn: Callable,
    args: tuple,
    kwargs: dict,
    tool_name: str,
    config: ToolSignatureConfig,
    on_veto: Optional[Callable]
) -> Any:
    """Execute function with VetoNet verification (sync version)."""
    from .guard import get_default_guard

    try:
        guard = get_default_guard()

        # Get intent
        intent = get_current_intent()
        if intent is None:
            if config.fail_open:
                logger.warning(f"No intent captured for {tool_name}, allowing (fail_open)")
            else:
                raise IntentNotSetError(tool_name=tool_name)

        # Map args to payload
        registry = get_registry()
        payload = registry.map_to_payload(tool_name, kwargs)

        # Verify with VetoNet
        if intent is not None:
            result = guard.verify_sync(intent.raw_message, payload)

            if result.blocked:
                exc = VetoBlockedToolException(
                    reason=result.reason,
                    confidence=result.confidence,
                    request_id=result.request_id
                ) if LANGCHAIN_AVAILABLE else VetoBlockedException(
                    reason=result.reason,
                    confidence=result.confidence,
                    request_id=result.request_id
                )

                if on_veto:
                    return on_veto(exc)
                raise exc

        # Verification passed - execute
        return fn(*args, **kwargs)

    except (VetoBlockedException, VetoBlockedToolException):
        raise
    except IntentNotSetError:
        raise
    except CircuitOpenError:
        if config.fail_open:
            logger.warning(f"Circuit open for {tool_name}, allowing (fail_open)")
            return fn(*args, **kwargs)
        raise VetoBlockedToolException(
            reason="VetoNet unavailable (circuit open)"
        ) if LANGCHAIN_AVAILABLE else VetoBlockedException(
            reason="VetoNet unavailable (circuit open)"
        )
    except VetoNetError as e:
        if config.fail_open:
            logger.warning(f"VetoNet error for {tool_name}: {e}, allowing (fail_open)")
            return fn(*args, **kwargs)
        raise


# Alias for simpler import
protect = protected_tool


__all__ = [
    "protected_tool",
    "protect",
]
