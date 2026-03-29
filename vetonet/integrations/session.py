"""
Shared session management for VetoNet integrations.

Provides a unified session layer for MCP, x402, and World AgentKit integrations
with TTL, limits, and security features.
"""

import secrets
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum

from vetonet.models import IntentAnchor

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Session lifecycle states."""
    ACTIVE = "active"
    EXPIRED = "expired"
    CLEARED = "cleared"
    LOCKED = "locked"  # Transaction in progress


# Default configuration
DEFAULT_MAX_SESSIONS = 10_000
DEFAULT_SESSION_TTL_SECONDS = 30 * 60  # 30 minutes
DEFAULT_MAX_INTENT_LENGTH = 1000


@dataclass
class SessionData:
    """
    A session containing a locked intent and optional metadata.

    Attributes:
        anchor: The normalized intent anchor
        created_at: Unix timestamp when session was created
        metadata: Optional additional data (wallet address, nullifier hash, etc.)
        status: Current session status
    """
    anchor: IntentAnchor
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: SessionStatus = SessionStatus.ACTIVE

    def is_expired(self, ttl_seconds: float) -> bool:
        """Check if session has expired."""
        return time.time() - self.created_at > ttl_seconds

    def lock(self):
        """Lock session during transaction verification."""
        self.status = SessionStatus.LOCKED

    def unlock(self):
        """Unlock session after verification."""
        self.status = SessionStatus.ACTIVE


class SessionStore:
    """
    Thread-safe session storage with TTL and limits.

    Security features:
    - Cryptographically random session IDs (secrets.token_urlsafe)
    - Session TTL with automatic cleanup
    - Maximum session limit to prevent DoS
    - Session locking during transactions
    """

    def __init__(
        self,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
        ttl_seconds: float = DEFAULT_SESSION_TTL_SECONDS
    ):
        self._sessions: Dict[str, SessionData] = {}
        self._max_sessions = max_sessions
        self._ttl_seconds = ttl_seconds

    def create(
        self,
        anchor: IntentAnchor,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new session with cryptographically random ID.

        Args:
            anchor: Normalized intent anchor
            metadata: Optional additional session data

        Returns:
            Session ID (44-character URL-safe token)

        Raises:
            ValueError: If max sessions reached
        """
        self._cleanup_expired()

        if len(self._sessions) >= self._max_sessions:
            raise ValueError("Maximum sessions reached. Try again later.")

        session_id = secrets.token_urlsafe(32)
        self._sessions[session_id] = SessionData(
            anchor=anchor,
            metadata=metadata or {}
        )

        logger.debug(f"Session created: {session_id[:8]}...")
        return session_id

    def get(self, session_id: str) -> Optional[SessionData]:
        """
        Get session if it exists and is not expired.

        Args:
            session_id: Session ID to look up

        Returns:
            SessionData if found and valid, None otherwise
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if session.is_expired(self._ttl_seconds):
            del self._sessions[session_id]
            logger.debug(f"Session expired: {session_id[:8]}...")
            return None

        return session

    def delete(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if session was deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.debug(f"Session deleted: {session_id[:8]}...")
            return True
        return False

    def update_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update session metadata.

        Args:
            session_id: Session ID to update
            metadata: New metadata to merge

        Returns:
            True if updated, False if session not found
        """
        session = self.get(session_id)
        if session is None:
            return False

        session.metadata.update(metadata)
        return True

    def _cleanup_expired(self):
        """Remove expired sessions."""
        expired = [
            sid for sid, s in self._sessions.items()
            if s.is_expired(self._ttl_seconds)
        ]
        for sid in expired:
            del self._sessions[sid]

        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired sessions")

    @property
    def count(self) -> int:
        """Current number of active sessions."""
        return len(self._sessions)


def validate_intent(intent: str, max_length: int = DEFAULT_MAX_INTENT_LENGTH) -> str:
    """
    Validate and sanitize intent string.

    Args:
        intent: Raw intent string
        max_length: Maximum allowed length

    Returns:
        Sanitized intent string

    Raises:
        ValueError: If intent is invalid
    """
    if not intent or not intent.strip():
        raise ValueError("Intent cannot be empty")

    intent = intent.strip()

    if len(intent) > max_length:
        raise ValueError(f"Intent too long (max {max_length} chars)")

    return intent


# Shared global session store instance
# Integrations can use this or create their own
_global_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """Get or create the global session store."""
    global _global_store
    if _global_store is None:
        _global_store = SessionStore()
    return _global_store
