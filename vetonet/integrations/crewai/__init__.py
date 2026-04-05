"""
VetoNet CrewAI Integration - Framework-Level Tool Call Interception

Intercepts CrewAI tool calls BEFORE execution, verifying real
parameters against the user's locked intent. The agent cannot lie about
what it's doing because VetoNet sees the actual tool call parameters.

Usage:
    from vetonet.integrations.crewai import VetoNetCrewAI, vetonet_tool

    veto = VetoNetCrewAI(api_key="veto_sk_live_xxx")
    veto.lock_intent("Buy a $50 Amazon gift card")

    # Decorator approach
    @vetonet_tool(field_map={"cost": "unit_price"})
    def buy_item(item: str, cost: float, vendor: str) -> str:
        '''Buy an item from a vendor.'''
        return execute_purchase(item, cost, vendor)

    # Or wrap an entire crew
    from vetonet.integrations.crewai import VetoNetCrew
    crew = VetoNetCrew(agents=[...], tasks=[...], vetonet_api_key="veto_sk_live_xxx")
    result = crew.kickoff()
"""

from .guard import VetoNetCrewAI, ToolCallResult
from .decorator import vetonet_tool
from .crew import VetoNetCrew

__all__ = [
    "VetoNetCrewAI",
    "VetoNetCrew",
    "vetonet_tool",
    "ToolCallResult",
]
