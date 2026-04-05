"""Tests for vetonet.checks.deterministic — all 10 deterministic checks."""

import pytest
from tests.conftest import make_anchor, make_payload
from vetonet.checks.deterministic import (
    check_price,
    check_category,
    check_vendor,
    check_quantity,
    check_hidden_fees,
    check_subscription_trap,
    check_currency_manipulation,
    check_scam_patterns,
    check_market_value,
    check_crypto_substitution,
    normalize_category,
)
from vetonet.config import VetoConfig


# ---------------------------------------------------------------------------
# check_price
# ---------------------------------------------------------------------------
class TestCheckPrice:
    def test_within_budget(self):
        anchor = make_anchor(max_price=100.0)
        payload = make_payload(unit_price=80.0)
        result = check_price(anchor, payload)
        assert result.passed is True

    def test_exactly_at_budget(self):
        anchor = make_anchor(max_price=100.0)
        payload = make_payload(unit_price=100.0)
        result = check_price(anchor, payload)
        assert result.passed is True

    def test_over_budget(self):
        anchor = make_anchor(max_price=100.0)
        payload = make_payload(unit_price=150.0)
        result = check_price(anchor, payload)
        assert result.passed is False
        assert "exceeds" in result.reason.lower()

    def test_with_fees_over_budget(self):
        anchor = make_anchor(max_price=100.0)
        payload = make_payload(
            unit_price=90.0,
            fees=[{"name": "tax", "amount": 15.0}],
        )
        result = check_price(anchor, payload)
        # total = 90 + 15 = 105 > 100
        assert result.passed is False

    def test_with_fees_within_budget(self):
        anchor = make_anchor(max_price=100.0)
        payload = make_payload(
            unit_price=80.0,
            fees=[{"name": "tax", "amount": 10.0}],
        )
        result = check_price(anchor, payload)
        # total = 80 + 10 = 90 <= 100
        assert result.passed is True

    def test_tolerance_allows_slight_overage(self):
        config = VetoConfig(price_tolerance=0.05)
        anchor = make_anchor(max_price=100.0)
        payload = make_payload(unit_price=104.0)
        result = check_price(anchor, payload, config)
        # max_allowed = 100 * 1.05 = 105, total = 104 <= 105
        assert result.passed is True

    def test_tolerance_still_catches_big_overage(self):
        config = VetoConfig(price_tolerance=0.05)
        anchor = make_anchor(max_price=100.0)
        payload = make_payload(unit_price=110.0)
        result = check_price(anchor, payload, config)
        assert result.passed is False

    def test_quantity_multiplied(self):
        anchor = make_anchor(max_price=200.0, quantity=2)
        payload = make_payload(unit_price=80.0, quantity=2)
        # total = 80 * 2 = 160 <= 200
        result = check_price(anchor, payload)
        assert result.passed is True

    def test_suspicion_weight_near_budget(self):
        anchor = make_anchor(max_price=100.0)
        payload = make_payload(unit_price=98.0)
        result = check_price(anchor, payload)
        assert result.passed is True
        # 98/100 = 0.98 > 0.95, so suspicion > 0
        assert result.suspicion_weight > 0

    def test_suspicion_weight_low_price(self):
        anchor = make_anchor(max_price=100.0)
        payload = make_payload(unit_price=50.0)
        result = check_price(anchor, payload)
        assert result.passed is True
        assert result.suspicion_weight == 0.0


# ---------------------------------------------------------------------------
# check_quantity
# ---------------------------------------------------------------------------
class TestCheckQuantity:
    def test_exact_match(self):
        anchor = make_anchor(quantity=3)
        payload = make_payload(quantity=3)
        result = check_quantity(anchor, payload)
        assert result.passed is True

    def test_over_quantity(self):
        anchor = make_anchor(quantity=1)
        payload = make_payload(quantity=5)
        result = check_quantity(anchor, payload)
        assert result.passed is False
        assert "exceeds" in result.reason.lower()

    def test_under_quantity(self):
        anchor = make_anchor(quantity=5)
        payload = make_payload(quantity=2)
        result = check_quantity(anchor, payload)
        assert result.passed is False
        assert "less than" in result.reason.lower()


