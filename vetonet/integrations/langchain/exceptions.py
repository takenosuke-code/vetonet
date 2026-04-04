"""
VetoNet LangChain Integration - Exception Hierarchy

Production-quality exceptions with:
- Clear error messages for debugging
- Structured data for programmatic handling
- Proper inheritance for catch-all patterns
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any
from datetime import datetime


class VetoNetError(Exception):
    """Base exception for all VetoNet errors."""

    def __init__(self, message: str, request_id: Optional[str] = None):
        self.message = message
        self.request_id = request_id
        self.timestamp = datetime.utcnow()
        super().__init__(message)

    def __str__(self) -> str:
        if self.request_id:
            return f"{self.message} (request_id={self.request_id})"
        return self.message


# =============================================================================
# Configuration Errors (fail fast at startup)
# =============================================================================

class VetoNetConfigError(VetoNetError):
    """Configuration error - missing or invalid settings."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        self.config_key = config_key
        super().__init__(message)


# =============================================================================
# API Errors (runtime, from HTTP calls)
# =============================================================================

class VetoNetAPIError(VetoNetError):
    """Base class for API-related errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        request_id: Optional[str] = None,
        response_body: Optional[dict] = None
    ):
        self.status_code = status_code
        self.response_body = response_body or {}
        super().__init__(message, request_id)


class VetoNetAuthError(VetoNetAPIError):
    """Authentication failed - invalid or expired API key (HTTP 401)."""

    def __init__(
        self,
        message: str = "Invalid or expired API key",
        request_id: Optional[str] = None
    ):
        super().__init__(message, status_code=401, request_id=request_id)


class VetoNetRateLimitError(VetoNetAPIError):
    """Rate limit exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None,
        limit: Optional[int] = None,
        remaining: Optional[int] = None,
        reset_at: Optional[datetime] = None,
        request_id: Optional[str] = None
    ):
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at
        super().__init__(message, status_code=429, request_id=request_id)

    def __str__(self) -> str:
        parts = [self.message]
        if self.retry_after:
            parts.append(f"retry_after={self.retry_after}s")
        if self.limit:
            parts.append(f"limit={self.limit}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        return " ".join(parts)


class VetoNetValidationError(VetoNetAPIError):
    """Request validation failed (HTTP 400)."""

    def __init__(
        self,
        message: str = "Invalid request",
        errors: Optional[List[dict]] = None,
        request_id: Optional[str] = None
    ):
        self.errors = errors or []
        super().__init__(message, status_code=400, request_id=request_id)


class VetoNetServiceError(VetoNetAPIError):
    """VetoNet service error (HTTP 5xx) - may be retryable."""

    def __init__(
        self,
        message: str = "VetoNet service error",
        status_code: int = 500,
        request_id: Optional[str] = None,
        retryable: bool = True
    ):
        self.retryable = retryable
        super().__init__(message, status_code=status_code, request_id=request_id)


class VetoNetTimeoutError(VetoNetAPIError):
    """Request timed out."""

    def __init__(
        self,
        message: str = "Request timed out",
        timeout: Optional[float] = None,
        request_id: Optional[str] = None
    ):
        self.timeout = timeout
        super().__init__(message, request_id=request_id)


class VetoNetNetworkError(VetoNetAPIError):
    """Network connectivity error."""

    def __init__(
        self,
        message: str = "Network error",
        original_error: Optional[Exception] = None,
        request_id: Optional[str] = None
    ):
        self.original_error = original_error
        super().__init__(message, request_id=request_id)


# =============================================================================
# Circuit Breaker Errors
# =============================================================================

class CircuitOpenError(VetoNetError):
    """Circuit breaker is open - requests are being rejected."""

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        failure_count: int = 0,
        recovery_time: Optional[float] = None
    ):
        self.failure_count = failure_count
        self.recovery_time = recovery_time
        super().__init__(message)

    def __str__(self) -> str:
        parts = [self.message]
        parts.append(f"failures={self.failure_count}")
        if self.recovery_time:
            parts.append(f"recovery_in={self.recovery_time:.1f}s")
        return " ".join(parts)


