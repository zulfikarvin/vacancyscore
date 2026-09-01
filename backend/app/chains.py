"""The analysis pipeline. No FastAPI imports -- the MCP server will call
`run_analysis` directly.

Three steps:

  1. Rank the user CVs locally with embeddings (free, milliseconds).
  2. Extract structured requirements from the vacancy (small Gemini call).
  3. Deep analysis of winning CV vs vacancy (main Gemini call, structured output).

Steps 2 and 3 are wired as one LCEL chain. Every prompt lives in this module as
a named constant.

`use_mock_llm` (or an absent GOOGLE_API_KEY) short-circuits steps 2 and 3 to a
hardcoded `VacancyAnalysis`, which is what the test suite and local frontend
work run against -- no test ever calls Gemini.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import re
from typing import TYPE_CHECKING

from pydantic import BaseModel

from app.config import settings
from app.embeddings import embed_vacancy, rank_by_similarity
from app.errors import AppError
from app.schemas import (
    CVScore,
    ExtractedRequirements,
    GapRow,
    MatchedKeyword,
    SubScores,
    VacancyAnalysis,
)

if TYPE_CHECKING:  # pragma: no cover - import kept out of the hot path
    from langchain_core.runnables import Runnable

# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------

REQUIREMENTS_EXTRACTION_PROMPT = """\
You extract the hiring requirements from a job vacancy.

Read the vacancy below and return structured data:
- role_title: the job title exactly as written.
- company: the hiring company, or an empty string if it is not stated.
- hard_requirements: the must-haves. Things the candidate is rejected for lacking.
- nice_to_haves: the preferred-but-optional items.
- keywords: a flat, de-duplicated list of concrete skills, tools, languages and
  domains a recruiter would search for. Use the vacancy wording.

Do not invent requirements that are not in the text. Do not editorialise.

VACANCY:
{vacancy_text}
"""

DEEP_ANALYSIS_PROMPT = """\
You are a blunt, experienced technical recruiter reviewing one CV against one \
vacancy. The candidate needs the truth, not encouragement.

RULES
1. Score honestly. Do not inflate. A CV missing several hard requirements is a
   weak fit even if it is a good CV in general. Reserve 85+ for candidates who
   would clearly reach an interview, and use the full range below 50.
2. Keyword matching is SEMANTIC, not literal. "ML" and "machine learning" are
   the same keyword; so are "PostgreSQL" and "Postgres", "REST APIs" and
   "building endpoints in FastAPI". Only list a keyword as matched if the CV
   genuinely evidences it, and say which section the evidence is in.
3. missing_keywords are requirements with no honest evidence anywhere in the CV.
   Never list something as both matched and missing.
4. Every gap row needs a specific, actionable suggested_fix -- an edit the
   candidate can make today to this CV. "Learn Kubernetes" is not acceptable;
   "Add the Helm chart you wrote for the checkout service to Projects, naming
   Kubernetes explicitly" is.
5. Set severity by how much the gap costs the application: high = a stated hard
   requirement is unevidenced, medium = weakly evidenced or buried, low =
   cosmetic or nice-to-have.
