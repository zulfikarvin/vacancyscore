"""Pydantic v2 schemas -- the single source of truth.

These models drive three things at once:
  1. LLM structured output (`llm.with_structured_output(VacancyAnalysis)`)
  2. FastAPI request/response validation
  3. The TypeScript interfaces in `frontend/lib/types.ts` (mirrored by hand)

Keep them boring and serialisable: no SQLAlchemy objects, no FastAPI imports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Severity = Literal["low", "medium", "high"]


# --------------------------------------------------------------------------
# Core analysis models (LLM structured output)
# --------------------------------------------------------------------------


class MatchedKeyword(BaseModel):
    """A vacancy keyword that is genuinely evidenced somewhere in the CV."""

    keyword: str = Field(description="The requirement/skill keyword from the vacancy.")
    location: str = Field(
        description="CV section where the evidence was found, e.g. 'Projects', 'Skills', 'Experience'."
    )


class GapRow(BaseModel):
    """One row of the gap table: a requirement the CV covers poorly or not at all."""

    requirement: str = Field(description="The vacancy requirement being assessed.")
    cv_evidence: str = Field(
        default="",
        description="What the CV currently shows for this requirement. Empty string if nothing supports it.",
    )
    severity: Severity = Field(
        description="How badly this gap hurts the application: low, medium or high."
    )
    suggested_fix: str = Field(
        description="One concrete, actionable edit the candidate can make to close the gap."
    )


class VacancyAnalysis(BaseModel):
    """The full analysis of one CV against one vacancy."""

    fit_score: int = Field(ge=0, le=100, description="Honest overall fit, 0-100. Do not inflate.")
    fit_label: str = Field(description="Short verdict, e.g. 'Strong fit', 'Decent fit', 'Weak fit'.")
    summary: str = Field(description="Plain-language verdict, 3 sentences maximum.")
    matched_keywords: list[MatchedKeyword] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    gaps: list[GapRow] = Field(default_factory=list)
    tips: list[str] = Field(
        default_factory=list,
        max_length=7,
        description="Imperative, concrete CV edits. At most 7.",
    )


class ExtractedRequirements(BaseModel):
    """Output of the cheap first Gemini call (step 2 of the pipeline)."""

    role_title: str = Field(default="", description="Job title as stated in the vacancy.")
    company: str = Field(default="", description="Hiring company, empty string if not stated.")
    hard_requirements: list[str] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list, description="Flat list of skill/tool keywords.")


class SubScores(BaseModel):
    """Three sub-scores rendered as progress bars on the dark hero card.

    Derived heuristically from `VacancyAnalysis` (see `chains.derive_sub_scores`)
    so that `VacancyAnalysis` stays exactly the shape the LLM is asked for.
    """

    profile: int = Field(ge=0, le=100)
    skills: int = Field(ge=0, le=100)
    summary: int = Field(ge=0, le=100)


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class RecoverySessionRequest(BaseModel):
    access_token: str = Field(min_length=20)
    refresh_token: str = Field(min_length=20)
    expires_in: int = Field(default=3600, ge=1, le=86_400)


class PasswordUpdateRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    created_at: datetime


class OkResponse(BaseModel):
    ok: bool = True


# --------------------------------------------------------------------------
# CVs
# --------------------------------------------------------------------------


class CVOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    filename: str
    char_count: int
    created_at: datetime


class CVUpdate(BaseModel):
    label: str = Field(min_length=1, max_length=120)


class CVScore(BaseModel):
    """Similarity of one of the user's CVs to the pasted vacancy, 0-100."""

    cv_id: int
    label: str
    similarity: float = Field(ge=0, le=100)
    strength_score: float = Field(default=0, ge=0, le=100)
    selection_score: float = Field(default=0, ge=0, le=100)


# --------------------------------------------------------------------------
# Analyses
# --------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    vacancy_text: str = Field(min_length=40)


class AnalysisResult(BaseModel):
    """Payload returned by POST /analyze and GET /analyses/{id}."""

    analysis_id: int
    #: Null only if the winning CV was deleted after the analysis was saved;
    #: `recommended_cv_label` is always present for display.
    recommended_cv: CVOut | None
    recommended_cv_label: str
    cv_scores: list[CVScore]
    analysis: VacancyAnalysis
    sub_scores: SubScores
    created_at: datetime


class AnalysisDetail(AnalysisResult):
    vacancy_text: str


class AnalysisListItem(BaseModel):
    """Sidebar history row."""

    id: int
    title: str
    fit_score: int
    fit_label: str
    recommended_cv_label: str
    created_at: datetime


# --------------------------------------------------------------------------
# Typed errors
# --------------------------------------------------------------------------

ErrorCode = Literal[
    "invalid_request",
    "unauthorized",
    "not_found",
    "email_taken",
    "invalid_credentials",
    "no_cvs",
    "cv_limit_reached",
    "vacancy_too_long",
    "file_too_large",
    "unsupported_file_type",
    "unreadable_file",
    "rate_limited",
    "llm_unavailable",
]


class ErrorResponse(BaseModel):
    code: ErrorCode
    message: str
    detail: dict[str, str | int] | None = None
