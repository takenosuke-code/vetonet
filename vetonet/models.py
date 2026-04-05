"""
Pydantic models for VetoNet.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


class VetoStatus(str, Enum):
    """Result status of a veto check."""

    APPROVED = "APPROVED"
    VETO = "VETO"


class IntentAnchor(BaseModel):
    """
    The user's locked intent - extracted from natural language.

    This represents what the user actually wants to purchase,
    locked at the moment of intent expression.
    """

    item_category: str = Field(description="Category of item (gift_card, flight, shoes, etc.)")
    max_price: float = Field(gt=0, description="Maximum price the user is willing to pay")
    currency: str = Field(default="USD", description="Currency code (USD, EUR, etc.)")
    quantity: int = Field(default=1, ge=1, description="Number of items to purchase")
    is_recurring: bool = Field(
        default=False, description="Whether this is a subscription/recurring purchase"
    )
    core_constraints: list[str] = Field(
        default_factory=list,
        description="Key constraints as 'key:value' pairs (brand:Nike, size:9)",
    )


class Fee(BaseModel):
    """A fee or additional charge."""

    name: str
    amount: float


class AgentPayload(BaseModel):
    """
    What the AI agent wants to execute.

    This represents the transaction the agent is attempting to make,
    which may or may not match the user's original intent.
    """

    item_description: str = Field(description="Description of the item being purchased")
    item_category: str = Field(description="Category of the item")
    unit_price: float = Field(gt=0, description="Price per item")
    quantity: int = Field(default=1, ge=1, description="Number of items")
    fees: list[Fee] = Field(
        default_factory=list, description="Additional fees (service fee, shipping, etc.)"
    )
    currency: str = Field(default="USD", description="Currency code")
    is_recurring: bool = Field(
        default=False, description="Whether this is a subscription/recurring charge"
    )
    vendor: str = Field(default="unknown", description="Vendor/merchant domain")
    metadata: dict = Field(default_factory=dict, description="Additional transaction metadata")

    @property
    def total_fees(self) -> float:
        """Sum of all fees."""
        return sum(fee.amount for fee in self.fees)

    @property
    def subtotal(self) -> float:
        """Price before fees."""
        return self.unit_price * self.quantity

    @property
    def total_price(self) -> float:
        """Total price including fees."""
        return self.subtotal + self.total_fees


class CheckResult(BaseModel):
    """Result of a single check."""

    name: str
    passed: bool
    reason: str
    score: Optional[float] = None
    suspicion_weight: float = 0.0


class VetoResult(BaseModel):
    """
    Final result of the veto check.

    Contains the decision, reason, and details of all checks performed.
    """

    status: VetoStatus
    reason: str
    checks: list[CheckResult] = Field(default_factory=list)

    @property
    def approved(self) -> bool:
        return self.status == VetoStatus.APPROVED

    @property
    def vetoed(self) -> bool:
        return self.status == VetoStatus.VETO
