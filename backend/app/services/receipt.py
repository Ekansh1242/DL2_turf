from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.domain.models.models import Booking, User, Resource
from app.services.branding import get_logo_bytes


def _generate_qr_code(booking_id: str) -> bytes:
    """QR code encodes the booking ID -- staff scan it at the facility
    to mark check-in (POST /admin/bookings/{id}/check-in), which
    replaces the manual rollno/branch logging the department used to do."""
    import qrcode

    img = qrcode.make(f"campussphere:checkin:{booking_id}")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def build_receipt_pdf(booking: Booking, user: User, resource: Resource, booked_by_staff: bool = False) -> bytes:
    """Build a small, printable/showable PDF receipt for a confirmed booking.

    Designed to be legible on a phone screen even with no internet --
    students can just show this to the turf/court in-charge.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A5,
        topMargin=14 * mm, bottomMargin=14 * mm, leftMargin=14 * mm, rightMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReceiptTitle", parent=styles["Title"], fontSize=16, textColor=colors.HexColor("#4c1d95"),
    )
    label_style = ParagraphStyle("Label", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    status_style = ParagraphStyle(
        "Status", parent=styles["Normal"], fontSize=11, textColor=colors.HexColor("#065f46"),
        spaceBefore=4, spaceAfter=10,
    )

    elements = []

    logo_bytes = get_logo_bytes()
    if logo_bytes is not None:
        elements.append(Image(io.BytesIO(logo_bytes), width=18 * mm, height=18 * mm))
        elements.append(Spacer(1, 2 * mm))

    elements.append(Paragraph("Shri Ramdeobaba College of Engineering &amp; Management", label_style))
    elements.append(Paragraph("CampusSphere &mdash; Booking Receipt", title_style))
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph("STATUS", label_style))
    elements.append(Paragraph("&#10003; CONFIRMED", status_style))

    rows = [
        ["Booking ID", booking.id],
        ["Sport / Facility", f"{resource.type.value.replace('_', ' ').title()} — {resource.name}"],
        ["Booked for", user.name],
        ["Email", user.email],
        ["Date", booking.start_time.strftime("%A, %d %B %Y")],
        ["Time", f"{booking.start_time.strftime('%I:%M %p')} - {booking.end_time.strftime('%I:%M %p')}"],
        ["Booked at", booking.created_at.strftime("%d %b %Y, %I:%M %p") if booking.created_at else "-"],
    ]
    if booked_by_staff:
        rows.append(["Booked by", "Sports Department (staff)"])
    table = Table(rows, colWidths=[38 * mm, 78 * mm])
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#e5e7eb")),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 6 * mm))

    try:
        qr_bytes = _generate_qr_code(booking.id)
        elements.append(Paragraph("CHECK-IN QR CODE", label_style))
        elements.append(Spacer(1, 2 * mm))
        elements.append(Image(io.BytesIO(qr_bytes), width=28 * mm, height=28 * mm))
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(
            "Staff scans this at the facility to check you in.",
            ParagraphStyle("QRCaption", parent=styles["Normal"], fontSize=8, textColor=colors.grey),
        ))
    except Exception:
        pass  # QR generation is decorative -- never block the receipt on it

    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(
        "Show this receipt at the facility if internet access isn't available. "
        "This booking is valid only for the date and time slot shown above.",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey),
    ))

    doc.build(elements)
    return buf.getvalue()
