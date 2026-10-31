"""
Shared state threaded through the AI booking graph:

booking_node (LLM: intent extraction + validation)
  -> scheduling_conflict_node (DB tools; LLM weighs trade-offs only on conflict)
  -> commit_node (deterministic FCFS-safe booking, only when no conflict)

status values: confirmed | needs_confirmation | recommendation |
               needs_info | rejected | not_yet_open | escalated
"""
from __future__ import annotations

from datetime import datetime
from typing import TypedDict, Optional


class AIBookingState(TypedDict, total=False):
    request_id: str
    user_id: str
    raw_text: str

    # booking_node
    sport: Optional[str]
    date: Optional[datetime]
    preferred_hour: Optional[int]
    players: Optional[int]

    # scheduling_conflict_node
    resource_id: Optional[str]
    resource_name: Optional[str]
    has_conflict: Optional[bool]
    candidates: list[dict]
    chosen_slot_start: Optional[datetime]
    chosen_slot_end: Optional[datetime]
    reasoning_text: Optional[str]
    decision_source: Optional[str]  # llm | deterministic_fallback

    # commit_node
    email_sent: bool
    booking_id: Optional[str]
    status: Optional[str]

    trace: list[dict]
