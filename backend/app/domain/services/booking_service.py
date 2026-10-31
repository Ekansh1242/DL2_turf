from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.models.models import Booking, BookingStatus, CreatedVia
from app.domain.services.slot_window import SlotWindow


@dataclass
class SlotRequest:
    resource_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    group_id: str | None = None


@dataclass
class BookingResult:
    success: bool
    booking_id: str | None = None
    message: str = ""
    next_window_opens_at: datetime | None = None


class BookingService:
    def __init__(self, db: Session):
        self.db = db

    def find_conflicts(self, req: SlotRequest) -> list[Booking]:
        stmt = select(Booking).where(
            and_(
                Booking.resource_id == req.resource_id,
                Booking.status == BookingStatus.confirmed,
                Booking.start_time < req.end_time,
                Booking.end_time > req.start_time,
            )
        )
        return list(self.db.execute(stmt).scalars().all())

    def book_slot(
        self, resource_id: str, user_id: str, slot: SlotWindow, now: datetime,
        created_via: CreatedVia = CreatedVia.manual,
    ) -> BookingResult:
        if not slot.is_bookable_at(now):
            if now < slot.window_opens_at:
                return BookingResult(
                    success=False,
                    message="Booking window hasn't opened yet -- opens 30 minutes before the slot.",
                    next_window_opens_at=slot.window_opens_at,
                )
            return BookingResult(success=False, message="This slot has already ended.")

        effective_start = slot.effective_start_for_booking_at(now)
        req = SlotRequest(resource_id=resource_id, user_id=user_id, start_time=effective_start, end_time=slot.slot_end)

        if self.find_conflicts(req):
            return BookingResult(
                success=False,
                message="This slot was just taken by another student. Please wait for the next slot's booking window to open.",
            )

        booking = Booking(
            resource_id=req.resource_id, user_id=req.user_id,
            start_time=req.start_time, end_time=req.end_time,
            status=BookingStatus.confirmed, created_via=created_via,
        )
        self.db.add(booking)
        try:
            self.db.commit()
            self.db.refresh(booking)
            return BookingResult(success=True, booking_id=booking.id, message="Booking confirmed.")
        except IntegrityError:
            self.db.rollback()
            return BookingResult(
                success=False,
                message="This slot was just taken by another student. Please wait for the next slot's booking window to open.",
            )

    def cancel_booking(self, booking_id: str, user_id: str, now: datetime) -> BookingResult:
        """Cancellation window: open until 30 minutes after the slot's
        nominal start time -- e.g. booking the 2-3pm slot at 1:30 sharp
        still leaves you until 2:30 to cancel. Using end_time - 30min as
        the deadline works even for prorated late bookings, since
        end_time is always the slot's real (non-prorated) end."""
        booking = self.db.get(Booking, booking_id)
        if booking is None:
            return BookingResult(success=False, message="Booking not found.")
        if booking.user_id != user_id:
            return BookingResult(success=False, message="You can only cancel your own bookings.")
        if booking.status != BookingStatus.confirmed:
            return BookingResult(success=False, message="This booking is not active.")

        cancel_deadline = booking.end_time - timedelta(minutes=30)
        if now > cancel_deadline:
            return BookingResult(
                success=False,
                message=f"Cancellation window has closed (was open until {cancel_deadline.strftime('%I:%M %p')}).",
            )

        booking.status = BookingStatus.cancelled
        self.db.commit()
        return BookingResult(success=True, booking_id=booking.id, message="Booking cancelled.")
