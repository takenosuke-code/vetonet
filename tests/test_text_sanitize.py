"""Tests for vetonet.text_sanitize — Unicode/leet speak normalization."""

import pytest
from vetonet.text_sanitize import normalize_text


class TestCyrillicHomoglyphs:
    def test_cyrillic_a(self):
        """Cyrillic 'а' (U+0430) should become Latin 'a'."""
        assert normalize_text("\u0430pple") == "apple"

    def test_cyrillic_o(self):
        """Cyrillic 'о' (U+043E) should become Latin 'o'."""
        assert normalize_text("g\u043e\u043egle") == "google"

    def test_cyrillic_c(self):
        """Cyrillic 'с' (U+0441) should become Latin 'c'."""
        assert normalize_text("\u0441at") == "cat"

    def test_mixed_cyrillic_latin(self):
        """Mixed Cyrillic/Latin should normalize to pure Latin."""
        # "аmаzon" with Cyrillic а's
        result = normalize_text("\u0430m\u0430zon")
        assert result == "amazon"


class TestLeetSpeak:
    def test_s3rvice(self):
        assert normalize_text("s3rvice") == "service"

    def test_pr0cessing(self):
        assert normalize_text("pr0cessing") == "processing"

    def test_h4ndling(self):
        assert normalize_text("h4ndling") == "handling"

    def test_skip_leet_preserves_digits(self):
        """With skip_leet=True, digits should be preserved."""
        result = normalize_text("shop123.com", skip_leet=True)
        assert "123" in result

    def test_dollar_sign_to_s(self):
        assert normalize_text("$ervice") == "service"

    def test_at_sign_to_a(self):
        assert normalize_text("@pple") == "apple"


class TestInvisibleCharacters:
    def test_zero_width_space(self):
        """Zero-width space (U+200B) should be stripped."""
        result = normalize_text("ser\u200Bvice")
        assert result == "service"

    def test_zero_width_joiner(self):
        """Zero-width joiner (U+200D) should be stripped."""
        result = normalize_text("fee\u200D")
        assert result == "fee"

    def test_soft_hyphen(self):
        """Soft hyphen (U+00AD) should be stripped."""
        result = normalize_text("pro\u00ADcessing")
        assert result == "processing"


class TestHyphensAndUnderscores:
    def test_hyphens_removed_by_default(self):
        result = normalize_text("proc-essing")
        assert result == "processing"

    def test_underscores_removed_by_default(self):
        result = normalize_text("service_fee")
        assert result == "servicefee"

    def test_preserve_hyphens(self):
        result = normalize_text("proc-essing", preserve_hyphens=True)
        assert "-" in result

    def test_preserve_underscores(self):
        result = normalize_text("service_fee", preserve_hyphens=True)
        assert "_" in result


class TestWhitespace:
    def test_collapses_multiple_spaces(self):
        result = normalize_text("service    fee")
        assert result == "service fee"

    def test_strips_leading_trailing(self):
        result = normalize_text("  service fee  ")
        assert result == "service fee"


class TestMixedAttacks:
    def test_cyrillic_plus_leet(self):
        """Combined Cyrillic homoglyph + leet speak attack."""
        # "s3rvic3" with Cyrillic 'е' in "s3rvic3"
        result = normalize_text("s3rvi\u0441\u0435")
        assert result == "service"

    def test_invisible_plus_leet(self):
        """Invisible character + leet speak."""
        result = normalize_text("s3\u200Brvice")
        assert result == "service"
