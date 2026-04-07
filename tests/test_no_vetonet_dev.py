"""Tests ensuring the old api.vetonet.dev domain is fully replaced."""

import pathlib

import pytest

# Repo root is three levels up from this test file
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

FILES = [
    REPO_ROOT / "playground" / "src" / "App.jsx",
    REPO_ROOT / "playground" / "src" / "LandingPage.jsx",
]


class TestOldDomainAbsent:
    """The deprecated api.vetonet.dev domain must not appear in frontend code."""

    @pytest.mark.parametrize("filepath", FILES, ids=lambda p: p.name)
    def test_no_vetonet_dev(self, filepath):
        """api.vetonet.dev should be completely removed from {filepath.name}."""
        content = filepath.read_text(encoding="utf-8")
        assert "api.vetonet.dev" not in content, (
            f"Found deprecated domain 'api.vetonet.dev' in {filepath}"
        )


class TestNewDomainPresent:
    """The new api.veto-net.org domain must be present in frontend code examples."""

    @pytest.mark.parametrize("filepath", FILES, ids=lambda p: p.name)
    def test_veto_net_org_present(self, filepath):
        """api.veto-net.org should appear in {filepath.name}."""
        content = filepath.read_text(encoding="utf-8")
        assert "api.veto-net.org" in content, (
            f"Expected 'api.veto-net.org' in {filepath}"
        )
