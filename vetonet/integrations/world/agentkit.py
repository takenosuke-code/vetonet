"""
World AgentKit + VetoNet integration.

Combines proof-of-human (World ID) with intent verification (VetoNet)
for maximum trust in AI agent transactions.
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from vetonet import VetoNet
from vetonet.models import VetoResult
from vetonet.integrations.session import SessionStore, validate_intent
from vetonet.integrations.world.verify import (
    WorldIDVerifier,
    WorldIDVerification,
    verify_world_id_sync
)

logger = logging.getLogger(__name__)


@dataclass
class HumanVerifiedTransaction:
    """Result of a human-verified transaction check."""
    approved: bool
    human_verified: bool
    intent_verified: bool
    nullifier_hash: Optional[str]  # Unique human identifier
    reason: str
    veto_result: Optional[VetoResult] = None


class WorldVetoNet:
    """
    VetoNet with World ID proof-of-human verification.

    Ensures:
    1. A real human authorized this agent (World ID)
    2. The transaction matches the human's intent (VetoNet)

    Security features:
    - Orb-level verification for high-value transactions
    - Nullifier tracking per action
    - Rate limiting per human (nullifier)
    - Session binding to verified human

    Usage:
        wv = WorldVetoNet(world_app_id="app_xxx")

        # User provides World ID proof when locking intent
        result = wv.lock_intent_with_proof(
            intent="Buy $50 Amazon gift card",
            world_proof={...}  # From World ID widget
        )

        if result["status"] == "locked":
            session_id = result["session_id"]

            # Agent shops and finds a deal
            verification = wv.verify_transaction(
                session_id=session_id,
                payload={
                    "item_description": "Amazon $50 Gift Card",
                    "unit_price": 50.00,
                    "vendor": "amazon.com"
                }
            )

            if verification.approved:
                # Safe to execute - verified human + verified intent
                execute_purchase()
    """

    def __init__(
        self,
        world_app_id: Optional[str] = None,
        veto_provider: str = "groq",
        veto_api_key: Optional[str] = None,
        require_orb_above: float = 100.0  # Require orb for transactions > $100
    ):
        """
        Initialize WorldVetoNet.

        Args:
            world_app_id: World App ID (or set WORLD_APP_ID env var)
            veto_provider: VetoNet LLM provider
            veto_api_key: VetoNet API key
            require_orb_above: Require orb verification for amounts above this
        """
        self.world_app_id = world_app_id or os.environ.get("WORLD_APP_ID")
        self.require_orb_above = require_orb_above

        self.veto = VetoNet(
            provider=veto_provider,
            api_key=veto_api_key or os.environ.get("VETONET_API_KEY")
        )

        self.world_verifier = WorldIDVerifier(app_id=self.world_app_id)
        self.sessions = SessionStore()

        # Rate limiting per human (nullifier)
        self._human_usage: Dict[str, Dict[str, Any]] = {}

    def lock_intent_with_proof(
        self,
        intent: str,
        world_proof: dict
    ) -> dict:
        """
        Lock intent with World ID proof-of-human.

        Args:
            intent: User's purchase intent
            world_proof: World ID proof from widget

        Returns:
            Dict with session_id and status, or error
        """
        try:
            intent = validate_intent(intent)

            # Verify World ID
            world_result = verify_world_id_sync(
                app_id=self.world_app_id,
                proof=world_proof,
                action=f"vetonet_lock"
            )

            if not world_result.verified:
                return {
                    "status": "error",
                    "error": "World ID verification failed",
                    "details": world_result.error
                }

            # Normalize intent with VetoNet
            anchor = self.veto.normalizer.normalize(intent)

            # Check rate limits for this human
            nullifier = world_result.nullifier_hash
            if not self._check_rate_limit(nullifier):
                return {
                    "status": "error",
                    "error": "Rate limit exceeded for this human"
                }

            # Create session with human verification metadata
            session_id = self.sessions.create(
                anchor=anchor,
                metadata={
                    "nullifier_hash": nullifier,
                    "human_verified": True,
                    "verification_level": world_result.verification_level
                }
            )

            return {
                "status": "locked",
                "session_id": session_id,
                "human_verified": True,
                "anchor": {
                    "item_category": anchor.item_category,
                    "max_price": anchor.max_price,
                    "currency": anchor.currency,
                }
            }

        except ValueError as e:
            return {"status": "error", "error": str(e)}
        except Exception as e:
            logger.error(f"lock_intent_with_proof failed: {e}")
            return {"status": "error", "error": "Failed to lock intent"}

    def verify_transaction(
        self,
        session_id: str,
        payload: dict
    ) -> HumanVerifiedTransaction:
        """
        Verify transaction with human + intent verification.

        Args:
            session_id: Session with locked intent
            payload: Agent's proposed transaction dict

        Returns:
            HumanVerifiedTransaction result
        """
        session = self.sessions.get(session_id)
        if session is None:
            return HumanVerifiedTransaction(
                approved=False,
                human_verified=False,
                intent_verified=False,
                nullifier_hash=None,
                reason="No intent locked for this session"
            )

        # Check if high-value transaction requires orb verification
        amount = float(payload.get("unit_price", 0)) * int(payload.get("quantity", 1))
        if amount > self.require_orb_above:
            if session.metadata.get("verification_level") != "orb":
                return HumanVerifiedTransaction(
                    approved=False,
                    human_verified=False,
                    intent_verified=False,
                    nullifier_hash=session.metadata.get("nullifier_hash"),
                    reason=f"Orb verification required for transactions over ${self.require_orb_above}"
                )

        # Verify intent with VetoNet
        veto_result = self.veto.verify(session.anchor, payload)

        # Update usage tracking
        nullifier = session.metadata.get("nullifier_hash")
        if veto_result.approved and nullifier:
            self._record_usage(nullifier, amount)

        return HumanVerifiedTransaction(
            approved=veto_result.approved and session.metadata.get("human_verified", False),
            human_verified=session.metadata.get("human_verified", False),
            intent_verified=veto_result.approved,
            nullifier_hash=nullifier,
            reason=veto_result.reason,
            veto_result=veto_result
        )

    def get_human_limits(self, nullifier_hash: str) -> dict:
        """
        Get rate limits and usage for a verified human.

        Args:
            nullifier_hash: Unique human identifier

        Returns:
            Dict with current usage and limits
        """
        usage = self._human_usage.get(nullifier_hash, {
            "daily_transactions": 0,
            "daily_spend": 0.0
        })

        return {
            "nullifier_hash": nullifier_hash,
            "daily_transactions": usage.get("daily_transactions", 0),
            "daily_limit": 10,
            "daily_spend": usage.get("daily_spend", 0.0),
            "daily_spend_limit": 1000.0,
            "remaining_transactions": max(0, 10 - usage.get("daily_transactions", 0)),
            "remaining_spend": max(0, 1000.0 - usage.get("daily_spend", 0.0))
        }

    def _check_rate_limit(self, nullifier: str) -> bool:
        """Check if human is within rate limits."""
        limits = self.get_human_limits(nullifier)
        return (
            limits["remaining_transactions"] > 0 and
            limits["remaining_spend"] > 0
        )

    def _record_usage(self, nullifier: str, amount: float):
        """Record a transaction for rate limiting."""
        if nullifier not in self._human_usage:
            self._human_usage[nullifier] = {
                "daily_transactions": 0,
                "daily_spend": 0.0
            }

        self._human_usage[nullifier]["daily_transactions"] += 1
        self._human_usage[nullifier]["daily_spend"] += amount

    def clear_session(self, session_id: str) -> bool:
        """Clear a session after transaction completes."""
        return self.sessions.delete(session_id)
