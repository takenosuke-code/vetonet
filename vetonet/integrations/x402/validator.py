"""
x402 payment validation with VetoNet.

Validates x402 payments against locked user intents before settlement.
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional, Set

from vetonet import VetoNet
from vetonet.models import IntentAnchor
from vetonet.integrations.session import SessionStore, validate_intent

logger = logging.getLogger(__name__)


@dataclass
class PaymentValidation:
    """Result of a payment validation check."""
    approved: bool
    reason: str
    session_id: Optional[str] = None
    nonce: Optional[str] = None


class X402Validator:
    """
    Validates x402 payments against VetoNet intents.

    Security features:
    - Session-to-wallet binding
    - Payment nonce tracking (replay protection)
    - Intent locking during verification
    """

    def __init__(
        self,
        veto: Optional[VetoNet] = None,
        session_store: Optional[SessionStore] = None
    ):
        """
        Initialize x402 validator.

        Args:
            veto: VetoNet instance (created if not provided)
            session_store: Session store (created if not provided)
        """
        self.veto = veto or VetoNet(
            provider=os.environ.get("VETONET_PROVIDER", "groq"),
            api_key=os.environ.get("VETONET_API_KEY")
        )
        self.sessions = session_store or SessionStore()
        self._used_nonces: Set[str] = set()

    def register_intent(
        self,
        intent: str,
        wallet_address: Optional[str] = None
    ) -> dict:
        """
        Register user intent before agent shops.

        Args:
            intent: Natural language purchase intent
            wallet_address: Optional wallet address to bind session

        Returns:
            Dict with session_id and anchor details
        """
        try:
            intent = validate_intent(intent)
            anchor = self.veto.normalizer.normalize(intent)

            metadata = {}
            if wallet_address:
                metadata["wallet_address"] = wallet_address.lower()

            session_id = self.sessions.create(anchor, metadata=metadata)

            return {
                "status": "registered",
                "session_id": session_id,
                "anchor": {
                    "item_category": anchor.item_category,
                    "max_price": anchor.max_price,
                    "currency": anchor.currency,
                }
            }
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"register_intent failed: {e}")
            return {"error": "Failed to register intent"}

    def validate_payment(
        self,
        session_id: str,
        amount: float,
        merchant: str,
        description: str,
        currency: str = "USD",
        nonce: Optional[str] = None,
        wallet_address: Optional[str] = None
    ) -> PaymentValidation:
        """
        Validate a payment request against locked intent.

        Called when x402 payment is about to settle.

        Args:
            session_id: Session with locked intent
            amount: Payment amount
            merchant: Merchant/vendor name
            description: Item description
            currency: Currency code
            nonce: Payment nonce for replay protection
            wallet_address: Wallet making payment (for session binding)

        Returns:
            PaymentValidation result
        """
        # Replay protection
        if nonce:
            if nonce in self._used_nonces:
                return PaymentValidation(
                    approved=False,
                    reason="Payment nonce already used (replay detected)",
                    session_id=session_id,
                    nonce=nonce
                )

        # Get session
        session = self.sessions.get(session_id)
        if session is None:
            return PaymentValidation(
                approved=False,
                reason="No intent registered for this session",
                session_id=session_id
            )

        # Wallet binding check
        bound_wallet = session.metadata.get("wallet_address")
        if bound_wallet and wallet_address:
            if wallet_address.lower() != bound_wallet:
                return PaymentValidation(
                    approved=False,
                    reason="Wallet address does not match session",
                    session_id=session_id
                )

        # Lock session during verification
        session.lock()

        try:
            result = self.veto.verify(session.anchor, {
                "item_description": description,
                "unit_price": amount,
                "vendor": merchant,
                "currency": currency,
                "quantity": 1
            })

            # Mark nonce as used if approved
            if result.approved and nonce:
                self._used_nonces.add(nonce)

            return PaymentValidation(
                approved=result.approved,
                reason=result.reason,
                session_id=session_id,
                nonce=nonce
            )
        finally:
            session.unlock()

    def clear_session(self, session_id: str) -> bool:
        """Clear a session after transaction completes."""
        return self.sessions.delete(session_id)
