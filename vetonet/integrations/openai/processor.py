"""
VetoNet OpenAI SDK Integration - Tool Call Processor

Extracts function call tool_calls from OpenAI responses, verifies each
against the locked intent via VetoNet, and executes approved tools.

Key difference from Anthropic: OpenAI's tool_call.function.arguments is a
JSON string, not a dict. Must parse with json.loads() and handle JSONDecodeError
(fail-closed).
"""

import inspect
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("vetonet.openai")


@dataclass
class ToolCallResult:
    """Result of processing a single OpenAI tool call."""

    tool_call_id: str
    tool_name: str
    approved: bool
    result: Optional[Any] = None
    blocked_reason: Optional[str] = None
    error: Optional[str] = None
    request_id: Optional[str] = None

    def to_tool_message(self) -> dict:
        """Convert to OpenAI tool message format.

        Returns:
            {"role": "tool", "tool_call_id": "...", "content": "..."}
        """
        if self.approved and self.error is None:
            content = str(self.result) if self.result is not None else ""
        elif not self.approved:
            content = f"[BLOCKED by VetoNet] {self.blocked_reason}"
        else:
            content = f"[ERROR] {self.error}"

        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "content": content,
        }


def extract_tool_calls(response) -> List[dict]:
    """Extract tool calls from an OpenAI ChatCompletion response.

    Handles both SDK objects (response.choices[0].message.tool_calls)
    and raw dicts.

    Returns:
        List of {"id": str, "name": str, "arguments": dict}
    """
    calls = []

    # Get message from response object or dict
    message = None

    # SDK object: response.choices[0].message
    choices = getattr(response, "choices", None)
    if choices is not None and len(choices) > 0:
        choice = choices[0]
        message = getattr(choice, "message", None)
        if message is None and isinstance(choice, dict):
            message = choice.get("message")
    elif isinstance(response, dict):
        choices_list = response.get("choices", [])
        if choices_list:
            message = choices_list[0].get("message")

    if message is None:
        return calls

    # Get tool_calls from message
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls is None and isinstance(message, dict):
        tool_calls = message.get("tool_calls")
    if not tool_calls:
        return calls

    for tc in tool_calls:
        # SDK object
        if hasattr(tc, "id"):
            call_id = tc.id
            func = getattr(tc, "function", None)
            if func is None:
                continue
            name = getattr(func, "name", "")
            args_str = getattr(func, "arguments", "{}")
        # Raw dict
        elif isinstance(tc, dict):
            call_id = tc.get("id", "")
            func = tc.get("function", {})
            name = func.get("name", "")
            args_str = func.get("arguments", "{}")
        else:
            continue

        # Parse arguments JSON string (fail-closed on parse error)
        if isinstance(args_str, dict):
            arguments = args_str
        elif isinstance(args_str, str):
            try:
                arguments = json.loads(args_str)
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to parse arguments for tool call {call_id} ({name}): {e}"
                )
                # Fail-closed: include with empty args so it gets blocked
                calls.append({
                    "id": call_id,
                    "name": name,
                    "arguments": None,
                    "parse_error": str(e),
                })
                continue
        else:
            arguments = {}

        calls.append({
            "id": call_id,
            "name": name,
            "arguments": arguments,
        })

    return calls


class ToolCallProcessor:
    """Processes OpenAI tool calls with VetoNet verification.

    For each tool call:
    1. Parses JSON arguments string
    2. Maps raw parameters to AgentPayload via ToolRegistry
    3. Verifies against locked intent via APIClient
    4. Executes approved tools, blocks rejected ones
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
        """Process tool calls synchronously.

        Args:
            response: OpenAI ChatCompletion response
            executors: Map of tool_name -> callable

        Returns:
            List of ToolCallResult for each tool call
        """
        calls = extract_tool_calls(response)
        results = []

        for call in calls:
            result = self._process_single(call, executors)
            results.append(result)

        return results

    async def process_async(
        self,
        response,
        executors: Dict[str, Callable],
    ) -> List[ToolCallResult]:
        """Process tool calls asynchronously."""
        calls = extract_tool_calls(response)
        results = []

        for call in calls:
            result = await self._process_single_async(call, executors)
            results.append(result)

        return results

    def _process_single(
        self,
        call: dict,
        executors: Dict[str, Callable],
    ) -> ToolCallResult:
        """Process a single tool call synchronously."""
        call_id = call["id"]
        tool_name = call["name"]
        arguments = call.get("arguments")

        # Fail-closed on JSON parse error
        if arguments is None:
            parse_error = call.get("parse_error", "unknown parse error")
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"Failed to parse tool arguments: {parse_error}",
            )

        # Check intent
        if not self._locked_intent:
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason="No intent set. Call lock_intent() before processing tool calls.",
            )

        # Check executor exists
        executor = executors.get(tool_name)
        if executor is None:
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"No executor registered for tool '{tool_name}'",
            )

        # Map parameters to AgentPayload
        try:
            payload = self._registry.map_to_payload(tool_name, arguments)
        except Exception as e:
            logger.warning(f"Parameter mapping failed for {tool_name}: {e}")
            return ToolCallResult(
                tool_call_id=call_id,
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
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"Verification unavailable: {e}",
            )

        if veto_response.blocked:
            logger.info(f"Tool {tool_name} blocked: {veto_response.reason}")
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=veto_response.reason,
                request_id=veto_response.request_id,
            )

        # Execute the tool
        try:
            result = executor(**arguments)
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=True,
                result=result,
                request_id=veto_response.request_id,
            )
        except Exception as e:
            logger.error(f"Tool {tool_name} execution error: {e}")
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=True,
                error=str(e),
                request_id=veto_response.request_id,
            )

    async def _process_single_async(
        self,
        call: dict,
        executors: Dict[str, Callable],
    ) -> ToolCallResult:
        """Process a single tool call asynchronously."""
        call_id = call["id"]
        tool_name = call["name"]
        arguments = call.get("arguments")

        # Fail-closed on JSON parse error
        if arguments is None:
            parse_error = call.get("parse_error", "unknown parse error")
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"Failed to parse tool arguments: {parse_error}",
            )

        if not self._locked_intent:
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason="No intent set. Call lock_intent() before processing tool calls.",
            )

        executor = executors.get(tool_name)
        if executor is None:
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"No executor registered for tool '{tool_name}'",
            )

        try:
            payload = self._registry.map_to_payload(tool_name, arguments)
        except Exception as e:
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"Parameter mapping failed: {e}",
            )

        try:
            veto_response = await self._client.check(self._locked_intent, payload)
        except Exception as e:
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=f"Verification unavailable: {e}",
            )

        if veto_response.blocked:
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=False,
                blocked_reason=veto_response.reason,
                request_id=veto_response.request_id,
            )

        try:
            if inspect.iscoroutinefunction(executor):
                result = await executor(**arguments)
            else:
                result = executor(**arguments)
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=True,
                result=result,
                request_id=veto_response.request_id,
            )
        except Exception as e:
            return ToolCallResult(
                tool_call_id=call_id,
                tool_name=tool_name,
                approved=True,
                error=str(e),
                request_id=veto_response.request_id,
            )
