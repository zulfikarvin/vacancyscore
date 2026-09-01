"""SQLAlchemy models + user-scoped CRUD.

Importable without FastAPI (the MCP server will reuse these functions verbatim).

SCOPING RULE -- every read/write helper that touches user data takes `user_id`
as its first argument after the session and filters on it. There is deliberately
no `get_cv(cv_id)` / `get_analysis(id)` without a user, so a route cannot
accidentally reach across tenants.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    create_engine,
    func,
    select,
    text,
)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)
from sqlalchemy.pool import NullPool

from app.config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    cvs: Mapped[list["CV"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class CV(Base):
    __tablename__ = "cvs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(120))
    filename: Mapped[str] = mapped_column(String(255))
    content_text: Mapped[str] = mapped_column(Text)
    # Nullable so CVs created before original-file storage remain readable.
    file_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    #: Embedding vector, stored as a JSON array of floats. About 10 CVs per user,
    #: so an in-process cosine calculation beats a vector DB.
    embedding_json: Mapped[str] = mapped_column(Text, default="[]")
    # Lets the application safely re-embed records when the provider, model,
    # or vector dimensions change.
    embedding_model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="cvs")

    @property
    def embedding(self) -> list[float]:
        return json.loads(self.embedding_json or "[]")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    recommended_cv_id: Mapped[int | None] = mapped_column(
        ForeignKey("cvs.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(160))
    vacancy_text: Mapped[str] = mapped_column(Text)
    fit_score: Mapped[int] = mapped_column(Integer, default=0)
    fit_label: Mapped[str] = mapped_column(String(60), default="")
    recommended_cv_label: Mapped[str] = mapped_column(String(120), default="")
    #: Serialised VacancyAnalysis / list[CVScore] / SubScores.
    analysis_json: Mapped[str] = mapped_column(Text)
    cv_scores_json: Mapped[str] = mapped_column(Text, default="[]")
    sub_scores_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    user: Mapped[User] = relationship(back_populates="analyses")


# --------------------------------------------------------------------------
# Engine / session
# --------------------------------------------------------------------------


def _database_url(raw_url: str) -> str:
    """Normalize provider/ORM-flavoured URLs for SQLAlchemy + psycopg 3."""
    url = make_url(raw_url)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    # Supabase's Prisma snippet includes Prisma-specific parameters that
    # libpq/psycopg does not recognize.
    query = dict(url.query)
    query.pop("pgbouncer", None)
    query.pop("connection_limit", None)
    url = url.set(query=query)
    return url.render_as_string(hide_password=False)


def _engine_kwargs(url: str) -> dict[str, Any]:
    if url.startswith("sqlite"):
        # One connection reused across the FastAPI threadpool workers.
        return {"connect_args": {"check_same_thread": False}}
    # Supavisor transaction mode (port 6543) does not support prepared
    # statements. `None` disables psycopg's automatic preparation.
    kwargs: dict[str, Any] = {"connect_args": {"prepare_threshold": None}}
    if settings.vercel:
        # A serverless instance is short-lived. Supabase's transaction pooler
        # owns connection reuse, so a process-local SQLAlchemy pool only wastes
        # scarce database connections.
        kwargs["poolclass"] = NullPool
    else:
        kwargs["pool_pre_ping"] = True
    return kwargs


database_url = _database_url(settings.database_url)
engine = create_engine(database_url, **_engine_kwargs(database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)
    # Lightweight backwards-compatible migration while the project has no
    # dedicated migration framework.
    from sqlalchemy import inspect

    columns = {column["name"] for column in inspect(engine).get_columns("cvs")}
    with engine.begin() as connection:
        if "file_data" not in columns:
            binary_type = "BYTEA" if engine.dialect.name == "postgresql" else "BLOB"
            connection.exec_driver_sql(f"ALTER TABLE cvs ADD COLUMN file_data {binary_type}")
        if "content_type" not in columns:
            connection.exec_driver_sql("ALTER TABLE cvs ADD COLUMN content_type VARCHAR(120)")
        if "embedding_model" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE cvs ADD COLUMN embedding_model VARCHAR(160)"
            )

        # Persist the current history naming convention for rows saved by older
        # versions. This is idempotent, so it is safe on every application boot.
        from app.chains import normalize_history_title

        rows = connection.execute(select(Analysis.id, Analysis.title)).all()
        for analysis_id, old_title in rows:
            new_title = normalize_history_title(old_title or "")
            if new_title != old_title:
                connection.execute(
                    Analysis.__table__.update()
                    .where(Analysis.id == analysis_id)
                    .values(title=new_title)
                )


def database_status() -> dict[str, str]:
    """Small credential-safe connectivity check used by setup and diagnostics."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {
        "dialect": engine.dialect.name,
        "host": engine.url.host or "local file",
        "database": engine.url.database or "",
    }


