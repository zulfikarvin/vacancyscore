"""Serverless-friendly embedding client and cosine ranking helpers.

Production uses Gemini's embedding REST endpoint, so Vercel does not download
PyTorch or a local Hugging Face model. Tests and offline development use the
deterministic hashing implementation below.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

import httpx

from app.config import settings
from app.errors import AppError

_COS_FLOOR = 0.20
_COS_CEIL = 0.80


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class HashingEmbedder:
    """Deterministic offline stand-in with the production vector dimension."""

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim or settings.embedding_dimensions

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in re.findall(r"[a-z0-9+#.]+", text.lower()):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            vector[index] += 1.0 if digest[4] % 2 else -1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class GeminiEmbedder:
    """Direct Gemini REST client; avoids adding another heavyweight SDK."""

    def __init__(self, model: str, dimensions: int, api_key: str) -> None:
        self.model = model
        self.dimensions = dimensions
        self.api_key = api_key

    def _embed(self, text: str) -> list[float]:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:embedContent"
        )
        try:
            response = httpx.post(
                url,
                headers={"x-goog-api-key": self.api_key},
                json={
                    "model": f"models/{self.model}",
                    "content": {
                        "parts": [{"text": text[: settings.embedding_max_chars]}]
                    },
                    "taskType": "SEMANTIC_SIMILARITY",
                    "outputDimensionality": self.dimensions,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            vector = response.json()["embedding"]["values"]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise AppError(
                "llm_unavailable",
                "The matching service is temporarily unavailable. Please try again.",
                {"provider": "gemini-embeddings"},
            ) from exc
        return [float(value) for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    if settings.use_mock_llm or not settings.google_api_key:
        return HashingEmbedder()
    return GeminiEmbedder(
        settings.embedding_model,
        settings.embedding_dimensions,
        settings.google_api_key,
    )


def embedding_version() -> str:
    provider = (
        "hash" if settings.use_mock_llm or not settings.google_api_key else "gemini"
    )
    return f"{provider}:{settings.embedding_model}:{settings.embedding_dimensions}"


def embed_cv(text: str) -> list[float]:
    return get_embedder().embed_documents([text])[0]


def embed_vacancy(text: str) -> list[float]:
    return get_embedder().embed_query(text)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity in [-1, 1]. Returns zero for incompatible vectors."""
    if not a or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def to_percentage(cosine: float) -> float:
    scaled = (cosine - _COS_FLOOR) / (_COS_CEIL - _COS_FLOOR)
    return round(min(max(scaled, 0.0), 1.0) * 100, 1)


def rank_by_similarity(
    query: Sequence[float], candidates: Sequence[tuple[int, Sequence[float]]]
) -> list[tuple[int, float]]:
    scored = [
        (candidate_id, cosine_similarity(query, vector))
        for candidate_id, vector in candidates
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [(candidate_id, to_percentage(score)) for candidate_id, score in scored]
