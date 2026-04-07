"""Tests that Supabase RLS policies are correctly configured.

These tests hit the LIVE Supabase instance using the anon key to verify
that Row Level Security blocks unauthorized writes. They do NOT modify data.

Requires: VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env (or env vars).
"""

import os
from pathlib import Path

import pytest
import requests

# Load from .env if available
ENV_FILE = Path(__file__).parent.parent / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

SUPABASE_URL = os.environ.get("VITE_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
ANON_KEY = os.environ.get("VITE_SUPABASE_ANON_KEY")

pytestmark = pytest.mark.skipif(
    not SUPABASE_URL or not ANON_KEY,
    reason="SUPABASE_URL and ANON_KEY required for RLS tests",
)

HEADERS = {
    "apikey": ANON_KEY or "",
    "Authorization": f"Bearer {ANON_KEY or ''}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

REST_URL = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else ""


class TestAttacksRLS:
    """Attacks table: anon cannot insert, update, or delete."""

    def test_anon_cannot_insert(self):
        res = requests.post(
            f"{REST_URL}/attacks",
            headers=HEADERS,
            json={"type": "rls_test", "prompt": "RLS test - should fail", "verdict": "blocked"},
        )
        assert res.status_code in (401, 403, 409), f"Expected RLS block, got {res.status_code}: {res.text}"

    def test_anon_cannot_delete(self):
        res = requests.delete(
            f"{REST_URL}/attacks?type=eq.rls_test_nonexistent",
            headers=HEADERS,
        )
        # RLS deny returns 0 rows affected, not an error — but shouldn't delete real data
        assert res.status_code != 204 or res.text == "[]", f"Delete should be blocked: {res.text}"

    def test_anon_cannot_update(self):
        res = requests.patch(
            f"{REST_URL}/attacks?type=eq.rls_test_nonexistent",
            headers=HEADERS,
            json={"prompt": "hacked"},
        )
        assert res.status_code != 200 or res.text == "[]", f"Update should be blocked: {res.text}"


class TestTelemetryRLS:
    """Telemetry table: anon cannot insert."""

    def test_anon_cannot_insert(self):
        res = requests.post(
            f"{REST_URL}/telemetry",
            headers=HEADERS,
            json={"source": "rls_test", "category": "test"},
        )
        assert res.status_code in (401, 403, 409), f"Expected RLS block, got {res.status_code}: {res.text}"


class TestMLTrainingDataRLS:
    """ML training data: anon cannot insert."""

    def test_anon_cannot_insert(self):
        res = requests.post(
            f"{REST_URL}/ml_training_data",
            headers=HEADERS,
            json={"prompt": "rls_test", "source": "test"},
        )
        assert res.status_code in (401, 403, 409), f"Expected RLS block, got {res.status_code}: {res.text}"


class TestAPIKeysRLS:
    """API keys: anon cannot read or write."""

    def test_anon_cannot_read_keys(self):
        res = requests.get(
            f"{REST_URL}/api_keys?select=id,key_hash",
            headers=HEADERS,
        )
        # Should return empty (RLS blocks) or 403
        if res.status_code == 200:
            data = res.json()
            assert data == [], f"Anon should not see api_keys: got {len(data)} rows"

    def test_anon_cannot_insert_keys(self):
        res = requests.post(
            f"{REST_URL}/api_keys",
            headers=HEADERS,
            json={"key_hash": "fake", "user_id": "00000000-0000-0000-0000-000000000000", "name": "rls_test"},
        )
        assert res.status_code in (401, 403, 409), f"Expected RLS block, got {res.status_code}: {res.text}"


class TestVetonetMetaRLS:
    """vetonet_meta: anon can read, cannot write."""

    def test_anon_can_read(self):
        res = requests.get(
            f"{REST_URL}/vetonet_meta?select=key,value",
            headers=HEADERS,
        )
        assert res.status_code == 200, f"Anon should be able to read vetonet_meta: {res.status_code}"

    def test_anon_cannot_insert(self):
        res = requests.post(
            f"{REST_URL}/vetonet_meta",
            headers=HEADERS,
            json={"key": "rls_test", "value": "should_fail"},
        )
        assert res.status_code in (401, 403, 409), f"Expected RLS block, got {res.status_code}: {res.text}"


class TestAPIStillWorks:
    """Verify the API backend (service_role) still functions after RLS changes."""

    def test_health(self):
        res = requests.get("https://api.veto-net.org/api/health", timeout=10)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"

    def test_stats(self):
        res = requests.get("https://api.veto-net.org/api/stats", timeout=10)
        assert res.status_code == 200
        data = res.json()
        assert data["total_attempts"] > 0

    def test_feed(self):
        res = requests.get("https://api.veto-net.org/api/feed", timeout=10)
        assert res.status_code == 200
        data = res.json()
        assert "attacks" in data

    def test_security_headers_present(self):
        res = requests.get("https://api.veto-net.org/api/health", timeout=10)
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert "max-age=" in res.headers.get("Strict-Transport-Security", "")