@contextmanager
def session_scope() -> Iterator[Session]:
    """Standalone session for non-FastAPI callers (scripts, the future MCP server)."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email.lower().strip()))


def get_user_by_id(session: Session, user_id: str) -> User | None:
    return session.get(User, user_id)


def create_user(session: Session, user_id: str, email: str, created_at: datetime | None = None) -> User:
    user = User(id=user_id, email=email.lower().strip(), created_at=created_at or utcnow())
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# --------------------------------------------------------------------------
# CVs (all user-scoped)
# --------------------------------------------------------------------------


def list_cvs(session: Session, user_id: int) -> list[CV]:
    return list(
        session.scalars(
            select(CV)
            .where(CV.user_id == user_id)
            .order_by(CV.created_at.desc(), CV.id.desc())
        )
    )


def get_cv(session: Session, user_id: int, cv_id: int) -> CV | None:
    return session.scalar(select(CV).where(CV.id == cv_id, CV.user_id == user_id))


def count_cvs(session: Session, user_id: int) -> int:
    return (
        session.scalar(select(func.count()).select_from(CV).where(CV.user_id == user_id))
        or 0
    )


def create_cv(
    session: Session,
    user_id: int,
    *,
    label: str,
    filename: str,
    content_text: str,
    embedding: list[float],
    embedding_model: str | None = None,
    file_data: bytes | None = None,
    content_type: str | None = None,
) -> CV:
    cv = CV(
        user_id=user_id,
        label=label,
        filename=filename,
        content_text=content_text,
        file_data=file_data,
        content_type=content_type,
        char_count=len(content_text),
        embedding_json=json.dumps([round(float(x), 6) for x in embedding]),
        embedding_model=embedding_model,
    )
    session.add(cv)
    session.commit()
    session.refresh(cv)
    return cv


def update_cv_embedding(
    session: Session,
    cv: CV,
    embedding: list[float],
    embedding_model: str,
) -> None:
    cv.embedding_json = json.dumps([round(float(x), 6) for x in embedding])
    cv.embedding_model = embedding_model
    session.add(cv)


def delete_cv(session: Session, user_id: int, cv_id: int) -> bool:
    cv = get_cv(session, user_id, cv_id)
    if cv is None:
        return False
    session.delete(cv)
    session.commit()
    return True


def update_cv_label(session: Session, user_id: str, cv_id: int, label: str) -> CV | None:
    cv = get_cv(session, user_id, cv_id)
    if cv is None:
        return None
    cv.label = label.strip()
    session.commit()
    session.refresh(cv)
    return cv


# --------------------------------------------------------------------------
# Analyses (all user-scoped)
# --------------------------------------------------------------------------


def list_analyses(session: Session, user_id: int, limit: int = 100) -> list[Analysis]:
    return list(
        session.scalars(
            select(Analysis)
            .where(Analysis.user_id == user_id)
            .order_by(Analysis.created_at.desc(), Analysis.id.desc())
            .limit(limit)
        )
    )


def get_analysis(session: Session, user_id: int, analysis_id: int) -> Analysis | None:
    return session.scalar(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user_id)
    )


def delete_analysis(session: Session, user_id: int, analysis_id: int) -> bool:
    analysis = get_analysis(session, user_id, analysis_id)
    if analysis is None:
        return False
    session.delete(analysis)
    session.commit()
    return True


def count_analyses_since(session: Session, user_id: int, since: datetime) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(Analysis)
            .where(Analysis.user_id == user_id, Analysis.created_at >= since)
        )
        or 0
    )


def create_analysis(
    session: Session,
    user_id: int,
    *,
    title: str,
    vacancy_text: str,
    recommended_cv_id: int | None,
    recommended_cv_label: str,
    fit_score: int,
    fit_label: str,
    analysis_json: str,
    cv_scores_json: str,
    sub_scores_json: str,
) -> Analysis:
    analysis = Analysis(
        user_id=user_id,
        title=title,
        vacancy_text=vacancy_text,
        recommended_cv_id=recommended_cv_id,
        recommended_cv_label=recommended_cv_label,
        fit_score=fit_score,
        fit_label=fit_label,
        analysis_json=analysis_json,
        cv_scores_json=cv_scores_json,
        sub_scores_json=sub_scores_json,
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis
