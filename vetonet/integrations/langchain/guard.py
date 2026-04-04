"""
VetoNet LangChain Integration - VetoNetGuard Orchestrator

Central class that wires all components together:
- APIClient for verification
- IntentStore for conversation tracking
- ToolRegistry for signature mapping
- CircuitBreaker for resilience
"""

import logging
import os
from typing import Any, Dict, List, Optional

from .types import VetoResponse, VetoNetGuardConfig, CircuitBreakerConfig, VetoNetClientConfig
from .exceptions import VetoNetConfigError
from .client import APIClient
from .circuit import CircuitBreaker
from .intent import IntentStore, get_intent_store
from .registry import ToolRegistry, get_registry
from .callback import VetoNetCallbackHandler, AsyncVetoNetCallbackHandler

logger = logging.getLogger("vetonet.langchain")


class VetoNetGuard:
    """Central orchestrator for VetoNet LangChain integration.

    Wires together all components:
    - APIClient for verification calls
    - IntentStore for conversation tracking
    - ToolRegistry for signature mapping
    - CircuitBreaker for resilience
    - Callback handlers for LangChain

    Usage:
        # Simple - uses env vars
        guard = VetoNetGuard()

        # With explicit config
        guard = VetoNetGuard(api_key="veto_sk_live_xxx")

        # Get callback handler
        handler = guard.get_callback_handler()
        agent = create_agent(llm, tools, callbacks=[handler])

        # Verify manually
        result = await guard.verify_async(intent, payload)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[VetoNetGuardConfig] = None,
        intent_store: Optional[IntentStore] = None,
        registry: Optional[ToolRegistry] = None,
    ):
        """Initialize VetoNetGuard.

        Args:
            api_key: VetoNet API key. Falls back to VETONET_API_KEY env var.
            config: Full configuration. Overrides api_key if both provided.
            intent_store: IntentStore instance. Uses default if not provided.
            registry: ToolRegistry instance. Uses default if not provided.

        Raises:
            VetoNetConfigError: If no API key provided and not in env
        """
        # Build config
        if config is not None:
            self._config = config
        else:
            key = api_key or os.environ.get("VETONET_API_KEY")
            if not key:
                raise VetoNetConfigError(
                    "API key required. Set VETONET_API_KEY env var or pass api_key.",
                    config_key="api_key"
                )
            self._config = VetoNetGuardConfig(api_key=key)

        # Initialize components
        self._circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=self._config.circuit_breaker_threshold,
                recovery_timeout=self._config.circuit_breaker_timeout,
            )
        )

        # Build client config with all settings from guard config
        client_config = VetoNetClientConfig(
            api_key=self._config.api_key,
            base_url=self._config.api_base,
            timeout=self._config.timeout,
        )
        self._client = APIClient(
            config=client_config,
            circuit_breaker=self._circuit_breaker
        )

        self._intent_store = intent_store or get_intent_store(
            max_history=self._config.max_history_turns
        )

        self._registry = registry or get_registry()

        # Callback handlers (created lazily)
        self._callback_handler: Optional[VetoNetCallbackHandler] = None
        self._async_callback_handler: Optional[AsyncVetoNetCallbackHandler] = None

    @property
    def config(self) -> VetoNetGuardConfig:
        """Get configuration."""
        return self._config

    @property
    def client(self) -> APIClient:
        """Get API client."""
        return self._client

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Get circuit breaker."""
        return self._circuit_breaker

    @property
    def intent_store(self) -> IntentStore:
        """Get intent store."""
        return self._intent_store

    @property
    def registry(self) -> ToolRegistry:
        """Get tool registry."""
        return self._registry

    def get_callback_handler(self) -> VetoNetCallbackHandler:
        """Get sync callback handler for LangChain.

        Returns the same instance on repeated calls.

        Usage:
            handler = guard.get_callback_handler()
            agent = create_agent(llm, tools, callbacks=[handler])
        """
        if self._callback_handler is None:
            self._callback_handler = VetoNetCallbackHandler(store=self._intent_store)
        return self._callback_handler

    def get_async_callback_handler(self) -> AsyncVetoNetCallbackHandler:
        """Get async callback handler for LangChain.

        Returns the same instance on repeated calls.
        """
        if self._async_callback_handler is None:
            self._async_callback_handler = AsyncVetoNetCallbackHandler(
                store=self._intent_store
            )
        return self._async_callback_handler

    async def verify_async(
        self,
        intent: str,
        payload: Dict[str, Any]
    ) -> VetoResponse:
        """Verify a transaction asynchronously.

        Args:
            intent: User's intent (natural language)
            payload: Agent's proposed action (AgentPayload dict)

        Returns:
            VetoResponse with verdict
        """
        return await self._client.check(intent, payload)

    def verify_sync(
        self,
        intent: str,
        payload: Dict[str, Any]
    ) -> VetoResponse:
        """Verify a transaction synchronously.

        Args:
            intent: User's intent (natural language)
            payload: Agent's proposed action (AgentPayload dict)

        Returns:
            VetoResponse with verdict
        """
        return self._client.check_sync(intent, payload)

    async def close(self) -> None:
        """Close all resources."""
        await self._client.close()

    def close_sync(self) -> None:
        """Close sync resources."""
        self._client.close_sync()

    async def __aenter__(self) -> "VetoNetGuard":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    def __enter__(self) -> "VetoNetGuard":
        """Sync context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Sync context manager exit."""
        self.close_sync()


# =============================================================================
# Default Guard Management
# =============================================================================

_default_guard: Optional[VetoNetGuard] = None


def get_default_guard() -> VetoNetGuard:
    """Get or create the default VetoNetGuard instance.

    Raises:
        VetoNetConfigError: If no API key in env
    """
    global _default_guard
    if _default_guard is None:
        _default_guard = VetoNetGuard()
    return _default_guard


def set_default_guard(guard: VetoNetGuard) -> None:
    """Set the default VetoNetGuard instance."""
    global _default_guard
    _default_guard = guard


def init(
    api_key: Optional[str] = None,
    **kwargs
) -> VetoNetGuard:
    """Initialize VetoNet with configuration.

    Convenience function that creates and sets the default guard.

    Args:
        api_key: VetoNet API key
        **kwargs: Additional VetoNetGuardConfig options

    Returns:
        The created VetoNetGuard instance

    Example:
        from vetonet.langchain import init

        init(api_key="veto_sk_live_xxx")
        # Now all @protected_tool decorators will use this config
    """
    # Build config if api_key provided OR if kwargs provided (e.g., api_base)
    config = None
    if api_key or kwargs:
        config = VetoNetGuardConfig(api_key=api_key, **kwargs)
    guard = VetoNetGuard(api_key=api_key, config=config)
    set_default_guard(guard)
    return guard


__all__ = [
    "VetoNetGuard",
    "get_default_guard",
    "set_default_guard",
    "init",
]
