"""
Supabase client wrapper for VetoNet.

Handles all database operations with Supabase.
Falls back gracefully if Supabase is not configured.
"""

import os
import json
from datetime import datetime
from typing import Optional
from supabase import create_client, Client


_client: Optional[Client] = None


def get_client() -> Optional[Client]:
    """Get or create the Supabase client."""
    global _client

    if _client is not None:
        return _client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        return None

    try:
        _client = create_client(url, key)
        return _client
    except Exception as e:
        print(f"Supabase connection failed: {e}")
        return None


def log_attack(
    type: str,
    prompt: str,
    intent: dict = None,
    payload: dict = None,
    verdict: str = None,
    blocked_by: str = None,
    checks: list = None,
    confidence: float = None,
    reasoning: str = None,
    attack_vector: str = None,
    source: str = None,
) -> Optional[str]:
    """
    Log an attack attempt to Supabase.

    Args:
        type: Type of attempt (demo, redteam, api_check, fuzzer)
        source: Where the attempt came from (playground, api, fuzzer, sdk)
        intent: Full IntentAnchor dict (use intent.model_dump())
        payload: Full AgentPayload dict (use payload.model_dump())
        blocked_by: Which check blocked it (if blocked)

    Returns the attack ID if successful, None otherwise.
    """
    client = get_client()
    if not client:
        return None

    try:
        data = {
            "type": type,
            "prompt": prompt[:1000] if prompt else None,  # Truncate long prompts
            "intent": intent,
            "payload": payload,
            "verdict": verdict,
            "blocked_by": blocked_by,
            "checks": checks,
            "confidence": confidence,
            "reasoning": reasoning[:500] if reasoning else None,  # Truncate reasoning
            "attack_vector": attack_vector,
            "source": source,
        }

        result = client.table("attacks").insert(data).execute()

        if result.data and len(result.data) > 0:
            return result.data[0].get("id")
        return None

    except Exception as e:
        print(f"Supabase log_attack error: {e}")
        return None


def submit_feedback(attack_id: str, feedback: str) -> bool:
    """
    Submit user feedback for an attack verdict.

    Args:
        attack_id: UUID of the attack
        feedback: One of 'correct', 'false_positive', 'false_negative'

    Returns:
        True if successful, False otherwise
    """
    client = get_client()
    if not client:
        return False

    if feedback not in ('correct', 'false_positive', 'false_negative'):
        return False

    try:
        result = client.table("attacks").update({
            "feedback": feedback,
            "feedback_at": datetime.utcnow().isoformat(),
        }).eq("id", attack_id).execute()

        return result.data is not None and len(result.data) > 0

    except Exception as e:
        print(f"Supabase submit_feedback error: {e}")
        return False


def get_stats() -> dict:
    """Get attack statistics using count queries (no 1000 row limit)."""
    client = get_client()
    if not client:
        return {
            "total_attempts": 0,
            "blocked": 0,
            "bypassed": 0,
            "bypass_rate": 0,
            "feedback_count": 0,
        }

    try:
        # Use count queries to avoid 1000 row limit
        total_result = client.table("attacks").select("id", count="exact").execute()
        blocked_result = client.table("attacks").select("id", count="exact").eq("verdict", "blocked").execute()
        bypassed_result = client.table("attacks").select("id", count="exact").eq("verdict", "approved").execute()
        feedback_result = client.table("attacks").select("id", count="exact").not_.is_("feedback", "null").execute()

        total = total_result.count or 0
        blocked = blocked_result.count or 0
        bypassed = bypassed_result.count or 0
        feedback_count = feedback_result.count or 0

        return {
            "total_attempts": total,
            "blocked": blocked,
            "bypassed": bypassed,
            "bypass_rate": round(bypassed / max(total, 1) * 100, 2),
            "feedback_count": feedback_count,
        }

    except Exception as e:
        print(f"Supabase get_stats error: {e}")
        return {
            "total_attempts": 0,
            "blocked": 0,
            "bypassed": 0,
            "bypass_rate": 0,
            "feedback_count": 0,
        }


def get_vector_stats() -> list:
    """Get attack vector statistics for leaderboard using pagination."""
    client = get_client()
    if not client:
        return []

    try:
        # Paginate to get ALL attacks (bypass 1000 row limit)
        stats = {}
        page_size = 1000
        offset = 0

        while True:
            result = client.table("attacks").select(
                "attack_vector, verdict"
            ).not_.is_("attack_vector", "null").range(offset, offset + page_size - 1).execute()

            if not result.data:
                break

            for attack in result.data:
                vector = attack.get("attack_vector")
                if not vector:
                    continue

                if vector not in stats:
                    stats[vector] = {"total": 0, "blocked": 0, "bypassed": 0}

                stats[vector]["total"] += 1
                if attack.get("verdict") == "approved":
                    stats[vector]["bypassed"] += 1
                else:
                    stats[vector]["blocked"] += 1

            # If we got fewer than page_size, we've reached the end
            if len(result.data) < page_size:
                break
            offset += page_size

        # Convert to list and sort by total
        vectors = [
            {"vector": k, **v}
            for k, v in sorted(stats.items(), key=lambda x: x[1]["total"], reverse=True)
        ][:10]

        return vectors

    except Exception as e:
        print(f"Supabase get_vector_stats error: {e}")
        return []


