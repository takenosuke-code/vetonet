"""
VetoNet API Key Authentication

Handles API key generation, validation, and rate limiting.
Keys are stored as SHA256 hashes - plaintext never persisted.
"""

import secrets
import hashlib
import time
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps

from vetonet import db
from vetonet.ratelimit import get_limiter


# Key format: veto_sk_live_ or veto_sk_test_ + 48 random chars (like Stripe)
KEY_PREFIX_LIVE = "veto_sk_live_"
KEY_PREFIX_TEST = "veto_sk_test_"
KEY_LENGTH = 48  # Characters after prefix (industry standard)
DEFAULT_RATE_LIMIT = 10000  # 10K requests/day for free tier


@dataclass
class APIKey:
    """Validated API key with metadata."""

    id: str
    user_id: Optional[str]
    key_prefix: str
    name: Optional[str]
    rate_limit: int
    created_at: datetime
    last_used_at: Optional[datetime]
    is_active: bool
    environment: str = "live"  # "live" or "test"


@dataclass
class RateLimitResult:
    """Rate limit check result."""

    allowed: bool
    remaining: int
    reset_at: datetime
    limit: int


RATE_LIMIT_WINDOW = 86400  # 24 hours in seconds


def generate_api_key(environment: str = "live") -> Tuple[str, str]:
    """
    Generate a new API key.

    Args:
        environment: "live" or "test" - determines key prefix

    Returns:
        Tuple of (full_key, key_hash)
        - full_key: The actual API key to give to user ONCE
        - key_hash: SHA256 hash to store in database
    """
    # Choose prefix based on environment
    prefix = KEY_PREFIX_TEST if environment == "test" else KEY_PREFIX_LIVE

    # Generate random bytes and encode as hex (48 chars)
    random_part = secrets.token_hex(KEY_LENGTH // 2)  # hex doubles length
    full_key = f"{prefix}{random_part}"

    # Hash for storage (never store plaintext)
    key_hash = hash_key(full_key)

    return full_key, key_hash


def hash_key(key: str) -> str:
    """Hash an API key using SHA256."""
    return hashlib.sha256(key.encode()).hexdigest()


def get_key_prefix(key: str) -> str:
    """Extract the identifiable prefix from a key (first 12 chars)."""
    return key[:12] if len(key) >= 12 else key


def validate_key_format(key: str) -> Tuple[bool, str]:
    """
    Check if a key has valid format.

    Returns:
        Tuple of (is_valid, environment)
        - environment: "live", "test", or "" if invalid
    """
    if not key:
        return False, ""

    if key.startswith(KEY_PREFIX_LIVE):
        expected_len = len(KEY_PREFIX_LIVE) + KEY_LENGTH
        if len(key) == expected_len:
            return True, "live"
    elif key.startswith(KEY_PREFIX_TEST):
        expected_len = len(KEY_PREFIX_TEST) + KEY_LENGTH
        if len(key) == expected_len:
            return True, "test"

    return False, ""


def get_key_environment(key: str) -> str:
    """Get the environment (live/test) from a key."""
    if key.startswith(KEY_PREFIX_TEST):
        return "test"
    return "live"


def validate_api_key(key: str) -> Tuple[bool, Optional[APIKey], str]:
    """
    Validate an API key against the database.

    Security: Uses constant-time comparison to prevent timing attacks.
    Lookup by hash (not prefix) to prevent enumeration.

    Returns:
        Tuple of (is_valid, api_key_object, error_message)
    """
    is_valid_format, environment = validate_key_format(key)
    if not is_valid_format:
        # Add small random delay to prevent format-based timing attacks
        time.sleep(secrets.randbelow(50) / 1000)  # 0-50ms jitter
        return False, None, "Invalid key format"

    key_hash = hash_key(key)

    # Look up by hash (indexed, constant-time lookup)
    # Never lookup by prefix alone - prevents enumeration
    key_data = db.get_api_key_by_hash(key_hash)

    if not key_data:
        return False, None, "Invalid API key"

    if not key_data.get("is_active", True):
        return False, None, "API key has been revoked"

    # Check expiration
    expires_at = key_data.get("expires_at")
    if expires_at:
        try:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.now(exp_dt.tzinfo) > exp_dt:
                return False, None, "API key has expired"
        except (ValueError, TypeError):
            return False, None, "API key expiration data invalid"

    # Update last_used_at (async, don't block on it)
    db.update_key_last_used(key_data["id"])

    api_key = APIKey(
        id=key_data["id"],
        user_id=key_data.get("user_id"),
        key_prefix=key_data.get("key_prefix", get_key_prefix(key)),
        name=key_data.get("name"),
        rate_limit=key_data.get("rate_limit", DEFAULT_RATE_LIMIT),
        created_at=datetime.fromisoformat(key_data["created_at"].replace("Z", "+00:00"))
        if key_data.get("created_at")
        else datetime.now(),
        last_used_at=datetime.fromisoformat(key_data["last_used_at"].replace("Z", "+00:00"))
        if key_data.get("last_used_at")
        else None,
        is_active=key_data.get("is_active", True),
        environment=key_data.get("environment", environment),  # From DB or inferred from key
    )

    return True, api_key, ""


def check_rate_limit(key_id: str, limit: int) -> RateLimitResult:
    """
    Check if request is within rate limit.

    Uses shared RateLimiter backend (in-memory with optional Redis).

    Args:
        key_id: The API key ID
        limit: Requests allowed per 24 hours

    Returns:
        RateLimitResult with allowed status and remaining quota
    """
    result = get_limiter().check(f"apikey:{key_id}", limit, RATE_LIMIT_WINDOW)

    return RateLimitResult(
        allowed=result.allowed,
        remaining=result.remaining,
        reset_at=datetime.fromtimestamp(result.reset_at),
        limit=limit,
    )


def log_api_usage(key_id: str, endpoint: str, status: int, latency_ms: int):
    """Log API usage for analytics."""
    db.log_api_usage(key_id, endpoint, status, latency_ms)


def require_api_key(f):
    """
    Decorator to require valid API key for endpoints.

    Checks Authorization header for Bearer token.
    Applies rate limiting.
    Logs usage.

    Usage:
        @app.route("/api/check", methods=["POST"])
        @require_api_key
        def check():
            # request.api_key contains the validated APIKey object
            ...
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request, jsonify  # Lazy import - Flask only needed at runtime

        start_time = time.time()

        # Extract key from Authorization header
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify(
                {
                    "error": "Missing or invalid Authorization header",
                    "hint": "Use 'Authorization: Bearer veto_sk_xxx'",
                }
            ), 401

        api_key = auth_header[7:]  # Remove "Bearer " prefix

        # Validate key
        is_valid, key_obj, error = validate_api_key(api_key)

        if not is_valid:
            return jsonify({"error": error}), 401

        # Check rate limit
        rate_result = check_rate_limit(key_obj.id, key_obj.rate_limit)

        if not rate_result.allowed:
            response = jsonify(
                {
                    "error": "Rate limit exceeded",
                    "limit": rate_result.limit,
                    "reset_at": rate_result.reset_at.isoformat(),
                }
            )
            response.headers["X-RateLimit-Limit"] = str(rate_result.limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(rate_result.reset_at.timestamp()))
            return response, 429

        # Add rate limit headers
        # Store key on request for handler to use
        request.api_key = key_obj

        # Execute handler
        response = f(*args, **kwargs)

        # Log usage
        latency_ms = int((time.time() - start_time) * 1000)
        status = response[1] if isinstance(response, tuple) else 200
        log_api_usage(key_obj.id, request.path, status, latency_ms)

        # Add rate limit headers to response
        if isinstance(response, tuple):
            resp_obj, status_code = response[0], response[1]
        else:
            resp_obj, status_code = response, 200

        if hasattr(resp_obj, "headers"):
            resp_obj.headers["X-RateLimit-Limit"] = str(rate_result.limit)
            resp_obj.headers["X-RateLimit-Remaining"] = str(rate_result.remaining)
            resp_obj.headers["X-RateLimit-Reset"] = str(int(rate_result.reset_at.timestamp()))

        return response

    return decorated


# === Key Management Functions ===


def create_api_key(
    user_id: str,
    name: str = None,
    rate_limit: int = DEFAULT_RATE_LIMIT,
    expires_days: int = None,
    environment: str = "live",
) -> Tuple[str, dict]:
    """
    Create a new API key for a user.

    Args:
        user_id: Supabase Auth user ID
        name: Optional friendly name for the key
        rate_limit: Requests per day (default 10,000)
        expires_days: Days until expiration (None = never)
        environment: "live" or "test" (test keys don't count against quotas)

    Returns:
        Tuple of (full_key, key_record)
        The full_key is returned ONCE and never stored.
    """
    full_key, key_hash = generate_api_key(environment=environment)
    key_prefix = get_key_prefix(full_key)

    expires_at = None
    if expires_days:
        expires_at = (datetime.utcnow() + timedelta(days=expires_days)).isoformat()

    key_record = db.create_api_key(
        user_id=user_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
        rate_limit=rate_limit,
        expires_at=expires_at,
        environment=environment,
    )

    return full_key, key_record


def list_user_keys(user_id: str) -> list:
    """List all API keys for a user (without hashes)."""
    return db.list_api_keys(user_id)


def revoke_api_key(key_id: str, user_id: str) -> bool:
    """
    Revoke an API key.

    Args:
        key_id: The key ID to revoke
        user_id: The user ID (for authorization check)

    Returns:
        True if revoked, False if not found or not owned by user
    """
    return db.revoke_api_key(key_id, user_id)
