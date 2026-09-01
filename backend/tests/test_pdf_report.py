from datetime import datetime, timezone
from io import BytesIO

from pypdf import PdfReader

from app.pdf_report import build_analysis_pdf
from app.schemas import CVScore, GapRow, MatchedKeyword, SubScores, VacancyAnalysis


def test_analysis_pdf_contains_the_complete_report():
    pdf = build_analysis_pdf(
        title="Backend Engineer - Northwind Labs",
        created_at=datetime(2026, 8, 31, 12, 30, tzinfo=timezone.utc),
        recommended_cv_label="General CV",
        cv_scores=[
            CVScore(
                cv_id=1,
                label="General CV",
                similarity=78,
                strength_score=85,
                selection_score=82,
            )
        ],
        analysis=VacancyAnalysis(
            fit_score=76,
            fit_label="Good fit",
            summary="Strong evidence for the core backend responsibilities.",
            matched_keywords=[MatchedKeyword(keyword="Python", location="Experience")],
            missing_keywords=["Kubernetes"],
            gaps=[
                GapRow(
                    requirement="Kubernetes",
                    cv_evidence="No evidence found",
                    severity="medium",
                    suggested_fix="Add the deployment project and name the orchestration tools used.",
                )
            ],
            tips=["Quantify the API performance improvement."],
        ),
        sub_scores=SubScores(profile=80, skills=72, summary=78),
    )

    assert pdf.startswith(b"%PDF")
    reader = PdfReader(BytesIO(pdf))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Backend Engineer - Northwind Labs" in extracted
    assert "General CV (recommended)" in extracted
    assert "Requirement gaps" in extracted
    assert "Quantify the API performance improvement" in extracted
