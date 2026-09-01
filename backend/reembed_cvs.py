"""Regenerate every stored CV vector with the currently configured embedder."""

from sqlalchemy import select

from app.embeddings import embed_cv, embedding_version
from app.store import CV, SessionLocal, update_cv_embedding


def main() -> None:
    session = SessionLocal()
    try:
        cvs = list(session.scalars(select(CV).order_by(CV.id)))
        print(f"Re-embedding {len(cvs)} CV(s)...", flush=True)
        for index, cv in enumerate(cvs, start=1):
            update_cv_embedding(
                session, cv, embed_cv(cv.content_text), embedding_version()
            )
            print(f"[{index}/{len(cvs)}] {cv.label}", flush=True)
        session.commit()
        print("All CV embeddings are current.", flush=True)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
