"""
Mock PayPal API for VetoNet Demo.

Simulates PayPal's Agent Toolkit API without requiring real credentials.
In production, this would be replaced with actual PayPal SDK calls.
"""

import time
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class PaymentStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass
class PayPalOrder:
    """Represents a PayPal order."""
    order_id: str
    amount: float
    currency: str
    description: str
    vendor: str
    status: PaymentStatus
    blocked_reason: Optional[str] = None


class MockPayPalClient:
    """
    Mock PayPal Agent Toolkit client.

    In a real implementation, this would use:
    - paypal-agent-toolkit Python SDK
    - PayPal sandbox environment
    - Real OAuth credentials
    """

    def __init__(self, sandbox: bool = True):
        self.sandbox = sandbox
        self.orders: dict[str, PayPalOrder] = {}
        self._order_counter = 0

    def create_order(
        self,
        amount: float,
        currency: str,
        description: str,
        vendor: str,
    ) -> PayPalOrder:
        """
        Create a new PayPal order.

        In sandbox mode, this simulates the API call.
        """
        self._order_counter += 1
        order_id = f"PAYPAL-{self._order_counter:06d}-SANDBOX" if self.sandbox else f"PAYPAL-{self._order_counter:06d}"

        order = PayPalOrder(
            order_id=order_id,
            amount=amount,
            currency=currency,
            description=description,
            vendor=vendor,
            status=PaymentStatus.PENDING,
        )

        self.orders[order_id] = order
        return order

    def execute_order(self, order_id: str) -> PayPalOrder:
        """
        Execute (complete) a PayPal order.

        This is where the actual payment would happen.
        """
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")

        order = self.orders[order_id]

        if order.status == PaymentStatus.BLOCKED:
            return order

        # Simulate processing time
        time.sleep(0.5)

        order.status = PaymentStatus.COMPLETED
        return order

    def block_order(self, order_id: str, reason: str) -> PayPalOrder:
        """
        Block an order from being executed.

        This is what VetoNet does when it detects an attack.
        """
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")

        order = self.orders[order_id]
        order.status = PaymentStatus.BLOCKED
        order.blocked_reason = reason
        return order


def demo_paypal():
    """Demo the mock PayPal client."""
    print("=" * 60)
    print("Mock PayPal API Demo")
    print("=" * 60)

    client = MockPayPalClient(sandbox=True)

    # Create an order
    print("\nCreating order...")
    order = client.create_order(
        amount=50.00,
        currency="USD",
        description="Amazon Gift Card $50",
        vendor="amazon.com",
    )
    print(f"Order created: {order.order_id}")
    print(f"Status: {order.status.value}")

    # Execute the order
    print("\nExecuting order...")
    order = client.execute_order(order.order_id)
    print(f"Status: {order.status.value}")
    print("Payment completed!")


if __name__ == "__main__":
    demo_paypal()
