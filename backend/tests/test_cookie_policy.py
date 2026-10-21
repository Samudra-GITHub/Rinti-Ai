"""Session-cookie policy follows production, however production is signalled.

A live Vercel Production deployment can be running without ENVIRONMENT=production
(it was, when this was written). Vercel itself sets VERCEL_ENV=production on every
Production deployment, so that must be enough to get the __Host- name and the
Secure flag. Preview deployments and local development must not be affected.

Each case runs in a fresh interpreter against COPIES of the files involved in an
empty temp directory, with a minimal environment, so neither a developer's .env nor
shell variables can change the outcome. The DATABASE_URL is a non-routable
placeholder (required by the Vercel startup guard); nothing connects to it.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLACEHOLDER_URL = "postgresql://example.invalid/placeholder"
_PASSTHROUGH = ("SYSTEMROOT", "PATH", "TEMP", "TMP", "HOME", "USERPROFILE", "LOCALAPPDATA")

_PROBE = """
import json
from starlette.responses import Response
from auth import security
r = Response()
r.set_cookie(security.SESSION_COOKIE_NAME, "token", max_age=60, **security.cookie_kwargs())
print(json.dumps({
    "name": security.SESSION_COOKIE_NAME,
    "is_production": security.IS_PRODUCTION,
    "flags": security.cookie_kwargs(),
    "header": r.headers["set-cookie"],
}))
"""


@pytest.fixture
def probe(tmp_path):
    (tmp_path / "auth").mkdir()
    shutil.copy(os.path.join(BACKEND, "config.py"), tmp_path / "config.py")
    shutil.copy(os.path.join(BACKEND, "auth", "__init__.py"), tmp_path / "auth" / "__init__.py")
    shutil.copy(os.path.join(BACKEND, "auth", "security.py"), tmp_path / "auth" / "security.py")

    def run(**extra_env):
        env = {k: os.environ[k] for k in _PASSTHROUGH if k in os.environ}
        env.update(extra_env)
        result = subprocess.run(
            [sys.executable, "-c", _PROBE], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    return run


def test_local_development_cookie_is_not_secure(probe):
    out = probe()
    assert (out["is_production"], out["name"], out["flags"]["secure"]) == (False, "rinti_session", False)


def test_environment_production_gives_the_host_cookie(probe):
    out = probe(ENVIRONMENT="production", DATABASE_URL=PLACEHOLDER_URL)
    assert (out["is_production"], out["name"], out["flags"]["secure"]) == (True, "__Host-rinti_session", True)


def test_vercel_production_is_enough_even_without_environment_set(probe):
    # The live situation: ENVIRONMENT was never set, but Vercel marks the deployment as Production.
    out = probe(VERCEL="1", VERCEL_ENV="production", DATABASE_URL=PLACEHOLDER_URL)
    assert (out["is_production"], out["name"], out["flags"]["secure"]) == (True, "__Host-rinti_session", True)


@pytest.mark.parametrize("vercel_env", ["preview", "development"])
def test_other_vercel_environments_are_not_treated_as_production(probe, vercel_env):
    out = probe(VERCEL="1", VERCEL_ENV=vercel_env, DATABASE_URL=PLACEHOLDER_URL)
    assert (out["is_production"], out["name"], out["flags"]["secure"]) == (False, "rinti_session", False)


def test_the_production_cookie_satisfies_the_host_prefix_rules(probe):
    """Browsers silently reject a __Host- cookie unless it is Secure, Path=/ and has no Domain."""
    header = probe(VERCEL="1", VERCEL_ENV="production", DATABASE_URL=PLACEHOLDER_URL)["header"]
    assert header.startswith("__Host-rinti_session=")
    assert "; Secure" in header and "Path=/" in header
    assert "Domain" not in header
    assert "HttpOnly" in header and "SameSite=lax" in header
