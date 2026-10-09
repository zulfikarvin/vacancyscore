"""Exercise the deployed /api prefix, cookies, uploads, and binary responses."""

from fastapi.testclient import TestClient

from api.index import app
from tests.conftest import SAMPLE_CV, SAMPLE_VACANCY


def test_deployed_health_and_docs():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        assert client.get("/api/openapi.json").status_code == 200
        assert client.get("/health").status_code == 404


def test_deployed_auth_and_cv_upload():
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/signup",
            json={"email": "vercel@example.com", "password": "correct-horse-battery"},
        )
        assert response.status_code == 201, response.text
        assert "vs_access_token" in client.cookies
        assert client.get("/api/auth/me").status_code == 200
        response = client.post(
            "/api/cvs",
            data={"label": "Deployment test"},
            files={"file": ("cv.txt", SAMPLE_CV.encode(), "text/plain")},
        )
        assert response.status_code == 201, response.text
        cv_id = response.json()["id"]
        assert client.get("/api/cvs").status_code == 200
        download = client.get(f"/api/cvs/{cv_id}/file?download=true")
        assert download.status_code == 200
        assert download.content == SAMPLE_CV.encode()
        analysis = client.post("/api/analyze", json={"vacancy_text": SAMPLE_VACANCY})
        assert analysis.status_code == 200, analysis.text
        report = client.get(f"/api/analyses/{analysis.json()['analysis_id']}/pdf")
        assert report.status_code == 200, report.text
        assert report.headers["content-type"] == "application/pdf"
        assert report.content.startswith(b"%PDF")
        assert client.post("/api/auth/logout").status_code == 200
        assert client.get("/api/auth/me").status_code == 401
        assert client.get("/api/does-not-exist").status_code == 404
