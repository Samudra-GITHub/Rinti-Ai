"""Vercel Serverless Function entrypoint for Rinti backend.

Mounts the FastAPI app so Vercel deploys it as a Function under /api/*.
"""

import sys
import os

try:
    # Add the backend directory to sys.path so imports work
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

    # Import and check config first
    from config import settings
    print(f"✓ Config loaded: environment={settings.environment}, db_url_set={bool(settings.database_url)}")

    # Import the FastAPI app
    from main import app
    print("✓ FastAPI app imported successfully")

except Exception as e:
    import traceback
    print(f"✗ Failed to load app: {e}")
    traceback.print_exc()
    raise

# Vercel's Python runtime looks for an `app` variable
# This is the FastAPI instance that Vercel will mount
