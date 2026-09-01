"""Supabase Auth with access/refresh tokens kept in HTTP-only cookies."""
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from urllib.parse import quote
import httpx
from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session
from app import store
from app.config import settings
from app.errors import AppError

ACCESS_COOKIE = "vs_access_token"
REFRESH_COOKIE = "vs_refresh_token"

def get_db() -> Iterator[Session]:
    db = store.SessionLocal()
    try: yield db
    finally: db.close()

def _headers(token: str | None = None) -> dict[str, str]:
    headers = {"apikey": settings.next_public_supabase_publishable_key, "Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    return headers

def _call(path: str, body: dict) -> dict:
    if not settings.next_public_supabase_url or not settings.next_public_supabase_publishable_key:
        raise AppError("invalid_request", "Supabase Auth is not configured.")
    try:
        response = httpx.post(f"{settings.next_public_supabase_url.rstrip('/')}/auth/v1/{path}", headers=_headers(), json=body, timeout=15)
    except httpx.HTTPError as exc:
        raise AppError("invalid_credentials", "Authentication service is unavailable.") from exc
    data = response.json()
    if response.status_code >= 400:
        message = data.get("msg") or data.get("message") or "Authentication failed."
        if response.status_code == 429:
            raise AppError("rate_limited", "Please wait before requesting another email.")
        raise AppError("email_taken" if "already" in message.lower() else "invalid_credentials", message)
    return data


def request_password_reset(email: str) -> None:
    """Ask Supabase to email a recovery link without revealing account existence."""
    redirect_url = f"{settings.public_app_url.rstrip('/')}/reset-password"
    _call(f"recover?redirect_to={quote(redirect_url, safe='')}", {"email": email})


def accept_recovery_session(
    db: Session, access_token: str, refresh_token: str, expires_in: int
) -> tuple[store.User, dict]:
    """Validate recovery-link tokens before moving them into HTTP-only cookies."""
    try:
        response = httpx.get(
            f"{settings.next_public_supabase_url.rstrip('/')}/auth/v1/user",
            headers=_headers(access_token),
            timeout=10,
        )
    except httpx.HTTPError as exc:
        raise AppError("invalid_credentials", "That recovery link could not be verified.") from exc
    if response.status_code != 200:
        raise AppError("invalid_credentials", "That recovery link is invalid or has expired.")
    session = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
    }
    return _profile(db, response.json()), session


def update_password_from_session(request: Request, response: Response, password: str) -> None:
    """Update the current Supabase user's password and end the recovery session."""
    access_token = request.cookies.get(ACCESS_COOKIE)
    if not access_token:
        raise AppError("unauthorized", "Open a fresh password recovery link first.")

    try:
        result = httpx.put(
            f"{settings.next_public_supabase_url.rstrip('/')}/auth/v1/user",
            headers=_headers(access_token),
            json={"password": password},
            timeout=15,
        )
    except httpx.HTTPError as exc:
        raise AppError("invalid_credentials", "The password could not be updated.") from exc

    if result.status_code >= 400:
        try:
            message = result.json().get("msg") or result.json().get("message")
        except ValueError:
            message = None
        raise AppError(
            "invalid_credentials",
            message or "That recovery session has expired. Request a new link.",
        )
    clear_session_cookie(response)

def _profile(db: Session, payload: dict) -> store.User:
    source = payload.get("user") or payload
    user_id, email = source.get("id"), source.get("email")
    if not user_id or not email: raise AppError("invalid_credentials", "Supabase returned an invalid user.")
    user = store.get_user_by_id(db, user_id)
    if user is None:
        raw = source.get("created_at")
        created = datetime.fromisoformat(raw.replace("Z", "+00:00")) if raw else None
        user = store.create_user(db, user_id, email, created)
    return user

def signup(db: Session, email: str, password: str) -> tuple[store.User, dict]:
    result = _call("signup", {"email": email, "password": password})
    if not result.get("access_token"):
        raise AppError("invalid_credentials", "Check your email to confirm your account, then sign in.")
    return _profile(db, result), result

def authenticate(db: Session, email: str, password: str) -> tuple[store.User, dict]:
    result = _call("token?grant_type=password", {"email": email, "password": password})
    return _profile(db, result), result

def set_session_cookies(response: Response, result: dict) -> None:
    options = dict(httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite, path="/")
    response.set_cookie(ACCESS_COOKIE, result["access_token"], max_age=int(result.get("expires_in", 3600)), **options)
    response.set_cookie(REFRESH_COOKIE, result["refresh_token"], max_age=settings.session_ttl_days * 86400, **options)

def clear_session_cookie(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(name, httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite, path="/")

def current_user(request: Request, response: Response, db: Session = Depends(get_db)) -> store.User:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token: raise AppError("unauthorized", "You need to sign in.")
    try:
        result = httpx.get(f"{settings.next_public_supabase_url.rstrip('/')}/auth/v1/user", headers=_headers(token), timeout=10)
    except httpx.HTTPError as exc:
        raise AppError("unauthorized", "Authentication service is unavailable.") from exc
    if result.status_code == 401 and request.cookies.get(REFRESH_COOKIE):
        refreshed = _call("token?grant_type=refresh_token", {"refresh_token": request.cookies[REFRESH_COOKIE]})
        set_session_cookies(response, refreshed)
        return _profile(db, refreshed)
    if result.status_code != 200: raise AppError("unauthorized", "Your session has expired. Please sign in again.")
    return _profile(db, result.json())
