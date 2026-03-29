"""
VetoNet MCP Server.

Exposes VetoNet verification as MCP tools for use with Claude Desktop,
GPT, and any MCP-compatible AI agent.

Usage:
    # Run directly
    fastmcp run vetonet/integrations/mcp/server.py

    # With SSE transport for remote access
    fastmcp run vetonet/integrations/mcp/server.py --transport sse --port 8000

    # Test with MCP Inspector
    fastmcp dev vetonet/integrations/mcp/server.py
"""

import os
import secrets
import time
import logging
from typing import Optional
from dataclasses import dataclass, field

from mcp.server.fastmcp import FastMCP

from vetonet import VetoNet
from vetonet.models import AgentPayload, IntentAnchor

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("VetoNet")

# Configuration
MAX_SESSIONS = 10_000
SESSION_TTL_SECONDS = 30 * 60  # 30 minutes
MAX_INTENT_LENGTH = 1000


@dataclass
class Session:
    """A locked intent session with TTL."""
    anchor: IntentAnchor
    created_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return time.time() - self.created_at > SESSION_TTL_SECONDS


class SessionStore:
    """Thread-safe session storage with TTL and limits."""

    def __init__(self, max_sessions: int = MAX_SESSIONS):
        self._sessions: dict[str, Session] = {}
        self._max_sessions = max_sessions

    def create(self, anchor: IntentAnchor) -> str:
        """Create a new session with cryptographically random ID."""
        self._cleanup_expired()

        if len(self._sessions) >= self._max_sessions:
            raise ValueError("Maximum sessions reached. Try again later.")

        session_id = secrets.token_urlsafe(32)
        self._sessions[session_id] = Session(anchor=anchor)
        return session_id

    def get(self, session_id: str) -> Optional[Session]:
        """Get session if it exists and is not expired."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.is_expired():
            del self._sessions[session_id]
            return None
        return session

    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def _cleanup_expired(self):
        """Remove expired sessions."""
        expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
        for sid in expired:
            del self._sessions[sid]


# Global instances
_veto: Optional[VetoNet] = None
_sessions = SessionStore()


def _get_veto() -> VetoNet:
    """Lazy-load VetoNet instance."""
    global _veto
    if _veto is None:
        _veto = VetoNet(
            provider=os.environ.get("VETONET_PROVIDER", "groq"),
            api_key=os.environ.get("VETONET_API_KEY"),
        )
    return _veto


def _validate_intent(intent: str) -> str:
    """Validate and sanitize intent string."""
    if not intent or not intent.strip():
        raise ValueError("Intent cannot be empty")
    intent = intent.strip()
    if len(intent) > MAX_INTENT_LENGTH:
        raise ValueError(f"Intent too long (max {MAX_INTENT_LENGTH} chars)")
    return intent


@mcp.tool()
def lock_intent(intent: str) -> dict:
    """
    Lock a user's purchase intent for verification.

    Call this BEFORE the agent starts shopping to establish what the user wants.
    Returns a session_id to use with verify_transaction.

    Args:
        intent: Natural language purchase intent (e.g., "$50 Amazon Gift Card")

    Returns:
        Session ID and normalized intent anchor
    """
    try:
        intent = _validate_intent(intent)
        veto = _get_veto()

        # Normalize intent to structured anchor
        anchor = veto.normalizer.normalize(intent)

        # Create session
        session_id = _sessions.create(anchor)

        return {
            "status": "locked",
            "session_id": session_id,
            "anchor": {
                "item_category": anchor.item_category,
                "max_price": anchor.max_price,
                "currency": anchor.currency,
                "core_constraints": anchor.core_constraints,
            }
        }
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"lock_intent failed: {e}")
        return {"error": "Failed to lock intent"}


@mcp.tool()
def verify_transaction(
    session_id: str,
    item_description: str,
    unit_price: float,
    vendor: str,
    quantity: int = 1,
    currency: str = "USD",
    fees: list = None
) -> dict:
    """
    Verify a transaction against the locked intent.

    Call this BEFORE executing a purchase to check if it matches user intent.

    Args:
        session_id: Session ID from lock_intent
        item_description: What the agent is purchasing
        unit_price: Price per unit
        vendor: Vendor domain (e.g., "amazon.com")
        quantity: Number of items (default: 1)
        currency: Currency code (default: "USD")
        fees: Optional list of fees [{"name": "...", "amount": ...}]

    Returns:
        Verification result with approved/blocked status and reason
    """
    try:
        session = _sessions.get(session_id)
        if session is None:
            return {"error": "Session not found or expired"}

        anchor = session.anchor
        veto = _get_veto()

        # Build payload
        payload = AgentPayload(
            item_description=item_description,
            item_category=anchor.item_category,
            unit_price=unit_price,
            quantity=quantity,
            vendor=vendor,
            currency=currency,
            fees=[{"name": f["name"], "amount": f["amount"]} for f in (fees or [])],
            is_recurring=False
        )

        # Verify
        result = veto.engine.check(anchor, payload)

        return {
            "approved": result.approved,
            "status": result.status.value,
            "reason": result.reason,
            "checks": [
                {"name": c.name, "passed": c.passed, "reason": c.reason}
                for c in result.checks
            ]
        }
    except Exception as e:
        logger.error(f"verify_transaction failed: {e}")
        return {"error": "Verification failed"}


@mcp.tool()
def check_transaction(
    intent: str,
    item_description: str,
    unit_price: float,
    vendor: str,
    quantity: int = 1
) -> dict:
    """
    Quick one-shot verification without session management.

    Use this for simple, single transactions. For multi-step shopping flows,
    use lock_intent + verify_transaction instead.

    Args:
        intent: What the user wants (e.g., "$50 Amazon Gift Card")
        item_description: What the agent is purchasing
        unit_price: Price per unit
        vendor: Vendor domain
        quantity: Number of items (default: 1)

    Returns:
        Verification result with approved/blocked status
    """
    try:
        intent = _validate_intent(intent)
        veto = _get_veto()

        result = veto.verify(intent, {
            "item_description": item_description,
            "unit_price": unit_price,
            "vendor": vendor,
            "quantity": quantity
        })

        return {
            "approved": result.approved,
            "reason": result.reason
        }
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"check_transaction failed: {e}")
        return {"error": "Verification failed"}


@mcp.tool()
def clear_intent(session_id: str) -> dict:
    """
    Clear a locked intent after transaction completes.

    Call this after a successful purchase or when the session is no longer needed.

    Args:
        session_id: Session ID to clear

    Returns:
        Status indicating if session was cleared
    """
    if _sessions.delete(session_id):
        return {"status": "cleared"}
    return {"status": "not_found"}


if __name__ == "__main__":
    mcp.run()
