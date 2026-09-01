"""FastAPI app and routes.

Routes stay thin on purpose: parse the request, call into `auth` / `store` /
`chains`, serialise the result. All the logic those routes call is importable
without FastAPI, so the same functions can be wrapped in a FastMCP server later.

Every user-data route depends on `current_user` and passes `user.id` into the
store layer; no route ever accepts a user id from the client.
"""

from __future__ import annotations

import json
import re
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, Request, Response, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import auth, limits, parsing, store
from app.auth import current_user, get_db
from app.chains import CVCandidate, normalize_history_title, run_analysis
from app.config import settings
from app.embeddings import embed_cv, embedding_version
from app.errors import AppError
from app.pdf_report import build_analysis_pdf
from app.schemas import (
    AnalysisDetail,
    AnalysisListItem,
    AnalysisResult,
    AnalyzeRequest,
    CVOut,
    CVUpdate,
    CVScore,
    ErrorResponse,
    ForgotPasswordRequest,
    LoginRequest,
    OkResponse,
    PasswordUpdateRequest,
    RecoverySessionRequest,
    SignupRequest,
    SubScores,
    UserOut,
    VacancyAnalysis,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema creation belongs to setup, not every serverless cold start. Local
    # development still initializes automatically for convenience.
    if not settings.vercel:
        store.init_db()
    yield


app = FastAPI(
    title="VacancyScore API",
    version="0.1.0",
    description="AI vacancy analyzer: rank your CVs against a vacancy and score the fit.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,  # required for the session cookie
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Error handling -- everything the frontend sees is an ErrorResponse
# --------------------------------------------------------------------------


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    body = ErrorResponse(code=exc.code, message=exc.message, detail=exc.detail)
    return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    body = ErrorResponse(
        code="invalid_request",
        message=str(first.get("msg", "That request was not valid.")),
        detail={"field": ".".join(str(p) for p in first.get("loc", [])[1:]) or "body"},
    )
    return JSONResponse(status_code=422, content=body.model_dump(mode="json"))


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "llm": "live" if settings.llm_enabled else "mock"}


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


@app.post("/auth/signup", response_model=UserOut, status_code=201, tags=["auth"])
def signup(payload: SignupRequest, response: Response, db: Session = Depends(get_db)) -> UserOut:
    user, session = auth.signup(db, payload.email, payload.password)
    auth.set_session_cookies(response, session)
    return UserOut.model_validate(user)


@app.post("/auth/login", response_model=UserOut, tags=["auth"])
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserOut:
    user, session = auth.authenticate(db, payload.email, payload.password)
    auth.set_session_cookies(response, session)
    return UserOut.model_validate(user)


@app.post("/auth/forgot-password", response_model=OkResponse, tags=["auth"])
def forgot_password(payload: ForgotPasswordRequest) -> OkResponse:
    auth.request_password_reset(payload.email)
    return OkResponse()


@app.post("/auth/recovery-session", response_model=UserOut, tags=["auth"])
def recovery_session(
    payload: RecoverySessionRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> UserOut:
    user, session = auth.accept_recovery_session(
        db, payload.access_token, payload.refresh_token, payload.expires_in
    )
    auth.set_session_cookies(response, session)
    return UserOut.model_validate(user)


@app.put("/auth/password", response_model=OkResponse, tags=["auth"])
def update_password(
    payload: PasswordUpdateRequest, request: Request, response: Response
) -> OkResponse:
    auth.update_password_from_session(request, response, payload.password)
    return OkResponse()


@app.post("/auth/logout", response_model=OkResponse, tags=["auth"])
def logout(response: Response) -> OkResponse:
    auth.clear_session_cookie(response)
    return OkResponse()


@app.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(user: store.User = Depends(current_user)) -> UserOut:
    return UserOut.model_validate(user)


# --------------------------------------------------------------------------
# CVs
# --------------------------------------------------------------------------


@app.get("/cvs", response_model=list[CVOut], tags=["cvs"])
def list_cvs(
    user: store.User = Depends(current_user), db: Session = Depends(get_db)
) -> list[CVOut]:
    return [CVOut.model_validate(cv) for cv in store.list_cvs(db, user.id)]


@app.post("/cvs", response_model=CVOut, status_code=201, tags=["cvs"])
async def upload_cv(
    label: str = Form(..., min_length=1, max_length=120),
    file: UploadFile = File(...),
    user: store.User = Depends(current_user),
    db: Session = Depends(get_db),
) -> CVOut:
    limits.check_cv_quota(db, user.id)
    data = await file.read()
    limits.check_upload_size(len(data))

    text = parsing.extract_text(file.filename or "", data)
    cv = store.create_cv(
        db,
        user.id,
        label=label.strip(),
        filename=file.filename or "cv",
        content_text=text,
        embedding=embed_cv(text),
        embedding_model=embedding_version(),
        file_data=data,
        content_type=file.content_type,
    )
    return CVOut.model_validate(cv)


@app.get("/cvs/{cv_id}/file", tags=["cvs"])
def get_cv_file(
    cv_id: int,
    download: bool = False,
    user: store.User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Return the original upload, or extracted text for legacy CV records."""
    cv = store.get_cv(db, user.id, cv_id)
    if cv is None:
        raise AppError("not_found", "That CV does not exist.")

    is_pdf = (cv.content_type or "").lower() == "application/pdf" or cv.filename.lower().endswith(".pdf")
    # Browsers can render PDFs directly. DOCX cannot be embedded reliably, so
    # its viewer uses the already-extracted text while downloads stay original.
    if cv.file_data and (download or is_pdf):
        data = cv.file_data
        media_type = cv.content_type or "application/octet-stream"
        filename = cv.filename
    else:
        data = cv.content_text.encode("utf-8")
        media_type = "text/plain; charset=utf-8"
        filename = f"{Path(cv.filename).stem}.txt"

    disposition = "attachment" if download else "inline"
    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f"{disposition}; filename*=UTF-8''{quote(filename)}"
            )
        },
    )


@app.patch("/cvs/{cv_id}", response_model=CVOut, tags=["cvs"])
def update_cv(
    cv_id: int,
    payload: CVUpdate,
    user: store.User = Depends(current_user),
    db: Session = Depends(get_db),
) -> CVOut:
    cv = store.update_cv_label(db, user.id, cv_id, payload.label)
    if cv is None:
        raise AppError("not_found", "That CV does not exist.")
    return CVOut.model_validate(cv)


@app.delete("/cvs/{cv_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["cvs"])
def delete_cv(
    cv_id: int, user: store.User = Depends(current_user), db: Session = Depends(get_db)
) -> Response:
    if not store.delete_cv(db, user.id, cv_id):
        raise AppError("not_found", "That CV does not exist.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------
# Analyses
# --------------------------------------------------------------------------


@app.post("/analyze", response_model=AnalysisResult, tags=["analyses"])
def analyze(
    payload: AnalyzeRequest,
    user: store.User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AnalysisResult:
    vacancy_text = payload.vacancy_text.strip()
    limits.check_vacancy_length(vacancy_text)
    limits.check_analyze_rate_limit(db, user.id)

    cvs = store.list_cvs(db, user.id)
    current_embedding = embedding_version()
    embeddings_changed = False
    for cv in cvs:
        if (
            cv.embedding_model != current_embedding
            or len(cv.embedding) != settings.embedding_dimensions
        ):
            store.update_cv_embedding(
                db, cv, embed_cv(cv.content_text), current_embedding
            )
            embeddings_changed = True
    if embeddings_changed:
        db.commit()

    outcome = run_analysis(
        vacancy_text,
        [
            CVCandidate(id=cv.id, label=cv.label, text=cv.content_text, embedding=cv.embedding)
            for cv in cvs
        ],
    )
    winner = next(cv for cv in cvs if cv.id == outcome.recommended_cv_id)

    row = store.create_analysis(
        db,
        user.id,
        title=outcome.title,
        vacancy_text=vacancy_text,
        recommended_cv_id=winner.id,
        recommended_cv_label=winner.label,
        fit_score=outcome.analysis.fit_score,
        fit_label=outcome.analysis.fit_label,
        analysis_json=outcome.analysis.model_dump_json(),
        cv_scores_json=json.dumps([s.model_dump() for s in outcome.cv_scores]),
        sub_scores_json=outcome.sub_scores.model_dump_json(),
    )

    return AnalysisResult(
        analysis_id=row.id,
        recommended_cv=CVOut.model_validate(winner),
        recommended_cv_label=winner.label,
        cv_scores=outcome.cv_scores,
        analysis=outcome.analysis,
        sub_scores=outcome.sub_scores,
        created_at=row.created_at,
    )


@app.get("/analyses", response_model=list[AnalysisListItem], tags=["analyses"])
def list_analyses(
    user: store.User = Depends(current_user), db: Session = Depends(get_db)
) -> list[AnalysisListItem]:
    return [
        AnalysisListItem(
            id=row.id,
            title=normalize_history_title(row.title),
            fit_score=row.fit_score,
            fit_label=row.fit_label,
            recommended_cv_label=row.recommended_cv_label,
            created_at=row.created_at,
        )
        for row in store.list_analyses(db, user.id)
    ]


@app.get("/analyses/{analysis_id}", response_model=AnalysisDetail, tags=["analyses"])
def get_analysis(
    analysis_id: int,
    user: store.User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AnalysisDetail:
    row = store.get_analysis(db, user.id, analysis_id)
    if row is None:
        raise AppError("not_found", "That analysis does not exist.")

    cv = store.get_cv(db, user.id, row.recommended_cv_id) if row.recommended_cv_id else None
    return AnalysisDetail(
        analysis_id=row.id,
        recommended_cv=CVOut.model_validate(cv) if cv else None,
        recommended_cv_label=row.recommended_cv_label,
        cv_scores=[CVScore(**s) for s in json.loads(row.cv_scores_json)],
        analysis=VacancyAnalysis.model_validate_json(row.analysis_json),
        sub_scores=SubScores.model_validate_json(row.sub_scores_json),
        created_at=row.created_at,
        vacancy_text=row.vacancy_text,
    )


@app.get("/analyses/{analysis_id}/pdf", tags=["analyses"])
def download_analysis_pdf(
    analysis_id: int,
    user: store.User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    row = store.get_analysis(db, user.id, analysis_id)
    if row is None:
        raise AppError("not_found", "That analysis does not exist.")

    title = normalize_history_title(row.title)
    pdf = build_analysis_pdf(
        title=title,
        created_at=row.created_at,
        recommended_cv_label=row.recommended_cv_label,
        cv_scores=[CVScore(**score) for score in json.loads(row.cv_scores_json)],
        analysis=VacancyAnalysis.model_validate_json(row.analysis_json),
        sub_scores=SubScores.model_validate_json(row.sub_scores_json),
    )
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-")[:80] or "analysis"
    filename = f"VacancyScore-{slug}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.delete("/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["analyses"])
def delete_analysis(
    analysis_id: int,
    user: store.User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    if not store.delete_analysis(db, user.id, analysis_id):
        raise AppError("not_found", "That analysis does not exist.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
