"""Tests verifying the Railway URL migration to api.veto-net.org."""

import pathlib

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

OLD_URL = "web-production-fec907.up.railway.app"
NEW_URL = "api.veto-net.org"

# Every file that previously contained the Railway URL.
FILES_THAT_HAD_RAILWAY_URL = [
    "vetonet/integrations/langchain/types.py",
    "vetonet/telemetry.py",
    "playground/src/config.js",
    "playground/vite.config.js",
    "README.md",
    "examples/quickstart_api.py",
    "scripts/pentest.py",
    "scripts/fuzzer.py",
    "scripts/mega_pentest.py",
    "test_edge_cases.py",
    "test_creative_attacks.py",
    "test_aggressive.py",
]

# SDK files that must contain the new URL.
SDK_FILES_WITH_NEW_URL = [
    "vetonet/integrations/langchain/types.py",
    "vetonet/telemetry.py",
]


class TestRailwayUrlRemoved:
    """Verify the old Railway URL is absent from every previously-affected file."""

    @pytest.mark.parametrize("rel_path", FILES_THAT_HAD_RAILWAY_URL)
    def test_old_url_absent(self, rel_path: str):
        """The legacy Railway URL must not appear in {rel_path}."""
        filepath = PROJECT_ROOT / rel_path
        content = filepath.read_text(encoding="utf-8")
        assert OLD_URL not in content, (
            f"{rel_path} still contains the old Railway URL"
        )


class TestNewUrlPresent:
    """Verify the new api.veto-net.org URL is present in SDK source files."""

    @pytest.mark.parametrize("rel_path", SDK_FILES_WITH_NEW_URL)
    def test_new_url_present(self, rel_path: str):
        """api.veto-net.org must appear in {rel_path}."""
        filepath = PROJECT_ROOT / rel_path
        content = filepath.read_text(encoding="utf-8")
        assert NEW_URL in content, (
            f"{rel_path} is missing the new URL ({NEW_URL})"
        )
