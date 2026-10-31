"""
WaitlistService -- lets a student join a waitlist for a slot that's
currently booked. If that exact booking gets cancelled, the earliest
'waiting' entry for the same resource+time is notified by email (FCFS
applies to the waitlist itself too, not just the original booking).

This is intentionally simple for v1: no auto-booking on notify (the
student still has to come back and book it themselves within the
normal window) -- auto-booking on their behalf would silently spend
their booking slot without confirmation, which is worse UX than a
heads-up email.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.domain.models.models import WaitlistEntry, WaitlistStatus, User, Resource
from app.services.email_service import send_plain_email


@dataclass
class JoinWaitlistResult:
    success: bool
    entry_id: str | None = None
    message: str = ""


class WaitlistService:
    def __init__(self, db: Session):
        self.db = db

    def join(self, resource_id: str, user_id: str, slot_start: datetime, slot_end: datetime) -> JoinWaitlistResult:
        existing = self.db.execute(
            select(WaitlistEntry).where(
                and_(
                    WaitlistEntry.resource_id == resource_id,
                    WaitlistEntry.user_id == user_id,
                    WaitlistEntry.slot_start == slot_start,
                    WaitlistEntry.status == WaitlistStatus.waiting,
                )
            )
        ).scalar_one_or_none()
        if existing:
            return JoinWaitlistResult(success=True, entry_id=existing.id, message="You're already on the waitlist for this slot.")

        entry = WaitlistEntry(resource_id=resource_id, user_id=user_id, slot_start=slot_start, slot_end=slot_end)
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return JoinWaitlistResult(success=True, entry_id=entry.id, message="Added to the waitlist. We'll email you if the slot opens up.")

    def notify_next_on_cancel(self, resource_id: str, slot_start: datetime, slot_end: datetime) -> bool:
        """Call this right after a booking for (resource_id, slot_start,
        slot_end) is cancelled. Notifies the earliest waiting entry, if
        any, and marks it notified. Returns True if someone was notified."""
        next_entry = self.db.execute(
            select(WaitlistEntry).where(
                and_(
                    WaitlistEntry.resource_id == resource_id,
                    WaitlistEntry.slot_start == slot_start,
                    WaitlistEntry.slot_end == slot_end,
                    WaitlistEntry.status == WaitlistStatus.waiting,
                )
            ).order_by(WaitlistEntry.created_at.asc())
        ).scalars().first()

        if next_entry is None:
            return False

        user = self.db.get(User, next_entry.user_id)
        resource = self.db.get(Resource, resource_id)
        if user and resource:
            send_plain_email(
                to_email=user.email,
                subject=f"A slot opened up: {resource.name}",
                body_text=(
                    f"Hi {user.name},\n\nGood news -- the {slot_start.strftime('%I:%M %p')} - "
                    f"{slot_end.strftime('%I:%M %p')} slot for {resource.name} on "
                    f"{slot_start.strftime('%A, %d %B')} just opened up because someone cancelled.\n\n"
                    "Log in to CampusSphere and book it before someone else does -- "
                    "this is first-come, first-served like any other slot.\n\n-- CampusSphere"
                ),
            )

        next_entry.status = WaitlistStatus.notified
        next_entry.notified_at = datetime.utcnow()
        self.db.commit()
        return True

    def my_waitlist(self, user_id: str) -> list[WaitlistEntry]:
        return list(self.db.execute(
            select(WaitlistEntry).where(
                and_(WaitlistEntry.user_id == user_id, WaitlistEntry.status == WaitlistStatus.waiting)
            ).order_by(WaitlistEntry.created_at.desc())
        ).scalars().all())