# =============================================================================
# Verification Errors (transaction blocked)
# =============================================================================

@dataclass
class CheckDetail:
    """Details of a single verification check."""
    id: str
    name: str
    passed: bool
    reason: str
    score: Optional[float] = None


class VetoBlockedException(VetoNetError):
    """Transaction was blocked by VetoNet verification.

    This extends ToolException pattern for LangChain compatibility.
    When handle_tool_error=True, LangChain will catch this gracefully.
    """

    def __init__(
        self,
        reason: str,
        checks: Optional[List[CheckDetail]] = None,
        confidence: Optional[float] = None,
        request_id: Optional[str] = None,
        intent: Optional[str] = None,
        payload: Optional[dict] = None
    ):
        self.reason = reason
        self.checks = checks or []
        self.confidence = confidence
        self.intent = intent
        self.payload = payload

        message = f"Transaction blocked: {reason}"
        super().__init__(message, request_id)

    @property
    def failed_checks(self) -> List[CheckDetail]:
        """Return only the checks that failed."""
        return [c for c in self.checks if not c.passed]

    def to_dict(self) -> dict:
        """Serialize for logging/API responses."""
        return {
            "blocked": True,
            "reason": self.reason,
            "confidence": self.confidence,
            "request_id": self.request_id,
            "failed_checks": [
                {"id": c.id, "name": c.name, "reason": c.reason}
                for c in self.failed_checks
            ]
        }


# =============================================================================
# Signature/Mapping Errors
# =============================================================================

class SignatureError(VetoNetError):
    """Error in tool signature configuration."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        field: Optional[str] = None
    ):
        self.tool_name = tool_name
        self.field = field
        super().__init__(message)


class MappingError(VetoNetError):
    """Error mapping tool arguments to AgentPayload."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        source_field: Optional[str] = None,
        target_field: Optional[str] = None,
        value: Any = None
    ):
        self.tool_name = tool_name
        self.source_field = source_field
        self.target_field = target_field
        self.value = value
        super().__init__(message)


# =============================================================================
# Intent Errors
# =============================================================================

class IntentNotSetError(VetoNetError):
    """No intent was captured for verification."""

    def __init__(
        self,
        message: str = "No purchase intent captured. Ensure VetoNetCallbackHandler is attached.",
        tool_name: Optional[str] = None
    ):
        self.tool_name = tool_name
        super().__init__(message)


# =============================================================================
# Utility: Try to import LangChain's ToolException for compatibility
# =============================================================================

try:
    from langchain_core.tools import ToolException

    # Make VetoBlockedException compatible with LangChain's error handling
    class VetoBlockedToolException(ToolException, VetoBlockedException):
        """VetoNet block that integrates with LangChain's tool error handling."""

        def __init__(self, reason: str, **kwargs):
            VetoBlockedException.__init__(self, reason, **kwargs)
            ToolException.__init__(self, f"Transaction blocked: {reason}")

    # Export this as the preferred exception when LangChain is available
    LANGCHAIN_AVAILABLE = True

except ImportError:
    # LangChain not installed - VetoBlockedException works standalone
    VetoBlockedToolException = VetoBlockedException
    LANGCHAIN_AVAILABLE = False


__all__ = [
    # Base
    "VetoNetError",
    "VetoNetConfigError",

    # API errors
    "VetoNetAPIError",
    "VetoNetAuthError",
    "VetoNetRateLimitError",
    "VetoNetValidationError",
    "VetoNetServiceError",
    "VetoNetTimeoutError",
    "VetoNetNetworkError",

    # Circuit breaker
    "CircuitOpenError",

    # Verification
    "VetoBlockedException",
    "VetoBlockedToolException",
    "CheckDetail",

    # Mapping
    "SignatureError",
    "MappingError",

    # Intent
    "IntentNotSetError",

    # Constants
    "LANGCHAIN_AVAILABLE",
]