6. tips are at most 7 concrete edits, written as imperatives. Prefer edits that
   quantify: suggest the metric to add ("state the dataset size", "give the
   latency you cut it to"). No generic CV advice.
7. summary is at most 3 sentences: the verdict, the single biggest strength, the
   single biggest blocker.
8. fit_label is a short verdict such as "Strong fit", "Decent fit" or "Weak fit",
   consistent with fit_score.

EXTRACTED REQUIREMENTS
{requirements}

VACANCY
{vacancy_text}

CANDIDATE CV ("{cv_label}")
{cv_text}
"""

# --------------------------------------------------------------------------
# Inputs / outputs
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CVCandidate:
    """One of the user CVs, decoupled from the ORM row."""

    id: int
    label: str
    text: str
    embedding: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class AnalysisOutcome:
    recommended_cv_id: int
    cv_scores: list[CVScore]
    analysis: VacancyAnalysis
    sub_scores: SubScores
    title: str


# --------------------------------------------------------------------------
# Step 1 -- local CV ranking
# --------------------------------------------------------------------------


def rank_cvs(vacancy_text: str, candidates: list[CVCandidate]) -> tuple[CVCandidate, list[CVScore]]:
    """Pick the strongest credible CV that also fits the vacancy."""
    if not candidates:
        raise AppError("no_cvs", "Upload a CV before running an analysis.")

    by_id = {c.id: c for c in candidates}
    query = embed_vacancy(vacancy_text)
    ranked = rank_by_similarity(query, [(c.id, c.embedding) for c in candidates])

    scores = []
    for cv_id, similarity in ranked:
        strength = cv_strength_score(by_id[cv_id].text)
        # Strength is deliberately the larger share: a polished, evidenced CV
        # should beat a thin document with incidental keyword overlap, while
        # vacancy relevance still materially affects the recommendation.
        selection = round(strength * 0.55 + similarity * 0.45, 1)
        scores.append(
            CVScore(
                cv_id=cv_id,
                label=by_id[cv_id].label,
                similarity=similarity,
                strength_score=strength,
                selection_score=selection,
            )
        )
    scores.sort(key=lambda item: (item.selection_score, item.similarity), reverse=True)
    return by_id[scores[0].cv_id], scores


def cv_strength_score(text: str) -> float:
    """Estimate CV evidence quality without another paid model call.

    Rewards complete structure, quantified evidence, achievement language,
    readable detail and concrete bullet points. It never inspects identity,
    age, gender, photo, or other protected characteristics.
    """
    lowered = text.lower()
    section_patterns = {
        "experience": 10,
        "skills": 5,
        "education": 5,
        "summary": 5,
        "projects": 5,
    }
    sections = sum(
        weight
        for name, weight in section_patterns.items()
        if re.search(rf"(?m)^\s*(?:professional\s+)?{name}\b", lowered)
    )

    metrics = len(
        re.findall(
            r"(?:[$€£]\s?\d|\b\d+(?:[.,]\d+)?\s?(?:%|k|m|million|users|clients|projects|years|months|hours|days)\b)",
            lowered,
        )
    )
    quantified = min(metrics * 4, 24)

    impact_verbs = len(
        re.findall(
            r"\b(?:achieved|built|created|delivered|designed|developed|drove|grew|improved|increased|launched|led|managed|optimized|reduced|saved|scaled|streamlined)\b",
            lowered,
        )
    )
    impact = min(impact_verbs * 2, 20)

    detail = min(len(text) / 5_000 * 16, 16)
    bullet_lines = sum(1 for line in text.splitlines() if re.match(r"\s*[-•*]", line))
    bullets = min(bullet_lines, 10)

    words = re.findall(r"[a-z][a-z0-9+#.-]+", lowered)
    diversity = min((len(set(words)) / max(len(words), 1)) * 30, 10)
    return round(min(sections + quantified + impact + detail + bullets + diversity, 100), 1)


# --------------------------------------------------------------------------
# Steps 2 + 3 -- the LCEL chain
# --------------------------------------------------------------------------

#: Gemini is cheap but not free, and a 40-page CV adds nothing after the first
#: few pages. Truncation happens here rather than at upload so the stored text
#: stays complete for embedding and future re-analysis.
MAX_CV_CHARS_TO_LLM = 20_000
MAX_VACANCY_CHARS_TO_LLM = 15_000


@lru_cache(maxsize=2)
def get_llm(model: str | None = None):
    """A cached Gemini client for extraction or deep analysis."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model or settings.gemini_model,
        google_api_key=settings.google_api_key,
        # Low but not zero: the analysis should be stable across re-runs, while
        # the tips still need to read like prose rather than a template.
        temperature=0.2,
        max_retries=2,
        timeout=90,
    )


