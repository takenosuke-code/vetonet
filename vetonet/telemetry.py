"""
VetoNet Anonymous Telemetry

Collects anonymized attack patterns from SDK users to improve the classifier.
All data is hashed/anonymized before logging - no PII, no raw intents.

Privacy:
- Opt-in by default (telemetry=False unless explicitly enabled)
- Intent strings are hashed (SHA-256, truncated)
- Only patterns collected: category, price range, pass/fail, check names
- No vendor names, no item descriptions, no API keys
"""

import hashlib
import logging
import os
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Telemetry endpoint (VetoNet API on Railway)
TELEMETRY_URL = os.environ.get(
    "VETONET_TELEMETRY_URL",
    "https://web-production-fec907.up.railway.app/api/telemetry"
)


@dataclass
class TelemetryEvent:
    """Anonymized telemetry event."""
    intent_hash: str
    category: str
    price_bucket: str  # "0-50", "50-100", "100-500", "500+"
    approved: bool
    checks_failed: List[str]
    classifier_score: Optional[float]
    source: str  # "sdk_telemetry"


def _hash_intent(category: str, max_price: float) -> str:
    """Create irreversible hash of intent."""
    raw = f"{category}:{max_price}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _price_bucket(price: float) -> str:
    """Convert price to anonymous bucket."""
    if price <= 50:
        return "0-50"
    elif price <= 100:
        return "50-100"
    elif price <= 500:
        return "100-500"
    else:
        return "500+"


def log_telemetry(
    anchor,
    payload,
    result,
    source: str = "sdk_telemetry"
) -> bool:
    """
    Log anonymized verification result.

    Args:
        anchor: IntentAnchor (normalized intent)
        payload: AgentPayload (transaction)
        result: VetoResult (verification result)
        source: Where the event came from

    Returns:
        True if logged successfully, False otherwise
    """
    try:
        # Build anonymized event
        event = TelemetryEvent(
            intent_hash=_hash_intent(anchor.item_category, anchor.max_price),
            category=anchor.item_category,
            price_bucket=_price_bucket(payload.unit_price),
            approved=result.approved,
            checks_failed=[c.name for c in result.checks if not c.passed],
            classifier_score=next(
                (c.score for c in result.checks if c.name == "classifier"),
                None
            ),
            source=source
        )

        # Try Supabase first (if configured locally)
        if _log_to_supabase(event):
            return True

        # Try remote API
        if _log_to_api(event):
            return True

        logger.debug("Telemetry: No backend available")
        return False

    except Exception as e:
        logger.debug(f"Telemetry error: {e}")
        return False


def _log_to_supabase(event: TelemetryEvent) -> bool:
    """Log to local Supabase if configured."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        return False

    try:
        from supabase import create_client
        client = create_client(url, key)

        client.table("telemetry").insert({
            "intent_hash": event.intent_hash,
            "category": event.category,
            "price_bucket": event.price_bucket,
            "approved": event.approved,
            "checks_failed": event.checks_failed,
            "classifier_score": event.classifier_score,
            "source": event.source
        }).execute()

        return True
    except Exception as e:
        logger.debug(f"Supabase telemetry error: {e}")
        return False


def _log_to_api(event: TelemetryEvent) -> bool:
    """Log to VetoNet API."""
    try:
        import requests

        response = requests.post(
            TELEMETRY_URL,
            json={
                "intent_hash": event.intent_hash,
                "category": event.category,
                "price_bucket": event.price_bucket,
                "approved": event.approved,
                "checks_failed": event.checks_failed,
                "classifier_score": event.classifier_score,
                "source": event.source
            },
            timeout=2.0  # Don't block on telemetry
        )

        return response.status_code == 200
    except Exception as e:
        logger.debug(f"API telemetry error: {e}")
        return False


# Convenience for checking if telemetry is possible
def is_telemetry_available() -> bool:
    """Check if telemetry backend is configured."""
    return bool(
        os.environ.get("SUPABASE_URL") or
        os.environ.get("VETONET_TELEMETRY_URL")
    )
