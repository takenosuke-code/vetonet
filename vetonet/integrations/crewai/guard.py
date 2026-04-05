"""
VetoNet CrewAI Integration - Guard Orchestrator

Central class that wires all components for CrewAI's tool calling pattern.
Intercepts tool calls, verifies real parameters, executes or blocks.
"""

import logging
import os
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from vetonet.integrations.langchain.types import (
    VetoResponse,
    VetoNetGuardConfig,
    VetoNetClientConfig,
    CircuitBreakerConfig,
)
from vetonet.integrations.langchain.exceptions import (
    VetoNetConfigError,
    VetoBlockedException,
    IntentNotSetError,
)
from vetonet.integrations.langchain.client import APIClient
from vetonet.integrations.langchain.circuit import CircuitBreaker
from vetonet.integrations.langchain.registry import (
    ToolRegistry,
    ToolSignatureConfig,
)

logger = logging.getLogger("vetonet.crewai")

# Module-level context var so the decorator can find the active guard
_active_guard: ContextVar[Optional["VetoNetCrewAI"]] = ContextVar(
    "vetonet_crewai_guard", default=None
)


def get_active_guard() -> Optional["VetoNetCrewAI"]:
    """Get the currently active VetoNetCrewAI guard."""
    return _active_guard.get()


@dataclass
class ToolCallResult:
    """Result of a VetoNet-verified tool call."""

    tool_name: str
    approved: bool
    result: Optional[Any] = None
    blocked_reason: Optional[str] = None
    error: Optional[str] = None
    request_id: Optional[str] = None


