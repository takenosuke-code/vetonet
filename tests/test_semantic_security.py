"""Tests for security-critical functions in vetonet.checks.semantic."""

import pytest

from vetonet.checks.semantic import _validate_score, _sanitize_reason


class TestValidateScore:
    """_validate_score must safely coerce any LLM output to [0.0, 1.0]."""

    @pytest.mark.parametrize("value,expected", [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)])
    def test_valid_scores_pass_through(self, value, expected):
        assert _validate_score(value) == expected

    def test_bool_true_returns_zero(self):
        """bool is a subclass of int; float(True)==1.0 would silently pass."""
        assert _validate_score(True) == 0.0

    def test_bool_false_returns_zero(self):
        assert _validate_score(False) == 0.0

    def test_nan_returns_zero(self):
        assert _validate_score(float("nan")) == 0.0

    def test_positive_inf_returns_zero(self):
        assert _validate_score(float("inf")) == 0.0

    def test_negative_inf_returns_zero(self):
        assert _validate_score(float("-inf")) == 0.0

    def test_numeric_string_coerced(self):
        assert _validate_score("0.5") == 0.5

    def test_non_numeric_string_returns_zero(self):
        assert _validate_score("abc") == 0.0

    def test_none_returns_zero(self):
        assert _validate_score(None) == 0.0

    def test_negative_returns_zero(self):
        assert _validate_score(-0.1) == 0.0

    def test_over_range_returns_zero(self):
        assert _validate_score(1.1) == 0.0

    def test_very_large_returns_zero(self):
        assert _validate_score(9999) == 0.0


class TestSanitizeReason:
    """_sanitize_reason must neutralize XSS, control chars, and length bombs."""

    def test_normal_string_passes_through(self):
        assert _sanitize_reason("Exact brand match") == "Exact brand match"

    def test_truncated_at_500_chars(self):
        long = "A" * 600
        result = _sanitize_reason(long)
        assert len(result) <= 500

    def test_html_tags_escaped(self):
        result = _sanitize_reason("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;" in result

    def test_control_characters_stripped(self):
        result = _sanitize_reason("clean\x00\x1f\x7ftext")
        assert "\x00" not in result
        assert "\x1f" not in result
        assert "\x7f" not in result
        assert "cleantext" in result

    def test_non_string_coerced(self):
        result = _sanitize_reason(42)
        assert result == "42"

    def test_none_coerced(self):
        result = _sanitize_reason(None)
        assert result == "None"

    def test_list_coerced(self):
        result = _sanitize_reason([1, 2, 3])
        assert "1" in result
