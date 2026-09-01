"""Local CPU embeddings + cosine ranking.

Pure logic, no FastAPI. Two halves:

* `rank_by_similarity` / `cosine_similarity` -- numpy maths, trivially testable.
* `get_embedder()` -- the model itself, lazily constructed so importing this
  module never pulls torch into a test process.

Why no vector DB: similarity is only ever computed inside one user account,
against at most `MAX_CVS_PER_USER` (10) vectors. A numpy dot product over 10
rows is microseconds; an index would be pure operational cost. See README.

`HashingEmbedder` is the dev/test stand-in: deterministic pseudo-vectors that
keep the whole upload -> rank -> analyse flow exercisable without a 130MB
download, and that keep the test suite offline.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

import numpy as np

from app.config import settings

#: Measured cosine range for bge-small-en-v1.5 on real CV/vacancy pairs: a
#: matching CV scores ~0.80, a plausible-but-wrong one ~0.58, and a completely
#: unrelated CV ~0.48. Raw cosines therefore bunch into a narrow high band, and
#: printing them directly would tell the user a pastry-chef CV is a 51% match.
#: These bounds stretch that band into a percentage that reads honestly.
_COS_FLOOR = 0.40
_COS_CEIL = 0.85


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class HashingEmbedder:
    """Deterministic bag-of-words hashing embedder.

    Not semantic -- it only exists so that dev/test runs have real vectors to
    rank without a 130MB model download. Same interface as LangChain embedders.
    """

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def _vector(self, text: str) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        for token in re.findall(r"[a-z0-9+#.]+", text.lower()):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 else -1.0
            vec[idx] += sign
        norm = float(np.linalg.norm(vec))
        if norm:
            vec /= norm
        return vec.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    """Return the process-wide embedder, built once on first use."""
    if settings.use_mock_llm:
        return HashingEmbedder()
    from langchain_huggingface import HuggingFaceEmbeddings

    # No bge query instruction prefix: that is for short-query retrieval, and a
    # pasted vacancy is long text being compared to other long text.
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def embed_cv(text: str) -> list[float]:
    return get_embedder().embed_documents([text])[0]


def embed_vacancy(text: str) -> list[float]:
    return get_embedder().embed_query(text)


# --------------------------------------------------------------------------
# Maths
# --------------------------------------------------------------------------


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity in [-1, 1]. Returns 0.0 for empty or zero vectors."""
    va, vb = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    if va.size == 0 or vb.size == 0 or va.size != vb.size:
        return 0.0
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def to_percentage(cosine: float) -> float:
    """Stretch a raw cosine into a human-readable 0-100 match percentage."""
    scaled = (cosine - _COS_FLOOR) / (_COS_CEIL - _COS_FLOOR)
    return round(min(max(scaled, 0.0), 1.0) * 100, 1)


def rank_by_similarity(
    query: Sequence[float], candidates: Sequence[tuple[int, Sequence[float]]]
) -> list[tuple[int, float]]:
    """Rank `(id, vector)` candidates against `query`.

    Returns `(id, percentage)` sorted best-first. Ties keep input order, so a
    user with two identical CVs gets a stable recommendation.

    Ordering is decided on the RAW cosine, never on the percentage: the
    percentage clamps at both ends, so two CVs that both sit below `_COS_FLOOR`
    would tie at 0% and the recommendation would collapse to insertion order
    even though one is genuinely closer.
    """
    scored = [(cid, cosine_similarity(query, vec)) for cid, vec in candidates]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [(cid, to_percentage(cosine)) for cid, cosine in scored]
