"""
VetoNet LangChain Integration - Async Detection Utilities

Robust detection of async callables with 8-layer detection strategy.
Handles all LangChain tool types including wrapped functions, classes, and Runnables.
"""

import asyncio
import functools
import inspect
from typing import Any, Callable, Coroutine, Optional, TypeVar, Union, get_type_hints
from functools import lru_cache

T = TypeVar("T")


class AsyncDetector:
    """Reliably detect whether a callable is async.

    Uses 8-layer detection strategy to handle all cases:
    1. Direct coroutine functions (async def)
    2. functools.partial wrapping async
    3. __wrapped__ attribute (decorated functions)
    4. Classes with async __call__
    5. LangChain Runnables with ainvoke
    6. StructuredTool coroutine/func attributes
    7. Return type hints (Coroutine, Awaitable)
    8. Async generators

    Fallback: Returns False (sync) when uncertain - safer because:
    - Calling sync without await = works
    - Awaiting sync = crash
    """

    def __init__(self, cache_size: int = 10000):
        """Initialize with optional cache size."""
        self._cache_size = cache_size
        # Use instance method with lru_cache
        self._is_async_cached = lru_cache(maxsize=cache_size)(self._is_async_impl)

    def is_async_callable(self, obj: Any) -> bool:
        """Detect if obj should be awaited.

        Args:
            obj: Any callable (function, class, Runnable, etc.)

        Returns:
            True if obj is async and should be awaited
        """
        # Use id() for caching since callables aren't always hashable
        try:
            return self._is_async_cached(id(obj), obj)
        except TypeError:
            # Unhashable - compute directly
            return self._is_async_impl(id(obj), obj)

    def _is_async_impl(self, obj_id: int, obj: Any) -> bool:
        """Implementation of async detection with 8 layers."""

        # Layer 1: Direct coroutine function
        if asyncio.iscoroutinefunction(obj):
            return True

        # Layer 2: Async generator function
        if inspect.isasyncgenfunction(obj):
            return True

        # Layer 3: functools.partial wrapping async
        if isinstance(obj, functools.partial):
            return self._is_async_impl(id(obj.func), obj.func)

        # Layer 4: Decorated functions with __wrapped__
        if hasattr(obj, "__wrapped__"):
            wrapped = getattr(obj, "__wrapped__")
            if asyncio.iscoroutinefunction(wrapped):
                return True
            # Recurse for nested decorators
            if hasattr(wrapped, "__wrapped__"):
                return self._is_async_impl(id(wrapped), wrapped)

        # Layer 5: Classes with async __call__
        if hasattr(obj, "__call__") and not inspect.isfunction(obj):
            call_method = getattr(type(obj), "__call__", None)
            if call_method and asyncio.iscoroutinefunction(call_method):
                return True
            # Also check instance's __call__ (might be overridden)
            instance_call = getattr(obj, "__call__", None)
            if instance_call and asyncio.iscoroutinefunction(instance_call):
                return True

        # Layer 6: LangChain Runnable - check for ainvoke
        if hasattr(obj, "ainvoke") and hasattr(obj, "invoke"):
            # Runnables have both; if ainvoke exists and is a coroutine method, it's async-capable
            ainvoke = getattr(obj, "ainvoke")
            if asyncio.iscoroutinefunction(ainvoke):
                return True

        # Layer 7: LangChain StructuredTool attributes
        if hasattr(obj, "coroutine"):
            coroutine_attr = getattr(obj, "coroutine")
            if coroutine_attr is not None:
                return True

        if hasattr(obj, "func"):
            func_attr = getattr(obj, "func")
            if asyncio.iscoroutinefunction(func_attr):
                return True

        # Layer 8: Return type hints (Coroutine, Awaitable)
        try:
            hints = get_type_hints(obj)
            return_hint = hints.get("return")
            if return_hint:
                # Check if return type is Coroutine or Awaitable
                origin = getattr(return_hint, "__origin__", None)
                if origin is not None:
                    origin_name = getattr(origin, "__name__", str(origin))
                    if origin_name in ("Coroutine", "Awaitable"):
                        return True
        except Exception:
            # Type hint inspection failed - not async
            pass

        # Fallback: assume sync (safer)
        return False

    def clear_cache(self) -> None:
        """Clear the detection cache."""
        self._is_async_cached.cache_clear()

    @property
    def cache_info(self):
        """Get cache statistics."""
        return self._is_async_cached.cache_info()


