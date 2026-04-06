"""Tests for playground/.env.example — ensures env documentation stays correct."""

import pathlib
import re

import pytest

# Resolve project root relative to this test file
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_EXAMPLE = PROJECT_ROOT / "playground" / ".env.example"


class TestEnvExampleExists:
    def test_file_exists(self):
        assert ENV_EXAMPLE.is_file(), f"Expected {ENV_EXAMPLE} to exist as a file"


class TestEnvExampleContents:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = ENV_EXAMPLE.read_text()

    def test_contains_supabase_url(self):
        assert "VITE_SUPABASE_URL" in self.content

    def test_contains_supabase_anon_key(self):
        assert "VITE_SUPABASE_ANON_KEY" in self.content

    def test_contains_repo_root_comment(self):
        """The file must warn that Vite reads .env from the repo root."""
        lower = self.content.lower()
        assert "repo root" in lower or "parent" in lower or "one directory up" in lower

    def test_no_real_api_keys(self):
        """Placeholder values only — no real Supabase project URLs."""
        # Allow the generic placeholder 'your-project.supabase.co' but reject
        # any real subdomain (alphanumeric 10+ chars before .supabase.co).
        real_url_pattern = re.compile(
            r"https://[a-z0-9]{10,}\.supabase\.co", re.IGNORECASE
        )
        matches = real_url_pattern.findall(self.content)
        assert matches == [], (
            f"Found what looks like a real Supabase URL in .env.example: {matches}"
        )

    def test_no_real_anon_key(self):
        """The anon key placeholder must not be a real JWT (real ones are 100+ chars)."""
        for line in self.content.splitlines():
            if line.startswith("#"):
                continue
            if "VITE_SUPABASE_ANON_KEY" in line:
                value = line.split("=", 1)[1].strip()
                assert len(value) < 50, (
                    "VITE_SUPABASE_ANON_KEY value looks like a real key "
                    f"(length {len(value)})"
                )
