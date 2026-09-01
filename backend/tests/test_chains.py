"""The LCEL pipeline, with Gemini replaced by a recording stub.

No test in this file (or any other) opens a network connection: `structured_llm`
is the single seam the whole chain goes through, so patching it swaps the model
out without touching the chain graph being tested.
"""

from __future__ import annotations

import pytest
from langchain_core.runnables import RunnableLambda

from app import chains
from app.chains import CVCandidate
from app.errors import AppError
from app.schemas import ExtractedRequirements, GapRow, MatchedKeyword, VacancyAnalysis
from tests.conftest import SAMPLE_CV, SAMPLE_VACANCY, upload_cv

FAKE_REQUIREMENTS = ExtractedRequirements(
    role_title="Backend Engineer (AI Platform)",
    company="Northwind Labs",
    hard_requirements=["3+ years Python", "FastAPI"],
    nice_to_haves=["Kubernetes"],
    keywords=["Python", "FastAPI", "Docker"],
)

FAKE_ANALYSIS = VacancyAnalysis(
    fit_score=71,
    fit_label="Decent fit",
    summary="Solid Python, thin on infrastructure.",
    matched_keywords=[MatchedKeyword(keyword="Python", location="Skills")],
    missing_keywords=["Docker"],
    gaps=[
        GapRow(
            requirement="Docker",
            cv_evidence="",
            severity="high",
            suggested_fix="Add a Deployment bullet naming Docker.",
        )
    ],
    tips=["Quantify the RAG project."],
)


@pytest.fixture
def recording_llm(monkeypatch):
    """Patch the model seam and record every prompt it is handed."""
    prompts: list[tuple[str, str]] = []

    def factory(schema):
        def run(prompt_value):
            prompts.append((schema.__name__, prompt_value.to_string()))
            return FAKE_REQUIREMENTS if schema is ExtractedRequirements else FAKE_ANALYSIS

        return RunnableLambda(run)

    monkeypatch.setattr(chains, "structured_llm", factory)
    return prompts


@pytest.fixture
def live_llm_settings(monkeypatch):
    """Flip `llm_enabled` on without ever reaching Google."""
    from app import embeddings
    from app.config import settings

    # Prime the embedder cache while the mock flag is still set, so flipping it
    # cannot trigger a HuggingFace model download inside a test.
    embeddings.get_embedder()
    monkeypatch.setattr(settings, "google_api_key", "test-key-never-used")
    monkeypatch.setattr(settings, "use_mock_llm", False)
    return settings


# --------------------------------------------------------------------------
# The fused chain
# --------------------------------------------------------------------------


def test_chain_runs_extraction_then_analysis(recording_llm):
    result = chains.build_analysis_chain().invoke(
        {"vacancy_text": SAMPLE_VACANCY, "cv_label": "Backend CV", "cv_text": SAMPLE_CV}
    )

    assert result["extracted"] == FAKE_REQUIREMENTS
    assert result["analysis"] == FAKE_ANALYSIS

    schemas_called = [name for name, _ in recording_llm]
    assert schemas_called == ["ExtractedRequirements", "VacancyAnalysis"]


def test_extraction_prompt_sees_only_the_vacancy(recording_llm):
    chains.build_analysis_chain().invoke(
        {"vacancy_text": SAMPLE_VACANCY, "cv_label": "Backend CV", "cv_text": SAMPLE_CV}
    )
    _, extraction_prompt = recording_llm[0]

    assert "Northwind Labs" in extraction_prompt  # from the vacancy text
    assert "Jane Doe" not in extraction_prompt  # the CV is not sent in step 2


def test_analysis_prompt_carries_cv_vacancy_and_extracted_requirements(recording_llm):
    chains.build_analysis_chain().invoke(
        {"vacancy_text": SAMPLE_VACANCY, "cv_label": "Backend CV", "cv_text": SAMPLE_CV}
    )
    _, analysis_prompt = recording_llm[1]

    assert "Backend CV" in analysis_prompt
    assert "Jane Doe" in analysis_prompt
    assert "Backend Engineer (AI Platform)" in analysis_prompt  # step 2 output
    assert "3+ years Python" in analysis_prompt
    assert "Do not inflate" in analysis_prompt  # the honesty rule survives


def test_long_inputs_are_truncated_before_they_reach_the_model(recording_llm):
    huge_cv = "x" * (chains.MAX_CV_CHARS_TO_LLM + 5_000)
    chains.analyse_with_llm(
        SAMPLE_VACANCY, CVCandidate(id=1, label="Huge", text=huge_cv, embedding=[])
    )
    _, analysis_prompt = recording_llm[1]

    # Count the run rather than every "x", since the prompt itself contains some.
    assert "x" * chains.MAX_CV_CHARS_TO_LLM in analysis_prompt
    assert "x" * (chains.MAX_CV_CHARS_TO_LLM + 1) not in analysis_prompt


