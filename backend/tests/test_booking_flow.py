"""
17 tests for the deterministic booking/equipment/no-show rules, plus
tests for the real LangGraph AI booking flow with the LLM calls mocked
(per standard practice: unit tests shouldn't require a live OpenAI key).
"""
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.domain.models.models import (
    Base, University, Campus, User, Resource, SportType, UserRole,
    EquipmentCatalog, BookingStatus, Booking,
)
from app.domain.services.slot_window import SlotWindow, generate_daily_slots
from app.domain.services.booking_service import BookingService
from app.domain.services.equipment_service import EquipmentService
from app.domain.services.noshow_service import NoShowService, NO_SHOW_BLOCK_THRESHOLD


def _frozen_datetime(fake_now: datetime):
    """A real datetime subclass with utcnow() overridden -- unlike a bare
    MagicMock, this keeps fromisoformat/other real methods working."""
    class Frozen(datetime):
        @classmethod
        def utcnow(cls):
            return fake_now
    return Frozen


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    uni = University(name="RCOEM")
    session.add(uni)
    session.flush()
    campus = Campus(university_id=uni.id, name="Main Campus")
    session.add(campus)
    session.flush()

    user = User(campus_id=campus.id, name="Ekansh", email="ekansh@rknec.edu", roll_no="21BCE001", role=UserRole.student)
    resource = Resource(campus_id=campus.id, name="Football Turf", type=SportType.football)
    session.add_all([user, resource])
    session.flush()

    ball = EquipmentCatalog(sport=SportType.football, name="Football", quantity_total=5, quantity_available=5)
    session.add(ball)
    session.commit()

    session.test_user = user
    session.test_resource = resource
    session.test_ball = ball
    yield session
    session.close()


# ---- slot window ----

def test_daily_slots_are_8am_to_7pm_hourly():
    slots = generate_daily_slots(datetime(2026, 8, 10))
    assert len(slots) == 11


def test_window_not_open_more_than_30_min_before():
    slot = SlotWindow(slot_start=datetime(2026, 8, 10, 14, 0), slot_end=datetime(2026, 8, 10, 15, 0))
    assert not slot.is_bookable_at(datetime(2026, 8, 10, 13, 20))


def test_window_open_exactly_30_min_before():
    slot = SlotWindow(slot_start=datetime(2026, 8, 10, 14, 0), slot_end=datetime(2026, 8, 10, 15, 0))
    assert slot.is_bookable_at(datetime(2026, 8, 10, 13, 30))


def test_window_closed_after_slot_ends():
    slot = SlotWindow(slot_start=datetime(2026, 8, 10, 14, 0), slot_end=datetime(2026, 8, 10, 15, 0))
    assert not slot.is_bookable_at(datetime(2026, 8, 10, 15, 1))


def test_late_booking_is_prorated():
    slot = SlotWindow(slot_start=datetime(2026, 8, 10, 14, 0), slot_end=datetime(2026, 8, 10, 15, 0))
    now = datetime(2026, 8, 10, 14, 10)
    assert slot.effective_start_for_booking_at(now) == now


# ---- FCFS booking ----

def _make_booking(db, hour=14):
    slot = SlotWindow(slot_start=datetime(2026, 8, 10, hour, 0), slot_end=datetime(2026, 8, 10, hour + 1, 0))
    return BookingService(db).book_slot(db.test_resource.id, db.test_user.id, slot, datetime(2026, 8, 10, hour - 1, 45))


def test_booking_succeeds_within_window(db):
    result = _make_booking(db)
    assert result.success


def test_second_booking_for_same_slot_rejected_fcfs(db):
    first = _make_booking(db)
    assert first.success
    second_user = User(campus_id=db.test_user.campus_id, name="Rahul", email="rahul@rknec.edu", roll_no="21BCE002", role=UserRole.student)
    db.add(second_user)
    db.commit()
    slot = SlotWindow(slot_start=datetime(2026, 8, 10, 14, 0), slot_end=datetime(2026, 8, 10, 15, 0))
    second = BookingService(db).book_slot(db.test_resource.id, second_user.id, slot, datetime(2026, 8, 10, 13, 45))
    assert not second.success
    assert "taken" in second.message.lower()


# ---- equipment / fines ----

def test_equipment_checkout_decrements_availability(db):
    booking = _make_booking(db)
    result = EquipmentService(db).checkout(booking.booking_id, db.test_user.id, db.test_ball.id, 1)
    assert result.success
    db.refresh(db.test_ball)
    assert db.test_ball.quantity_available == 4


