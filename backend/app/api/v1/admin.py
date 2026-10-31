"""
Admin/staff endpoints. Staff (teachers running the sports desk) reuse
the same 'admin' role and login flow as everyone else -- they just get
access to this router, gated by get_current_admin_id.

Two capabilities:
1. Live analytics -- aggregate queries over real booking data, no LLM
   involved (this is reporting, not agentic reasoning -- keeping that
   distinction honest).
2. Book-for-student -- for when a student has no phone/internet. Uses
   the exact same BookingService.book_slot as every other booking path,
   so FCFS/concurrency guarantees are never bypassed for staff either.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from pydantic import BaseModel
from sqlalchemy import func, extract, case
from sqlalchemy.orm import Session

from app.core.security import get_current_admin_id
from app.core.timezone import now_local
from app.db.session import get_db
from app.domain.models.models import (
    Booking, BookingStatus, User, Resource, CreatedVia, SportType,
)
from app.domain.services.booking_service import BookingService
from app.domain.services.slot_window import SlotWindow
from app.services.receipt import build_receipt_pdf
from app.services.email_service import send_booking_confirmation_email
from app.services.summary_report import build_summary_report_pdf

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ---------- Analytics ----------

class SummaryOut(BaseModel):
    total_bookings: int
    confirmed_bookings: int
    cancelled_bookings: int
    no_shows: int
    unique_students: int
    total_fines_rupees: int
    bookings_this_week: int


@router.get("/analytics/summary", response_model=SummaryOut)
def analytics_summary(db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    total = db.query(func.count(Booking.id)).scalar() or 0
    confirmed = db.query(func.count(Booking.id)).filter(Booking.status == BookingStatus.confirmed).scalar() or 0
    cancelled = db.query(func.count(Booking.id)).filter(Booking.status == BookingStatus.cancelled).scalar() or 0
    no_shows = db.query(func.count(Booking.id)).filter(Booking.status == BookingStatus.no_show).scalar() or 0
    unique_students = db.query(func.count(func.distinct(Booking.user_id))).scalar() or 0

    from app.domain.models.models import EquipmentLoan
    total_fines = db.query(func.coalesce(func.sum(EquipmentLoan.fine_rupees), 0)).scalar() or 0

    week_ago = now_local() - timedelta(days=7)
    this_week = db.query(func.count(Booking.id)).filter(Booking.created_at >= week_ago).scalar() or 0

    return SummaryOut(
        total_bookings=total, confirmed_bookings=confirmed, cancelled_bookings=cancelled,
        no_shows=no_shows, unique_students=unique_students,
        total_fines_rupees=total_fines, bookings_this_week=this_week,
    )


class TrendPoint(BaseModel):
    date: str
    count: int


@router.get("/analytics/trend", response_model=list[TrendPoint])
def analytics_trend(days: int = Query(30, le=180), db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    since = now_local() - timedelta(days=days)
    rows = (
        db.query(func.date(Booking.start_time).label("d"), func.count(Booking.id))
        .filter(Booking.start_time >= since, Booking.status == BookingStatus.confirmed)
        .group_by("d").order_by("d").all()
    )
    return [TrendPoint(date=str(d), count=c) for d, c in rows]


class SportBreakdown(BaseModel):
    sport: str
    count: int


@router.get("/analytics/by-sport", response_model=list[SportBreakdown])
def analytics_by_sport(db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    rows = (
        db.query(Resource.type, func.count(Booking.id))
        .join(Booking, Booking.resource_id == Resource.id)
        .filter(Booking.status == BookingStatus.confirmed)
        .group_by(Resource.type).all()
    )
    return [SportBreakdown(sport=t.value, count=c) for t, c in rows]


class DeptBreakdown(BaseModel):
    department: str
    count: int


@router.get("/analytics/by-department", response_model=list[DeptBreakdown])
def analytics_by_department(db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    rows = (
        db.query(func.coalesce(User.department, "Unspecified"), func.count(Booking.id))
        .join(Booking, Booking.user_id == User.id)
        .filter(Booking.status == BookingStatus.confirmed)
        .group_by(User.department).all()
    )
    return [DeptBreakdown(department=d, count=c) for d, c in rows]


class YearBreakdown(BaseModel):
    year: int
    count: int


@router.get("/analytics/by-year", response_model=list[YearBreakdown])
def analytics_by_year(db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    rows = (
        db.query(extract("year", Booking.start_time).label("yr"), func.count(Booking.id))
        .filter(Booking.status == BookingStatus.confirmed)
        .group_by("yr").order_by("yr").all()
    )
    return [YearBreakdown(year=int(y), count=c) for y, c in rows]


class PeakHour(BaseModel):
    hour: int
    count: int


@router.get("/analytics/peak-hours", response_model=list[PeakHour])
def analytics_peak_hours(db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    rows = (
        db.query(extract("hour", Booking.start_time).label("h"), func.count(Booking.id))
        .filter(Booking.status == BookingStatus.confirmed)
        .group_by("h").order_by("h").all()
    )
    return [PeakHour(hour=int(h), count=c) for h, c in rows]


class TopStudent(BaseModel):
    name: str
    email: str
    booking_count: int


@router.get("/analytics/top-students", response_model=list[TopStudent])
def analytics_top_students(limit: int = 10, db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    rows = (
        db.query(User.name, User.email, func.count(Booking.id).label("c"))
        .join(Booking, Booking.user_id == User.id)
        .filter(Booking.status == BookingStatus.confirmed)
        .group_by(User.id).order_by(func.count(Booking.id).desc()).limit(limit).all()
    )
    return [TopStudent(name=n, email=e, booking_count=c) for n, e, c in rows]


class EquipmentIssueBreakdown(BaseModel):
    equipment_name: str
    damaged_count: int
    lost_count: int
    total_fines_rupees: int


@router.get("/analytics/equipment-issues", response_model=list[EquipmentIssueBreakdown])
def analytics_equipment_issues(db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    """Which equipment gets damaged/lost most -- flags what the sports
    department should budget to replace or watch more closely."""
    from app.domain.models.models import EquipmentLoan, EquipmentCatalog, LoanStatus

    rows = (
        db.query(
            EquipmentCatalog.name,
            func.sum(case((EquipmentLoan.status == LoanStatus.returned_damaged, 1), else_=0)).label("damaged"),
            func.sum(case((EquipmentLoan.status == LoanStatus.lost, 1), else_=0)).label("lost"),
            func.coalesce(func.sum(EquipmentLoan.fine_rupees), 0).label("fines"),
        )
        .join(EquipmentLoan, EquipmentLoan.equipment_catalog_id == EquipmentCatalog.id)
        .group_by(EquipmentCatalog.id)
        .having(func.sum(EquipmentLoan.fine_rupees) > 0)
        .order_by(func.coalesce(func.sum(EquipmentLoan.fine_rupees), 0).desc())
        .all()
    )
    return [
        EquipmentIssueBreakdown(equipment_name=name, damaged_count=int(d or 0), lost_count=int(l or 0), total_fines_rupees=int(f or 0))
        for name, d, l, f in rows
    ]


class StudentFine(BaseModel):
    name: str
    email: str
    total_fines_rupees: int


@router.get("/analytics/fines-by-student", response_model=list[StudentFine])
def analytics_fines_by_student(db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    from app.domain.models.models import EquipmentLoan

    rows = (
        db.query(User.name, User.email, func.sum(EquipmentLoan.fine_rupees).label("total"))
        .join(EquipmentLoan, EquipmentLoan.user_id == User.id)
        .filter(EquipmentLoan.fine_rupees > 0)
        .group_by(User.id)
        .order_by(func.sum(EquipmentLoan.fine_rupees).desc())
        .all()
    )
    return [StudentFine(name=n, email=e, total_fines_rupees=int(t or 0)) for n, e, t in rows]


# ---------- Student search + book-for-student ----------

class StudentOut(BaseModel):
    id: str
    name: str
    email: str
    roll_no: str | None
    department: str | None
    is_blocked: bool


@router.get("/students/search", response_model=list[StudentOut])
def search_students(q: str = Query(..., min_length=1), db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    like = f"%{q}%"
    rows = (
        db.query(User)
        .filter(User.role == "student")
        .filter((User.name.ilike(like)) | (User.roll_no.ilike(like)) | (User.email.ilike(like)))
        .limit(20).all()
    )
    return [
        StudentOut(id=u.id, name=u.name, email=u.email, roll_no=u.roll_no, department=u.department, is_blocked=u.is_blocked)
        for u in rows
    ]


class BookForIn(BaseModel):
    student_id: str
    resource_id: str
    slot_start: datetime
    slot_end: datetime


class BookForOut(BaseModel):
    success: bool
    booking_id: str | None = None
    message: str
    email_sent: bool = False


@router.post("/bookings/book-for", response_model=BookForOut)
def book_for_student(body: BookForIn, db: Session = Depends(get_db), admin_id: str = Depends(get_current_admin_id)):
    student = db.get(User, body.student_id)
    if student is None or student.role != "student":
        raise HTTPException(status_code=404, detail="Student not found.")
    if student.is_blocked:
        raise HTTPException(status_code=403, detail="This student is temporarily blocked due to repeated no-shows.")
    resource = db.get(Resource, body.resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Turf/resource not found.")

    slot = SlotWindow(slot_start=body.slot_start, slot_end=body.slot_end)
    service = BookingService(db)
    result = service.book_slot(
        resource_id=body.resource_id, user_id=student.id, slot=slot,
        now=now_local(), created_via=CreatedVia.admin_override,
    )

    email_sent = False
    if result.success and result.booking_id:
        booking = db.get(Booking, result.booking_id)
        booking.booked_by_id = admin_id
        db.commit()

        from app.services.booking_notification import notify_booking
        email_sent = notify_booking(db, result.booking_id)

    return BookForOut(success=result.success, booking_id=result.booking_id, message=result.message, email_sent=email_sent)


class CheckInOut(BaseModel):
    success: bool
    student_name: str | None = None
    resource_name: str | None = None
    message: str


@router.post("/bookings/{booking_id}/check-in", response_model=CheckInOut)
def check_in_booking(booking_id: str, db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    """Staff scans the QR code on the student's receipt (or enters the
    booking ID manually) to mark check-in. Replaces the old manual
    rollno/branch logbook. A checked-in booking is never eligible to be
    marked as a no-show."""
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if booking.status != BookingStatus.confirmed:
        raise HTTPException(status_code=400, detail=f"Booking is '{booking.status.value}', not confirmed.")
    if booking.checked_in_at is not None:
        return CheckInOut(success=True, message="Already checked in.")

    booking.checked_in_at = now_local()
    db.commit()

    student = db.get(User, booking.user_id)
    resource = db.get(Resource, booking.resource_id)
    return CheckInOut(
        success=True, student_name=student.name if student else None,
        resource_name=resource.name if resource else None, message="Checked in.",
    )


# ---------- No-show marking ----------

class TodayBookingOut(BaseModel):
    booking_id: str
    student_name: str
    resource_name: str
    start_time: datetime
    end_time: datetime
    status: str
    checked_in: bool


@router.get("/bookings/today", response_model=list[TodayBookingOut])
def todays_bookings(db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    today = now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    rows = (
        db.query(Booking, User, Resource)
        .join(User, Booking.user_id == User.id)
        .join(Resource, Booking.resource_id == Resource.id)
        .filter(Booking.start_time >= today, Booking.start_time < tomorrow)
        .order_by(Booking.start_time).all()
    )
    return [
        TodayBookingOut(
            booking_id=b.id, student_name=u.name, resource_name=r.name,
            start_time=b.start_time, end_time=b.end_time, status=b.status.value,
            checked_in=b.checked_in_at is not None,
        )
        for b, u, r in rows
    ]


class MarkNoShowOut(BaseModel):
    success: bool
    message: str = ""


@router.post("/bookings/{booking_id}/no-show", response_model=MarkNoShowOut)
def mark_no_show(booking_id: str, db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    booking = db.get(Booking, booking_id)
    if booking is not None and booking.checked_in_at is not None:
        raise HTTPException(status_code=400, detail="Student already checked in for this booking.")
    from app.domain.services.noshow_service import NoShowService
    ok = NoShowService(db).mark_no_show(booking_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Booking not found or not confirmed.")
    return MarkNoShowOut(success=True, message="Marked as no-show.")


# ---------- Reports ----------

@router.get("/reports/bookings.csv")
def export_bookings_csv(db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    rows = (
        db.query(Booking, User, Resource)
        .join(User, Booking.user_id == User.id)
        .join(Resource, Booking.resource_id == Resource.id)
        .order_by(Booking.start_time.desc()).all()
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Booking ID", "Student", "Roll No", "Department", "Sport", "Start", "End", "Status", "Booked By Staff"])
    for booking, user, resource in rows:
        booked_by = "Yes" if booking.booked_by_id else "No"
        writer.writerow([
            booking.id, user.name, user.roll_no or "", user.department or "",
            resource.type.value, booking.start_time.isoformat(), booking.end_time.isoformat(),
            booking.status.value, booked_by,
        ])
    return Response(
        content=buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=campussphere-bookings.csv"},
    )


@router.get("/reports/summary.pdf")
def export_summary_pdf(db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    pdf_bytes = build_summary_report_pdf(db)
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=campussphere-summary-report.pdf"},
    )
