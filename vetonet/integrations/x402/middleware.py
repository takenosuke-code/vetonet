"""
x402 + VetoNet middleware.

Intercepts x402 payment flows and verifies transactions against user intent
before allowing payment settlement.

Supports both Flask and FastAPI frameworks.
"""

import os
import logging
from typing import Optional, Callable

from vetonet import VetoNet
from vetonet.integrations.x402.validator import X402Validator, PaymentValidation

logger = logging.getLogger(__name__)

# x402 header names
X402_PAYMENT_HEADER = "X-Payment"
X402_PAYMENT_SIGNATURE = "X-Payment-Signature"
VETONET_SESSION_HEADER = "X-VetoNet-Session"
VETONET_WALLET_HEADER = "X-VetoNet-Wallet"


class VetoNetX402Middleware:
    """
    Middleware that combines x402 payments with VetoNet verification.

    Flow:
    1. User locks intent via lock_intent endpoint
    2. Agent shops and finds items
    3. x402 returns 402 Payment Required
    4. Agent signs payment with X-VetoNet-Session header
    5. VetoNet intercepts and verifies intent match
    6. If approved, payment settles. If not, 403 Forbidden.

    Usage with Flask:
        from flask import Flask
        from vetonet.integrations.x402 import VetoNetX402Middleware

        app = Flask(__name__)
        x402_middleware = VetoNetX402Middleware()

        @app.before_request
        def verify_payment():
            return x402_middleware.flask_before_request()

        @app.route("/lock-intent", methods=["POST"])
        def lock_intent():
            data = request.json
            return x402_middleware.lock_intent(
                data["intent"],
                wallet_address=data.get("wallet_address")
            )
    """

    def __init__(
        self,
        veto: Optional[VetoNet] = None,
        validator: Optional[X402Validator] = None
    ):
        """
        Initialize x402 middleware.

        Args:
            veto: VetoNet instance (created if not provided)
            validator: X402Validator instance (created if not provided)
        """
        self.veto = veto or VetoNet(
            provider=os.environ.get("VETONET_PROVIDER", "groq"),
            api_key=os.environ.get("VETONET_API_KEY")
        )
        self.validator = validator or X402Validator(veto=self.veto)

    def lock_intent(
        self,
        intent: str,
        wallet_address: Optional[str] = None
    ) -> dict:
        """
        Lock intent before agent starts shopping.

        Args:
            intent: Natural language purchase intent
            wallet_address: Optional wallet address to bind session

        Returns:
            Dict with session_id and anchor details
        """
        return self.validator.register_intent(intent, wallet_address)

    def verify_payment(
        self,
        session_id: str,
        payment_details: dict,
        wallet_address: Optional[str] = None
    ) -> PaymentValidation:
        """
        Verify a payment against locked intent.

        Args:
            session_id: Session ID from lock_intent
            payment_details: Payment details dict with:
                - amount: Payment amount
                - merchant: Merchant name
                - description: Item description
                - currency: Currency code (default: USD)
                - nonce: Optional payment nonce
            wallet_address: Optional wallet making payment

        Returns:
            PaymentValidation result
        """
        return self.validator.validate_payment(
            session_id=session_id,
            amount=float(payment_details.get("amount", 0)),
            merchant=payment_details.get("merchant", ""),
            description=payment_details.get("description", ""),
            currency=payment_details.get("currency", "USD"),
            nonce=payment_details.get("nonce"),
            wallet_address=wallet_address
        )

    def clear_intent(self, session_id: str) -> dict:
        """Clear a session after transaction completes."""
        if self.validator.clear_session(session_id):
            return {"status": "cleared"}
        return {"status": "not_found"}

    # Flask integration

    def flask_before_request(self):
        """
        Flask before_request handler for x402 payment verification.

        Usage:
            @app.before_request
            def verify_payment():
                return x402_middleware.flask_before_request()

        Returns:
            None if no payment header or payment approved.
            403 response if payment blocked.
        """
        try:
            from flask import request, jsonify
        except ImportError:
            logger.error("Flask not installed")
            return None

        # Check if this is a payment request
        if X402_PAYMENT_SIGNATURE not in request.headers:
            return None

        session_id = request.headers.get(VETONET_SESSION_HEADER)
        if not session_id:
            return jsonify({"error": "Missing X-VetoNet-Session header"}), 403

        wallet_address = request.headers.get(VETONET_WALLET_HEADER)

        # Parse payment details from x402 headers/body
        # This is a simplified example - real implementation would
        # decode the actual x402 payment payload
        payment_details = {
            "amount": request.headers.get("X-Payment-Amount", 0),
            "merchant": request.headers.get("X-Payment-Merchant", ""),
            "description": request.headers.get("X-Payment-Description", ""),
            "nonce": request.headers.get("X-Payment-Nonce"),
        }

        result = self.verify_payment(session_id, payment_details, wallet_address)

        if not result.approved:
            return jsonify({
                "error": "Payment blocked by VetoNet",
                "reason": result.reason
            }), 403

        return None

    # FastAPI integration

    def fastapi_middleware(self, app):
        """
        Add VetoNet verification as FastAPI middleware.

        Usage:
            from fastapi import FastAPI
            from vetonet.integrations.x402 import VetoNetX402Middleware

            app = FastAPI()
            x402_middleware = VetoNetX402Middleware()
            x402_middleware.fastapi_middleware(app)
        """
        try:
            from fastapi import Request
            from fastapi.responses import JSONResponse
        except ImportError:
            logger.error("FastAPI not installed")
            return

        @app.middleware("http")
        async def vetonet_x402_check(request: Request, call_next):
            # Check if this is a payment request
            if X402_PAYMENT_SIGNATURE not in request.headers:
                return await call_next(request)

            session_id = request.headers.get(VETONET_SESSION_HEADER)
            if not session_id:
                return JSONResponse(
                    status_code=403,
                    content={"error": "Missing X-VetoNet-Session header"}
                )

            wallet_address = request.headers.get(VETONET_WALLET_HEADER)

            # Parse payment details
            payment_details = {
                "amount": request.headers.get("X-Payment-Amount", 0),
                "merchant": request.headers.get("X-Payment-Merchant", ""),
                "description": request.headers.get("X-Payment-Description", ""),
                "nonce": request.headers.get("X-Payment-Nonce"),
            }

            result = self.verify_payment(session_id, payment_details, wallet_address)

            if not result.approved:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Payment blocked by VetoNet",
                        "reason": result.reason
                    }
                )

            return await call_next(request)