# ---------------------------------------------------------------------------
# check_category
# ---------------------------------------------------------------------------
class TestCheckCategory:
    def test_exact_match(self):
        anchor = make_anchor(category="gift_card")
        payload = make_payload(category="gift_card")
        result = check_category(anchor, payload)
        assert result.passed is True

    def test_plural_handling(self):
        anchor = make_anchor(category="gift_card")
        payload = make_payload(category="gift_cards")
        result = check_category(anchor, payload)
        assert result.passed is True

    def test_case_insensitive(self):
        anchor = make_anchor(category="Gift_Card")
        payload = make_payload(category="gift_card")
        result = check_category(anchor, payload)
        assert result.passed is True

    def test_space_vs_underscore(self):
        anchor = make_anchor(category="gift card")
        payload = make_payload(category="gift_card")
        result = check_category(anchor, payload)
        assert result.passed is True

    def test_dash_vs_underscore(self):
        anchor = make_anchor(category="gift-card")
        payload = make_payload(category="gift_card")
        result = check_category(anchor, payload)
        assert result.passed is True

    def test_mismatch(self):
        anchor = make_anchor(category="electronics")
        payload = make_payload(category="clothing")
        result = check_category(anchor, payload)
        assert result.passed is False

    def test_double_s_not_stripped(self):
        """Words ending in 'ss' (like 'dress', 'glass') should NOT have trailing 's' removed."""
        assert normalize_category("dress") == "dress"  # ends in 'ss', kept intact
        assert normalize_category("glass") == "glass"  # ends in 'ss', kept intact
        # But a normal trailing 's' IS stripped
        assert normalize_category("shoes") == "shoe"


# ---------------------------------------------------------------------------
# check_currency_manipulation
# ---------------------------------------------------------------------------
class TestCheckCurrency:
    def test_match(self):
        anchor = make_anchor(currency="USD")
        payload = make_payload(currency="USD")
        result = check_currency_manipulation(anchor, payload)
        assert result.passed is True

    def test_case_insensitive(self):
        anchor = make_anchor(currency="usd")
        payload = make_payload(currency="USD")
        result = check_currency_manipulation(anchor, payload)
        assert result.passed is True

    def test_mismatch(self):
        anchor = make_anchor(currency="USD")
        payload = make_payload(currency="EUR")
        result = check_currency_manipulation(anchor, payload)
        assert result.passed is False
        assert "mismatch" in result.reason.lower()


# ---------------------------------------------------------------------------
# check_subscription_trap
# ---------------------------------------------------------------------------
class TestCheckSubscription:
    def test_both_one_time(self):
        anchor = make_anchor(is_recurring=False)
        payload = make_payload(is_recurring=False)
        result = check_subscription_trap(anchor, payload)
        assert result.passed is True

    def test_both_recurring(self):
        anchor = make_anchor(is_recurring=True)
        payload = make_payload(is_recurring=True)
        result = check_subscription_trap(anchor, payload)
        assert result.passed is True

    def test_payload_recurring_anchor_not(self):
        anchor = make_anchor(is_recurring=False)
        payload = make_payload(is_recurring=True)
        result = check_subscription_trap(anchor, payload)
        assert result.passed is False
        assert "recurring" in result.reason.lower()

    def test_payload_one_time_anchor_recurring(self):
        anchor = make_anchor(is_recurring=True)
        payload = make_payload(is_recurring=False)
        result = check_subscription_trap(anchor, payload)
        assert result.passed is False


# ---------------------------------------------------------------------------
# check_hidden_fees
# ---------------------------------------------------------------------------
class TestCheckHiddenFees:
    def test_no_fees(self):
        payload = make_payload(fees=[])
        result = check_hidden_fees(payload)
        assert result.passed is True

    def test_allowed_fee_tax(self):
        payload = make_payload(fees=[{"name": "tax", "amount": 5.0}])
        result = check_hidden_fees(payload)
        assert result.passed is True

    def test_suspicious_service_fee(self):
        payload = make_payload(fees=[{"name": "service fee", "amount": 10.0}])
        result = check_hidden_fees(payload)
        assert result.passed is False
        assert "service fee" in result.reason.lower()

    def test_suspicious_processing_fee(self):
        payload = make_payload(fees=[{"name": "processing fee", "amount": 8.0}])
        result = check_hidden_fees(payload)
        assert result.passed is False

    def test_leet_speak_obfuscation(self):
        """s3rvice fee should be caught after normalization."""
        payload = make_payload(fees=[{"name": "s3rvice fee", "amount": 10.0}])
        result = check_hidden_fees(payload)
        assert result.passed is False

    def test_hyphenated_obfuscation(self):
        """proc-essing fee should be caught after normalization."""
        payload = make_payload(fees=[{"name": "proc-essing fee", "amount": 10.0}])
        result = check_hidden_fees(payload)
        assert result.passed is False

    def test_insurance_suspicious(self):
        payload = make_payload(fees=[{"name": "insurance", "amount": 20.0}])
        result = check_hidden_fees(payload)
        assert result.passed is False

    def test_donation_suspicious(self):
        payload = make_payload(fees=[{"name": "donation", "amount": 5.0}])
        result = check_hidden_fees(payload)
        assert result.passed is False

    def test_suspicion_weight_with_allowed_fees(self):
        """Allowed fees should still generate some suspicion weight if large."""
        payload = make_payload(
            unit_price=50.0,
            fees=[{"name": "shipping", "amount": 20.0}],
        )
        result = check_hidden_fees(payload)
        assert result.passed is True
        assert result.suspicion_weight > 0


