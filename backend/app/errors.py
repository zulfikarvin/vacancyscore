"""Typed application errors.

Every failure the frontend is expected to render goes through `AppError`, which
serialises to the `ErrorResponse` schema. Routes raise these; a single exception
handler in `main.py` turns them into JSON.
"""

from __future__ import annotations

from app.schemas import ErrorCode

_STATUS: dict[str, int] = {
    "invalid_request": 422,
    "unauthorized": 401,
    "not_found": 404,
    "email_taken": 409,
    "invalid_credentials": 401,
    "no_cvs": 400,
    "cv_limit_reached": 409,
    "vacancy_too_long": 413,
    "file_too_large": 413,
    "unsupported_file_type": 415,
    "unreadable_file": 422,
    "rate_limited": 429,
    "llm_unavailable": 503,
}


class AppError(Exception):
    """Raised anywhere in the app; rendered as `ErrorResponse` by FastAPI."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        detail: dict[str, str | int] | None = None,
    ) -> None:
        super().__init__(message)
        self.code: ErrorCode = code
        self.message = message
        self.detail = detail

    @property
    def status_code(self) -> int:
        return _STATUS.get(self.code, 400)