def structured_llm(schema: type[BaseModel]) -> Runnable:
    """`llm.with_structured_output(schema)`.

    Isolated in one function so tests can swap the model out without touching
    the chain graph itself.
    """
    model = (
        settings.gemini_extraction_model
        if schema is ExtractedRequirements
        else settings.gemini_model
    )
    return get_llm(model).with_structured_output(schema)


def format_requirements(requirements: ExtractedRequirements) -> str:
    """Render step 2 output as the prompt block step 3 reads."""
    lines = []
    if requirements.role_title:
        lines.append(f"Role: {requirements.role_title}")
    if requirements.company:
        lines.append(f"Company: {requirements.company}")
    lines.append("Hard requirements:")
    lines.extend(f"  - {item}" for item in requirements.hard_requirements or ["(none stated)"])
    lines.append("Nice to have:")
    lines.extend(f"  - {item}" for item in requirements.nice_to_haves or ["(none stated)"])
    lines.append(f"Keywords: {', '.join(requirements.keywords) or '(none)'}")
    return "\n".join(lines)


def build_analysis_chain() -> Runnable:
    """Steps 2 and 3 fused into a single LCEL chain.

    Input:  {vacancy_text, cv_label, cv_text}
    Output: the same dict plus `extracted` (ExtractedRequirements) and
            `analysis` (VacancyAnalysis).

    `extracted` is carried through rather than discarded because the history
    title uses the role and company it found.
    """
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnableLambda, RunnablePassthrough

    extraction = (
        ChatPromptTemplate.from_template(REQUIREMENTS_EXTRACTION_PROMPT)
        | structured_llm(ExtractedRequirements)
    )
    analysis = (
        ChatPromptTemplate.from_template(DEEP_ANALYSIS_PROMPT)
        | structured_llm(VacancyAnalysis)
    )

    return (
        RunnablePassthrough.assign(extracted=extraction)
        | RunnablePassthrough.assign(
            requirements=RunnableLambda(lambda data: format_requirements(data["extracted"]))
        )
        | RunnablePassthrough.assign(analysis=analysis)
    )


def chain_inputs(vacancy_text: str, cv: CVCandidate) -> dict[str, str]:
    return {
        "vacancy_text": vacancy_text[:MAX_VACANCY_CHARS_TO_LLM],
        "cv_label": cv.label,
        "cv_text": cv.text[:MAX_CV_CHARS_TO_LLM],
    }


def analyse_with_llm(
    vacancy_text: str, cv: CVCandidate
) -> tuple[ExtractedRequirements, VacancyAnalysis]:
    """Run the fused chain, turning any Gemini failure into a typed error."""
    try:
        result = build_analysis_chain().invoke(chain_inputs(vacancy_text, cv))
    except Exception as exc:  # noqa: BLE001 - see _llm_error for the triage
        raise _llm_error(exc) from exc
    return result["extracted"], result["analysis"]


def extract_requirements(vacancy_text: str) -> ExtractedRequirements:
    """Step 2 on its own. Kept addressable for the future MCP server."""
    if not settings.llm_enabled:
        return _mock_requirements()
    from langchain_core.prompts import ChatPromptTemplate

    chain = (
        ChatPromptTemplate.from_template(REQUIREMENTS_EXTRACTION_PROMPT)
        | structured_llm(ExtractedRequirements)
    )
    try:
        return chain.invoke({"vacancy_text": vacancy_text[:MAX_VACANCY_CHARS_TO_LLM]})
    except Exception as exc:  # noqa: BLE001
        raise _llm_error(exc) from exc


def deep_analysis(
    vacancy_text: str, cv: CVCandidate, requirements: ExtractedRequirements
) -> VacancyAnalysis:
    """Step 3 on its own, given requirements you already have."""
    if not settings.llm_enabled:
        return _mock_analysis(cv.label)
    from langchain_core.prompts import ChatPromptTemplate

    chain = (
        ChatPromptTemplate.from_template(DEEP_ANALYSIS_PROMPT)
        | structured_llm(VacancyAnalysis)
    )
    payload = chain_inputs(vacancy_text, cv) | {
        "requirements": format_requirements(requirements)
    }
    try:
        return chain.invoke(payload)
    except Exception as exc:  # noqa: BLE001
        raise _llm_error(exc) from exc


