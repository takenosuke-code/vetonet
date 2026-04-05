"""Tests for VetoEngine semantic modes, suspicion scoring, and sentinel behaviour."""

from unittest.mock import patch

import pytest

from tests.conftest import make_anchor, make_payload
from vetonet.config import VetoConfig
from vetonet.engine import VetoEngine, _UNSET
from vetonet.models import CheckResult, VetoStatus


class TestSemanticModeAlwaysNoClient:
    """semantic_mode='always' with llm_client=None must fail closed (VETO)."""

    @patch("vetonet.engine.check_classifier")
    def test_always_mode_no_client_vetoes(self, mock_classifier):
        mock_classifier.return_value = None
        engine = VetoEngine(
            veto_config=VetoConfig(semantic_mode="always"),
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
        assert result.status == VetoStatus.VETO
        assert "unavailable" in result.reason.lower()


class TestSemanticModeNever:
    """semantic_mode='never' must skip semantic check entirely."""

    @patch("vetonet.engine.check_semantic_match")
    @patch("vetonet.engine.check_classifier")
    def test_never_mode_skips_semantic(self, mock_classifier, mock_semantic):
        mock_classifier.return_value = None
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
        mock_semantic.assert_not_called()


class TestSuspicionAccumulation:
    """Suspicion weights accumulate and trigger multipliers via the engine."""

    @staticmethod
    def _ok(name: str, weight: float) -> CheckResult:
        return CheckResult(name=name, passed=True, reason="ok", score=1.0, suspicion_weight=weight)

    @patch("vetonet.engine.check_classifier")
    @patch("vetonet.engine.check_crypto_substitution")
    @patch("vetonet.engine.check_market_value")
    @patch("vetonet.engine.check_scam_patterns")
    @patch("vetonet.engine.check_vendor")
    @patch("vetonet.engine.check_hidden_fees")
    @patch("vetonet.engine.check_subscription_trap")
    @patch("vetonet.engine.check_currency_manipulation")
    @patch("vetonet.engine.check_category")
    @patch("vetonet.engine.check_quantity")
    @patch("vetonet.engine.check_price")
    def test_suspicion_sum(
        self,
        m_price,
        m_qty,
        m_cat,
        m_currency,
        m_sub,
        m_fees,
        m_vendor,
        m_scam,
        m_market,
        m_crypto,
        m_classifier,
    ):
        """Two signals with weights 0.2+0.3 produce total 0.5, below default threshold."""
        m_price.return_value = self._ok("price", 0.2)
        m_qty.return_value = self._ok("quantity", 0.3)
        m_cat.return_value = self._ok("category", 0.0)
        m_currency.return_value = self._ok("currency", 0.0)
        m_sub.return_value = self._ok("subscription", 0.0)
        m_fees.return_value = self._ok("hidden_fees", 0.0)
        m_vendor.return_value = self._ok("vendor", 0.0)
        m_scam.return_value = self._ok("scam", 0.0)
        m_market.return_value = self._ok("market_value", 0.0)
        m_crypto.return_value = self._ok("crypto", 0.0)
        m_classifier.return_value = None

        engine = VetoEngine(
            veto_config=VetoConfig(
                semantic_mode="never",
                suspicion_threshold=0.6,
                suspicion_shadow_mode=False,
            ),
            llm_client=None,
        )
        anchor = make_anchor()
        payload = make_payload()
        result = engine.check(anchor, payload)
        # Total suspicion 0.5 < threshold 0.6 → approved without semantic
        assert result.status == VetoStatus.APPROVED
        weights = [c.suspicion_weight for c in result.checks]
        assert sum(weights) == pytest.approx(0.5)

    @patch("vetonet.engine.check_semantic_match")
    @patch("vetonet.engine.check_classifier")
    @patch("vetonet.engine.check_crypto_substitution")
    @patch("vetonet.engine.check_market_value")
    @patch("vetonet.engine.check_scam_patterns")
    @patch("vetonet.engine.check_vendor")
    @patch("vetonet.engine.check_hidden_fees")
    @patch("vetonet.engine.check_subscription_trap")
    @patch("vetonet.engine.check_currency_manipulation")
    @patch("vetonet.engine.check_category")
    @patch("vetonet.engine.check_quantity")
    @patch("vetonet.engine.check_price")
    def test_three_signals_multiplier(
        self,
        m_price,
        m_qty,
        m_cat,
        m_currency,
        m_sub,
        m_fees,
        m_vendor,
        m_scam,
        m_market,
        m_crypto,
        m_classifier,
        m_semantic,
    ):
        """Three nonzero signals get 1.3x multiplier; 0.1*3*1.3=0.39 crosses 0.35 threshold."""
        m_price.return_value = self._ok("price", 0.1)
        m_qty.return_value = self._ok("quantity", 0.1)
        m_cat.return_value = self._ok("category", 0.1)
        m_currency.return_value = self._ok("currency", 0.0)
        m_sub.return_value = self._ok("subscription", 0.0)
        m_fees.return_value = self._ok("hidden_fees", 0.0)
        m_vendor.return_value = self._ok("vendor", 0.0)
        m_scam.return_value = self._ok("scam", 0.0)
        m_market.return_value = self._ok("market_value", 0.0)
        m_crypto.return_value = self._ok("crypto", 0.0)
        m_classifier.return_value = None
        m_semantic.return_value = CheckResult(name="semantic", passed=True, reason="ok", score=0.9)

        mock_llm = object()
        engine = VetoEngine(
            veto_config=VetoConfig(
                semantic_mode="never",
                suspicion_threshold=0.35,
                suspicion_shadow_mode=False,
            ),
            llm_client=mock_llm,
        )
        anchor = make_anchor()
        payload = make_payload()
        engine.check(anchor, payload)
        # 0.1*3*1.3 = 0.39 >= 0.35 → semantic forced
        m_semantic.assert_called_once()

    @patch("vetonet.engine.check_semantic_match")
    @patch("vetonet.engine.check_classifier")
    @patch("vetonet.engine.check_crypto_substitution")
    @patch("vetonet.engine.check_market_value")
    @patch("vetonet.engine.check_scam_patterns")
    @patch("vetonet.engine.check_vendor")
    @patch("vetonet.engine.check_hidden_fees")
    @patch("vetonet.engine.check_subscription_trap")
    @patch("vetonet.engine.check_currency_manipulation")
    @patch("vetonet.engine.check_category")
    @patch("vetonet.engine.check_quantity")
    @patch("vetonet.engine.check_price")
    def test_four_signals_multiplier(
        self,
        m_price,
        m_qty,
        m_cat,
        m_currency,
        m_sub,
        m_fees,
        m_vendor,
        m_scam,
        m_market,
        m_crypto,
        m_classifier,
        m_semantic,
    ):
        """Four nonzero signals get 1.5x multiplier; 0.1*4*1.5=0.6 crosses 0.55 threshold."""
        m_price.return_value = self._ok("price", 0.1)
        m_qty.return_value = self._ok("quantity", 0.1)
        m_cat.return_value = self._ok("category", 0.1)
        m_currency.return_value = self._ok("currency", 0.1)
        m_sub.return_value = self._ok("subscription", 0.0)
        m_fees.return_value = self._ok("hidden_fees", 0.0)
        m_vendor.return_value = self._ok("vendor", 0.0)
        m_scam.return_value = self._ok("scam", 0.0)
        m_market.return_value = self._ok("market_value", 0.0)
        m_crypto.return_value = self._ok("crypto", 0.0)
        m_classifier.return_value = None
        m_semantic.return_value = CheckResult(name="semantic", passed=True, reason="ok", score=0.9)

        mock_llm = object()
        engine = VetoEngine(
            veto_config=VetoConfig(
                semantic_mode="never",
                suspicion_threshold=0.55,
                suspicion_shadow_mode=False,
            ),
            llm_client=mock_llm,
        )
        anchor = make_anchor()
        payload = make_payload()
        engine.check(anchor, payload)
        # 0.1*4*1.5 = 0.6 >= 0.55 → semantic forced
        m_semantic.assert_called_once()

    @patch("vetonet.engine.check_classifier")
    def test_suspicion_threshold_forces_semantic_when_client_present(self, mock_classifier):
        """High suspicion forces semantic even in 'never' mode when client exists."""
        mock_classifier.return_value = None

        mock_llm = object()  # non-None sentinel

        with patch("vetonet.engine.check_semantic_match") as mock_semantic:
            mock_semantic.return_value = CheckResult(
                name="semantic", passed=True, reason="ok", score=0.9
            )

            # Use "never" mode with a meaningful threshold (0.3).
            # An untrusted vendor (not in trusted_vendors, no suspicious TLD)
            # contributes 0.2 suspicion weight; a near-budget price ($99/$100)
            # contributes ~0.24 suspicion weight. Total ~0.44 crosses 0.3.
            engine = VetoEngine(
                veto_config=VetoConfig(
                    semantic_mode="never",
                    suspicion_threshold=0.3,
                    suspicion_shadow_mode=False,
                ),
                llm_client=mock_llm,
            )
            anchor = make_anchor(max_price=100.0, category="gift_card")
            payload = make_payload(
                description="Amazon Gift Card $50",
                category="gift_card",
                unit_price=99.0,
                vendor="giftcardsrus.com",
            )
            engine.check(anchor, payload)
            # Semantic should have been called because suspicion forced it
            mock_semantic.assert_called_once()


class TestUnsetSentinel:
    """The _UNSET sentinel lets VetoEngine(llm_client=None) explicitly set None."""

    def test_explicit_none_sets_none(self):
        engine = VetoEngine(llm_client=None)
        assert engine.llm_client is None

    def test_unset_is_not_none(self):
        assert _UNSET is not None
