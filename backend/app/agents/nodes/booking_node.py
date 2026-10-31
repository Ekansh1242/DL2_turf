"""
Booking Node (LLM) -- extracts intent from free text, then VALIDATES it
deterministically. The LLM may leave fields null; we never guess a sport
or time on the student's behalf.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.agents import trace
from app.agents.state import AIBookingState
from app.core.llm import get_llm_client
from app.core.timezone import now_local
from app.domain.models.models import SportType
from app.domain.services.slot_window import DAY_START_HOUR, DAY_END_HOUR

VALID_SPORTS = [s.value for s in SportType]

BOOKING_PARSE_PROMPT = f"""You extract fields from a student's request to book a
college sports facility. Valid sports: {", ".join(VALID_SPORTS)}.

Rules:
- Leave a field null if the student did not state it. NEVER guess a sport,
  date or time.
- Resolve relative dates ("today", "tomorrow") against the reference time.
- Map vague times to an hour: morning=9, afternoon=15, evening=18, night=20.
  An explicit time ("6pm", "18:00") always wins.
- players: number of people if mentioned, else null."""


class ParsedBookingIntent(BaseModel):
    sport: Optional[str] = Field(default=None, description="One of the valid sports, or null")
    date_iso: Optional[str] = Field(default=None, description="YYYY-MM-DD, or null")
    preferred_hour: Optional[int] = Field(default=None, description="24h hour, or null")
    players: Optional[int] = Field(default=None, description="Group size, or null")


def _stop(state: AIBookingState, status: str, message: str, t0: float, node_status: str = "completed"):
    state["status"] = status
    state["reasoning_text"] = message
    trace.record(state, "booking_node", node_status, message, t0)
    return state


async def booking_node(state: AIBookingState) -> AIBookingState:
    t0 = trace.start()
    now = now_local()
    if os.environ.get("BOOKING_NLU_BACKEND", "llm") == "local":
        from app.core.local_nlu import parse_booking
        intent, parsed = parse_booking(state['raw_text'], now)
        if intent != 'book':
            return _stop(state, 'needs_info', 'Please request a new booking here. Use My Bookings to cancel, or the slots view to check availability.', t0)
    else:
        llm = get_llm_client()
    
        parsed: ParsedBookingIntent = await llm.structured_call(
            system_prompt=BOOKING_PARSE_PROMPT,
            user_prompt=f"Reference time: {now.isoformat()} ({now.strftime('%A')})\nRequest: {state['raw_text']}",
            response_model=ParsedBookingIntent,
        )

    sport = (parsed.sport or "").strip().lower().replace(" ", "_")
    if sport not in VALID_SPORTS:
        return _stop(state, "needs_info",
                     "Which sport would you like? Options: " + ", ".join(s.replace("_", " ") for s in VALID_SPORTS) + ".", t0)

    try:
        date = datetime.fromisoformat(parsed.date_iso) if parsed.date_iso else None
    except ValueError:
        date = None
    if date is None:
        return _stop(state, "needs_info", "Which day should I book -- today or another date?", t0)
    if date.date() < now.date():
        return _stop(state, "rejected", f"{date.strftime('%d %b %Y')} is in the past.", t0)

    if parsed.preferred_hour is None:
        return _stop(state, "needs_info", "What time would you like? (slots run 8 AM - 7 PM)", t0)
    if not (DAY_START_HOUR <= parsed.preferred_hour < DAY_END_HOUR):
        return _stop(state, "rejected", f"{parsed.preferred_hour}:00 is outside slot hours (8 AM - 7 PM).", t0)

    state["sport"] = sport
    state["date"] = date.replace(hour=0, minute=0, second=0, microsecond=0)
    state["preferred_hour"] = parsed.preferred_hour
    state["players"] = parsed.players
    trace.record(state, "booking_node", "completed",
                 f"Understood: {sport.replace('_', ' ')}, {date.strftime('%d %b')}, {parsed.preferred_hour}:00"
                 + (f", {parsed.players} players" if parsed.players else ""), t0)
    return state
