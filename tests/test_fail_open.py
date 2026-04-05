"""Tests for the shared fail_open decision helper."""

import logging
import os
from unittest.mock import patch

from vetonet.integrations.fail_open import should_allow_fail_open

logger = logging.getLogger("test_fail_open")


class TestShouldAllowFailOpen:
    """Tests for the three-branch fail_open decision logic."""

    def test_fail_open_false_returns_false(self):
        """fail_open=False always returns False regardless of env var."""
        with patch.dict(os.environ, {"VETONET_ALLOW_FAIL_OPEN": "1"}):
            assert should_allow_fail_open(False, "buy_item", "circuit_open", logger) is False

    def test_fail_open_true_with_env_var_returns_true(self):
        """Both fail_open=True AND env var set -> allows bypass."""
        with patch.dict(os.environ, {"VETONET_ALLOW_FAIL_OPEN": "1"}):
            assert should_allow_fail_open(True, "buy_item", "circuit_open", logger) is True

    def test_fail_open_true_without_env_var_returns_false(self):
        """fail_open=True but env var not set -> fails closed."""
        with patch.dict(os.environ):
            os.environ.pop("VETONET_ALLOW_FAIL_OPEN", None)
            assert should_allow_fail_open(True, "buy_item", "circuit_open", logger) is False

    def test_fail_open_true_env_var_wrong_value_returns_false(self):
        """fail_open=True but env var is not '1' -> fails closed."""
        with patch.dict(os.environ, {"VETONET_ALLOW_FAIL_OPEN": "true"}):
            assert should_allow_fail_open(True, "buy_item", "circuit_open", logger) is False

    def test_bypass_logs_critical(self, caplog):
        """When bypass is allowed, logs at CRITICAL with [SECURITY] prefix."""
        with patch.dict(os.environ, {"VETONET_ALLOW_FAIL_OPEN": "1"}):
            with caplog.at_level(logging.CRITICAL):
                should_allow_fail_open(True, "buy_item", "circuit_open", logger)
        assert any("[SECURITY]" in r.message for r in caplog.records)
        assert any("circuit_open" in r.message for r in caplog.records)

    def test_refused_logs_warning(self, caplog):
        """When fail_open is True but env var missing, logs WARNING with [SECURITY]."""
        with patch.dict(os.environ):
            os.environ.pop("VETONET_ALLOW_FAIL_OPEN", None)
            with caplog.at_level(logging.WARNING):
                should_allow_fail_open(True, "buy_item", "vetonet_error", logger)
        assert any("[SECURITY]" in r.message for r in caplog.records)
        assert any("failing closed" in r.message for r in caplog.records)

    def test_tool_name_in_log_messages(self, caplog):
        """Tool name appears in log messages for traceability."""
        with patch.dict(os.environ, {"VETONET_ALLOW_FAIL_OPEN": "1"}):
            with caplog.at_level(logging.CRITICAL):
                should_allow_fail_open(True, "my_special_tool", "circuit_open", logger)
        assert any("my_special_tool" in r.message for r in caplog.records)
