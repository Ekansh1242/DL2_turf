"""Commit Node -- deterministic. Reuses the SAME BookingService as manual
booking, so FCFS + the DB exclusion constraint are never bypassed."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents import trace
from app.agents.state import AIBookingState
from app.core.timezone import now_local
from app.domain.models.models import CreatedVia
from app.domain.services.booking_service import BookingService
from app.domain.services.slot_window import SlotWindow


def commit_node(state: AIBookingState, db: Session) -> AIBookingState:
    t0 = trace.start()
    slot = SlotWindow(slot_start=state["chosen_slot_start"], slot_end=state["chosen_slot_end"])
    result = BookingService(db).book_slot(
        resource_id=state["resource_id"], user_id=state["user_id"],
        slot=slot, now=now_local(), created_via=CreatedVia.agent,
    )
    if result.success:
        from app.services.booking_notification import notify_booking
        state["email_sent"] = notify_booking(db, result.booking_id)
        state["booking_id"] = result.booking_id
        state["status"] = "confirmed"
        state["reasoning_text"] = f"Booked {state['resource_name']} at {slot.slot_start.strftime('%I:%M %p')}."
        trace.record(state, "commit_node", "completed", f"Persisted booking {result.booking_id[:8]} via BookingService.", t0, tool="book_slot")
    else:
        state["status"] = "escalated"
        state["reasoning_text"] = result.message
        trace.record(state, "commit_node", "failed", result.message, t0, tool="book_slot")
    return state
