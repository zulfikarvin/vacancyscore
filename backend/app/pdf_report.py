"""Generate a polished, portable PDF for a saved vacancy analysis."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas import CVScore, SubScores, VacancyAnalysis

PURPLE = colors.HexColor("#7C3AED")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#64748B")
PALE = colors.HexColor("#F5F3FF")
LINE = colors.HexColor("#E2E8F0")
GREEN = colors.HexColor("#15803D")
AMBER = colors.HexColor("#B45309")
RED = colors.HexColor("#B91C1C")


def _p(value: object, style: ParagraphStyle) -> Paragraph:
    text = str(value or "").translate(
        str.maketrans(
            {
                "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
                "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
                "\u2022": "-", "\u2190": "<-", "\u2192": "->", "\u00a0": " ",
            }
        )
    )
    text = escape(text).replace("\n", "<br/>")
    return Paragraph(text, style)


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 8.5 * mm, "VacancyScore analysis report")
    canvas.drawRightString(A4[0] - 18 * mm, 8.5 * mm, f"Page {document.page}")
    canvas.restoreState()


def build_analysis_pdf(
    *,
    title: str,
    created_at: datetime,
    recommended_cv_label: str,
    cv_scores: list[CVScore],
    analysis: VacancyAnalysis,
    sub_scores: SubScores,
) -> bytes:
    """Return a complete analysis report as PDF bytes."""
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=20 * mm,
        title=f"VacancyScore - {title}",
        author="VacancyScore",
    )

    base = getSampleStyleSheet()
    styles = {
        "brand": ParagraphStyle(
            "Brand", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=11, leading=14, textColor=PURPLE,
        ),
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=21, leading=25, textColor=INK, spaceAfter=4,
        ),
        "meta": ParagraphStyle(
            "Meta", parent=base["Normal"], fontSize=9, leading=12, textColor=MUTED,
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=13, leading=16, textColor=INK, spaceBefore=13, spaceAfter=7,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontSize=9.5, leading=14,
            textColor=INK, spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["BodyText"], fontSize=8, leading=11, textColor=INK,
        ),
        "table_header": ParagraphStyle(
            "TableHeader", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=8, leading=10, textColor=colors.white,
        ),
        "score": ParagraphStyle(
            "Score", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=25, leading=28, alignment=TA_CENTER, textColor=PURPLE,
        ),
        "score_label": ParagraphStyle(
            "ScoreLabel", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, alignment=TA_CENTER, textColor=INK,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["BodyText"], fontSize=9, leading=13,
            leftIndent=10, firstLineIndent=-8, textColor=INK, spaceAfter=4,
        ),
    }

    story = [
        _p("VacancyScore", styles["brand"]),
        Spacer(1, 3 * mm),
        _p(title, styles["title"]),
        _p(
            f"Analysed {created_at.strftime('%d %B %Y, %H:%M')} | Recommended CV: {recommended_cv_label}",
            styles["meta"],
        ),
        Spacer(1, 6 * mm),
    ]

    score_cells = [
        (_p(f"{analysis.fit_score}/100", styles["score"]), _p(analysis.fit_label, styles["score_label"])),
        (_p(f"{sub_scores.profile}%", styles["score"]), _p("Profile", styles["score_label"])),
        (_p(f"{sub_scores.skills}%", styles["score"]), _p("Skills", styles["score_label"])),
        (_p(f"{sub_scores.summary}%", styles["score"]), _p("Summary", styles["score_label"])),
    ]
    score_table = Table(
        [[Table([[value], [label]], colWidths=[38 * mm]) for value, label in score_cells]],
        colWidths=[42.5 * mm] * 4,
    )
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#DDD6FE")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDD6FE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([score_table, _p("Verdict", styles["section"]), _p(analysis.summary, styles["body"])])

    story.append(_p("CV ranking", styles["section"]))
    ranking_data = [[
        _p("CV", styles["table_header"]), _p("Match", styles["table_header"]),
        _p("Strength", styles["table_header"]), _p("Overall", styles["table_header"]),
    ]]
    for score in cv_scores:
        label = score.label
        if label == recommended_cv_label:
            label += " (recommended)"
        ranking_data.append([
            _p(label, styles["small"]),
            _p(f"{score.similarity:.0f}%", styles["small"]),
            _p(f"{score.strength_score:.0f}%", styles["small"]),
            _p(f"{score.selection_score:.0f}%", styles["small"]),
        ])
    ranking = Table(ranking_data, colWidths=[92 * mm, 26 * mm, 26 * mm, 26 * mm], repeatRows=1)
    ranking.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
    ]))
    story.append(ranking)

    keyword_section = [_p("Keyword evidence", styles["section"])]
    if analysis.matched_keywords:
        keyword_cells = [
            _p(f"+ {item.keyword} - {item.location}", styles["small"])
            for item in analysis.matched_keywords
        ]
        if len(keyword_cells) % 2:
            keyword_cells.append("")
        keyword_table = Table(
            [keyword_cells[index:index + 2] for index in range(0, len(keyword_cells), 2)],
            colWidths=[85 * mm, 85 * mm],
        )
        keyword_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("GRID", (0, 0), (-1, -1), 0.5, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        keyword_section.append(keyword_table)
    else:
        keyword_section.append(_p("No matched keywords were evidenced in this CV.", styles["body"]))
    if analysis.missing_keywords:
        keyword_section.append(_p("Missing: " + ", ".join(analysis.missing_keywords), styles["body"]))
    story.append(KeepTogether(keyword_section))

    story.append(_p("Requirement gaps", styles["section"]))
    if analysis.gaps:
        gap_data = [[
            _p("Requirement", styles["table_header"]), _p("CV evidence", styles["table_header"]),
            _p("Severity", styles["table_header"]), _p("Suggested fix", styles["table_header"]),
        ]]
        for gap in analysis.gaps:
            gap_data.append([
                _p(gap.requirement, styles["small"]),
                _p(gap.cv_evidence or "No evidence found", styles["small"]),
                _p(gap.severity.upper(), styles["small"]),
                _p(gap.suggested_fix, styles["small"]),
            ])
        gaps = Table(
            gap_data,
            colWidths=[43 * mm, 42 * mm, 20 * mm, 65 * mm],
            repeatRows=1,
        )
        gaps.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), INK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        for index, gap in enumerate(analysis.gaps, start=1):
            severity_color = {"high": RED, "medium": AMBER, "low": GREEN}.get(gap.severity, MUTED)
            gaps.setStyle(TableStyle([("TEXTCOLOR", (2, index), (2, index), severity_color)]))
        story.append(gaps)
    else:
        story.append(_p("No material gaps were identified.", styles["body"]))

    tips = [_p(f"{index}. {tip}", styles["bullet"]) for index, tip in enumerate(analysis.tips, start=1)]
    story.append(_p("Recommended edits", styles["section"]))
    story.extend(tips or [_p("No edits were suggested.", styles["body"])])

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output.getvalue()