def test_individual_steps_are_still_callable(recording_llm, live_llm_settings):
    requirements = chains.extract_requirements(SAMPLE_VACANCY)
    assert requirements == FAKE_REQUIREMENTS

    analysis = chains.deep_analysis(
        SAMPLE_VACANCY,
        CVCandidate(id=1, label="Backend CV", text=SAMPLE_CV, embedding=[]),
        requirements,
    )
    assert analysis == FAKE_ANALYSIS


# --------------------------------------------------------------------------
# Error mapping
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("exception", "fragment"),
    [
        (type("ResourceExhausted", (Exception,), {})("429 quota"), "quota is used up"),
        (type("ValidationError", (Exception,), {})("bad shape"), "did not fit the expected shape"),
        (RuntimeError("connection reset"), "not responding right now"),
    ],
)
def test_gemini_failures_become_typed_errors(exception, fragment, monkeypatch):
    def exploding(schema):
        return RunnableLambda(lambda _: (_ for _ in ()).throw(exception))

    monkeypatch.setattr(chains, "structured_llm", exploding)

    with pytest.raises(AppError) as caught:
        chains.analyse_with_llm(
            SAMPLE_VACANCY, CVCandidate(id=1, label="CV", text=SAMPLE_CV, embedding=[])
        )

    assert caught.value.code == "llm_unavailable"
    assert fragment in caught.value.message


def test_analyze_route_surfaces_llm_failure_as_503(
    make_user, monkeypatch, live_llm_settings
):
    def exploding(schema):
        return RunnableLambda(lambda _: (_ for _ in ()).throw(RuntimeError("boom")))

    monkeypatch.setattr(chains, "structured_llm", exploding)

    alice = make_user("alice@example.com")
    upload_cv(alice, "Backend CV")
    response = alice.post("/analyze", json={"vacancy_text": SAMPLE_VACANCY})

    assert response.status_code == 503
    assert response.json()["code"] == "llm_unavailable"


def test_analyze_route_uses_the_chain_when_the_llm_is_enabled(
    make_user, recording_llm, live_llm_settings
):
    alice = make_user("alice@example.com")
    upload_cv(alice, "Backend CV")

    body = alice.post("/analyze", json={"vacancy_text": SAMPLE_VACANCY}).json()

    assert body["analysis"]["fit_score"] == 71
    assert body["analysis"]["fit_label"] == "Decent fit"
    # The history title comes from what step 2 extracted, not the pasted text.
    assert (
        alice.get("/analyses").json()[0]["title"]
        == "Backend Engineer (AI Platform) - Northwind Labs"
    )


# --------------------------------------------------------------------------
# Derived values
# --------------------------------------------------------------------------


def test_format_requirements_is_readable_for_the_prompt():
    rendered = chains.format_requirements(FAKE_REQUIREMENTS)
    assert "Role: Backend Engineer (AI Platform)" in rendered
    assert "Company: Northwind Labs" in rendered
    assert "  - FastAPI" in rendered
    assert "Keywords: Python, FastAPI, Docker" in rendered


def test_sub_scores_track_keyword_coverage_and_gap_severity():
    sub = chains.derive_sub_scores(FAKE_ANALYSIS)
    assert sub.skills == 50  # 1 matched of 2 total keywords
    assert sub.profile == 80  # one high-severity gap costs 20
    assert 0 <= sub.summary <= 100


def test_sub_scores_survive_an_empty_analysis():
    empty = VacancyAnalysis(fit_score=0, fit_label="Weak fit", summary="")
    sub = chains.derive_sub_scores(empty)
    assert (sub.profile, sub.skills, sub.summary) == (100, 0, 25)


def test_title_is_always_role_dash_company():
    assert (
        chains.derive_title("ignored", FAKE_REQUIREMENTS)
        == "Backend Engineer (AI Platform) - Northwind Labs"
    )
    assert (
        chains.derive_title("\n\n  Senior Dev at Acme  \nrest")
        == "Senior Dev at Acme - Company not specified"
    )
    assert (
        chains.derive_title("   ")
        == "Role not specified - Company not specified"
    )


def test_title_keeps_the_shape_when_only_one_extracted_field_is_missing():
    no_company = FAKE_REQUIREMENTS.model_copy(update={"company": ""})
    no_role = FAKE_REQUIREMENTS.model_copy(update={"role_title": ""})

    assert (
        chains.derive_title("ignored", no_company)
        == "Backend Engineer (AI Platform) - Company not specified"
    )
    assert chains.derive_title("Fallback role", no_role) == "Fallback role - Northwind Labs"


def test_legacy_history_titles_are_normalized_for_display():
    assert chains.normalize_history_title("Data Analyst") == (
        "Data Analyst - Company not specified"
    )
    assert chains.normalize_history_title("Data Analyst - Acme") == "Data Analyst - Acme"
