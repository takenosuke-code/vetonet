"""
VetoNet LangChain Integration - Intent Store

Thread-safe intent capture and storage using contextvars.
Smart extraction heuristic finds purchase intent (not just first message).
"""

import re
from collections import deque
from contextvars import ContextVar
from datetime import datetime
from typing import Optional, List, Deque

from .types import ConversationMessage, IntentContext

# =============================================================================
# Purchase Intent Detection
# =============================================================================

# Patterns that indicate purchase intent
PURCHASE_VERBS = re.compile(
    r'\b(buy|purchase|order|book|get\s+me|subscribe|pay\s+for|checkout|acquire)\b',
    re.IGNORECASE
)

PRICE_PATTERNS = re.compile(
    r'\$\d+|\d+\s*dollars?|\d+\s*USD|'
    r'under\s+\d+|up\s+to\s+\d+|max(?:imum)?\s+\d+|'
    r'less\s+than\s+\d+|no\s+more\s+than\s+\d+|'
    r'budget\s+(?:of\s+)?\d+|limit\s+(?:of\s+)?\d+',
    re.IGNORECASE
)

PRODUCT_KEYWORDS = re.compile(
    r'\b(gift\s*card|subscription|ticket|flight|hotel|'
    r'item|product|service|membership|plan|license)\b',
    re.IGNORECASE
)


def has_purchase_signals(text: str) -> bool:
    """Check if text contains purchase intent signals.

    A message is considered purchase intent if it has:
    - A purchase verb (buy, order, etc.) OR
    - A price indicator ($50, under 100, etc.) AND any purchase-related keyword
    """
    # Strong signal: explicit purchase verb
    if PURCHASE_VERBS.search(text):
        return True

    # Medium signal: price + product keyword
    if PRICE_PATTERNS.search(text) and PRODUCT_KEYWORDS.search(text):
        return True

    # Weak signal: just price (might be informational)
    # We don't count this alone

    return False


def extract_price_limit(text: str) -> Optional[float]:
    """Extract maximum price from text.

    Examples:
        "under $50" -> 50.0
        "up to 100 dollars" -> 100.0
        "$75 max" -> 75.0
    """
    # Pattern: $N or N dollars
    price_match = re.search(r'\$(\d+(?:\.\d{2})?)|(\d+(?:\.\d{2})?)\s*dollars?', text, re.I)

    # Pattern: under/up to/max N
    limit_match = re.search(
        r'(?:under|up\s+to|max(?:imum)?|less\s+than|no\s+more\s+than|budget\s+(?:of\s+)?|limit\s+(?:of\s+)?)\s*'
        r'\$?(\d+(?:\.\d{2})?)',
        text, re.I
    )

    if limit_match:
        return float(limit_match.group(1))
    if price_match:
        return float(price_match.group(1) or price_match.group(2))

    return None


# =============================================================================
# Intent Store (Thread-Safe via ContextVars)
# =============================================================================

# Context variables for thread/async isolation
_conversation_history: ContextVar[Optional[Deque[ConversationMessage]]] = ContextVar(
    'vetonet_conversation', default=None
)
_current_intent: ContextVar[Optional[IntentContext]] = ContextVar(
    'vetonet_intent', default=None
)


