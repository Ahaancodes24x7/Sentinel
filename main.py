"""
Sentinel Root Application Entry Point.
Proxies to the integrated FastAPI application in backend/main.py.

Run from Sentinel root:
  uvicorn backend.main:app --reload --port 8000
or:
  uvicorn main:app --reload --port 8000
"""

from backend.main import app

__all__ = ["app"]
