"""
VetoNet LangChain Integration - Shared Types

Pydantic models for type safety and serialization.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

_DEFAULT_API_URL = "https://web-production-fec907.up.railway.app"


# =============================================================================
# Enums
# =============================================================================


class VetoStatus(str, Enum):
    """Verification result status."""

    APPROVED = "APPROVED"
    VETO = "VETO"


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Rejecting all requests
    HALF_OPEN = "half_open"  # Testing recovery


# =============================================================================
# API Response Models
# =============================================================================


class CheckResultModel(BaseModel):
    """Result of a single verification check."""

    id: str
    name: str
    passed: bool
    reason: str
    score: Optional[float] = None
    desc: str = ""

    class Config:
        frozen = True


class VetoResponse(BaseModel):
    """Response from VetoNet API /api/check endpoint."""

    verdict: Literal["approved", "blocked"]
    status: VetoStatus
    reason: str = ""
    confidence: Optional[float] = None
    checks: List[CheckResultModel] = Field(default_factory=list)
    request_id: str = ""

    @property
    def approved(self) -> bool:
        return self.verdict == "approved"

    @property
    def blocked(self) -> bool:
        return self.verdict == "blocked"

    class Config:
        frozen = True


# =============================================================================
# Intent Models
# =============================================================================


class ConversationMessage(BaseModel):
    """A single message in the conversation history."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


class IntentContext(BaseModel):
    """Context for intent verification.

    Contains the captured intent and conversation history.
    """

    raw_message: str  # Original user message identified as purchase intent
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    turn_index: int = 0  # Which turn triggered this
    captured_at: datetime = Field(default_factory=datetime.utcnow)

    # Normalized anchor (populated after API normalization)
    anchor: Optional[Dict[str, Any]] = None

    @property
    def has_anchor(self) -> bool:
        return self.anchor is not None

    class Config:
        frozen = False  # anchor can be set after creation


# =============================================================================
# Tool Signature Models
# =============================================================================


class ToolSignature(BaseModel):
    """Configuration for mapping tool parameters to AgentPayload fields.

    Example:
        ToolSignature(
            field_map={"cost": "unit_price", "seller": "vendor"},
            defaults={"item_category": "gift_card", "currency": "USD"}
        )
    """

    # Map: tool_param_name -> agentpayload_field_name
    field_map: Dict[str, str] = Field(default_factory=dict)

    # Static defaults for fields not in tool params
    defaults: Dict[str, Any] = Field(default_factory=dict)

    # Tool metadata
    tool_name: Optional[str] = None
    description: Optional[str] = None

    # Behavior flags
    fail_open: bool = False  # Allow transaction if VetoNet unavailable
    auto_infer: bool = True  # Auto-map params with matching names

    class Config:
        frozen = True


# =============================================================================
# Circuit Breaker State
# =============================================================================


@dataclass
class CircuitBreakerState:
    """Immutable snapshot of circuit breaker state."""

    state: CircuitState
    failure_count: int
    last_failure_time: Optional[float]
    last_success_time: Optional[float]
    recovery_deadline: Optional[float]

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED

    @property
    def is_half_open(self) -> bool:
        return self.state == CircuitState.HALF_OPEN


# =============================================================================
# Configuration Models
# =============================================================================


class VetoNetClientConfig(BaseModel):
    """Configuration for VetoNet API client."""

    api_key: str
    base_url: str = os.environ.get("VETONET_API_URL", _DEFAULT_API_URL)
    timeout: float = 5.0
    max_retries: int = 3
    retry_backoff_base: float = 0.5

    # Connection pooling
    max_connections: int = 100
    max_keepalive: int = 10
    keepalive_expiry: float = 30.0

    class Config:
        frozen = True


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: float = 30.0  # Seconds before half-open
    half_open_max_calls: int = 1  # Test calls in half-open
    max_samples: int = 100  # Max failure timestamps to track

    class Config:
        frozen = True


class VetoNetGuardConfig(BaseModel):
    """Configuration for VetoNetGuard orchestrator."""

    # API settings
    api_key: Optional[str] = None  # Falls back to VETONET_API_KEY env var
    api_base: str = os.environ.get("VETONET_API_URL", _DEFAULT_API_URL)
    timeout: float = 5.0

    # Circuit breaker
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 30.0

    # Behavior
    fail_open: bool = False  # Default fail mode

    # Intent capture
    max_history_turns: int = 20  # Max conversation turns to track

    class Config:
        frozen = True


# =============================================================================
# Logging Event Models
# =============================================================================


class VetoNetLogEvent(BaseModel):
    """Structured log event for observability."""

    event: str  # e.g., "request.start", "request.success", "circuit.open"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    tool_name: Optional[str] = None
    latency_ms: Optional[int] = None
    verdict: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_json_dict(self) -> dict:
        """Convert to JSON-serializable dict for logging."""
        d = {
            "event": self.event,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.request_id:
            d["request_id"] = self.request_id
        if self.tool_name:
            d["tool_name"] = self.tool_name
        if self.latency_ms is not None:
            d["latency_ms"] = self.latency_ms
        if self.verdict:
            d["verdict"] = self.verdict
        if self.error:
            d["error"] = self.error
        if self.metadata:
            d["metadata"] = self.metadata
        return d


__all__ = [
    # Enums
    "VetoStatus",
    "CircuitState",
    # API models
    "CheckResultModel",
    "VetoResponse",
    # Intent models
    "ConversationMessage",
    "IntentContext",
    # Tool signature
    "ToolSignature",
    # Circuit breaker
    "CircuitBreakerState",
    # Config models
    "VetoNetClientConfig",
    "CircuitBreakerConfig",
    "VetoNetGuardConfig",
    # Logging
    "VetoNetLogEvent",
]
