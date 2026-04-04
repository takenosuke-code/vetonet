"""
VetoNet LangChain Integration

Protect your LangChain agents from prompt injection attacks.

Quick Start:
    from vetonet.langchain import protected_tool, init

    # Initialize once
    init(api_key="veto_sk_live_xxx")  # Or set VETONET_API_KEY env var

    # Protect any tool
    @protected_tool
    def buy_item(item: str, price: float, vendor: str) -> str:
        '''Buy an item.'''
        return execute_purchase(item, price, vendor)

    # Use with LangChain agent
    from langchain.agents import create_tool_calling_agent

    agent = create_tool_calling_agent(llm, [buy_item], prompt)

With Custom Mapping:
    @protected_tool(
        field_map={"cost": "unit_price", "seller": "vendor"},
        defaults={"item_category": "gift_card"}
    )
    def buy_gift_card(cost: float, seller: str, recipient: str) -> str:
        ...

With Intent Capture:
    from vetonet.langchain import VetoNetGuard

    guard = VetoNetGuard()
    handler = guard.get_callback_handler()

    agent = create_tool_calling_agent(llm, tools, prompt, callbacks=[handler])
"""

# Core functionality
from .guard import (
    VetoNetGuard,
    init,
    get_default_guard,
    set_default_guard,
)

from .decorator import (
    protected_tool,
    protect,
)

from .callback import (
    VetoNetCallbackHandler,
    AsyncVetoNetCallbackHandler,
)

from .intent import (
    IntentStore,
    get_intent_store,
    get_current_intent,
    set_intent,
    clear_intent,
    capture_message,
)

from .registry import (
    ToolSignatureConfig,
    ToolRegistry,
    get_registry,
)

# Types
from .types import (
    VetoResponse,
    VetoStatus,
    IntentContext,
    ToolSignature,
    VetoNetGuardConfig,
)

# Exceptions
from .exceptions import (
    VetoNetError,
    VetoNetConfigError,
    VetoBlockedException,
    VetoBlockedToolException,
    VetoNetAuthError,
    VetoNetRateLimitError,
    VetoNetTimeoutError,
    VetoNetNetworkError,
    CircuitOpenError,
    IntentNotSetError,
    SignatureError,
    MappingError,
    LANGCHAIN_AVAILABLE,
)

# Low-level components (for advanced users)
from .client import APIClient
from .circuit import CircuitBreaker
from .async_utils import is_async_callable, is_async_context

__version__ = "1.0.0"

__all__ = [
    # Version
    "__version__",

    # Main API
    "init",
    "protected_tool",
    "protect",
    "VetoNetGuard",

    # Callback handlers
    "VetoNetCallbackHandler",
    "AsyncVetoNetCallbackHandler",

    # Intent management
    "IntentStore",
    "get_intent_store",
    "get_current_intent",
    "set_intent",
    "clear_intent",
    "capture_message",

    # Registry
    "ToolSignatureConfig",
    "ToolRegistry",
    "get_registry",

    # Types
    "VetoResponse",
    "VetoStatus",
    "IntentContext",
    "ToolSignature",
    "VetoNetGuardConfig",

    # Exceptions
    "VetoNetError",
    "VetoNetConfigError",
    "VetoBlockedException",
    "VetoBlockedToolException",
    "VetoNetAuthError",
    "VetoNetRateLimitError",
    "VetoNetTimeoutError",
    "VetoNetNetworkError",
    "CircuitOpenError",
    "IntentNotSetError",
    "SignatureError",
    "MappingError",

    # Low-level
    "APIClient",
    "CircuitBreaker",
    "is_async_callable",
    "is_async_context",

    # Constants
    "LANGCHAIN_AVAILABLE",

    # Guard management
    "get_default_guard",
    "set_default_guard",
]
