"""Render a screening result to a PDF case file (reportlab).

Optional: if reportlab isn't installed the export endpoint catches the ImportError
and falls back to JSON, so this never blocks the core product.
"""
from __future__ import annotations

from io import BytesIO

_RAG = {"RED": "#c81e1e", "AMBER": "#d97400", "GREEN": "#00703c",
        "Prohibited": "#c81e1e", "High": "#d97400"}


def render_case_pdf(result: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle)

    risk = result.get("risk_assessment", {})
    rating = risk.get("overall_rating", "—")
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            title=f"KYB case file — {result.get('company_number')}")
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, spaceBefore=10)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=12)
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=7.5,
                           textColor=colors.HexColor("#626a6e"))
    story = []

    story.append(Paragraph("KYB &amp; UK Sanctions — Case File", h1))
    story.append(Paragraph(
        f"<b>{result.get('company_name') or ''}</b> · Company {result.get('company_number')} "
        f"· screened {result.get('run_at','')}", small))
    story.append(Spacer(1, 6))

    band_color = colors.HexColor(_RAG.get(rating, "#3d4346"))
    verdict_tbl = Table([[
        Paragraph(f"<b>{rating}</b>", ParagraphStyle("v", parent=h1, textColor=colors.white)),
        Paragraph(f"<b>{risk.get('fca_fatf_band','')}</b><br/>{risk.get('summary','')}",
                  ParagraphStyle("vb", parent=body, textColor=colors.white)),
    ]], colWidths=[30 * mm, 140 * mm])
    verdict_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), band_color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(verdict_tbl)
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Required action:</b> {risk.get('required_action','')}", body))

    story.append(Paragraph("Risk factors", h2))
    rows = [["Severity", "Factor", "Evidence & provision"]]
    for f in risk.get("factors", []):
        if not f.get("triggered"):
            continue
        rows.append([
            f.get("severity", ""),
            Paragraph(f"<b>{f.get('label','')}</b><br/><font size=7>{f.get('code','')}</font>", body),
            Paragraph(f"{f.get('evidence','')}<br/><font size=7 color='#626a6e'>"
                      f"{f.get('provision','')} · confidence {f.get('confidence','')}</font>", body),
        ])
    if len(rows) == 1:
        rows.append(["—", "No risk factors triggered", ""])
    ftbl = Table(rows, colWidths=[18 * mm, 44 * mm, 108 * mm])
    ftbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#320f25")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9cdcf")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f7f7")]),
    ]))
    story.append(ftbl)

    matches = result.get("matches", [])
    story.append(Paragraph(f"Screening matches ({len(matches)})", h2))
    if not matches:
        story.append(Paragraph("No sanctions or Warning List alerts.", body))
    for m in matches[:25]:
        ev = m.get("evidence", {})
        story.append(Paragraph(
            f"<b>{m.get('verdict')}</b> · {m.get('list')} · <b>{m.get('subject_name')}</b> "
            f"({m.get('subject_type')}) → {m.get('matched_designation_id')} "
            f"“{m.get('matched_name')}” (score {m.get('score')})", body))
        if ev.get("regime_name"):
            story.append(Paragraph(f"<font size=7.5 color='#626a6e'>Regime: {ev.get('regime_name')} · "
                                   f"{', '.join(ev.get('sanctions_imposed') or [])}</font>", small))
        if ev.get("uk_statement_of_reasons"):
            story.append(Paragraph(f"<font size=7.5>UK Statement of Reasons: "
                                   f"{ev['uk_statement_of_reasons'][:600]}</font>", small))
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "This tool triages and prioritises officer review. Statuses are automated and must be "
        "confirmed against the live UK Sanctions List, FCA Warning List and Companies House before "
        "any regulatory action. Guidance, not legal advice — a human compliance officer decides.",
        small))
    story.append(Paragraph("Citations: " + " · ".join(risk.get("citations", [])), small))

    doc.build(story)
    return buf.getvalue()
