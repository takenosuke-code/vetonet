"""VetoNet integrations with external platforms."""
from .agentkit import VetoNetPolicyProvider
from .session import SessionStore, SessionData, validate_intent, get_session_store

__all__ = [
    # Original AgentKit
    "VetoNetPolicyProvider",
    # Session management
    "SessionStore",
    "SessionData",
    "validate_intent",
    "get_session_store",
]

# Lazy imports for optional integrations
def __getattr__(name):
    if name == "mcp":
        from vetonet.integrations import mcp
        return mcp
    if name == "x402":
        from vetonet.integrations import x402
        return x402
    if name == "world":
        from vetonet.integrations import world
        return world
    if name == "langchain":
        from vetonet.integrations import langchain
        return langchain
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
