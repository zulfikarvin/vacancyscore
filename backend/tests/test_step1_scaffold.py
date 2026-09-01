"""Step-1 checks: auth, user scoping and the mocked analyze flow.

The full suite (including the LLM-mocking tests) arrives in build step 5; these
exist so the scaffold is verified rather than assumed.
"""

from __future__ import annotations

from tests.conftest import SAMPLE_VACANCY, upload_cv


def test_health_reports_mock_llm(client):
    body = client.get("/health").json()
    assert body == {"status": "ok", "llm": "mock"}


def test_signup_logs_the_user_in(client):
    response = client.post(
        "/auth/signup", json={"email": "Jane@Example.com", "password": "correct-horse"}
    )
    assert response.status_code == 201
    assert response.json()["email"] == "jane@example.com"
    assert client.get("/auth/me").status_code == 200


def test_duplicate_email_is_rejected(client):
    payload = {"email": "dup@example.com", "password": "correct-horse"}
    client.post("/auth/signup", json=payload)
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 409
    assert response.json()["code"] == "email_taken"


def test_wrong_password_gives_typed_error(client):
    client.post("/auth/signup", json={"email": "a@example.com", "password": "correct-horse"})
    response = client.post("/auth/login", json={"email": "a@example.com", "password": "wrong-pass"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_password_is_not_stored_in_application_database(client):
    from app import store

    client.post("/auth/signup", json={"email": "hash@example.com", "password": "correct-horse"})
    with store.session_scope() as session:
        user = store.get_user_by_email(session, "hash@example.com")
        assert user is not None
        assert not hasattr(user, "password")
        assert not hasattr(user, "password_hash")


def test_protected_routes_require_authentication(client):
    for method, path in [
        ("get", "/cvs"),
        ("get", "/analyses"),
        ("get", "/auth/me"),
    ]:
        response = getattr(client, method)(path)
        assert response.status_code == 401, path
        assert response.json()["code"] == "unauthorized"


def test_analyze_returns_the_mock_analysis(make_user):
    alice = make_user("alice@example.com")
    assert upload_cv(alice, "Backend CV").status_code == 201

    response = alice.post("/analyze", json={"vacancy_text": SAMPLE_VACANCY})
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["recommended_cv"]["label"] == "Backend CV"
    assert 0 <= body["analysis"]["fit_score"] <= 100
    assert body["analysis"]["tips"]
    assert len(body["analysis"]["tips"]) <= 7
    assert set(body["sub_scores"]) == {"profile", "skills", "summary"}
    assert body["cv_scores"][0]["cv_id"] == body["recommended_cv"]["id"]

    history = alice.get("/analyses").json()
    assert len(history) == 1
    assert history[0]["id"] == body["analysis_id"]


def test_analyze_without_a_cv_is_a_typed_error(make_user):
    alice = make_user("alice@example.com")
    response = alice.post("/analyze", json={"vacancy_text": SAMPLE_VACANCY})
    assert response.status_code == 400
    assert response.json()["code"] == "no_cvs"


def test_best_matching_cv_wins(make_user):
    alice = make_user("alice@example.com")
    upload_cv(alice, "Backend CV")
    upload_cv(
        alice,
        "Pastry CV",
        "Pierre Doe\n\nEXPERIENCE\nHead pastry chef. Laminated doughs, viennoiserie, "
        "seasonal dessert menus for a 90-cover restaurant.\n\nSKILLS\nBaking, plating, "
        "kitchen management, food costing, supplier negotiation.\n",
    )

    body = alice.post("/analyze", json={"vacancy_text": SAMPLE_VACANCY}).json()
    assert body["recommended_cv"]["label"] == "Backend CV"
    assert body["cv_scores"][0]["similarity"] >= body["cv_scores"][1]["similarity"]


# --------------------------------------------------------------------------
# Cross-user isolation -- the failure mode to guard hardest against
# --------------------------------------------------------------------------


def test_users_cannot_see_each_others_cvs(make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    alice_cv_id = upload_cv(alice, "Alice CV").json()["id"]

    assert bob.get("/cvs").json() == []
    assert bob.delete(f"/cvs/{alice_cv_id}").status_code == 404
    # ... and the delete really did not happen.
    assert [cv["id"] for cv in alice.get("/cvs").json()] == [alice_cv_id]


def test_users_cannot_read_or_delete_each_others_analyses(make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    upload_cv(alice, "Alice CV")
    analysis_id = alice.post("/analyze", json={"vacancy_text": SAMPLE_VACANCY}).json()["analysis_id"]

    assert bob.get("/analyses").json() == []
    assert bob.get(f"/analyses/{analysis_id}").status_code == 404
    assert bob.delete(f"/analyses/{analysis_id}").status_code == 404
    assert alice.get(f"/analyses/{analysis_id}").status_code == 200


def test_a_forged_session_cookie_is_rejected(client):
    client.cookies.set("vs_access_token", "forged-token")
    assert client.get("/auth/me").status_code == 401


# --------------------------------------------------------------------------
# Limits
# --------------------------------------------------------------------------


def test_cv_quota_is_enforced(make_user, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "max_cvs_per_user", 2)
    alice = make_user("alice@example.com")
    assert upload_cv(alice, "One").status_code == 201
    assert upload_cv(alice, "Two").status_code == 201

    response = upload_cv(alice, "Three")
    assert response.status_code == 409
    assert response.json()["code"] == "cv_limit_reached"


def test_daily_analyze_limit_is_enforced(make_user, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "analyze_daily_limit", 1)
    alice = make_user("alice@example.com")
    upload_cv(alice, "Alice CV")

    assert alice.post("/analyze", json={"vacancy_text": SAMPLE_VACANCY}).status_code == 200
    response = alice.post("/analyze", json={"vacancy_text": SAMPLE_VACANCY})
    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
    assert response.json()["detail"]["limit"] == 1


def test_the_rate_limit_is_per_user(make_user, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "analyze_daily_limit", 1)
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    upload_cv(alice, "Alice CV")
    upload_cv(bob, "Bob CV")

    assert alice.post("/analyze", json={"vacancy_text": SAMPLE_VACANCY}).status_code == 200
    assert alice.post("/analyze", json={"vacancy_text": SAMPLE_VACANCY}).status_code == 429
    # Alice hitting her limit must not spend Bob's quota.
    assert bob.post("/analyze", json={"vacancy_text": SAMPLE_VACANCY}).status_code == 200


def test_oversized_vacancy_is_rejected(make_user, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "max_vacancy_chars", 200)
    alice = make_user("alice@example.com")
    upload_cv(alice, "Alice CV")

    response = alice.post("/analyze", json={"vacancy_text": "x " * 500})
    assert response.status_code == 413
    assert response.json()["code"] == "vacancy_too_long"


def test_unsupported_file_type_is_rejected(make_user):
    alice = make_user("alice@example.com")
    response = alice.post(
        "/cvs",
        data={"label": "Screenshot"},
        files={"file": ("cv.png", b"\x89PNG\r\n\x1a\n" + b"0" * 400, "image/png")},
    )
    assert response.status_code == 415
    assert response.json()["code"] == "unsupported_file_type"
