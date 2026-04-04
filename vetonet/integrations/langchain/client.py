"""
VetoNet LangChain Integration - API Client

Production-ready HTTP client with:
- Connection pooling (httpx)
- Retry with exponential backoff
- Circuit breaker integration
- Structured JSON logging
"""

import asyncio
import json
import logging
import os
import random
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from .types import (
    VetoResponse,
    CheckResultModel,
    VetoStatus,
    VetoNetClientConfig,
    CircuitBreakerConfig,
    VetoNetLogEvent,
)
from .exceptions import (
    VetoNetError,
    VetoNetAuthError,
    VetoNetRateLimitError,
    VetoNetValidationError,
    VetoNetServiceError,
    VetoNetTimeoutError,
    VetoNetNetworkError,
    CircuitOpenError,
)
from .circuit import CircuitBreaker

logger = logging.getLogger("vetonet.langchain")


class APIClient:
    """Async/sync HTTP client for VetoNet API.

    Features:
    - Connection pooling for performance
    - Exponential backoff retries
    - Circuit breaker for resilience
    - Structured JSON logging

    Usage:
        # Async
        async with APIClient(config) as client:
            result = await client.check(prompt, payload)

        # Sync
        client = APIClient(config)
        result = client.check_sync(prompt, payload)
    """

    def __init__(
        self,
        config: Optional[VetoNetClientConfig] = None,
        api_key: Optional[str] = None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """Initialize API client.

        Args:
            config: Full configuration. If not provided, uses defaults with api_key.
            api_key: API key. Falls back to VETONET_API_KEY env var.
            circuit_breaker: Optional circuit breaker instance.
        """
        # Build config
        if config is None:
            key = api_key or os.environ.get("VETONET_API_KEY")
            if not key:
                raise VetoNetError(
                    "API key required. Set VETONET_API_KEY env var or pass api_key."
                )
            config = VetoNetClientConfig(api_key=key)

        self._config = config
        self._circuit_breaker = circuit_breaker or CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=30.0
            )
        )

        # Clients (lazy-initialized)
        self._async_client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None

    def _build_headers(self, request_id: str) -> Dict[str, str]:
        """Build request headers."""
        return {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
            "User-Agent": "vetonet-langchain/1.0",
        }

    def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client with connection pooling."""
        if self._async_client is None:
            limits = httpx.Limits(
                max_connections=self._config.max_connections,
                max_keepalive_connections=self._config.max_keepalive,
                keepalive_expiry=self._config.keepalive_expiry
            )
            timeout = httpx.Timeout(
                connect=5.0,
                read=self._config.timeout,
                write=10.0,
                pool=5.0
            )
            self._async_client = httpx.AsyncClient(
                base_url=self._config.base_url,
                limits=limits,
                timeout=timeout
            )
        return self._async_client

    def _get_sync_client(self) -> httpx.Client:
        """Get or create sync HTTP client with connection pooling."""
        if self._sync_client is None:
            limits = httpx.Limits(
                max_connections=self._config.max_connections,
                max_keepalive_connections=self._config.max_keepalive,
                keepalive_expiry=self._config.keepalive_expiry
            )
            timeout = httpx.Timeout(
                connect=5.0,
                read=self._config.timeout,
                write=10.0,
                pool=5.0
            )
            self._sync_client = httpx.Client(
                base_url=self._config.base_url,
                limits=limits,
                timeout=timeout
            )
        return self._sync_client

    def _log_event(self, event: VetoNetLogEvent) -> None:
        """Log structured event."""
        logger.info(json.dumps(event.to_json_dict()))

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter.

        Formula: min(base * 2^attempt + random(), max_backoff)
        """
        base = self._config.retry_backoff_base
        max_backoff = 30.0
        backoff = min(base * (2 ** attempt) + random.random(), max_backoff)
        return backoff

    def _parse_rate_limit_headers(self, response: httpx.Response) -> dict:
        """Parse rate limit info from response headers."""
        return {
            "limit": int(response.headers.get("X-RateLimit-Limit", 0)),
            "remaining": int(response.headers.get("X-RateLimit-Remaining", 0)),
            "reset_at": int(response.headers.get("X-RateLimit-Reset", 0)),
            "retry_after": float(response.headers.get("Retry-After", 60)),
        }

    def _handle_error_response(
        self,
        response: httpx.Response,
        request_id: str
    ) -> None:
        """Handle error responses, raising appropriate exceptions."""
        status = response.status_code

        try:
            body = response.json()
        except Exception:
            body = {"error": response.text}

        if status == 401:
            raise VetoNetAuthError(
                message=body.get("error", "Invalid API key"),
                request_id=request_id
            )

        if status == 429:
            rate_info = self._parse_rate_limit_headers(response)
            raise VetoNetRateLimitError(
                message=body.get("error", "Rate limit exceeded"),
                retry_after=rate_info["retry_after"],
                limit=rate_info["limit"],
                remaining=rate_info["remaining"],
                request_id=request_id
            )

        if status == 400:
            raise VetoNetValidationError(
                message=body.get("error", "Invalid request"),
                errors=body.get("errors", []),
                request_id=request_id
            )

        if status >= 500:
            raise VetoNetServiceError(
                message=body.get("error", f"Service error: {status}"),
                status_code=status,
                request_id=request_id,
                retryable=True
            )

        # Unknown error
        raise VetoNetError(
            message=f"Unexpected error: {status} - {body}",
            request_id=request_id
        )

    def _parse_response(self, data: dict, request_id: str) -> VetoResponse:
        """Parse API response into VetoResponse model."""
        checks = [
            CheckResultModel(
                id=c.get("id", "unknown"),
                name=c.get("name", "Unknown Check"),
                passed=c.get("passed", True),
                reason=c.get("reason", ""),
                score=c.get("score"),
                desc=c.get("desc", "")
            )
            for c in data.get("checks", [])
        ]

        return VetoResponse(
            verdict=data.get("verdict", "blocked"),
            status=VetoStatus(data.get("status", "VETO")),
            reason=data.get("reason", ""),
            confidence=data.get("confidence"),
            checks=checks,
            request_id=data.get("request_id", request_id)
        )

    async def check(
        self,
        prompt: str,
        payload: Dict[str, Any]
    ) -> VetoResponse:
        """Verify a transaction asynchronously.

        Args:
            prompt: User's intent (natural language)
            payload: Agent's proposed action (AgentPayload dict)

        Returns:
            VetoResponse with verdict and details

        Raises:
            VetoNetAuthError: Invalid API key
            VetoNetRateLimitError: Rate limit exceeded
            VetoNetValidationError: Invalid request
            VetoNetServiceError: Server error
            VetoNetTimeoutError: Request timed out
            VetoNetNetworkError: Network error
            CircuitOpenError: Circuit breaker is open
        """
        request_id = str(uuid.uuid4())[:8]
        start_time = time.monotonic()

        self._log_event(VetoNetLogEvent(
            event="request.start",
            request_id=request_id,
            metadata={"prompt_length": len(prompt)}
        ))

        async def do_request() -> VetoResponse:
            client = self._get_async_client()

            for attempt in range(self._config.max_retries + 1):
                try:
                    response = await client.post(
                        "/api/check",
                        json={"prompt": prompt, "payload": payload},
                        headers=self._build_headers(request_id)
                    )

                    if response.status_code == 200:
                        data = response.json()
                        result = self._parse_response(data, request_id)

                        latency_ms = int((time.monotonic() - start_time) * 1000)
                        self._log_event(VetoNetLogEvent(
                            event="request.success",
                            request_id=request_id,
                            latency_ms=latency_ms,
                            verdict=result.verdict
                        ))

                        return result

                    # Handle errors
                    self._handle_error_response(response, request_id)

                except httpx.TimeoutException as e:
                    if attempt < self._config.max_retries:
                        backoff = self._calculate_backoff(attempt)
                        self._log_event(VetoNetLogEvent(
                            event="request.retry",
                            request_id=request_id,
                            error="timeout",
                            metadata={"attempt": attempt + 1, "backoff": backoff}
                        ))
                        await asyncio.sleep(backoff)
                        continue

                    raise VetoNetTimeoutError(
                        timeout=self._config.timeout,
                        request_id=request_id
                    )

                except httpx.ConnectError as e:
                    if attempt < self._config.max_retries:
                        backoff = self._calculate_backoff(attempt)
                        self._log_event(VetoNetLogEvent(
                            event="request.retry",
                            request_id=request_id,
                            error="connection",
                            metadata={"attempt": attempt + 1, "backoff": backoff}
                        ))
                        await asyncio.sleep(backoff)
                        continue

                    raise VetoNetNetworkError(
                        original_error=e,
                        request_id=request_id
                    )

                except VetoNetServiceError as e:
                    if e.retryable and attempt < self._config.max_retries:
                        backoff = self._calculate_backoff(attempt)
                        self._log_event(VetoNetLogEvent(
                            event="request.retry",
                            request_id=request_id,
                            error=f"service_{e.status_code}",
                            metadata={"attempt": attempt + 1, "backoff": backoff}
                        ))
                        await asyncio.sleep(backoff)
                        continue
                    raise

            # Should not reach here
            raise VetoNetError("Max retries exceeded", request_id=request_id)

        # Execute with circuit breaker
        try:
            return await self._circuit_breaker.acall(do_request)
        except CircuitOpenError:
            self._log_event(VetoNetLogEvent(
                event="circuit.open",
                request_id=request_id,
                error="circuit_breaker_open"
            ))
            raise

    def check_sync(
        self,
        prompt: str,
        payload: Dict[str, Any]
    ) -> VetoResponse:
        """Verify a transaction synchronously.

        Same as check() but blocking. Use for sync tools.
        """
        request_id = str(uuid.uuid4())[:8]
        start_time = time.monotonic()

        self._log_event(VetoNetLogEvent(
            event="request.start",
            request_id=request_id,
            metadata={"prompt_length": len(prompt), "sync": True}
        ))

        def do_request() -> VetoResponse:
            client = self._get_sync_client()

            for attempt in range(self._config.max_retries + 1):
                try:
                    response = client.post(
                        "/api/check",
                        json={"prompt": prompt, "payload": payload},
                        headers=self._build_headers(request_id)
                    )

                    if response.status_code == 200:
                        data = response.json()
                        result = self._parse_response(data, request_id)

                        latency_ms = int((time.monotonic() - start_time) * 1000)
                        self._log_event(VetoNetLogEvent(
                            event="request.success",
                            request_id=request_id,
                            latency_ms=latency_ms,
                            verdict=result.verdict
                        ))

                        return result

                    self._handle_error_response(response, request_id)

                except httpx.TimeoutException:
                    if attempt < self._config.max_retries:
                        backoff = self._calculate_backoff(attempt)
                        time.sleep(backoff)
                        continue

                    raise VetoNetTimeoutError(
                        timeout=self._config.timeout,
                        request_id=request_id
                    )

                except httpx.ConnectError as e:
                    if attempt < self._config.max_retries:
                        backoff = self._calculate_backoff(attempt)
                        time.sleep(backoff)
                        continue

                    raise VetoNetNetworkError(
                        original_error=e,
                        request_id=request_id
                    )

                except VetoNetServiceError as e:
                    if e.retryable and attempt < self._config.max_retries:
                        backoff = self._calculate_backoff(attempt)
                        time.sleep(backoff)
                        continue
                    raise

            raise VetoNetError("Max retries exceeded", request_id=request_id)

        # Execute with circuit breaker
        try:
            return self._circuit_breaker.call(do_request)
        except CircuitOpenError:
            self._log_event(VetoNetLogEvent(
                event="circuit.open",
                request_id=request_id,
                error="circuit_breaker_open"
            ))
            raise

    async def close(self) -> None:
        """Close HTTP clients and release resources."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

    def close_sync(self) -> None:
        """Close sync HTTP client."""
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

    async def __aenter__(self) -> "APIClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - close clients."""
        await self.close()

    def __enter__(self) -> "APIClient":
        """Sync context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Sync context manager exit."""
        self.close_sync()


__all__ = ["APIClient"]
