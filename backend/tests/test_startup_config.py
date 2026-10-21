"""Startup guard: a Vercel deployment (Production or Preview) must have DATABASE_URL.

Without it the backend would fall back to SQLite, which on Vercel's read-only
filesystem either fails with a cryptic error or silently loses data. Ordinary
local development must keep the SQLite fallback.

Each case runs in a fresh interpreter against a COPY of config.py in an empty
temp directory, with a minimal environment, so neither a developer's real .env
nor shell variables can change the outcome. The DATABASE_URL used here is a
non-routable placeholder; nothing ever connects to it.
"""

import os
import shutil
import subprocess
import sys

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLACEHOLDER_URL = "postgresql://example.invalid/placeholder"

_PASSTHROUGH = ("SYSTEMROOT", "PATH", "TEMP", "TMP", "HOME", "USERPROFILE", "LOCALAPPDATA")


@pytest.fixture
def run_config(tmp_path):
    shutil.copy(os.path.join(BACKEND, "config.py"), tmp_path / "config.py")

    def run(**extra_env):
        env = {k: os.environ[k] for k in _PASSTHROUGH if k in os.environ}
        env.update(extra_env)
        code = "from config import settings; print(repr(settings.database_url), settings.environment)"
        return subprocess.run(
            [sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60
        )

    return run


def test_local_development_without_database_url_keeps_the_sqlite_fallback(run_config):
    result = run_config()
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["''", "development"]


def test_an_empty_vercel_variable_counts_as_local(run_config):
    assert run_config(VERCEL="").returncode == 0


@pytest.mark.parametrize("vercel_env", ["preview", "production", "development"])
def test_vercel_without_database_url_fails_clearly_and_early(run_config, vercel_env):
    result = run_config(VERCEL="1", VERCEL_ENV=vercel_env)
    assert result.returncode != 0
    assert "FATAL" in result.stderr and "Vercel deployment" in result.stderr
    assert "DATABASE_URL is not set" in result.stderr
    assert "its own database" in result.stderr  # tells a Preview owner not to reuse production's


def test_vercel_preview_with_database_url_starts(run_config):
    result = run_config(VERCEL="1", VERCEL_ENV="preview", DATABASE_URL=PLACEHOLDER_URL)
    assert result.returncode == 0, result.stderr


def test_vercel_production_with_database_url_starts(run_config):
    result = run_config(VERCEL="1", VERCEL_ENV="production", ENVIRONMENT="production", DATABASE_URL=PLACEHOLDER_URL)
    assert result.returncode == 0, result.stderr


def test_production_without_database_url_still_fails(run_config):
    result = run_config(ENVIRONMENT="production")
    assert result.returncode != 0
    assert "environment=production" in result.stderr and "DATABASE_URL is not set" in result.stderr


def test_production_with_database_url_starts_and_the_value_is_never_echoed(run_config):
    result = run_config(ENVIRONMENT="production", DATABASE_URL=PLACEHOLDER_URL)
    assert result.returncode == 0, result.stderr
    assert "example.invalid" not in result.stderr


def test_the_failure_message_never_contains_other_environment_values(run_config):
    result = run_config(VERCEL="1", OPENAI_API_KEY="not-a-real-key-for-test", ENVIRONMENT="preview-x")
    assert result.returncode != 0
    assert "not-a-real-key-for-test" not in result.stderr
