"""
Scheduling + Conflict Node.

1. Deterministic tools: resolve the turf, load the day's real bookings,
   decide whether the preferred slot is bookable right now.
2. Only if it is NOT: build candidate slots from real data, drop any that
   violate hard rules, and let the LLM weigh the trade-offs between the
   rest. The LLM's pick is validated against the candidate list; an
   invalid pick or LLM failure falls back to a deterministic choice.
3. An alternative is never auto-booked -- it is returned as a proposal
   the student must confirm.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents import trace
from app.agents.state import AIBookingState
from app.core.llm import get_llm_client
from app.core.timezone import now_local
from app.domain.models.models import Resource, Booking, BookingStatus, SportType, EquipmentCatalog
from app.domain.services.slot_window import generate_daily_slots

MIN_USABLE_MINUTES = 30  # drop slivers of a slot that is almost over


class CandidateChoice(BaseModel):
    candidate_id: str = Field(description="id of one candidate from the provided list")
    reasoning_text: str = Field(description="One or two plain sentences explaining the trade-off")
    confidence: Literal["high", "medium", "low"]


CONFLICT_PROMPT = """A student's preferred slot is unavailable. Choose ONE candidate
from the list -- only use candidate ids that appear in it.

Each candidate has real facts:
- bookable_now: false means its booking window has not opened yet, so it can
  only be recommended, not booked immediately
- usable_minutes: time actually left in the slot
- minutes_from_preferred: distance from the requested time
- turf_load_today: how busy this turf already is today
- back_to_back: the neighbouring hour is also booked

Weigh closeness to the requested time against whether the student can book it
right now and how much playing time they get. Mention the trade-off briefly.
Do not claim anything that is not in the data."""


def _stop(state, status, message, t0, node_status="completed"):
    state["status"] = status
    state["reasoning_text"] = message
    trace.record(state, "scheduling_conflict_node", node_status, message, t0)
    return state


def _fallback(candidates: list[dict]) -> dict:
    return min(candidates, key=lambda c: (c["minutes_from_preferred"], not c["bookable_now"], -c["usable_minutes"]))


async def scheduling_conflict_node(state: AIBookingState, db: Session) -> AIBookingState:
    t0 = trace.start()
    sport = SportType(state["sport"])
    resource = db.query(Resource).filter(Resource.type == sport).first()
    if resource is None:
        return _stop(state, "escalated", f"No turf is configured for {sport.value.replace('_', ' ')}.", t0, "failed")

    state["resource_id"] = resource.id
    state["resource_name"] = resource.name

    date = state["date"]
    now = now_local()
    slots = generate_daily_slots(date)
    day_bookings = db.query(Booking).filter(
        Booking.resource_id == resource.id,
        Booking.status == BookingStatus.confirmed,
        Booking.start_time >= date,
        Booking.start_time < date.replace(hour=23, minute=59, second=59),
    ).all()
    booked_hours = {b.start_time.hour for b in day_bookings}
    pref = state["preferred_hour"]
    preferred_slot = next((s for s in slots if s.slot_start.hour == pref), None)

    # ---- no conflict path -------------------------------------------------
    if preferred_slot and pref not in booked_hours and preferred_slot.slot_end > now:
        if preferred_slot.is_bookable_at(now):
            state["has_conflict"] = False
            state["chosen_slot_start"], state["chosen_slot_end"] = preferred_slot.slot_start, preferred_slot.slot_end
            state["reasoning_text"] = "Your preferred slot is free."
            trace.record(state, "scheduling_conflict_node", "completed",
                         f"Checked {len(day_bookings)} booking(s) on {resource.name}: {pref}:00 is free, no conflict.", t0,
                         tool="availability_query")
            return state
        return _stop(state, "not_yet_open",
                     f"{pref}:00 is free, but booking opens at {preferred_slot.window_opens_at.strftime('%I:%M %p on %d %b')} "
                     "(slots open 30 minutes before they start).", t0)

    # ---- conflict path ----------------------------------------------------
    state["has_conflict"] = True
    candidates: list[dict] = []
    for s in slots:
        h = s.slot_start.hour
        usable = int((s.slot_end - max(s.slot_start, now)).total_seconds() // 60)
        if h in booked_hours or usable < MIN_USABLE_MINUTES:
            continue
        candidates.append({
            "candidate_id": f"slot_{h}",
            "start": s.slot_start, "end": s.slot_end,
            "bookable_now": s.is_bookable_at(now),
            "opens_at": s.window_opens_at.strftime("%H:%M"),
            "usable_minutes": min(usable, 60),
            "minutes_from_preferred": abs(h - pref) * 60,
            "turf_load_today": len(day_bookings),
            "back_to_back": (h - 1 in booked_hours) or (h + 1 in booked_hours),
        })

    if not candidates:
        return _stop(state, "escalated", "No suitable free slots remain for this turf on that day.", t0, "failed")

    equipment = db.query(EquipmentCatalog).filter(EquipmentCatalog.sport == sport).all()
    equip_text = ", ".join(f"{e.name}: {e.quantity_available} available" for e in equipment) or "none listed"

    decision_source, chosen, reason, confidence = "llm", None, None, None
    try:
        llm = get_llm_client()
        payload = [{k: (v.strftime("%H:%M") if k in ("start", "end") else v) for k, v in c.items()} for c in candidates]
        choice: CandidateChoice = await llm.structured_call(
            system_prompt=CONFLICT_PROMPT,
            user_prompt=(f"Student request: {state['raw_text']}\nPreferred hour: {pref}:00\n"
                         f"Players: {state.get('players') or 'not stated'}\n"
                         f"Equipment for this sport: {equip_text}\nCandidates: {payload}"),
            response_model=CandidateChoice,
        )
        chosen = next((c for c in candidates if c["candidate_id"] == choice.candidate_id), None)
        reason, confidence = choice.reasoning_text, choice.confidence
    except Exception:
        chosen = None

    if chosen is None:  # invalid pick or LLM failure -> safe deterministic choice
        decision_source = "deterministic_fallback"
        chosen = _fallback(candidates)
        reason = (f"{chosen['start'].strftime('%I:%M %p')} is the closest free slot"
                  + ("" if chosen["bookable_now"] else f" (booking opens at {chosen['opens_at']})") + ".")
        confidence = "medium"

    state["chosen_slot_start"], state["chosen_slot_end"] = chosen["start"], chosen["end"]
    state["reasoning_text"] = reason
    state["decision_source"] = decision_source
    state["candidates"] = [{**c, "start": c["start"].isoformat(), "end": c["end"].isoformat()} for c in candidates]
    state["status"] = "needs_confirmation" if chosen["bookable_now"] else "recommendation"
    trace.record(state, "scheduling_conflict_node",
                 "completed" if decision_source == "llm" else "fallback",
                 f"Conflict at {pref}:00. Evaluated {len(candidates)} real candidate(s); picked "
                 f"{chosen['start'].strftime('%H:%M')} ({decision_source}, confidence {confidence}). {reason}",
                 t0, tool="availability_query", decision_source=decision_source)
    return state
