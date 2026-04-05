"""
VetoNet Anthropic SDK Integration - Tool Call Processor

Extracts tool_use blocks from Anthropic responses, verifies each against
the locked intent via VetoNet, and executes approved tools.
"""

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("vetonet.anthropic")


@dataclass
class ToolCallResult:
    """Result of processing a single tool_use block."""

    tool_use_id: str
    tool_name: str
    approved: bool
    result: Optional[Any] = None
    blocked_reason: Optional[str] = None
    error: Optional[str] = None
    request_id: Optional[str] = None

    def to_anthropic_result(self) -> dict:
        """Convert to Anthropic tool_result message format."""
        if self.approved and self.error is None:
            content = str(self.result) if self.result is not None else ""
        elif not self.approved:
            content = f"[BLOCKED by VetoNet] {self.blocked_reason}"
        else:
            content = f"[ERROR] {self.error}"

        result = {
            "type": "tool_result",
            "tool_use_id": self.tool_use_id,
            "content": content,
        }
        # Only mark actual execution errors as is_error (not security blocks).
        # Security blocks should NOT be is_error because Claude may retry,
        # allowing an adversarial agent to probe for passing parameters.
        if self.error:
            result["is_error"] = True
        return result


def extract_tool_use_blocks(response) -> List[dict]:
    """Extract tool_use blocks from an Anthropic response.

    Handles both SDK objects (response.content) and raw dicts.

    Returns:
        List of {"id": str, "name": str, "input": dict}
    """
    blocks = []

    # Get content from response object or dict
    content = getattr(response, "content", None)
    if content is None and isinstance(response, dict):
        content = response.get("content", [])
    if content is None:
        return blocks

    for block in content:
        # SDK object (has .type attribute)
        if hasattr(block, "type"):
            if block.type == "tool_use":
                blocks.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input if isinstance(block.input, dict) else {},
                })
        # Raw dict
        elif isinstance(block, dict) and block.get("type") == "tool_use":
            blocks.append({
                "id": block.get("id", ""),
                "name": block.get("name", ""),
                "input": block.get("input", {}),
            })

    return blocks


class ToolCallProcessor:
    """Processes Anthropic tool_use blocks with VetoNet verification.

    For each tool_use block:
    1. Maps raw parameters to AgentPayload via ToolRegistry
    2. Verifies against locked intent via APIClient
    3. Executes approved tools, blocks rejected ones
    """

    def __init__(self, client, registry, locked_intent: Optional[str] = None):
        """
        Args:
            client: APIClient instance for VetoNet verification
            registry: ToolRegistry for parameter mapping
            locked_intent: The user's locked purchase intent
        """
        self._client = client
        self._registry = registry
        self._locked_intent = locked_intent

    def process(
        self,
        response,
        executors: Dict[str, Callable],
    ) -> List[ToolCallResult]:
        """Process tool_use blocks synchronously.

        Args:
            response: Anthropic Message response
            executors: Map of tool_name -> callable

        Returns:
            List of ToolCallResult for each tool_use block
        """
        blocks = extract_tool_use_blocks(response)
        results = []

        for block in blocks:
            result = self._process_single(block, executors)
            results.append(result)

        return results

    async def process_async(
        self,
        response,
        executors: Dict[str, Callable],
    ) -> List[ToolCallResult]:
        """Process tool_use blocks asynchronously."""
        blocks = extract_tool_use_blocks(response)
        results = []

        for block in blocks:
            result = await self._process_single_async(block, executors)
            results.append(result)

        return results

    def _process_single(
        self,
        block: dict,
        executors: Dict[str, Callable],
    ) -> ToolCallResult:
        """Process a single tool_use block synchronously."""
        tool_id = block["id"]
        tool_name = block["name"]
        tool_input = block["input"]

        # Check intent
        if not self._locked_intent:
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason="No intent set. Call lock_intent() before processing tool calls.",
            )

        # Check executor exists
        executor = executors.get(tool_name)
        if executor is None:
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"No executor registered for tool '{tool_name}'",
            )

        # Map parameters to AgentPayload
        try:
            payload = self._registry.map_to_payload(tool_name, tool_input)
        except Exception as e:
            logger.warning(f"Parameter mapping failed for {tool_name}: {e}")
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"Parameter mapping failed: {e}",
            )

        # Verify with VetoNet
        try:
            veto_response = self._client.check_sync(self._locked_intent, payload)
        except Exception as e:
            logger.error(f"VetoNet verification failed for {tool_name}: {e}")
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"Verification unavailable: {e}",
            )

        if veto_response.blocked:
            logger.info(f"Tool {tool_name} blocked: {veto_response.reason}")
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=veto_response.reason,
                request_id=veto_response.request_id,
            )

        # Execute the tool
        try:
            if inspect.iscoroutinefunction(executor):
                raise TypeError(
                    f"Executor '{tool_name}' is async. Use process_tool_calls_async() instead."
                )
            result = executor(**tool_input)
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                approved=True,
                result=result,
                request_id=veto_response.request_id,
            )
        except Exception as e:
            logger.error(f"Tool {tool_name} execution error: {e}")
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                approved=True,
                error=str(e),
                request_id=veto_response.request_id,
            )

    async def _process_single_async(
        self,
        block: dict,
        executors: Dict[str, Callable],
    ) -> ToolCallResult:
        """Process a single tool_use block asynchronously."""
        tool_id = block["id"]
        tool_name = block["name"]
        tool_input = block["input"]

        if not self._locked_intent:
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason="No intent set. Call lock_intent() before processing tool calls.",
            )

        executor = executors.get(tool_name)
        if executor is None:
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"No executor registered for tool '{tool_name}'",
            )

        try:
            payload = self._registry.map_to_payload(tool_name, tool_input)
        except Exception as e:
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"Parameter mapping failed: {e}",
            )

        try:
            veto_response = await self._client.check(self._locked_intent, payload)
        except Exception as e:
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"Verification unavailable: {e}",
            )

        if veto_response.blocked:
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=veto_response.reason,
                request_id=veto_response.request_id,
            )

        try:
            if inspect.iscoroutinefunction(executor):
                result = await executor(**tool_input)
            else:
                result = executor(**tool_input)
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                approved=True,
                result=result,
                request_id=veto_response.request_id,
            )
        except Exception as e:
            return ToolCallResult(
                tool_use_id=tool_id,
                tool_name=tool_name,
                approved=True,
                error=str(e),
                request_id=veto_response.request_id,
            )
