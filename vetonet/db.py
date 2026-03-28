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
) -> Optional[str]:
    """
    Log an attack attempt to Supabase.

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
    """Get attack statistics."""
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
        # Get all attacks
        result = client.table("attacks").select("verdict, feedback").execute()

        if not result.data:
            return {
                "total_attempts": 0,
                "blocked": 0,
                "bypassed": 0,
                "bypass_rate": 0,
                "feedback_count": 0,
            }

        total = len(result.data)
        blocked = sum(1 for r in result.data if r.get("verdict") == "blocked")
        bypassed = sum(1 for r in result.data if r.get("verdict") == "approved")
        feedback_count = sum(1 for r in result.data if r.get("feedback"))

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
    """Get attack vector statistics for leaderboard."""
    client = get_client()
    if not client:
        return []

    try:
        # Get all attacks with vectors
        result = client.table("attacks").select(
            "attack_vector, verdict"
        ).not_.is_("attack_vector", "null").execute()

        if not result.data:
            return []

        # Aggregate by vector
        stats = {}
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


def import_training_data(source: str, prompt: str, is_attack: bool, attack_type: str = None) -> bool:
    """Import a training data record (from Kaggle, etc.)."""
    client = get_client()
    if not client:
        return False

    try:
        client.table("training_data").insert({
            "source": source,
            "prompt": prompt,
            "is_attack": is_attack,
            "attack_type": attack_type,
        }).execute()
        return True

    except Exception as e:
        print(f"Supabase import_training_data error: {e}")
        return False


def get_training_data(source: str = None, limit: int = 10000) -> list:
    """Get training data for model training."""
    client = get_client()
    if not client:
        return []

    try:
        query = client.table("training_data").select("*")
        if source:
            query = query.eq("source", source)
        result = query.limit(limit).execute()

        return result.data or []

    except Exception as e:
        print(f"Supabase get_training_data error: {e}")
        return []