# Global instance for convenience
_detector = AsyncDetector()


def is_async_callable(obj: Any) -> bool:
    """Check if obj is an async callable.

    This is the main entry point for async detection.

    Args:
        obj: Any callable

    Returns:
        True if obj should be awaited

    Example:
        >>> async def async_func(): pass
        >>> def sync_func(): pass
        >>> is_async_callable(async_func)
        True
        >>> is_async_callable(sync_func)
        False
    """
    return _detector.is_async_callable(obj)


def is_async_context() -> bool:
    """Check if currently in an async context (event loop running).

    Returns:
        True if an event loop is running

    Example:
        >>> is_async_context()
        False
        >>> async def check():
        ...     return is_async_context()
        >>> asyncio.run(check())
        True
    """
    try:
        loop = asyncio.get_running_loop()
        return loop is not None and loop.is_running()
    except RuntimeError:
        return False


def unwrap_callable(obj: Any, max_depth: int = 10) -> Any:
    """Recursively unwrap a callable to get the original function.

    Handles functools.partial, functools.wraps, and similar wrappers.

    Args:
        obj: Wrapped callable
        max_depth: Maximum unwrap depth (prevents infinite loops)

    Returns:
        The innermost callable
    """
    depth = 0
    current = obj

    while depth < max_depth:
        depth += 1

        # Unwrap functools.partial
        if isinstance(current, functools.partial):
            current = current.func
            continue

        # Unwrap decorated functions
        if hasattr(current, "__wrapped__"):
            current = current.__wrapped__
            continue

        # No more wrapping
        break

    return current


async def safe_await(result: Any) -> Any:
    """Safely await a result if it's a coroutine.

    Useful when you don't know if a function returned a coroutine or a value.

    Args:
        result: Either a coroutine or a regular value

    Returns:
        The awaited result if coroutine, otherwise the value as-is

    Example:
        >>> async def async_fn():
        ...     return 42
        >>> def sync_fn():
        ...     return 42
        >>> await safe_await(async_fn())
        42
        >>> await safe_await(sync_fn())
        42
    """
    if asyncio.iscoroutine(result):
        return await result
    return result


def run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine synchronously.

    Handles nested event loops by using existing loop if available.

    Args:
        coro: Coroutine to run

    Returns:
        The result of the coroutine

    Raises:
        RuntimeError: If called from within an async context
    """
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context - can't run sync
        raise RuntimeError(
            "Cannot run sync from async context. Use 'await' instead."
        )
    except RuntimeError:
        # No running loop - create one
        return asyncio.run(coro)


def make_sync(async_fn: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """Convert an async function to sync.

    Warning: This creates a new event loop for each call.
    Only use for compatibility with sync-only code.

    Args:
        async_fn: Async function to wrap

    Returns:
        Sync function that runs the async function

    Example:
        >>> @make_sync
        ... async def fetch_data():
        ...     return "data"
        >>> fetch_data()  # No await needed
        'data'
    """
    @functools.wraps(async_fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(async_fn(*args, **kwargs))
    return wrapper


def make_async(sync_fn: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """Convert a sync function to async (runs in thread pool).

    Useful for wrapping blocking I/O operations.

    Args:
        sync_fn: Sync function to wrap

    Returns:
        Async function that runs sync_fn in a thread pool

    Example:
        >>> @make_async
        ... def blocking_io():
        ...     import time
        ...     time.sleep(1)
        ...     return "done"
        >>> await blocking_io()  # Non-blocking
        'done'
    """
    @functools.wraps(sync_fn)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: sync_fn(*args, **kwargs))
    return wrapper


__all__ = [
    "AsyncDetector",
    "is_async_callable",
    "is_async_context",
    "unwrap_callable",
    "safe_await",
    "run_sync",
    "make_sync",
    "make_async",
]
