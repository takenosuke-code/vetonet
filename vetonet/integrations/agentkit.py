"""
VetoNet integration with Coinbase AgentKit.

Provides a policy provider that uses VetoNet to verify agent transactions
before execution, preventing intent drift and prompt injection attacks.

Usage:
    from vetonet.integrations.agentkit import VetoNetPolicyProvider

    # Create the policy provider
    policy = VetoNetPolicyProvider(provider="groq", api_key="your-api-key")

    # Lock user intent at the start of a session
    policy.lock_intent("session-123", "Buy a $50 Amazon gift card")

    # Later, verify transactions before execution
    result = policy.verify_transaction(
        session_id="session-123",
        item_description="Amazon Gift Card - $50",
        amount=50.00,
        vendor="amazon.com"
    )

    if result["approved"]:
        # Proceed with transaction
        pass
    else:
        # Block transaction, show reason
        print(result["reason"])
"""

from typing import Any, Optional

# Handle optional coinbase_agentkit dependency
try:
    from coinbase_agentkit import create_action
    HAS_AGENTKIT = True
except ImportError:
    HAS_AGENTKIT = False
    # Create a no-op decorator when agentkit is not installed
    def create_action(name: str = "", description: str = ""):
        def decorator(func):
            return func
        return decorator

from vetonet import VetoNet, IntentAnchor, AgentPayload


class VetoNetPolicyProvider:
    """
    Policy provider for Coinbase AgentKit that uses VetoNet
    to verify agent transactions against locked user intent.

    This prevents AI agents from executing unauthorized transactions
    due to prompt injection or intent drift attacks.

    Attributes:
        veto: The VetoNet instance used for verification
        intents: Dictionary mapping session IDs to locked IntentAnchors
    """

    def __init__(
        self,
        provider: str = "groq",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the VetoNet policy provider.

        Args:
            provider: LLM provider for semantic checks
                      ("ollama", "groq", "anthropic", "openai", "none")
            api_key: API key for the LLM provider (required for hosted providers)
            model: Override the default model for the provider
            **kwargs: Additional configuration options passed to VetoNet
        """
        self.veto = VetoNet(
            provider=provider,
            api_key=api_key,
            model=model,
            **kwargs
        )
        self.intents: dict[str, IntentAnchor] = {}

    @create_action(
        name="lock_intent",
        description="Lock the user's purchase intent at the start of a shopping session. "
                    "This creates an immutable record of what the user wants to buy."
    )
    def lock_intent(
        self,
        session_id: str,
        user_request: str,
    ) -> dict[str, Any]:
        """
        Lock the user's intent for a session.

        Parses the natural language request and creates a structured
        IntentAnchor that will be used to verify all subsequent transactions.

        Args:
            session_id: Unique identifier for the shopping session
            user_request: Natural language description of what user wants to buy
                         (e.g., "Buy a $50 Amazon gift card")

        Returns:
            dict with:
                - success: bool indicating if intent was locked
                - intent: dict representation of the parsed intent
                - message: Human-readable status message
        """
        if self.veto.normalizer is None:
            return {
                "success": False,
                "intent": None,
                "message": "Cannot parse intent: LLM provider is set to 'none'. "
                          "Use a provider like 'groq' or 'ollama' for intent parsing."
            }

        try:
            # Parse natural language into structured intent
            intent = self.veto.normalizer.normalize(user_request)
            self.intents[session_id] = intent

            return {
                "success": True,
                "intent": intent.model_dump(),
                "message": f"Intent locked: {intent.item_category} up to "
                          f"{intent.currency} {intent.max_price}"
            }
        except Exception as e:
            return {
                "success": False,
                "intent": None,
                "message": f"Failed to parse intent: {str(e)}"
            }

    @create_action(
        name="verify_transaction",
        description="Verify a proposed transaction against the user's locked intent. "
                    "Returns approval status and reason. Must be called before executing "
                    "any purchase transaction."
    )
    def verify_transaction(
        self,
        session_id: str,
        item_description: str,
        amount: float,
        vendor: str = "unknown",
        quantity: int = 1,
        fees: Optional[list[dict[str, Any]]] = None,
        currency: str = "USD",
        is_recurring: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Verify a transaction against the locked intent.

        Runs VetoNet's checks (price bounds, category match, semantic alignment)
        to determine if the proposed transaction matches the user's original intent.

        Args:
            session_id: Session ID that was used to lock the intent
            item_description: Description of item being purchased
            amount: Total transaction amount (unit_price * quantity)
            vendor: Merchant/vendor domain or name
            quantity: Number of items being purchased
            fees: List of fee dicts with 'name' and 'amount' keys
            currency: Currency code (USD, EUR, etc.)
            is_recurring: Whether this is a subscription/recurring charge
            metadata: Additional transaction metadata

        Returns:
            dict with:
                - approved: bool indicating if transaction is approved
                - reason: Human-readable explanation of the decision
                - checks: List of individual check results
                - status: "APPROVED" or "VETO"
        """
        # Check if intent exists for this session
        if session_id not in self.intents:
            return {
                "approved": False,
                "reason": f"No locked intent found for session '{session_id}'. "
                         "Call lock_intent() first.",
                "checks": [],
                "status": "VETO"
            }

        intent = self.intents[session_id]

        # Calculate unit price from total amount
        unit_price = amount / quantity if quantity > 0 else amount

        # Build the agent payload
        payload = AgentPayload(
            item_description=item_description,
            item_category=intent.item_category,  # Use intent's category
            unit_price=unit_price,
            quantity=quantity,
            fees=fees or [],
            currency=currency,
            is_recurring=is_recurring,
            vendor=vendor,
            metadata=metadata or {},
        )

        # Run VetoNet verification
        try:
            result = self.veto.check(intent, payload)

            return {
                "approved": result.approved,
                "reason": result.reason,
                "checks": [check.model_dump() for check in result.checks],
                "status": result.status.value
            }
        except Exception as e:
            return {
                "approved": False,
                "reason": f"Verification error: {str(e)}",
                "checks": [],
                "status": "VETO"
            }

    def clear_intent(self, session_id: str) -> bool:
        """
        Clear the locked intent for a session.

        Should be called when a session ends or when the user
        wants to start a new shopping session.

        Args:
            session_id: Session ID to clear

        Returns:
            True if intent was cleared, False if no intent existed
        """
        if session_id in self.intents:
            del self.intents[session_id]
            return True
        return False

    def get_intent(self, session_id: str) -> Optional[dict[str, Any]]:
        """
        Get the locked intent for a session.

        Args:
            session_id: Session ID to look up

        Returns:
            Dict representation of the IntentAnchor, or None if not found
        """
        intent = self.intents.get(session_id)
        if intent:
            return intent.model_dump()
        return None
