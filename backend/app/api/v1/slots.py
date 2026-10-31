from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.models.models import Resource, Booking, BookingStatus
from app.domain.services.slot_window import generate_daily_slots
from app.core.timezone import now_local, to_local_naive

router = APIRouter(prefix="/api/v1/slots", tags=["slots"])


class SlotOut(BaseModel):
    slot_start: datetime
    slot_end: datetime
    window_opens_at: datetime
    is_booked: bool
    is_bookable_now: bool


@router.get("", response_model=list[SlotOut])
def get_slots(resource_id: str = Query(...), date: datetime = Query(...), db: Session = Depends(get_db)):
    date = to_local_naive(date)
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found.")
    slots = generate_daily_slots(date)
    existing = db.query(Booking).filter(
        Booking.resource_id == resource_id,
        Booking.status == BookingStatus.confirmed,
        Booking.start_time >= date.replace(hour=0, minute=0, second=0, microsecond=0),
        Booking.start_time < date.replace(hour=23, minute=59, second=59),
    ).all()
    booked_starts = {b.start_time.replace(minute=0, second=0, microsecond=0) for b in existing}
    now = now_local()
    out = []
    for slot in slots:
        is_booked = slot.slot_start in booked_starts
        out.append(SlotOut(
            slot_start=slot.slot_start, slot_end=slot.slot_end, window_opens_at=slot.window_opens_at,
            is_booked=is_booked, is_bookable_now=(not is_booked) and slot.is_bookable_at(now),
        ))
    return out