def test_returning_damaged_equipment_applies_standard_fine(db):
    booking = _make_booking(db)
    result = EquipmentService(db).checkout(booking.booking_id, db.test_user.id, db.test_ball.id, 1)
    success, fine = EquipmentService(db).return_item(result.loan_id, condition="damaged")
    assert success and fine == 250


# ---- no-shows ----

def test_user_blocked_after_threshold_no_shows(db):
    for i in range(NO_SHOW_BLOCK_THRESHOLD):
        booking = _make_booking(db, hour=8 + i)
        NoShowService(db).mark_no_show(booking.booking_id)
    db.refresh(db.test_user)
    assert db.test_user.is_blocked


# ---- AI booking graph (LLM mocked) ----

# ---- AI booking graph (LLM mocked, clock frozen) ---------------------------
from contextlib import ExitStack
from app.agents.graph import build_ai_booking_graph
from app.agents.nodes.booking_node import ParsedBookingIntent
from app.agents.nodes.scheduling_conflict_node import CandidateChoice

DAY = "2026-08-10"


async def _run(db, intent, now, conflict_llm=None, text="book it"):
    """Run the real graph. `conflict_llm` is an AsyncMock for the conflict node."""
    booking_llm = AsyncMock()
    booking_llm.structured_call.return_value = intent
    with ExitStack() as s:
        s.enter_context(patch("app.agents.nodes.booking_node.get_llm_client", return_value=booking_llm))
        s.enter_context(patch("app.agents.nodes.scheduling_conflict_node.get_llm_client", return_value=conflict_llm or AsyncMock()))
        for mod in ("booking_node", "scheduling_conflict_node", "commit_node"):
            s.enter_context(patch(f"app.agents.nodes.{mod}.now_local", return_value=now))
        return await build_ai_booking_graph(db).ainvoke(
            {"request_id": "r", "user_id": db.test_user.id, "raw_text": text, "trace": []})


def _intent(sport="football", date=DAY, hour=8, players=None):
    return ParsedBookingIntent(sport=sport, date_iso=date, preferred_hour=hour, players=players)


def _confirmed_count(db):
    return db.query(Booking).filter(Booking.status == BookingStatus.confirmed).count()


@pytest.mark.asyncio
async def test_no_conflict_commits_and_trace_is_measured(db):
    final = await _run(db, _intent(hour=8), datetime(2026, 8, 10, 7, 45))
    assert final["status"] == "confirmed" and final["booking_id"]
    assert [t["node"] for t in final["trace"]] == ["booking_node", "scheduling_conflict_node", "commit_node"]
    assert all(isinstance(t["duration_ms"], int) and t["status"] == "completed" for t in final["trace"])
    assert db.get(Booking, final["booking_id"]).created_via.value == "agent"


@pytest.mark.asyncio
async def test_conflict_proposes_but_does_not_book(db):
    _make_booking(db, hour=8)  # someone else holds the preferred slot
    llm = AsyncMock()
    llm.structured_call.return_value = CandidateChoice(candidate_id="slot_9", reasoning_text="Next free slot.", confidence="high")
    final = await _run(db, _intent(hour=8), datetime(2026, 8, 10, 8, 35), conflict_llm=llm)
    assert final["status"] == "needs_confirmation"
    assert final["chosen_slot_start"].hour == 9 and final["decision_source"] == "llm"
    assert _confirmed_count(db) == 1  # nothing auto-booked
    assert "commit_node" not in [t["node"] for t in final["trace"]]


@pytest.mark.asyncio
async def test_invalid_llm_choice_falls_back_to_valid_candidate(db):
    _make_booking(db, hour=8)
    llm = AsyncMock()
    llm.structured_call.return_value = CandidateChoice(candidate_id="slot_99", reasoning_text="x", confidence="high")
    final = await _run(db, _intent(hour=8), datetime(2026, 8, 10, 8, 35), conflict_llm=llm)
    assert final["decision_source"] == "deterministic_fallback"
    assert final["chosen_slot_start"].hour == 9
    assert final["trace"][1]["status"] == "fallback"


