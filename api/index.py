"""Vercel Serverless Function entrypoint for Rinti backend.

Mounts the FastAPI app so Vercel deploys it as a Function under /api/*.
The frontend's existing proxy routes at frontend/app/api/* will forward
to these functions automatically.
"""

import sys
import os

# Add the backend directory to sys.path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import app

# Vercel's Python runtime looks for an `app` variable
# This is the FastAPI instance that Vercel will mount