# ---------------------------------------------------------------------------
# check_vendor
# ---------------------------------------------------------------------------
class TestCheckVendor:
    def test_trusted_vendor(self):
        payload = make_payload(vendor="amazon.com")
        result = check_vendor(payload)
        assert result.passed is True
        assert "trusted" in result.reason.lower()
        assert result.suspicion_weight == 0.0

    def test_unknown_vendor(self):
        payload = make_payload(vendor="randomshop.com")
        result = check_vendor(payload)
        assert result.passed is True
        assert "unknown" in result.reason.lower()
        assert result.suspicion_weight > 0

    def test_suspicious_tld_ru(self):
        payload = make_payload(vendor="shop.ru")
        result = check_vendor(payload)
        assert result.passed is False
        assert ".ru" in result.reason

    def test_suspicious_tld_tk(self):
        payload = make_payload(vendor="deals.tk")
        result = check_vendor(payload)
        assert result.passed is False

    def test_brand_spoofing_amazon(self):
        anchor = make_anchor(core_constraints=["brand:Amazon"])
        payload = make_payload(vendor="amazon-giftcards.com")
        result = check_vendor(payload, anchor=anchor)
        assert result.passed is False
        assert "not official" in result.reason.lower()

    def test_brand_match_official_domain(self):
        anchor = make_anchor(core_constraints=["brand:Amazon"])
        payload = make_payload(vendor="amazon.com")
        result = check_vendor(payload, anchor=anchor)
        assert result.passed is True

    def test_brand_match_subdomain(self):
        """store.apple.com should be accepted for brand:Apple."""
        anchor = make_anchor(core_constraints=["brand:Apple"])
        payload = make_payload(vendor="store.apple.com")
        result = check_vendor(payload, anchor=anchor)
        assert result.passed is True

    def test_no_brand_constraint_passes(self):
        anchor = make_anchor(core_constraints=[])
        payload = make_payload(vendor="randomshop.com")
        result = check_vendor(payload, anchor=anchor)
        assert result.passed is True


# ---------------------------------------------------------------------------
# check_scam_patterns
# ---------------------------------------------------------------------------
class TestCheckScamPatterns:
    def test_clean_description(self):
        payload = make_payload(description="Amazon Gift Card $50")
        result = check_scam_patterns(payload)
        assert result.passed is True

    def test_gift_card_email_scam(self):
        payload = make_payload(
            description="Send gift card to: urgent_payment@gmail.com",
            category="gift_card",
        )
        result = check_scam_patterns(payload)
        assert result.passed is False

    def test_tech_support_scam(self):
        """Needs 2+ matches from tech support patterns."""
        payload = make_payload(
            description="Your computer is infected with virus detected. Call Microsoft support now.",
        )
        result = check_scam_patterns(payload)
        assert result.passed is False
        assert "tech support" in result.reason.lower()

    def test_nigerian_prince(self):
        payload = make_payload(
            description="Prince of Nigeria wants to transfer fund worth $10 million",
        )
        result = check_scam_patterns(payload)
        assert result.passed is False

    def test_grandparent_scam(self):
        """Needs 2+ matches: family reference + emergency."""
        payload = make_payload(
            description="Grandma I'm in jail and need bail money",
        )
        result = check_scam_patterns(payload)
        assert result.passed is False
        assert "grandparent" in result.reason.lower()

    def test_romance_scam(self):
        """Needs 2+ matches from romance patterns."""
        payload = make_payload(
            description="I met online dating and am stuck in airport overseas, please send money",
        )
        result = check_scam_patterns(payload)
        assert result.passed is False
        assert "romance" in result.reason.lower()

    def test_irs_scam(self):
        payload = make_payload(
            description="IRS payment required immediately",
        )
        result = check_scam_patterns(payload)
        assert result.passed is False

    def test_urgency_language(self):
        payload = make_payload(
            description="Urgent payment needed for emergency send now",
        )
        result = check_scam_patterns(payload)
        assert result.passed is False

    def test_phone_number_in_description(self):
        payload = make_payload(
            description="Call +1-800-555-1234 for tech support",
        )
        result = check_scam_patterns(payload)
        assert result.passed is False

    def test_whatsapp_in_description(self):
        payload = make_payload(
            description="Contact WhatsApp +44 7911 123456 for details",
        )
        result = check_scam_patterns(payload)
        assert result.passed is False

    def test_single_grandparent_keyword_not_enough(self):
        """A single grandparent keyword should NOT trigger (needs 2+)."""
        payload = make_payload(description="Gift for grandma birthday")
        result = check_scam_patterns(payload)
        assert result.passed is True