def get_recent_attacks(limit: int = 20) -> list:
    """Get recent attacks for the feed."""
    client = get_client()
    if not client:
        return []

    try:
        result = client.table("attacks").select(
            "id, created_at, prompt, verdict, blocked_by, attack_vector, payload, confidence"
        ).order("created_at", desc=True).limit(limit).execute()

        return result.data or []

    except Exception as e:
        print(f"Supabase get_recent_attacks error: {e}")
        return []


def get_attacks_for_export(limit: int = 1000) -> list:
    """Get attacks for CSV export."""
    client = get_client()
    if not client:
        return []

    try:
        result = client.table("attacks").select("*").order(
            "created_at", desc=True
        ).limit(limit).execute()

        return result.data or []

    except Exception as e:
        print(f"Supabase get_attacks_for_export error: {e}")
        return []


# ============== ML Training Data ==============

def add_training_data(
    prompt: str,
    intent: dict,
    payload: dict,
    is_attack: bool,
    source: str = "synthetic",
    attack_vector: str = None,
    blocked_by: str = None,
    confidence: float = None,
) -> bool:
    """
    Add a training data record to ml_training_data.

    Use for synthetic data generation or manual additions.
    Real attack data is auto-copied via database trigger.
    """
    client = get_client()
    if not client:
        return False

    try:
        import hashlib
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

        client.table("ml_training_data").insert({
            "source": source,
            "prompt": prompt,
            "intent": intent,
            "payload": payload,
            "is_attack": is_attack,
            "attack_vector": attack_vector,
            "blocked_by": blocked_by,
            "confidence": confidence,
            "human_verified": source == "synthetic",  # Synthetic data is "verified" by design
            "prompt_hash": prompt_hash,
        }).execute()
        return True

    except Exception as e:
        print(f"Supabase add_training_data error: {e}")
        return False


def get_ml_training_data(
    is_attack: bool = None,
    verified_only: bool = False,
    attack_vector: str = None,
    limit: int = 10000,
) -> list:
    """
    Get ML training data for model training.

    Args:
        is_attack: Filter by attack (True) or legitimate (False)
        verified_only: Only return human-verified records
        attack_vector: Filter by specific attack vector
        limit: Max records to return
    """
    client = get_client()
    if not client:
        return []

    try:
        query = client.table("ml_training_data").select(
            "prompt, intent, payload, is_attack, attack_vector, blocked_by, confidence"
        )

        if is_attack is not None:
            query = query.eq("is_attack", is_attack)
        if verified_only:
            query = query.eq("human_verified", True)
        if attack_vector:
            query = query.eq("attack_vector", attack_vector)

        result = query.limit(limit).execute()
        return result.data or []

    except Exception as e:
        print(f"Supabase get_ml_training_data error: {e}")
        return []


def get_training_stats() -> dict:
    """Get ML training data statistics."""
    client = get_client()
    if not client:
        return {}

    try:
        total = client.table("ml_training_data").select("id", count="exact").execute()
        attacks = client.table("ml_training_data").select("id", count="exact").eq("is_attack", True).execute()
        legitimate = client.table("ml_training_data").select("id", count="exact").eq("is_attack", False).execute()
        verified = client.table("ml_training_data").select("id", count="exact").eq("human_verified", True).execute()

        return {
            "total": total.count or 0,
            "attacks": attacks.count or 0,
            "legitimate": legitimate.count or 0,
            "verified": verified.count or 0,
        }

    except Exception as e:
        print(f"Supabase get_training_stats error: {e}")
        return {}


def mark_as_verified(training_id: str, feedback: str = "correct") -> bool:
    """Mark a training record as human-verified."""
    client = get_client()
    if not client:
        return False

    try:
        client.table("ml_training_data").update({
            "human_verified": True,
            "feedback": feedback,
        }).eq("id", training_id).execute()
        return True

    except Exception as e:
        print(f"Supabase mark_as_verified error: {e}")
        return False


# ============== API Key Management ==============

def create_api_key(
    user_id: str,
    key_hash: str,
    key_prefix: str,
    name: str = None,
    rate_limit: int = 10000,
    expires_at: str = None,
    environment: str = "live",
) -> Optional[dict]:
    """
    Create a new API key record.

    Args:
        user_id: Supabase Auth user ID
        key_hash: SHA256 hash of the actual key
        key_prefix: First 12 chars for identification
        name: Friendly name for the key
        rate_limit: Requests per day (default 10,000)
        expires_at: ISO timestamp for expiration
        environment: "live" or "test"

    Returns:
        The created key record (without hash), or None on error
    """
    client = get_client()
    if not client:
        return None

    try:
        data = {
            "user_id": user_id,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "name": name,
            "rate_limit": rate_limit,
            "is_active": True,
            "environment": environment,
        }

        if expires_at:
            data["expires_at"] = expires_at

        result = client.table("api_keys").insert(data).execute()

        if result.data and len(result.data) > 0:
            # Remove hash from response
            record = result.data[0].copy()
            record.pop("key_hash", None)
            return record
        return None

    except Exception as e:
        print(f"Supabase create_api_key error: {e}")
        return None


