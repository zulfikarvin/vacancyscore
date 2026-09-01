"""Regenerate every stored CV vector with the currently configured embedder."""

import json

from sqlalchemy import select

from app.embeddings import embed_cv
from app.store import CV, SessionLocal


def main() -> None:
    session = SessionLocal()
    try:
        cvs = list(session.scalars(select(CV).order_by(CV.id)))
        print(f"Re-embedding {len(cvs)} CV(s)...", flush=True)
        for index, cv in enumerate(cvs, start=1):
            vector = embed_cv(cv.content_text)
            cv.embedding_json = json.dumps([round(float(value), 6) for value in vector])
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