# ---------------------------------------------------------------------------
# check_market_value
# ---------------------------------------------------------------------------
class TestCheckMarketValue:
    def test_cheap_iphone_flagged(self):
        payload = make_payload(description="iPhone 15 Pro Max", unit_price=50.0)
        result = check_market_value(payload)
        assert result.passed is False
        assert "iphone" in result.reason.lower()

    def test_reasonable_iphone_passes(self):
        payload = make_payload(description="iPhone 15 Pro Max", unit_price=999.0)
        result = check_market_value(payload)
        assert result.passed is True

    def test_half_price_iphone_passes(self):
        """50% off is allowed (used/sale). Minimum = 400 * 0.5 = 200."""
        payload = make_payload(description="iPhone 15 (used)", unit_price=250.0)
        result = check_market_value(payload)
        assert result.passed is True

    def test_car_in_gift_card_not_flagged(self):
        """The word 'car' inside 'gift card' should NOT trigger car check."""
        payload = make_payload(description="Amazon gift card", unit_price=25.0)
        result = check_market_value(payload)
        assert result.passed is True

    def test_rental_skipped(self):
        payload = make_payload(
            description="Rolex rental for 1 day",
            unit_price=50.0,
            category="rental",
        )
        result = check_market_value(payload)
        assert result.passed is True
        assert "rental" in result.reason.lower()

    def test_charter_skipped(self):
        payload = make_payload(
            description="Yacht charter for the weekend",
            unit_price=500.0,
        )
        result = check_market_value(payload)
        assert result.passed is True

    def test_cheap_ps5_flagged(self):
        payload = make_payload(description="PS5 Digital Edition", unit_price=20.0)
        result = check_market_value(payload)
        assert result.passed is False

    def test_cheap_rolex_flagged(self):
        payload = make_payload(description="Rolex Submariner", unit_price=500.0)
        result = check_market_value(payload)
        assert result.passed is False

    def test_unknown_item_passes(self):
        payload = make_payload(description="Handmade pottery", unit_price=5.0)
        result = check_market_value(payload)
        assert result.passed is True

    def test_booking_keyword_skipped(self):
        payload = make_payload(description="Laptop booking for event", unit_price=10.0)
        result = check_market_value(payload)
        assert result.passed is True


# ---------------------------------------------------------------------------
# check_crypto_substitution
# ---------------------------------------------------------------------------
class TestCheckCryptoSubstitution:
    def test_btc_vs_wbtc(self):
        anchor = make_anchor(category="crypto btc")
        payload = make_payload(description="Purchase WBTC wrapped bitcoin", category="crypto")
        result = check_crypto_substitution(anchor, payload)
        assert result.passed is False

    def test_eth_vs_steth(self):
        anchor = make_anchor(category="crypto eth")
        payload = make_payload(description="Buy stETH staked ether", category="crypto")
        result = check_crypto_substitution(anchor, payload)
        assert result.passed is False

    def test_matching_crypto(self):
        anchor = make_anchor(category="crypto btc")
        payload = make_payload(description="Buy 1 BTC Bitcoin", category="crypto")
        result = check_crypto_substitution(anchor, payload)
        assert result.passed is True

    def test_non_crypto_skipped(self):
        anchor = make_anchor(category="shoes")
        payload = make_payload(description="Nike Air Max", category="shoes")
        result = check_crypto_substitution(anchor, payload)
        assert result.passed is True
        assert "not a crypto" in result.reason.lower()

    def test_wrapped_derivative_flagged(self):
        """Any wrapped derivative in a crypto transaction should be flagged."""
        anchor = make_anchor(category="crypto")
        payload = make_payload(description="Purchase weth for DeFi", category="crypto")
        result = check_crypto_substitution(anchor, payload)
        assert result.passed is False

    def test_usdc_vs_usdt(self):
        anchor = make_anchor(category="crypto usdc")
        payload = make_payload(description="Buy USDT Tether", category="crypto")
        result = check_crypto_substitution(anchor, payload)
        assert result.passed is False
