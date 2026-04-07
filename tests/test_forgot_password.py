"""Tests for forgot password flow in playground/src/AuthPage.jsx."""

import pathlib

import pytest

AUTHPAGE = pathlib.Path(__file__).resolve().parents[1] / "playground" / "src" / "AuthPage.jsx"


@pytest.fixture(scope="module")
def authpage_source() -> str:
    """Read AuthPage.jsx source once for all tests in this module."""
    return AUTHPAGE.read_text(encoding="utf-8")


class TestForgotPasswordFlow:
    def test_reset_password_for_email_present(self, authpage_source):
        """resetPasswordForEmail Supabase call must exist."""
        assert "resetPasswordForEmail" in authpage_source

    def test_password_recovery_event_handled(self, authpage_source):
        """PASSWORD_RECOVERY event must be handled in onAuthStateChange."""
        assert "PASSWORD_RECOVERY" in authpage_source

    def test_update_user_present(self, authpage_source):
        """updateUser call must exist for setting the new password."""
        assert "updateUser" in authpage_source

    def test_forgot_mode_string_exists(self, authpage_source):
        """The 'forgot' auth mode string must be present."""
        assert "'forgot'" in authpage_source

    def test_forgot_text_exists(self, authpage_source):
        """UI must contain 'Forgot' text for the link."""
        assert "Forgot" in authpage_source

    def test_send_reset_link_button_text(self, authpage_source):
        """Submit button must show 'Send Reset Link' in forgot mode."""
        assert "Send Reset Link" in authpage_source

    def test_back_to_sign_in_text(self, authpage_source):
        """Forgot mode must have a 'Back to sign in' link."""
        assert "Back to sign in" in authpage_source

    def test_show_reset_form_state_exists(self, authpage_source):
        """showResetForm state variable must be declared."""
        assert "showResetForm" in authpage_source
