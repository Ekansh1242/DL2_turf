"""
Admin summary report -- a printable PDF with the college header, a real
bar chart of bookings-by-sport, and breakdown tables. Built entirely
from live aggregate queries (same underlying queries as the JSON
analytics endpoints) -- no LLM involved, this is reporting, not agentic
reasoning.
"""
from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.models.models import Booking, BookingStatus, User, Resource, EquipmentLoan
from app.services.branding import get_logo_bytes


def _sport_breakdown(db: Session) -> list[tuple[str, int]]:
    rows = (
        db.query(Resource.type, func.count(Booking.id))
        .join(Booking, Booking.resource_id == Resource.id)
        .filter(Booking.status == BookingStatus.confirmed)
        .group_by(Resource.type).all()
    )
    return [(t.value.replace("_", " ").title(), c) for t, c in rows]


def _dept_breakdown(db: Session) -> list[tuple[str, int]]:
    rows = (
        db.query(func.coalesce(User.department, "Unspecified"), func.count(Booking.id))
        .join(Booking, Booking.user_id == User.id)
        .filter(Booking.status == BookingStatus.confirmed)
        .group_by(User.department).all()
    )
    return [(d, c) for d, c in rows]


def _make_bar_chart(data: list[tuple[str, int]], width=160 * mm, height=70 * mm) -> Drawing:
    drawing = Drawing(width, height)
    chart = VerticalBarChart()
    chart.x, chart.y = 40, 20
    chart.width, chart.height = width - 60, height - 40
    values = [v for _, v in data] or [0]
    chart.data = [values]
    chart.categoryAxis.categoryNames = [k for k, _ in data] or ["No data"]
    chart.categoryAxis.labels.angle = 30
    chart.categoryAxis.labels.dy = -12
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    chart.bars[0].fillColor = colors.HexColor("#7c3aed")
    drawing.add(chart)
    return drawing


def build_summary_report_pdf(db: Session) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=16 * mm, bottomMargin=16 * mm, leftMargin=16 * mm, rightMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=18, textColor=colors.HexColor("#4c1d95"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#4c1d95"), spaceBefore=10, spaceAfter=6)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, textColor=colors.grey)

    elements = []
    logo = get_logo_bytes()
    if logo is not None:
        elements.append(Image(io.BytesIO(logo), width=16 * mm, height=16 * mm))
        elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph("Shri Ramdeobaba College of Engineering &amp; Management", small))
    elements.append(Paragraph("CampusSphere &mdash; Sports Facility Report", title_style))
    elements.append(Paragraph(f"Generated {datetime.now().strftime('%d %B %Y, %I:%M %p')}", small))
    elements.append(Spacer(1, 6 * mm))

    # Summary numbers
    total = db.query(func.count(Booking.id)).scalar() or 0
    confirmed = db.query(func.count(Booking.id)).filter(Booking.status == BookingStatus.confirmed).scalar() or 0
    no_shows = db.query(func.count(Booking.id)).filter(Booking.status == BookingStatus.no_show).scalar() or 0
    unique_students = db.query(func.count(func.distinct(Booking.user_id))).scalar() or 0
    total_fines = db.query(func.coalesce(func.sum(EquipmentLoan.fine_rupees), 0)).scalar() or 0

    summary_rows = [
        ["Total bookings", str(total)],
        ["Confirmed", str(confirmed)],
        ["No-shows", str(no_shows)],
        ["Unique students", str(unique_students)],
        ["Total fines collected", f"Rs. {total_fines}"],
    ]
    summary_table = Table(summary_rows, colWidths=[70 * mm, 40 * mm])
    summary_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#e5e7eb")),
    ]))
    elements.append(summary_table)

    # Bookings by sport
    elements.append(Paragraph("Bookings by Sport", h2))
    sport_data = _sport_breakdown(db)
    elements.append(_make_bar_chart(sport_data))

    # Bookings by department
    elements.append(Paragraph("Bookings by Department", h2))
    dept_data = _dept_breakdown(db)
    dept_rows = [["Department", "Bookings"]] + [[d, str(c)] for d, c in dept_data] if dept_data else [["No data", "-"]]
    dept_table = Table(dept_rows, colWidths=[90 * mm, 40 * mm])
    dept_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3e8ff")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
    ]))
    elements.append(dept_table)

    doc.build(elements)
    return buf.getvalue()