def get_api_key_by_hash(key_hash: str) -> Optional[dict]:
    """
    Look up an API key by its hash.

    Used for validating incoming requests.

    Returns:
        Key record if found and active, None otherwise
    """
    client = get_client()
    if not client:
        return None

    try:
        result = client.table("api_keys").select(
            "id, user_id, key_prefix, name, rate_limit, created_at, last_used_at, expires_at, is_active"
        ).eq("key_hash", key_hash).execute()

        if result.data and len(result.data) > 0:
            return result.data[0]
        return None

    except Exception as e:
        print(f"Supabase get_api_key_by_hash error: {e}")
        return None


def update_key_last_used(key_id: str) -> bool:
    """Update the last_used_at timestamp for a key."""
    client = get_client()
    if not client:
        return False

    try:
        client.table("api_keys").update({
            "last_used_at": datetime.utcnow().isoformat(),
        }).eq("id", key_id).execute()
        return True

    except Exception as e:
        print(f"Supabase update_key_last_used error: {e}")
        return False


def list_api_keys(user_id: str) -> list:
    """
    List all API keys for a user.

    Returns keys without the hash (for security).
    """
    client = get_client()
    if not client:
        return []

    try:
        result = client.table("api_keys").select(
            "id, key_prefix, name, rate_limit, created_at, last_used_at, expires_at, is_active"
        ).eq("user_id", user_id).order("created_at", desc=True).execute()

        return result.data or []

    except Exception as e:
        print(f"Supabase list_api_keys error: {e}")
        return []


def revoke_api_key(key_id: str, user_id: str) -> bool:
    """
    Revoke (deactivate) an API key.

    Only the owner can revoke their key.
    """
    client = get_client()
    if not client:
        return False

    try:
        result = client.table("api_keys").update({
            "is_active": False,
        }).eq("id", key_id).eq("user_id", user_id).execute()

        return result.data is not None and len(result.data) > 0

    except Exception as e:
        print(f"Supabase revoke_api_key error: {e}")
        return False


def log_api_usage(key_id: str, endpoint: str, status: int, latency_ms: int) -> bool:
    """Log an API request for analytics."""
    client = get_client()
    if not client:
        return False

    try:
        client.table("api_usage").insert({
            "key_id": key_id,
            "endpoint": endpoint,
            "response_status": status,
            "latency_ms": latency_ms,
        }).execute()
        return True

    except Exception as e:
        print(f"Supabase log_api_usage error: {e}")
        return False


def get_key_usage_stats(key_id: str, days: int = 30) -> dict:
    """Get usage statistics for an API key."""
    client = get_client()
    if not client:
        return {"total_requests": 0, "avg_latency_ms": 0}

    try:
        # Get recent usage
        result = client.table("api_usage").select(
            "response_status, latency_ms"
        ).eq("key_id", key_id).execute()

        if not result.data:
            return {"total_requests": 0, "avg_latency_ms": 0}

        total = len(result.data)
        avg_latency = sum(r.get("latency_ms", 0) for r in result.data) / max(total, 1)
        success = sum(1 for r in result.data if 200 <= r.get("response_status", 0) < 300)

        return {
            "total_requests": total,
            "avg_latency_ms": round(avg_latency, 2),
            "success_rate": round(success / max(total, 1) * 100, 2),
        }

    except Exception as e:
        print(f"Supabase get_key_usage_stats error: {e}")
        return {"total_requests": 0, "avg_latency_ms": 0}


# ============== Security Audit Logging ==============

def log_key_audit(
    key_id: str,
    action: str,
    reason: str = None,
    ip_address: str = None,
    user_agent: str = None,
) -> bool:
    """
    Log security-relevant API key operations.

    Actions: created, deleted, rotated, used, failed_auth, rate_limited
    """
    client = get_client()
    if not client:
        return False

    try:
        client.table("api_key_audit").insert({
            "key_id": key_id,
            "action": action,
            "reason": reason,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }).execute()
        return True

    except Exception as e:
        # Don't fail silently on audit - this is security-critical
        print(f"SECURITY WARNING: Audit log failed: {e}")
        return False


def get_failed_auth_count(key_id: str, minutes: int = 5) -> int:
    """
    Count failed auth attempts for a key in recent time window.

    Used to detect brute-force attacks.
    """
    client = get_client()
    if not client:
        return 0

    try:
        # Count failed_auth events in last N minutes
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()

        result = client.table("api_key_audit").select(
            "id", count="exact"
        ).eq("key_id", key_id).eq("action", "failed_auth").gte(
            "created_at", cutoff
        ).execute()

        return result.count if result.count else 0

    except Exception as e:
        print(f"Supabase get_failed_auth_count error: {e}")
        return 0