def _llm_error(exc: Exception) -> AppError:
    """Map a Gemini/LangChain failure onto something the UI can show.

    Quota exhaustion is the one the shared demo key actually hits, so it gets
    its own message; everything else is one honest "try again".
    """
    if isinstance(exc, AppError):
        return exc

    name = type(exc).__name__
    text = str(exc).lower()

    if name in {"ResourceExhausted", "TooManyRequests"} or "quota" in text or "429" in text:
        return AppError(
            "llm_unavailable",
            "The shared Gemini quota is used up for now. Try again a little later.",
            {"reason": name},
        )
    if name == "ValidationError":
        return AppError(
            "llm_unavailable",
            "The model returned an analysis that did not fit the expected shape. Try again.",
            {"reason": name},
        )
    return AppError(
        "llm_unavailable",
        "The analysis service is not responding right now. Try again in a moment.",
        {"reason": name},
    )


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def run_analysis(vacancy_text: str, candidates: list[CVCandidate]) -> AnalysisOutcome:
    """Full pipeline. The only entry point routes (and later MCP tools) need."""
    winner, cv_scores = rank_cvs(vacancy_text, candidates)

    if settings.llm_enabled:
        requirements, analysis = analyse_with_llm(vacancy_text, winner)
    else:
        requirements = _mock_requirements()
        analysis = _mock_analysis(winner.label)

    return AnalysisOutcome(
        recommended_cv_id=winner.id,
        cv_scores=cv_scores,
        analysis=analysis,
        sub_scores=derive_sub_scores(analysis),
        title=derive_title(vacancy_text, requirements),
    )


# --------------------------------------------------------------------------
# Derived display values
# --------------------------------------------------------------------------

_SEVERITY_PENALTY = {"high": 20, "medium": 12, "low": 5}


def derive_sub_scores(analysis: VacancyAnalysis) -> SubScores:
    """The three progress bars on the hero card.

    Heuristics, not a second LLM call -- they are presentation detail and must
    stay consistent with `fit_score`, which is the number that actually matters.

    * skills  -- share of required keywords the CV evidences.
    * profile -- 100 minus a severity-weighted penalty for each gap row.
    * summary -- how the overall verdict reads, weighted towards `fit_score`.
    """
    matched = len(analysis.matched_keywords)
    missing = len(analysis.missing_keywords)
    total = matched + missing
    skills = round(matched / total * 100) if total else analysis.fit_score

    penalty = sum(_SEVERITY_PENALTY.get(gap.severity, 10) for gap in analysis.gaps)
    profile = max(0, 100 - penalty)

    summary = round((analysis.fit_score * 2 + skills + profile) / 4)
    return SubScores(
        profile=_clamp(profile), skills=_clamp(skills), summary=_clamp(summary)
    )


def derive_title(vacancy_text: str, requirements: ExtractedRequirements | None = None) -> str:
    """Return every history-row title in the stable ``Role - Company`` shape."""
    role = requirements.role_title.strip() if requirements else ""
    company = requirements.company.strip() if requirements else ""

    # Mock mode or a failed extraction can leave the role empty. The first
    # non-empty vacancy line is still a useful, non-invented fallback for it.
    if not role:
        role = next(
            (line.strip() for line in vacancy_text.splitlines() if line.strip()),
            "Role not specified",
        )

    role = " ".join(role.split()) or "Role not specified"
    company = " ".join(company.split()) or "Company not specified"

    # AnalysisRow.title is VARCHAR(160). Keeping each side to 78 characters
    # guarantees the separator and both values are retained.
    return f"{role[:78]} - {company[:79]}"


