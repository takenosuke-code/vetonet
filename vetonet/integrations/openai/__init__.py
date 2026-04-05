"""
VetoNet OpenAI SDK Integration - Framework-Level Tool Call Interception

Intercepts OpenAI function calls BEFORE execution, verifying real
parameters against the user's locked intent. Supports both standard
function calling and the OpenAI Agents SDK.

Usage:
    from vetonet.integrations.openai import VetoNetOpenAI

    veto = VetoNetOpenAI(api_key="veto_sk_live_xxx")
    veto.lock_intent("Buy a $50 Amazon gift card")

    response = client.chat.completions.create(
        model="gpt-4o",
        tools=[...],
        messages=[...]
    )

    # Verify and execute tool calls - blocks malicious ones
    results = veto.process_tool_calls(response, executors={
        "buy_item": buy_item_function,
    })

    # Get OpenAI-formatted tool messages for next turn
    tool_messages = [r.to_tool_message() for r in results]
"""

from .guard import VetoNetOpenAI
from .processor import ToolCallResult
from .decorator import vetonet_function_tool

__all__ = [
    "VetoNetOpenAI",
    "ToolCallResult",
    "vetonet_function_tool",
]
