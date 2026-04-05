"""
VetoNet CrewAI Integration - VetoNetCrew Wrapper

Wraps an entire CrewAI Crew with VetoNet protection. Automatically
intercepts all agent tool calls and verifies against task intent.
"""

import functools
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional

from vetonet.integrations.langchain.exceptions import (
    VetoBlockedException,
    IntentNotSetError,
)
from vetonet.integrations.langchain.registry import ToolSignatureConfig
from .guard import VetoNetCrewAI, _active_guard

logger = logging.getLogger("vetonet.crewai")

# Try to import CrewAI
try:
    from crewai import Crew, Agent, Task

    _HAS_CREWAI = True
except ImportError:
    _HAS_CREWAI = False
    Crew = None
    Agent = None
    Task = None


class VetoNetCrew:
    """Wraps an entire CrewAI Crew with VetoNet protection.

    Automatically extracts intent from tasks, wraps all agent tools
    with VetoNet verification, and cleans up after execution.

    Usage:
        crew = VetoNetCrew(
            agents=[researcher, buyer],
            tasks=[research_task, buy_task],
            vetonet_api_key="veto_sk_live_xxx",
            field_maps={"buy_item": {"cost": "unit_price"}},
        )
        result = crew.kickoff()
    """

    def __init__(
        self,
        agents: List[Any],
        tasks: List[Any],
        vetonet_api_key: Optional[str] = None,
        field_maps: Optional[Dict[str, Dict[str, str]]] = None,
        **crew_kwargs: Any,
    ):
        """Initialize VetoNetCrew.

        Args:
            agents: List of CrewAI Agent objects
            tasks: List of CrewAI Task objects
            vetonet_api_key: VetoNet API key. Falls back to VETONET_API_KEY env var.
            field_maps: Map of tool_name -> field_map for parameter mapping
            **crew_kwargs: Additional kwargs passed to CrewAI Crew constructor
        """
        if not _HAS_CREWAI:
            raise ImportError(
                "crewai is required for VetoNetCrew. Install with: pip install crewai"
            )

        self._agents = agents
        self._tasks = tasks
        self._field_maps = field_maps or {}
        self._crew_kwargs = crew_kwargs
        self._guard = VetoNetCrewAI(api_key=vetonet_api_key)
        self._original_tools: Dict[int, List[Any]] = {}

    def _extract_intent(self) -> str:
        """Extract intent from task descriptions.

        Combines all task descriptions into a single intent string.
        Uses the first task description if only one task exists.

        Returns:
            Combined intent string

        Raises:
            IntentNotSetError: If no task descriptions found
        """
        descriptions = []
        for task in self._tasks:
            desc = getattr(task, "description", None)
            if desc and isinstance(desc, str) and desc.strip():
                descriptions.append(desc.strip())

        if not descriptions:
            raise IntentNotSetError(
                message="No task descriptions found to extract intent from.",
            )

        if len(descriptions) == 1:
            return descriptions[0]

        return " | ".join(descriptions)

    def _wrap_tool(self, tool: Any, tool_name: str) -> Any:
        """Wrap a single CrewAI tool with VetoNet verification.

        Handles tools that are objects with a .func attribute or callable directly.

        Args:
            tool: CrewAI tool object or callable
            tool_name: Name to use for registry lookup

        Returns:
            Wrapped tool with VetoNet verification
        """
        # Register field mapping if provided
        field_map = self._field_maps.get(tool_name, {})
        config = ToolSignatureConfig(
            field_map=field_map,
            defaults={},
            auto_infer=True,
        )
        self._guard.registry.register(tool_name, config)

        # Get the underlying callable
        original_func = getattr(tool, "func", None)
        if original_func is None and callable(tool):
            original_func = tool

        if original_func is None:
            logger.warning(f"Cannot wrap tool '{tool_name}': no callable found")
            return tool

        guard = self._guard

        @functools.wraps(original_func)
        def protected_func(*args, **kwargs):
            if guard.intent is None:
                raise IntentNotSetError(
                    message="No intent locked for VetoNetCrew.",
                    tool_name=tool_name,
                )

            try:
                payload = guard.registry.map_to_payload(tool_name, kwargs)
                result = guard._client.check_sync(guard.intent, payload)

                if result.blocked:
                    raise VetoBlockedException(
                        reason=result.reason,
                        confidence=result.confidence,
                        request_id=result.request_id,
                    )

                return original_func(*args, **kwargs)

            except (VetoBlockedException, IntentNotSetError):
                raise
            except Exception as e:
                logger.error(f"VetoNet verification error for {tool_name}: {e}")
                raise VetoBlockedException(
                    reason=f"Verification unavailable: {e}",
                )

        # Preserve signature for CrewAI
        protected_func.__signature__ = inspect.signature(original_func)

        # Replace func on tool object if it has one
        if hasattr(tool, "func"):
            tool.func = protected_func
            return tool

        return protected_func

    def _wrap_all_tools(self) -> None:
        """Wrap all agent tools with VetoNet verification.

        Stores originals for cleanup.
        """
        for agent in self._agents:
            tools = getattr(agent, "tools", None)
            if tools is None:
                continue

            agent_id = id(agent)
            self._original_tools[agent_id] = list(tools)

            wrapped = []
            for tool in tools:
                # Get tool name
                tool_name = getattr(tool, "name", None)
                if tool_name is None:
                    tool_name = getattr(tool, "__name__", None)
                if tool_name is None:
                    tool_name = type(tool).__name__

                # Skip if already a vetonet-protected tool (check for marker)
                if getattr(tool, "_vetonet_protected", False):
                    wrapped.append(tool)
                    continue

                wrapped_tool = self._wrap_tool(tool, tool_name)
                if hasattr(wrapped_tool, "_vetonet_protected"):
                    wrapped_tool._vetonet_protected = True
                elif hasattr(wrapped_tool, "func"):
                    wrapped_tool._vetonet_protected = True

                wrapped.append(wrapped_tool)

            agent.tools = wrapped

    def _restore_tools(self) -> None:
        """Restore original tools after execution."""
        for agent in self._agents:
            agent_id = id(agent)
            original = self._original_tools.get(agent_id)
            if original is not None:
                agent.tools = original
        self._original_tools.clear()

    def kickoff(self) -> Any:
        """Run the crew with VetoNet protection.

        1. Extracts intent from task descriptions
        2. Wraps all agent tools with VetoNet verification
        3. Runs the CrewAI Crew
        4. Restores original tools

        Returns:
            CrewAI Crew output
        """
        # Extract and lock intent
        intent = self._extract_intent()
        self._guard.lock_intent(intent)
        logger.info(f"VetoNetCrew intent: {intent[:100]}...")

        # Wrap tools
        self._wrap_all_tools()

        # Set the active guard so @vetonet_tool decorator can find it
        token = _active_guard.set(self._guard)

        try:
            # Create and run the crew
            crew = Crew(
                agents=self._agents,
                tasks=self._tasks,
                **self._crew_kwargs,
            )
            return crew.kickoff()
        finally:
            # Always restore original tools and clean up
            _active_guard.reset(token)
            self._restore_tools()
            self._guard.close_sync()


__all__ = [
    "VetoNetCrew",
]
