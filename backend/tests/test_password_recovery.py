from starlette.requests import Request
from starlette.responses import Response

from app import auth
from app.config import settings


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


def test_password_reset_email_uses_the_configured_public_app(monkeypatch):
    captured = {}
    monkeypatch.setattr(settings, "public_app_url", "https://vacancyscore.vercel.app/")

    def fake_call(path: str, body: dict) -> dict:
        captured.update(path=path, body=body)
        return {}

    monkeypatch.setattr(auth, "_call", fake_call)
    auth.request_password_reset("person@example.com")

    assert captured == {
        "path": (
            "recover?redirect_to="
            "https%3A%2F%2Fvacancyscore.vercel.app%2Freset-password"
        ),
        "body": {"email": "person@example.com"},
    }


def test_password_update_uses_cookie_token_and_clears_recovery_session(monkeypatch):
    captured = {}

    def fake_put(url: str, *, headers: dict, json: dict, timeout: int):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return FakeResponse(200)

    monkeypatch.setattr(auth.httpx, "put", fake_put)
    request = Request(
        {
            "type": "http",
            "method": "PUT",
            "path": "/auth/password",
            "headers": [(b"cookie", b"vs_access_token=recovery-access-token")],
        }
    )
    response = Response()

    auth.update_password_from_session(request, response, "new-secure-password")

    assert captured["json"] == {"password": "new-secure-password"}
    assert captured["headers"]["Authorization"] == "Bearer recovery-access-token"
    cookies = response.headers.getlist("set-cookie")
    assert any(cookie.startswith("vs_access_token=") and "Max-Age=0" in cookie for cookie in cookies)
    assert any(cookie.startswith("vs_refresh_token=") and "Max-Age=0" in cookie for cookie in cookies)
