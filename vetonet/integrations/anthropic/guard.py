"""
VetoNet Anthropic SDK Integration - Guard Orchestrator

Central class that wires all components for Anthropic's tool calling pattern.
Intercepts tool_use blocks, verifies real parameters, executes or blocks.
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional

from vetonet.integrations.langchain.types import (
    VetoResponse,
    VetoNetGuardConfig,
    VetoNetClientConfig,
    CircuitBreakerConfig,
)
from vetonet.integrations.langchain.exceptions import (
    VetoNetConfigError,
    IntentNotSetError,
)
from vetonet.integrations.langchain.client import APIClient
from vetonet.integrations.langchain.circuit import CircuitBreaker
from vetonet.integrations.langchain.registry import (
    ToolRegistry,
    ToolSignatureConfig,
)
from .processor import ToolCallProcessor, ToolCallResult

logger = logging.getLogger("vetonet.anthropic")


class VetoNetAnthropic:
    """Framework-level interception for Anthropic SDK tool calls.

    Intercepts Claude's tool_use blocks BEFORE execution, verifying
    the real parameters against the user's locked intent.

    Usage:
        veto = VetoNetAnthropic(api_key="veto_sk_live_xxx")
        veto.lock_intent("Buy a $50 Amazon gift card")

        response = client.messages.create(model="...", tools=[...], messages=[...])
        results = veto.process_tool_calls(response, executors={"buy_item": buy_item})

        # Get tool results for next turn
        tool_results = [r.to_anthropic_result() for r in results]
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[VetoNetGuardConfig] = None,
        registry: Optional[ToolRegistry] = None,
    ):
        """Initialize VetoNetAnthropic.

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

    def lock_intent(self, intent: str) -> None:
        """Lock the user's purchase intent.

        Must be called before process_tool_calls(). This is the intent
        that all tool calls will be verified against.

        Args:
            intent: Natural language intent (e.g., "Buy a $50 Amazon gift card")
        """
        if not intent or not intent.strip():
            raise ValueError("Intent cannot be empty")
        self._locked_intent = intent.strip()
        logger.info(f"Intent locked: {self._locked_intent[:100]}...")

    def lock_intent_from_messages(self, messages: List[dict]) -> Optional[str]:
        """Auto-detect and lock intent from Anthropic messages list.

        Scans messages for the first user message (typically the intent).

        Args:
            messages: Anthropic-format messages list

        Returns:
            The detected intent string, or None if not found
        """
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    self.lock_intent(content)
                    return content
                # Handle content blocks (vision, multi-part)
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = block.get("text", "").strip()
                            if text:
                                self.lock_intent(text)
                                return text
        return None

    def register_tool(
        self,
        name: str,
        executor: Callable,
        field_map: Optional[Dict[str, str]] = None,
        defaults: Optional[Dict[str, Any]] = None,
        auto_infer: bool = True,
    ) -> None:
        """Register a tool with its executor and field mapping.

        Args:
            name: Tool name (must match the name in Anthropic's tool definition)
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
        self._executors[name] = executor

    def process_tool_calls(
        self,
        response,
        executors: Optional[Dict[str, Callable]] = None,
    ) -> List[ToolCallResult]:
        """Process tool_use blocks from Claude's response.

        Verifies each tool call against the locked intent, then executes
        approved tools. Returns results for all tool calls.

        Args:
            response: Anthropic Message response object
            executors: Map of tool_name -> callable. Overrides pre-registered executors.

        Returns:
            List of ToolCallResult (one per tool_use block)
        """
        merged_executors = dict(self._executors)
        if executors:
            merged_executors.update(executors)

        processor = ToolCallProcessor(
            client=self._client,
            registry=self._registry,
            locked_intent=self._locked_intent,
        )
        return processor.process(response, merged_executors)

    async def process_tool_calls_async(
        self,
        response,
        executors: Optional[Dict[str, Callable]] = None,
    ) -> List[ToolCallResult]:
        """Process tool_use blocks asynchronously."""
        merged_executors = dict(self._executors)
        if executors:
            merged_executors.update(executors)

        processor = ToolCallProcessor(
            client=self._client,
            registry=self._registry,
            locked_intent=self._locked_intent,
        )
        return await processor.process_async(response, merged_executors)

    def get_tool_results(
        self,
        response,
        executors: Optional[Dict[str, Callable]] = None,
    ) -> List[dict]:
        """Process tool calls and return Anthropic-formatted tool results.

        Convenience method that returns dicts ready to append to messages.

        Returns:
            List of {"type": "tool_result", "tool_use_id": "...", "content": "..."}
        """
        results = self.process_tool_calls(response, executors)
        return [r.to_anthropic_result() for r in results]

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
        await self._client.close()

    def close_sync(self) -> None:
        """Close sync resources."""
        self._client.close_sync()

    async def __aenter__(self) -> "VetoNetAnthropic":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    def __enter__(self) -> "VetoNetAnthropic":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close_sync()
