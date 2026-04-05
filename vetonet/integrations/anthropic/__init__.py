"""
VetoNet Anthropic SDK Integration - Framework-Level Tool Call Interception

Intercepts Claude's tool_use blocks BEFORE execution, verifying real
parameters against the user's locked intent. The agent cannot lie about
what it's doing because VetoNet sees the actual tool call parameters.

Usage:
    from vetonet.integrations.anthropic import VetoNetAnthropic

    veto = VetoNetAnthropic(api_key="veto_sk_live_xxx")
    veto.lock_intent("Buy a $50 Amazon gift card")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        tools=[...],
        messages=[...]
    )

    # Verify and execute tool calls - blocks malicious ones
    results = veto.process_tool_calls(response, executors={
        "buy_item": buy_item_function,
    })

    # Get Anthropic-formatted tool results for next turn
    tool_results = [r.to_anthropic_result() for r in results]
"""

from .guard import VetoNetAnthropic
from .processor import ToolCallProcessor, ToolCallResult

__all__ = [
    "VetoNetAnthropic",
    "ToolCallProcessor",
    "ToolCallResult",
]
