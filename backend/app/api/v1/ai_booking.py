"""
POST /api/v1/bookings/ai-book -- live entrypoint for the LangGraph agent.

Statuses: confirmed | needs_confirmation | recommendation | needs_info |
          rejected | not_yet_open | escalated
An alternative slot is NEVER auto-booked: the student confirms it through
the normal POST /bookings/confirm, which re-checks availability.
"""
from __future__ import annotations

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.graph import build_ai_booking_graph, GRAPH_RECURSION_LIMIT
from app.core.security import get_current_user_id
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/bookings", tags=["ai-booking"])


class AIBookIn(BaseModel):
    message: str


class Proposal(BaseModel):
    resource_id: str
    slot_start: str
    slot_end: str


class AIBookOut(BaseModel):
    status: str
    booking_id: str | None = None
    resource_name: str | None = None
    message: str
    proposal: Proposal | None = None
    candidates: list[dict] = []
    decision_source: str | None = None
    email_sent: bool = False
    total_ms: int = 0
    trace: list[dict]


@router.post("/ai-book", response_model=AIBookOut)
async def ai_book(body: AIBookIn, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Please describe what you want to book.")
    try:
        graph = build_ai_booking_graph(db)
        final = await graph.ainvoke(
            {"request_id": str(uuid.uuid4()), "user_id": user_id, "raw_text": body.message.strip(), "trace": []},
            config={"recursion_limit": GRAPH_RECURSION_LIMIT},
        )
    except RuntimeError as e:  # e.g. OPENAI_API_KEY missing -- fail loudly
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        logger.exception("AI booking graph failed")
        raise HTTPException(status_code=502, detail="The AI assistant had a problem. Please try again or book manually.")

    status = final.get("status", "escalated")
    proposal = None
    if status in ("needs_confirmation", "recommendation") and final.get("chosen_slot_start"):
        proposal = Proposal(
            resource_id=final["resource_id"],
            slot_start=final["chosen_slot_start"].isoformat(),
            slot_end=final["chosen_slot_end"].isoformat(),
        )
    trace = final.get("trace", [])
    return AIBookOut(
        email_sent=final.get("email_sent", False),
        status=status, booking_id=final.get("booking_id"), resource_name=final.get("resource_name"),
        message=final.get("reasoning_text") or "Could not complete the request.",
        proposal=proposal, candidates=final.get("candidates", []),
        decision_source=final.get("decision_source"),
        total_ms=sum(t.get("duration_ms", 0) for t in trace), trace=trace,
    )