class IntentStore:
    """Thread-safe intent storage using contextvars.

    Each async task/thread gets isolated storage automatically.
    No need for locks - contextvars handle isolation.

    Usage:
        store = IntentStore()

        # Capture messages as conversation progresses
        store.capture("Buy me a $50 gift card", role="user")
        store.capture("Found Amazon gift card for $49.99", role="assistant")

        # Get intent when tool is invoked
        intent = store.get_purchase_intent()
        # Returns IntentContext with "Buy me a $50 gift card"
    """

    def __init__(self, max_history: int = 20):
        """Initialize intent store.

        Args:
            max_history: Maximum conversation turns to retain (bounded memory)
        """
        self._max_history = max_history

    def _get_history(self) -> Deque[ConversationMessage]:
        """Get or create conversation history for current context."""
        history = _conversation_history.get()
        if history is None:
            history = deque(maxlen=self._max_history)
            _conversation_history.set(history)
        return history

    def capture(
        self,
        content: str,
        role: str = "user",
        metadata: Optional[dict] = None
    ) -> None:
        """Record a conversation message.

        Called by callback handler as conversation progresses.

        Args:
            content: Message content
            role: Message role (user, assistant, system)
            metadata: Optional metadata
        """
        if not content or not content.strip():
            return

        # Truncate very long messages
        content = content[:10000] if len(content) > 10000 else content

        msg = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )

        history = self._get_history()
        history.append(msg)

    def get_purchase_intent(self) -> Optional[IntentContext]:
        """Get the most recent message with purchase intent.

        Searches backwards through conversation history to find
        the most recent user message with purchase signals.

        Returns:
            IntentContext if found, None otherwise
        """
        # Check if we already have a cached intent
        cached = _current_intent.get()
        if cached is not None:
            return cached

        history = self._get_history()
        if not history:
            return None

        # Search backwards for purchase intent
        history_list = list(history)
        for i in range(len(history_list) - 1, -1, -1):
            msg = history_list[i]
            if msg.role == "user" and has_purchase_signals(msg.content):
                context = IntentContext(
                    raw_message=msg.content,
                    conversation_history=history_list[:i+1],
                    turn_index=i,
                    captured_at=datetime.utcnow()
                )
                # Cache it
                _current_intent.set(context)
                return context

        # Fallback: use most recent user message even without signals
        for i in range(len(history_list) - 1, -1, -1):
            msg = history_list[i]
            if msg.role == "user":
                context = IntentContext(
                    raw_message=msg.content,
                    conversation_history=history_list[:i+1],
                    turn_index=i,
                    captured_at=datetime.utcnow()
                )
                _current_intent.set(context)
                return context

        return None

    def set_intent(self, raw_message: str, anchor: Optional[dict] = None) -> IntentContext:
        """Explicitly set the intent (for testing or manual override).

        Args:
            raw_message: The user's intent message
            anchor: Optional pre-normalized IntentAnchor dict

        Returns:
            The created IntentContext
        """
        history = self._get_history()
        context = IntentContext(
            raw_message=raw_message,
            conversation_history=list(history),
            turn_index=len(history),
            captured_at=datetime.utcnow(),
            anchor=anchor
        )
        _current_intent.set(context)
        return context

    def clear(self) -> None:
        """Clear conversation history and cached intent."""
        _conversation_history.set(None)
        _current_intent.set(None)

    def get_history(self) -> List[ConversationMessage]:
        """Get conversation history as a list."""
        history = self._get_history()
        return list(history)

    @property
    def history_length(self) -> int:
        """Number of messages in history."""
        history = _conversation_history.get()
        return len(history) if history else 0


# Global instance for convenience
_default_store: Optional[IntentStore] = None


def get_intent_store(max_history: int = 20) -> IntentStore:
    """Get or create the default IntentStore instance."""
    global _default_store
    if _default_store is None:
        _default_store = IntentStore(max_history=max_history)
    return _default_store


def capture_message(content: str, role: str = "user") -> None:
    """Convenience function to capture a message in the default store."""
    get_intent_store().capture(content, role)


def get_current_intent() -> Optional[IntentContext]:
    """Convenience function to get current intent from the default store."""
    return get_intent_store().get_purchase_intent()


def set_intent(raw_message: str, anchor: Optional[dict] = None) -> IntentContext:
    """Convenience function to set intent in the default store."""
    return get_intent_store().set_intent(raw_message, anchor)


def clear_intent() -> None:
    """Convenience function to clear the default store."""
    get_intent_store().clear()


__all__ = [
    # Classes
    "IntentStore",

    # Detection functions
    "has_purchase_signals",
    "extract_price_limit",

    # Convenience functions
    "get_intent_store",
    "capture_message",
    "get_current_intent",
    "set_intent",
    "clear_intent",
]
