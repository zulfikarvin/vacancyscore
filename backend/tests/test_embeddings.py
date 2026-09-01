"""Ranking maths and CV parsing.

Deliberately model-free: `cosine_similarity`, `to_percentage` and
`rank_by_similarity` are the parts that decide which CV wins, so they are tested
directly rather than through a 130MB download.
"""

from __future__ import annotations

import pytest

from app.embeddings import (
    HashingEmbedder,
    cosine_similarity,
    rank_by_similarity,
    to_percentage,
)
from app.errors import AppError
from app.parsing import extract_text, normalise


# --------------------------------------------------------------------------
# Cosine similarity
# --------------------------------------------------------------------------


def test_identical_vectors_are_one():
    assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)


def test_scaling_does_not_change_similarity():
    assert cosine_similarity([1.0, 2.0], [10.0, 20.0]) == pytest.approx(1.0)


def test_orthogonal_vectors_are_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_opposite_vectors_are_minus_one():
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


@pytest.mark.parametrize(
    ("a", "b"),
    [([], [1.0]), ([1.0], []), ([0.0, 0.0], [1.0, 1.0]), ([1.0, 2.0], [1.0, 2.0, 3.0])],
)
def test_degenerate_inputs_are_zero_not_an_exception(a, b):
    """A CV stored before embeddings existed must not crash a whole analysis."""
    assert cosine_similarity(a, b) == 0.0


# --------------------------------------------------------------------------
# Percentage mapping
# --------------------------------------------------------------------------


def test_percentages_are_clamped_to_the_readable_band():
    assert to_percentage(-0.5) == 0.0
    assert to_percentage(0.40) == 0.0
    assert to_percentage(0.625) == 50.0
    assert to_percentage(0.85) == 100.0
    assert to_percentage(1.0) == 100.0


# --------------------------------------------------------------------------
# Ranking
# --------------------------------------------------------------------------


def test_ranking_is_best_first():
    query = [1.0, 0.0]
    ranked = rank_by_similarity(
        query, [(1, [0.0, 1.0]), (2, [1.0, 0.0]), (3, [0.7, 0.7])]
    )
    assert [cv_id for cv_id, _ in ranked] == [2, 3, 1]


def test_ties_keep_input_order_so_the_recommendation_is_stable():
    query = [1.0, 0.0]
    ranked = rank_by_similarity(query, [(7, [1.0, 0.0]), (8, [2.0, 0.0])])
    assert [cv_id for cv_id, _ in ranked] == [7, 8]


def test_ranking_an_empty_candidate_list_is_empty():
    assert rank_by_similarity([1.0, 0.0], []) == []


def test_ranking_survives_candidates_that_all_clamp_to_zero_percent():
    """Order comes from the raw cosine, not the clamped display percentage.

    Both of these sit below `_COS_FLOOR`, so both render as 0%. The closer one
    must still win -- otherwise the recommendation silently becomes whichever
    CV was uploaded last.
    """
    query = [1.0, 0.0]
    closer = [0.35, 0.94]  # cosine ~0.35
    further = [0.10, 1.0]  # cosine ~0.10

    ranked = rank_by_similarity(query, [(1, further), (2, closer)])

    assert [cv_id for cv_id, _ in ranked] == [2, 1]
    assert [pct for _, pct in ranked] == [0.0, 0.0]


# --------------------------------------------------------------------------
# The dev/test embedder
# --------------------------------------------------------------------------


def test_hashing_embedder_is_deterministic_and_normalised():
    embedder = HashingEmbedder(dim=64)
    first = embedder.embed_query("FastAPI and PostgreSQL")
    second = embedder.embed_query("FastAPI and PostgreSQL")

    assert first == second
    assert len(first) == 64
    assert cosine_similarity(first, second) == pytest.approx(1.0)


def test_hashing_embedder_separates_unrelated_text():
    embedder = HashingEmbedder(dim=384)
    backend = embedder.embed_documents(["python fastapi postgresql docker"])[0]
    pastry = embedder.embed_documents(["croissant lamination butter pastry"])[0]

    assert cosine_similarity(backend, pastry) < 0.2


# --------------------------------------------------------------------------
# CV parsing
# --------------------------------------------------------------------------


def test_normalise_collapses_runs_of_whitespace():
    assert normalise("a   b\r\n\r\n\r\n\r\nc  ") == "a b\n\nc"


def test_plain_text_cvs_are_accepted():
    body = "Jane Doe\n" + ("Backend engineer with FastAPI experience. " * 5)
    assert "Jane Doe" in extract_text("cv.txt", body.encode("utf-8"))


def test_images_are_rejected_by_extension():
    with pytest.raises(AppError) as caught:
        extract_text("cv.png", b"\x89PNG" + b"0" * 500)
    assert caught.value.code == "unsupported_file_type"
    assert caught.value.status_code == 415


def test_a_file_with_no_readable_text_is_rejected():
    """A scanned CV parses to almost nothing; say so rather than storing junk."""
    with pytest.raises(AppError) as caught:
        extract_text("cv.txt", b"short")
    assert caught.value.code == "unreadable_file"
