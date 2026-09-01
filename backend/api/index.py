"""Vercel Python Function entrypoint for the VacancyScore FastAPI app."""

from app.main import app

__all__ = ["app"]
