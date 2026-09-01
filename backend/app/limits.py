"""Abuse protection.

The Gemini key and its quota are shared by every user of the deployed demo, so
each guard here is the difference between a portfolio project and a free LLM
proxy for the internet. All limits come from env vars via `settings`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import store
from app.config import settings
from app.errors import AppError


def start_of_utc_day(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def check_analyze_rate_limit(session: Session, user_id: str) -> None:
    """At most `ANALYZE_DAILY_LIMIT` analyses per user per UTC day."""
    since = start_of_utc_day()
    used = store.count_analyses_since(session, user_id, since)
    if used >= settings.analyze_daily_limit:
        resets_at = since + timedelta(days=1)
        raise AppError(
            "rate_limited",
            f"Daily limit reached ({settings.analyze_daily_limit} analyses). "
            "The counter resets at midnight UTC.",
            {
                "limit": settings.analyze_daily_limit,
                "used": used,
                "resets_at": resets_at.isoformat(),
            },
        )


def check_cv_quota(session: Session, user_id: str) -> None:
    stored = store.count_cvs(session, user_id)
    if stored >= settings.max_cvs_per_user:
        raise AppError(
            "cv_limit_reached",
            f"You can store up to {settings.max_cvs_per_user} CVs. Delete one to upload another.",
            {"limit": settings.max_cvs_per_user, "stored": stored},
        )


def check_vacancy_length(vacancy_text: str) -> None:
    if len(vacancy_text) > settings.max_vacancy_chars:
        raise AppError(
            "vacancy_too_long",
            f"That vacancy is {len(vacancy_text):,} characters. "
            f"The maximum is {settings.max_vacancy_chars:,} -- paste the description only.",
            {"limit": settings.max_vacancy_chars, "length": len(vacancy_text)},
        )


def check_upload_size(size_bytes: int) -> None:
    if size_bytes > settings.max_upload_bytes:
        raise AppError(
            "file_too_large",
            f"That file is larger than {settings.max_upload_bytes // (1024 * 1024)}MB.",
            {"limit": settings.max_upload_bytes, "size": size_bytes},
        )