def normalize_history_title(title: str) -> str:
    """Give legacy saved rows the same shape without inventing a company."""
    cleaned = " ".join(title.split())
    if " - " in cleaned:
        return cleaned[:160]
    return derive_title(cleaned)


def _clamp(value: int) -> int:
    return max(0, min(100, int(value)))


# --------------------------------------------------------------------------
# Step-1 mock (also the fixture the frontend is built against)
# --------------------------------------------------------------------------


def _mock_requirements() -> ExtractedRequirements:
    return ExtractedRequirements(
        # Left blank on purpose: mock-mode titles use the vacancy's first line
        # for the role and the explicit missing-company placeholder.
        role_title="",
        company="",
        hard_requirements=[
            "3+ years Python in production",
            "FastAPI or similar async web framework",
            "PostgreSQL and schema design",
            "Docker and CI/CD",
            "LLM application experience (RAG, structured output)",
        ],
        nice_to_haves=["Kubernetes", "Terraform", "Open-source contributions"],
        keywords=[
            "Python",
            "FastAPI",
            "PostgreSQL",
            "Docker",
            "CI/CD",
            "LangChain",
            "RAG",
            "Kubernetes",
            "Terraform",
            "pytest",
        ],
    )


def _mock_analysis(cv_label: str = "CV") -> VacancyAnalysis:
    return VacancyAnalysis(
        fit_score=64,
        fit_label="Decent fit",
        summary=(
            f"{cv_label} covers the core Python and API work this role is built on, and the "
            "LangChain project is directly relevant. The gap is infrastructure: nothing in the "
            "CV evidences Docker, CI/CD or any deployment ownership. Tighten the platform "
            "story and this becomes an interview."
        ),
        matched_keywords=[
            MatchedKeyword(keyword="Python", location="Skills"),
            MatchedKeyword(keyword="FastAPI", location="Experience"),
            MatchedKeyword(keyword="PostgreSQL", location="Experience"),
            MatchedKeyword(keyword="LangChain", location="Projects"),
            MatchedKeyword(keyword="RAG", location="Projects"),
            MatchedKeyword(keyword="pytest", location="Skills"),
        ],
        missing_keywords=["Docker", "CI/CD", "Kubernetes", "Terraform"],
        gaps=[
            GapRow(
                requirement="Docker and CI/CD",
                cv_evidence="",
                severity="high",
                suggested_fix=(
                    "Add a Deployment line to your most recent role naming Docker and the CI "
                    "provider you used, and say what the pipeline ran (tests, build, deploy)."
                ),
            ),
            GapRow(
                requirement="3+ years Python in production",
                cv_evidence="Two roles listing Python, dates suggest around 2.5 years.",
                severity="medium",
                suggested_fix=(
                    "State total Python experience explicitly in your summary line, counting "
                    "the freelance work you currently list without dates."
                ),
            ),
            GapRow(
                requirement="PostgreSQL and schema design",
                cv_evidence="PostgreSQL listed under Skills only.",
                severity="medium",
                suggested_fix=(
                    "Move PostgreSQL into an Experience bullet: name a schema you designed, "
                    "the table count, and the query time you improved."
                ),
            ),
            GapRow(
                requirement="Kubernetes",
                cv_evidence="",
                severity="low",
                suggested_fix=(
                    "Nice-to-have only. If you have touched Helm or kubectl at all, add one "
                    "line under Tools rather than leaving it blank."
                ),
            ),
        ],
        tips=[
            "Add a Deployment bullet naming Docker and your CI provider to the most recent role.",
            "Quantify the RAG project: corpus size, retrieval latency, and accuracy delta.",
            "Move PostgreSQL out of the skills list and into a results-bearing bullet.",
            "State total years of production Python in the opening summary line.",
            "Rename the Projects heading to lead with the LangChain work, not the coursework.",
            "Cut the 2019 internship bullet to one line to make room for platform detail.",
        ],
    )