@pytest.mark.asyncio
async def test_llm_failure_in_conflict_node_falls_back(db):
    _make_booking(db, hour=8)
    llm = AsyncMock()
    llm.structured_call.side_effect = Exception("network down")
    final = await _run(db, _intent(hour=8), datetime(2026, 8, 10, 8, 35), conflict_llm=llm)
    assert final["status"] == "needs_confirmation" and final["decision_source"] == "deterministic_fallback"


@pytest.mark.asyncio
async def test_future_slot_is_recommendation_not_bookable_now(db):
    """Preferred 9am is taken at 8:35; 10am window hasn't opened, 9:30 -> recommend, never book."""
    _make_booking(db, hour=9)
    llm = AsyncMock()
    llm.structured_call.return_value = CandidateChoice(candidate_id="slot_10", reasoning_text="Closest.", confidence="medium")
    final = await _run(db, _intent(hour=9), datetime(2026, 8, 10, 8, 35), conflict_llm=llm)
    assert final["status"] == "recommendation"
    assert any(c["candidate_id"] == "slot_10" and c["bookable_now"] is False for c in final["candidates"])
    assert _confirmed_count(db) == 1


@pytest.mark.asyncio
async def test_unsupported_sport_asks_for_info_and_skips_other_nodes(db):
    final = await _run(db, _intent(sport="swimming"), datetime(2026, 8, 10, 7, 45))
    assert final["status"] == "needs_info" and "Which sport" in final["reasoning_text"]
    assert [t["node"] for t in final["trace"]] == ["booking_node"]


@pytest.mark.asyncio
async def test_missing_time_asks_for_info(db):
    final = await _run(db, ParsedBookingIntent(sport="football", date_iso=DAY), datetime(2026, 8, 10, 7, 45))
    assert final["status"] == "needs_info" and _confirmed_count(db) == 0


@pytest.mark.asyncio
async def test_past_date_rejected(db):
    final = await _run(db, _intent(date="2026-08-01"), datetime(2026, 8, 10, 7, 45))
    assert final["status"] == "rejected"


@pytest.mark.asyncio
async def test_hour_outside_slot_hours_rejected(db):
    final = await _run(db, _intent(hour=22), datetime(2026, 8, 10, 7, 45))
    assert final["status"] == "rejected"


@pytest.mark.asyncio
async def test_window_not_open_yet_explains_when_it_opens(db):
    final = await _run(db, _intent(hour=14), datetime(2026, 8, 10, 9, 0))
    assert final["status"] == "not_yet_open" and "01:30 PM" in final["reasoning_text"]
    assert _confirmed_count(db) == 0


@pytest.mark.asyncio
async def test_no_open_slots_escalates(db):
    for h in range(8, 19):
        _make_booking(db, hour=h)
    final = await _run(db, _intent(hour=8), datetime(2026, 8, 10, 8, 20), conflict_llm=AsyncMock())
    assert final["status"] == "escalated" and _confirmed_count(db) == 11


# ---- Analytics agent (allowlist + grounding) -------------------------------
@pytest.mark.asyncio
async def test_analytics_agent_routes_to_allowlisted_tool_and_grounds_answer(db):
    from app.agents.analytics_agent import run_analytics_agent, ToolChoice, Answer
    _make_booking(db, hour=14)
    llm = AsyncMock()
    llm.structured_call.side_effect = [ToolChoice(tool="by_sport"), Answer(answer="Football has 1 booking.")]
    with patch("app.agents.analytics_agent.get_llm_client", return_value=llm):
        out = await run_analytics_agent("which sport is busiest?", db)
    assert out["tool"] == "by_sport" and out["data"] == [{"sport": "football", "count": 1}]
    assert [t["node"] for t in out["trace"]] == ["router", "analytics_query", "summariser"]


@pytest.mark.asyncio
async def test_analytics_agent_skips_llm_summary_when_no_data(db):
    from app.agents.analytics_agent import run_analytics_agent, ToolChoice
    llm = AsyncMock()
    llm.structured_call.return_value = ToolChoice(tool="by_sport")
    with patch("app.agents.analytics_agent.get_llm_client", return_value=llm):
        out = await run_analytics_agent("anything", db)
    assert out["answer"] == "There is no booking data for that yet."
    assert llm.structured_call.call_count == 1  # no hallucination opportunity


def test_analytics_tool_names_are_a_fixed_allowlist():
    from pydantic import ValidationError
    from app.agents.analytics_agent import ToolChoice
    with pytest.raises(ValidationError):
        ToolChoice(tool="DROP TABLE bookings")
