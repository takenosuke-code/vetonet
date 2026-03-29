"""
MCP (Model Context Protocol) integration for VetoNet.

Exposes VetoNet as MCP tools for use with Claude, GPT, and other MCP-compatible agents.
"""

from vetonet.integrations.mcp.server import mcp, lock_intent, verify_transaction, check_transaction, clear_intent

__all__ = ["mcp", "lock_intent", "verify_transaction", "check_transaction", "clear_intent"]
