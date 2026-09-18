"""Vercel Serverless Function entrypoint for Rinti backend.

Mounts the FastAPI app so Vercel deploys it as a Function under /api/*.
Lives at frontend/api/index.py because the Vercel project's Root Directory
is set to frontend/ — Vercel only auto-detects Python Functions under the
Root Directory, so this file must be inside frontend/ rather than at the
repo root. The backend package itself was not moved; only this path
changed, so the relative lookup below goes up two levels (out of
frontend/api/, out of frontend/) to reach the sibling backend/ directory.
"""

import sys
import os

try:
    # Add the backend directory to sys.path so imports work.
    # __file__ is at <repo_root>/frontend/api/index.py, so backend/ is
    # two levels up (out of api/, out of frontend/), then into backend/.
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

    # Import and check config first
    from config import settings
    print(f"[OK] Config loaded: environment={settings.environment}, db_url_set={bool(settings.database_url)}")

    # Import the FastAPI app
    from main import app
    print("[OK] FastAPI app imported successfully")

except Exception as e:
    import traceback
    print(f"[ERROR] Failed to load app: {e}")
    traceback.print_exc()
    raise

# Vercel's Python runtime looks for an `app` variable
# This is the FastAPI instance that Vercel will mount
