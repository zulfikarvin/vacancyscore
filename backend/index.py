"""Conventional Vercel FastAPI entrypoint.

Vercel discovers a root-level index.py automatically. The application itself
remains in app.main so local Uvicorn and Vercel run identical code.
"""

from app.main import app

__all__ = ["app"]
