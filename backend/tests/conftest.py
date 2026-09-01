"""Test configuration.

Env vars are set *before* importing anything from `app`, because `app.config`
builds a single cached `Settings` instance at import time.

No test ever reaches Gemini: `USE_MOCK_LLM=true` keeps `chains` on the
hardcoded analysis and `embeddings` on the deterministic hashing embedder.
"""

from __future__ import annotations

import os
import tempfile

_TMP_DB = os.path.join(tempfile.mkdtemp(prefix="vacancyscore-tests-"), "test.db")

os.environ.update(
    DATABASE_URL=f"sqlite:///{_TMP_DB}",
    SECRET_KEY="test-secret-key-not-used-in-production",
    USE_MOCK_LLM="true",
    GOOGLE_API_KEY="",
    ENVIRONMENT="dev",
    ANALYZE_DAILY_LIMIT="10",
    MAX_CVS_PER_USER="10",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import store  # noqa: E402
from app.main import app  # noqa: E402

SAMPLE_CV = (
    "Jane Doe\n\n"
    "SUMMARY\nBackend engineer with production Python experience.\n\n"
    "EXPERIENCE\nBuilt FastAPI services backed by PostgreSQL for a payments team.\n\n"
    "PROJECTS\nRetrieval-augmented chatbot using LangChain and local embeddings.\n\n"
    "SKILLS\nPython, FastAPI, PostgreSQL, pytest, SQLAlchemy, LangChain\n"
)

SAMPLE_VACANCY = (
    "Backend Engineer (AI Platform) at Northwind Labs\n\n"
    "We are looking for a backend engineer to build and operate our LLM platform. "
    "You will design FastAPI services, own PostgreSQL schemas, and ship them with "
    "Docker and CI/CD. Experience with LangChain, RAG and structured output is "
    "strongly preferred. Kubernetes and Terraform are nice to have.\n"
)


@pytest.fixture(autouse=True)
def clean_database():
    """Every test starts from an empty schema."""
    store.Base.metadata.drop_all(store.engine)
    store.Base.metadata.create_all(store.engine)
    yield
    store.Base.metadata.drop_all(store.engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(client):
    """Return a factory producing an authenticated client for a fresh account."""

    def _make(email: str, password: str = "correct-horse-battery") -> TestClient:
        session_client = TestClient(app)
        response = session_client.post(
            "/auth/signup", json={"email": email, "password": password}
        )
        assert response.status_code == 201, response.text
        return session_client

    return _make


def upload_cv(session_client: TestClient, label: str, text: str = SAMPLE_CV):
    return session_client.post(
        "/cvs",
        data={"label": label},
        files={"file": (f"{label}.txt", text.encode("utf-8"), "text/plain")},
    )