class VetoNetCrewAI:
    """Framework-level interception for CrewAI tool calls.

    Intercepts tool calls BEFORE execution, verifying the real parameters
    against the user's locked intent.

    Usage:
        with VetoNetCrewAI(api_key="veto_sk_live_xxx") as veto:
            veto.lock_intent("Buy a $50 Amazon gift card")
            veto.register_tool("buy_item", buy_item_fn, field_map={"cost": "unit_price"})
            result = veto.verify_and_execute("buy_item", {"cost": 50, "item": "gift card"})
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[VetoNetGuardConfig] = None,
        registry: Optional[ToolRegistry] = None,
    ):
        """Initialize VetoNetCrewAI.

        Args:
            api_key: VetoNet API key. Falls back to VETONET_API_KEY env var.
            config: Full configuration override.
            registry: ToolRegistry instance. Creates new one if not provided.
        """
        if config is not None:
            self._config = config
        else:
            key = api_key or os.environ.get("VETONET_API_KEY")
            if not key:
                raise VetoNetConfigError(
                    "API key required. Set VETONET_API_KEY env var or pass api_key.",
                    config_key="api_key",
                )
            self._config = VetoNetGuardConfig(api_key=key)

        self._circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=self._config.circuit_breaker_threshold,
                recovery_timeout=self._config.circuit_breaker_timeout,
            )
        )

        resolved_key = self._config.api_key or os.environ.get("VETONET_API_KEY")
        if not resolved_key:
            raise VetoNetConfigError(
                "API key required. Set VETONET_API_KEY env var or pass api_key.",
                config_key="api_key",
            )

        client_config = VetoNetClientConfig(
            api_key=resolved_key,
            base_url=self._config.api_base,
            timeout=self._config.timeout,
        )
        self._client = APIClient(
            config=client_config,
            circuit_breaker=self._circuit_breaker,
        )

        self._registry = registry or ToolRegistry()
        self._locked_intent: Optional[str] = None
        self._executors: Dict[str, Callable] = {}
        self._token: Optional[object] = None

    def lock_intent(self, intent: str) -> None:
        """Lock the user's purchase intent.

        Must be called before verify_and_execute(). This is the intent
        that all tool calls will be verified against.

        Args:
            intent: Natural language intent (e.g., "Buy a $50 Amazon gift card")
        """
        if not isinstance(intent, str) or not intent.strip():
            raise ValueError("Intent must be a non-empty string")
        self._locked_intent = intent.strip()
        logger.info(f"Intent locked: {self._locked_intent[:100]}...")

    def lock_intent_from_task(self, task) -> Optional[str]:
        """Extract and lock intent from a CrewAI Task object.

        Uses the task's description as the intent source.

        Args:
            task: CrewAI Task object (must have .description attribute)

        Returns:
            The detected intent string, or None if not found
        """
        description = getattr(task, "description", None)
        if description and isinstance(description, str) and description.strip():
            self.lock_intent(description)
            return description
        return None

    def register_tool(
        self,
        name: str,
        executor: Optional[Callable] = None,
        field_map: Optional[Dict[str, str]] = None,
        defaults: Optional[Dict[str, Any]] = None,
        auto_infer: bool = True,
    ) -> None:
        """Register a tool with its executor and field mapping.

        Args:
            name: Tool name (must match the name used in CrewAI)
            executor: Function to call when the tool is approved
            field_map: Map tool param names to AgentPayload fields
            defaults: Default values for unmapped fields
            auto_infer: Auto-map common param names (price -> unit_price, etc.)
        """
        config = ToolSignatureConfig(
            field_map=field_map or {},
            defaults=defaults or {},
            auto_infer=auto_infer,
        )
        self._registry.register(name, config)
        if executor is not None:
            self._executors[name] = executor

    def verify_and_execute(
        self,
        tool_name: str,
        kwargs: Dict[str, Any],
        executor: Optional[Callable] = None,
    ) -> ToolCallResult:
        """Verify a tool call against the locked intent and execute if approved.

        Args:
            tool_name: Name of the tool being called
            kwargs: Arguments passed to the tool
            executor: Executor override. Falls back to registered executor.

        Returns:
            ToolCallResult with the outcome

        Raises:
            VetoBlockedException: If the tool call is blocked
            IntentNotSetError: If no intent is locked
        """
        # Fail closed: no intent = block
        if not self._locked_intent:
            raise IntentNotSetError(
                message="No intent locked. Call lock_intent() before verify_and_execute().",
                tool_name=tool_name,
            )

        # Resolve executor
        fn = executor or self._executors.get(tool_name)
        if fn is None:
            return ToolCallResult(
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"No executor registered for tool '{tool_name}'",
            )

        # Map parameters to AgentPayload
        try:
            payload = self._registry.map_to_payload(tool_name, kwargs)
        except Exception as e:
            logger.warning(f"Parameter mapping failed for {tool_name}: {e}")
            return ToolCallResult(
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"Parameter mapping failed: {e}",
            )

        # Verify with VetoNet API
        try:
            veto_response = self._client.check_sync(self._locked_intent, payload)
        except Exception as e:
            logger.error(f"VetoNet verification failed for {tool_name}: {e}")
            return ToolCallResult(
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"Verification unavailable: {e}",
            )

        if veto_response.blocked:
            logger.info(f"Tool {tool_name} blocked: {veto_response.reason}")
            raise VetoBlockedException(
                reason=veto_response.reason,
                confidence=veto_response.confidence,
                request_id=veto_response.request_id,
            )

        # Approved - execute the tool
        try:
            result = fn(**kwargs)
            return ToolCallResult(
                tool_name=tool_name,
                approved=True,
                result=result,
                request_id=veto_response.request_id,
            )
        except Exception as e:
            logger.error(f"Tool {tool_name} execution error: {e}")
            return ToolCallResult(
                tool_name=tool_name,
                approved=True,
                error=str(e),
                request_id=veto_response.request_id,
            )

    @property
    def intent(self) -> Optional[str]:
        """Get the currently locked intent."""
        return self._locked_intent

    @property
    def registry(self) -> ToolRegistry:
        """Get the tool registry."""
        return self._registry

    async def close(self) -> None:
        """Close all resources."""
        if self._token is not None:
            _active_guard.reset(self._token)
            self._token = None
        await self._client.close()

    def close_sync(self) -> None:
        """Close sync resources."""
        if self._token is not None:
            _active_guard.reset(self._token)
            self._token = None
        self._client.close_sync()

    def __enter__(self) -> "VetoNetCrewAI":
        self._token = _active_guard.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close_sync()

    async def __aenter__(self) -> "VetoNetCrewAI":
        self._token = _active_guard.set(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
