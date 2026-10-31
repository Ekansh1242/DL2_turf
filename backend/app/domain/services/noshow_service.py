from __future__ import annotations
from app.domain.models.models import Booking, BookingStatus, NoShowRecord, User

NO_SHOW_BLOCK_THRESHOLD = 3


class NoShowService:
    def __init__(self, db):
        self.db = db

    def mark_no_show(self, booking_id: str) -> bool:
        booking = self.db.get(Booking, booking_id)
        if booking is None or booking.status != BookingStatus.confirmed:
            return False
        booking.status = BookingStatus.no_show
        record = NoShowRecord(booking_id=booking.id, user_id=booking.user_id)
        self.db.add(record)
        user = self.db.get(User, booking.user_id)
        if user:
            user.no_show_count += 1
            if user.no_show_count >= NO_SHOW_BLOCK_THRESHOLD:
                user.is_blocked = True
        self.db.commit()
        return True
