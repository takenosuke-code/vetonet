"""
VetoNet LangChain Integration - Thread-Safe Circuit Breaker

Production-quality circuit breaker with:
- Atomic state transitions (no race conditions)
- Bounded memory (SlidingWindowCounter)
- Both sync and async support
- Proper half-open behavior
"""

import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, TypeVar

from .types import CircuitState, CircuitBreakerConfig, CircuitBreakerState
from .exceptions import CircuitOpenError

T = TypeVar("T")


class SlidingWindowCounter:
    """Thread-safe sliding window for counting failures.

    Uses a bounded deque to track failure timestamps.
    Memory is bounded: max_samples * 8 bytes = ~800 bytes for 100 samples.
    """

    def __init__(self, window_seconds: float = 60.0, max_samples: int = 100):
        self._window = window_seconds
        self._max_samples = max_samples
        self._timestamps: deque = deque(maxlen=max_samples)
        self._lock = threading.Lock()

    def record(self) -> None:
        """Record a failure at current time."""
        with self._lock:
            self._timestamps.append(time.monotonic())

    def count(self) -> int:
        """Count failures within the sliding window."""
        now = time.monotonic()
        cutoff = now - self._window

        with self._lock:
            # Remove old entries (deque handles max_samples automatically)
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()
            return len(self._timestamps)

    def clear(self) -> None:
        """Clear all recorded failures."""
        with self._lock:
            self._timestamps.clear()


class CircuitBreaker:
    """Thread-safe circuit breaker for resilience.

    State Machine:
        CLOSED → (N failures) → OPEN → (timeout) → HALF_OPEN
        HALF_OPEN → (success) → CLOSED
        HALF_OPEN → (failure) → OPEN

    Thread-Safety:
        - State transitions are atomic (protected by RLock)
        - Function execution happens OUTSIDE the lock (allows concurrency)
        - Async calls use asyncio.Lock for coordination

    Usage:
        cb = CircuitBreaker()

        # Sync usage
        result = cb.call(lambda: api_request())

        # Async usage
        result = await cb.acall(lambda: async_api_request())

        # Decorator usage
        @cb.protect
        def my_function():
            ...
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker.

        Args:
            config: Configuration options. Uses defaults if not provided.
        """
        self._config = config or CircuitBreakerConfig()

        # State
        self._state = CircuitState.CLOSED
        self._failure_counter = SlidingWindowCounter(
            window_seconds=self._config.recovery_timeout,
            max_samples=self._config.max_samples
        )
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._half_open_calls = 0

        # Thread-safety
        self._lock = threading.RLock()
        self._async_lock: Optional[asyncio.Lock] = None

    def _get_async_lock(self) -> asyncio.Lock:
        """Lazy-create async lock (can't create at __init__ if no event loop)."""
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock

    @property
    def state(self) -> CircuitState:
        """Current circuit state (thread-safe read)."""
        with self._lock:
            self._maybe_transition_to_half_open()
            return self._state

    def get_state(self) -> CircuitBreakerState:
        """Get full state snapshot."""
        with self._lock:
            self._maybe_transition_to_half_open()
            recovery_deadline = None
            if self._state == CircuitState.OPEN and self._last_failure_time:
                recovery_deadline = self._last_failure_time + self._config.recovery_timeout

            return CircuitBreakerState(
                state=self._state,
                failure_count=self._failure_counter.count(),
                last_failure_time=self._last_failure_time,
                last_success_time=self._last_success_time,
                recovery_deadline=recovery_deadline
            )

    def _maybe_transition_to_half_open(self) -> None:
        """Check if we should transition from OPEN to HALF_OPEN.

        Must be called with lock held.
        """
        if self._state != CircuitState.OPEN:
            return

        if self._last_failure_time is None:
            return

        elapsed = time.monotonic() - self._last_failure_time
        if elapsed >= self._config.recovery_timeout:
            self._state = CircuitState.HALF_OPEN
            self._half_open_calls = 0

    def _can_execute(self) -> bool:
        """Check if execution is allowed. Must be called with lock held."""
        self._maybe_transition_to_half_open()

        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            return False

        if self._state == CircuitState.HALF_OPEN:
            # Only allow limited calls in half-open
            if self._half_open_calls < self._config.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

        return False

    def _record_success(self) -> None:
        """Record successful execution. Thread-safe."""
        with self._lock:
            self._last_success_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                # Successful test call - close the circuit
                self._state = CircuitState.CLOSED
                self._failure_counter.clear()
                self._half_open_calls = 0

    def _record_failure(self, exc: Optional[Exception] = None) -> None:
        """Record failed execution. Thread-safe."""
        with self._lock:
            now = time.monotonic()
            self._last_failure_time = now
            self._failure_counter.record()

            if self._state == CircuitState.HALF_OPEN:
                # Failed test call - reopen the circuit
                self._state = CircuitState.OPEN
                self._half_open_calls = 0

            elif self._state == CircuitState.CLOSED:
                # Check if we should open
                if self._failure_counter.count() >= self._config.failure_threshold:
                    self._state = CircuitState.OPEN

    def call(self, func: Callable[[], T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection.

        Thread-safe: Lock protects state check, function executes outside lock.

        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function

        Returns:
            Result of func()

        Raises:
            CircuitOpenError: If circuit is open
            Exception: Any exception from func (also recorded as failure)
        """
        # ATOMIC: Check state and reserve slot
        with self._lock:
            if not self._can_execute():
                state = self.get_state()
                raise CircuitOpenError(
                    failure_count=state.failure_count,
                    recovery_time=state.recovery_deadline - time.monotonic()
                    if state.recovery_deadline else None
                )

        # CONCURRENT: Execute outside lock
        try:
            if args or kwargs:
                result = func(*args, **kwargs)
            else:
                result = func()
            self._record_success()
            return result
        except Exception as e:
            self._record_failure(e)
            raise

    async def acall(
        self,
        func: Callable[[], Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """Execute async function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to function

        Returns:
            Result of await func()

        Raises:
            CircuitOpenError: If circuit is open
            Exception: Any exception from func
        """
        # Use async lock for coordination between async calls
        async_lock = self._get_async_lock()

        async with async_lock:
            # Check state (sync lock protects shared state)
            with self._lock:
                if not self._can_execute():
                    state = self.get_state()
                    raise CircuitOpenError(
                        failure_count=state.failure_count,
                        recovery_time=state.recovery_deadline - time.monotonic()
                        if state.recovery_deadline else None
                    )

        # Execute outside both locks
        try:
            if args or kwargs:
                result = await func(*args, **kwargs)
            else:
                result = await func()
            self._record_success()
            return result
        except Exception as e:
            self._record_failure(e)
            raise

    def protect(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to protect a function with circuit breaker.

        Example:
            @circuit_breaker.protect
            def api_call():
                ...
        """
        import functools
        from .async_utils import is_async_callable

        if is_async_callable(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self.acall(lambda: func(*args, **kwargs))
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self.call(lambda: func(*args, **kwargs))
            return sync_wrapper

    def reset(self) -> None:
        """Manually reset circuit to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_counter.clear()
            self._half_open_calls = 0
            self._last_failure_time = None

    def force_open(self) -> None:
        """Manually force circuit to open state."""
        with self._lock:
            self._state = CircuitState.OPEN
            self._last_failure_time = time.monotonic()

    def __repr__(self) -> str:
        state = self.get_state()
        return (
            f"CircuitBreaker(state={state.state.value}, "
            f"failures={state.failure_count}, "
            f"threshold={self._config.failure_threshold})"
        )


__all__ = [
    "CircuitBreaker",
    "SlidingWindowCounter",
]
