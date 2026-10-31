from __future__ import annotations
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.domain.models.models import Resource, User, CreatedVia, Booking
from app.domain.services.booking_service import BookingService
from app.domain.services.slot_window import SlotWindow
from app.core.timezone import now_local
from app.services.receipt import build_receipt_pdf
from app.services.email_service import send_booking_confirmation_email

router = APIRouter(prefix="/api/v1/bookings", tags=["bookings"])


class ConfirmBookingIn(BaseModel):
    resource_id: str
    slot_start: datetime
    slot_end: datetime


class ConfirmBookingOut(BaseModel):
    success: bool
    booking_id: str | None = None
    message: str
    next_window_opens_at: datetime | None = None
    email_sent: bool = False


@router.post("/confirm", response_model=ConfirmBookingOut)
def confirm_booking(body: ConfirmBookingIn, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Your account is temporarily blocked due to repeated no-shows.")
    resource = db.get(Resource, body.resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Turf/resource not found.")
    slot = SlotWindow(slot_start=body.slot_start, slot_end=body.slot_end)
    service = BookingService(db)
    result = service.book_slot(resource_id=body.resource_id, user_id=user_id, slot=slot, now=now_local(), created_via=CreatedVia.manual)

    email_sent = False
    if result.success and result.booking_id:
        from app.services.booking_notification import notify_booking
        email_sent = notify_booking(db, result.booking_id)

    return ConfirmBookingOut(
        success=result.success, booking_id=result.booking_id, message=result.message,
        next_window_opens_at=result.next_window_opens_at, email_sent=email_sent,
    )


@router.get("/{booking_id}/receipt.pdf")
def get_booking_receipt(booking_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found.")
    user = db.get(User, user_id)
    if booking.user_id != user_id and (user is None or user.role != "admin"):
        raise HTTPException(status_code=403, detail="Not your booking.")
    resource = db.get(Resource, booking.resource_id)
    booking_user = db.get(User, booking.user_id)
    pdf_bytes = build_receipt_pdf(booking, booking_user, resource)
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="campussphere-receipt-{booking.id[:8]}.pdf"'},
    )


class CancelBookingOut(BaseModel):
    success: bool
    message: str


@router.patch("/{booking_id}/cancel", response_model=CancelBookingOut)
def cancel_booking(booking_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    booking_before = db.get(Booking, booking_id)
    resource_id = booking_before.resource_id if booking_before else None
    slot_start = booking_before.start_time if booking_before else None
    slot_end = booking_before.end_time if booking_before else None

    service = BookingService(db)
    result = service.cancel_booking(booking_id, user_id=user_id, now=now_local())

    if result.success and resource_id:
        # A slot just freed up -- tell the earliest waitlisted student.
        from app.domain.services.waitlist_service import WaitlistService
        WaitlistService(db).notify_next_on_cancel(resource_id, slot_start, slot_end)

    return CancelBookingOut(success=result.success, message=result.message)


class JoinWaitlistIn(BaseModel):
    resource_id: str
    slot_start: datetime
    slot_end: datetime


class JoinWaitlistOut(BaseModel):
    success: bool
    entry_id: str | None = None
    message: str


@router.post("/waitlist/join", response_model=JoinWaitlistOut)
def join_waitlist(body: JoinWaitlistIn, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    from app.domain.services.waitlist_service import WaitlistService
    result = WaitlistService(db).join(body.resource_id, user_id, body.slot_start, body.slot_end)
    return JoinWaitlistOut(success=result.success, entry_id=result.entry_id, message=result.message)


@router.get("/mine", response_model=list[dict])
def my_bookings(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """Upcoming + recent bookings for the logged-in student, used to
    show a cancel button with the live cancellation deadline."""
    rows = (
        db.query(Booking, Resource)
        .join(Resource, Booking.resource_id == Resource.id)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.start_time.desc())
        .limit(20).all()
    )
    out = []
    for booking, resource in rows:
        cancel_deadline = booking.end_time - timedelta(minutes=30)
        out.append({
            "id": booking.id,
            "resource_name": resource.name,
            "sport": resource.type.value,
            "start_time": booking.start_time.isoformat(),
            "end_time": booking.end_time.isoformat(),
            "status": booking.status.value,
            "cancel_deadline": cancel_deadline.isoformat(),
            "can_cancel": booking.status.value == "confirmed" and now_local() <= cancel_deadline,
        })
    return out
