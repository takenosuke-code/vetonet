"""Shared fixtures for VetoNet tests."""

import pytest
from vetonet.models import IntentAnchor, AgentPayload, Fee


def make_anchor(
    category: str = "gift_card",
    max_price: float = 100.0,
    currency: str = "USD",
    quantity: int = 1,
    is_recurring: bool = False,
    core_constraints: list[str] | None = None,
) -> IntentAnchor:
    """Factory for IntentAnchor with sensible defaults."""
    return IntentAnchor(
        item_category=category,
        max_price=max_price,
        currency=currency,
        quantity=quantity,
        is_recurring=is_recurring,
        core_constraints=core_constraints or [],
    )


def make_payload(
    description: str = "Amazon Gift Card",
    category: str = "gift_card",
    unit_price: float = 50.0,
    quantity: int = 1,
    fees: list[dict] | None = None,
    currency: str = "USD",
    is_recurring: bool = False,
    vendor: str = "amazon.com",
    metadata: dict | None = None,
) -> AgentPayload:
    """Factory for AgentPayload with sensible defaults."""
    fee_objects = [Fee(name=f["name"], amount=f["amount"]) for f in fees] if fees else []
    return AgentPayload(
        item_description=description,
        item_category=category,
        unit_price=unit_price,
        quantity=quantity,
        fees=fee_objects,
        currency=currency,
        is_recurring=is_recurring,
        vendor=vendor,
        metadata=metadata or {},
    )


@pytest.fixture
def anchor_factory():
    """Provide make_anchor as a fixture."""
    return make_anchor


@pytest.fixture
def payload_factory():
    """Provide make_payload as a fixture."""
    return make_payload
