"""Tests for vetonet.models — Pydantic model validation and computed properties."""

import pytest
from vetonet.models import IntentAnchor, AgentPayload, Fee, VetoResult, VetoStatus, CheckResult
from pydantic import ValidationError


class TestAgentPayloadComputedProperties:
    def test_total_fees_no_fees(self):
        p = AgentPayload(
            item_description="Test", item_category="test", unit_price=10.0
        )
        assert p.total_fees == 0.0

    def test_total_fees_with_fees(self):
        p = AgentPayload(
            item_description="Test",
            item_category="test",
            unit_price=10.0,
            fees=[Fee(name="tax", amount=1.50), Fee(name="shipping", amount=3.00)],
        )
        assert p.total_fees == pytest.approx(4.50)

    def test_subtotal(self):
        p = AgentPayload(
            item_description="Test",
            item_category="test",
            unit_price=25.0,
            quantity=3,
        )
        assert p.subtotal == pytest.approx(75.0)

    def test_total_price_no_fees(self):
        p = AgentPayload(
            item_description="Test",
            item_category="test",
            unit_price=50.0,
            quantity=2,
        )
        assert p.total_price == pytest.approx(100.0)

    def test_total_price_with_fees(self):
        p = AgentPayload(
            item_description="Test",
            item_category="test",
            unit_price=50.0,
            quantity=2,
            fees=[Fee(name="tax", amount=10.0)],
        )
        assert p.total_price == pytest.approx(110.0)


class TestIntentAnchorValidation:
    def test_valid_anchor(self):
        a = IntentAnchor(item_category="shoes", max_price=200.0)
        assert a.item_category == "shoes"
        assert a.max_price == 200.0
        assert a.currency == "USD"
        assert a.quantity == 1
        assert a.is_recurring is False

    def test_max_price_must_be_positive(self):
        with pytest.raises(ValidationError):
            IntentAnchor(item_category="shoes", max_price=0)

    def test_max_price_negative_rejected(self):
        with pytest.raises(ValidationError):
            IntentAnchor(item_category="shoes", max_price=-10.0)

    def test_quantity_must_be_at_least_one(self):
        with pytest.raises(ValidationError):
            IntentAnchor(item_category="shoes", max_price=100.0, quantity=0)

    def test_core_constraints_default_empty(self):
        a = IntentAnchor(item_category="shoes", max_price=100.0)
        assert a.core_constraints == []


class TestAgentPayloadValidation:
    def test_unit_price_must_be_positive(self):
        with pytest.raises(ValidationError):
            AgentPayload(
                item_description="Test", item_category="test", unit_price=0
            )

    def test_quantity_must_be_at_least_one(self):
        with pytest.raises(ValidationError):
            AgentPayload(
                item_description="Test",
                item_category="test",
                unit_price=10.0,
                quantity=0,
            )

    def test_defaults(self):
        p = AgentPayload(
            item_description="Test", item_category="test", unit_price=10.0
        )
        assert p.currency == "USD"
        assert p.is_recurring is False
        assert p.vendor == "unknown"
        assert p.fees == []
        assert p.metadata == {}


class TestVetoResult:
    def test_approved_properties(self):
        r = VetoResult(status=VetoStatus.APPROVED, reason="All good")
        assert r.approved is True
        assert r.vetoed is False

    def test_veto_properties(self):
        r = VetoResult(status=VetoStatus.VETO, reason="Bad transaction")
        assert r.approved is False
        assert r.vetoed is True

    def test_checks_list(self):
        r = VetoResult(
            status=VetoStatus.APPROVED,
            reason="OK",
            checks=[
                CheckResult(name="price", passed=True, reason="OK"),
                CheckResult(name="category", passed=True, reason="OK"),
            ],
        )
        assert len(r.checks) == 2
