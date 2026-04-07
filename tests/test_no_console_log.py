"""Tests that playground source files use console.warn instead of console.log in catch blocks."""

from pathlib import Path

import pytest

PLAYGROUND_SRC = Path(__file__).resolve().parent.parent / "playground" / "src"

FILES = [
    PLAYGROUND_SRC / "App.jsx",
    PLAYGROUND_SRC / "LandingPage.jsx",
]


class TestNoConsoleLog:
    """Ensure no non-comment lines use console.log in playground source files."""

    @pytest.mark.parametrize("filepath", FILES, ids=lambda p: p.name)
    def test_no_console_log(self, filepath: Path):
        lines = filepath.read_text(encoding="utf-8").splitlines()
        violations = []
        for i, line in enumerate(lines, start=1):
            stripped = line.lstrip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if "console.log(" in line:
                violations.append(f"  line {i}: {line.strip()}")
        assert violations == [], (
            f"console.log found in {filepath.name}:\n" + "\n".join(violations)
        )


class TestConsoleWarnPresent:
    """Verify that the expected console.warn calls exist in each file."""

    @pytest.mark.parametrize("filepath", FILES, ids=lambda p: p.name)
    def test_console_warn_api_unavailable(self, filepath: Path):
        content = filepath.read_text(encoding="utf-8")
        assert "console.warn('API unavailable" in content, (
            f"{filepath.name} should contain console.warn('API unavailable ...') "
            "for diagnostic context in catch blocks"
        )
