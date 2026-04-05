"""Tests for vetonet.engine — VetoEngine orchestration."""

import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import make_anchor, make_payload
from vetonet.engine import VetoEngine
from vetonet.models import VetoStatus, CheckResult
from vetonet.config import VetoConfig


class TestEngineApproval:
    def test_all_checks_pass_approved(self):
        """A clean transaction should be APPROVED."""
        engine = VetoEngine(
            veto_config=VetoConfig(semantic_mode="never"),
            llm_client=None,
        )
        anchor = make_anchor(max_price=100.0, category="gift_card")
        payload = make_payload(
            description="Amazon Gift Card $50",
            category="gift_card",
            unit_price=50.0,
            vendor="amazon.com",
        )
        result = engine.check(anchor, payload)
        assert result.status == VetoStatus.APPROVED
        assert result.approved is True
        assert result.vetoed is False


class TestEngineVeto:
    def test_price_fail_vetoes(self):
        """Over-budget transaction should be VETOED."""
        engine = VetoEngine(
            veto_config=VetoConfig(semantic_mode="never"),
            llm_client=None,
        )
        anchor = make_anchor(max_price=50.0, category="gift_card")
        payload = make_payload(
            description="Amazon Gift Card $100",
            category="gift_card",
            unit_price=100.0,
            vendor="amazon.com",
        )
        result = engine.check(anchor, payload)
        assert result.status == VetoStatus.VETO
        assert "exceeds" in result.reason.lower()

    def test_category_fail_vetoes(self):
        """Category mismatch should be VETOED."""
        engine = VetoEngine(
            veto_config=VetoConfig(semantic_mode="never"),
            llm_client=None,
        )
        anchor = make_anchor(max_price=100.0, category="electronics")
        payload = make_payload(
            description="Nike Shoes",
            category="shoes",
            unit_price=80.0,
            vendor="nike.com",
        )
        result = engine.check(anchor, payload)
        assert result.status == VetoStatus.VETO

    def test_first_failing_check_stops_execution(self):
        """Engine should fail fast — veto on first failure."""
        engine = VetoEngine(
            veto_config=VetoConfig(semantic_mode="never"),
            llm_client=None,
        )
        anchor = make_anchor(max_price=10.0, category="gift_card")
        payload = make_payload(
            description="Amazon Gift Card",
            category="electronics",  # wrong category
            unit_price=100.0,  # over budget
            vendor="amazon.com",
        )
        result = engine.check(anchor, payload)
        assert result.status == VetoStatus.VETO
        # Price check runs first and should fail
        assert result.checks[0].name == "price"
        assert result.checks[0].passed is False
        # Only one check should have been run (fail fast)
        assert len(result.checks) == 1


class TestEngineClassifierMocked:
    @patch("vetonet.engine.check_classifier")
    def test_classifier_veto(self, mock_classifier):
        """Classifier detecting an attack should VETO."""
        mock_classifier.return_value = CheckResult(
            name="classifier",
            passed=False,
            reason="ML classifier detected attack (confidence: 0.95)",
            score=0.95,
        )
        engine = VetoEngine(
            veto_config=VetoConfig(semantic_mode="never"),
            llm_client=None,
        )
        anchor = make_anchor(max_price=100.0, category="gift_card")
        payload = make_payload(
            description="Amazon Gift Card",
            category="gift_card",
            unit_price=50.0,
            vendor="amazon.com",
        )
        result = engine.check(anchor, payload)
        assert result.status == VetoStatus.VETO
        assert "classifier" in result.reason.lower()

    @patch("vetonet.engine.check_classifier")
    def test_classifier_pass(self, mock_classifier):
        """Classifier approving should let transaction through."""
        mock_classifier.return_value = CheckResult(
            name="classifier",
            passed=True,
            reason="ML classifier: legitimate (confidence: 0.90)",
            score=0.10,
        )
        engine = VetoEngine(
            veto_config=VetoConfig(semantic_mode="never"),
            llm_client=None,
        )
        anchor = make_anchor(max_price=100.0, category="gift_card")
        payload = make_payload(
            description="Amazon Gift Card",
            category="gift_card",
            unit_price=50.0,
            vendor="amazon.com",
        )
        result = engine.check(anchor, payload)
        assert result.status == VetoStatus.APPROVED

    @patch("vetonet.engine.check_classifier")
    def test_classifier_none_means_uncertain(self, mock_classifier):
        """Classifier returning None means uncertain — should still pass without semantic."""
        mock_classifier.return_value = None
        engine = VetoEngine(
            veto_config=VetoConfig(semantic_mode="never"),
            llm_client=None,
        )
        anchor = make_anchor(max_price=100.0, category="gift_card")
        payload = make_payload(
            description="Amazon Gift Card",
            category="gift_card",
            unit_price=50.0,
            vendor="amazon.com",
        )
        result = engine.check(anchor, payload)
        assert result.status == VetoStatus.APPROVED


class TestEngineSuspicion:
    @patch("vetonet.engine.check_classifier")
    def test_accumulated_suspicion_tracked(self, mock_classifier):
        """Suspicion weights accumulate across checks."""
        mock_classifier.return_value = None
        engine = VetoEngine(
            veto_config=VetoConfig(
                semantic_mode="never",
                suspicion_shadow_mode=True,
            ),
            llm_client=None,
        )
        # Transaction that passes all checks but has suspicion signals
        anchor = make_anchor(max_price=100.0, category="gift_card")
        payload = make_payload(
            description="Amazon Gift Card",
            category="gift_card",
            unit_price=99.0,  # near budget -> price suspicion
            vendor="randomshop.com",  # unknown vendor -> vendor suspicion
            fees=[{"name": "shipping", "amount": 0.50}],  # small fee -> fee suspicion
        )
        result = engine.check(anchor, payload)
        # Should still pass (shadow mode logs but doesn't veto)
        assert result.status == VetoStatus.APPROVED
        # Verify suspicion weights exist
        suspicion_checks = [c for c in result.checks if c.suspicion_weight > 0]
        assert len(suspicion_checks) >= 1
