"""
Admin Analytics Agent -- read-only.

Step 1 (LLM): map the question to ONE tool from a fixed allowlist.
Step 2 (deterministic): run the existing, validated analytics query.
Step 3 (LLM): summarise ONLY the returned data.
The LLM never writes SQL and never touches the database.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents import trace
from app.core.llm import get_llm_client

ToolName = Literal["summary", "trend", "by_sport", "by_department", "by_year",
                   "peak_hours", "top_students", "equipment_issues", "fines_by_student"]


class ToolChoice(BaseModel):
    tool: ToolName
    days: int = Field(default=30, description="Look-back window, only used by 'trend'")


class Answer(BaseModel):
    answer: str


def _run_tool(tool: str, days: int, db: Session):
    from app.api.v1 import admin as a  # existing deterministic analytics queries
    days = max(1, min(days, 180))
    fn = {
        "summary": lambda: a.analytics_summary(db=db, _=""),
        "trend": lambda: a.analytics_trend(days=days, db=db, _=""),
        "by_sport": lambda: a.analytics_by_sport(db=db, _=""),
        "by_department": lambda: a.analytics_by_department(db=db, _=""),
        "by_year": lambda: a.analytics_by_year(db=db, _=""),
        "peak_hours": lambda: a.analytics_peak_hours(db=db, _=""),
        "top_students": lambda: a.analytics_top_students(limit=5, db=db, _=""),
        "equipment_issues": lambda: a.analytics_equipment_issues(db=db, _=""),
        "fines_by_student": lambda: a.analytics_fines_by_student(db=db, _=""),
    }[tool]
    result = fn()
    if isinstance(result, list):
        return [r.model_dump() for r in result]
    return result.model_dump()


async def run_analytics_agent(question: str, db: Session) -> dict:
    events: list[dict] = []
    llm = get_llm_client()

    t0 = trace.start()
    choice: ToolChoice = await llm.structured_call(
        system_prompt=("You route a staff member's question about sports-facility bookings to exactly one "
                       "analytics tool. summary=totals/no-shows/fines; trend=bookings per day; by_sport; "
                       "by_department; by_year; peak_hours=busiest hours; top_students; "
                       "equipment_issues=damaged/lost gear; fines_by_student."),
        user_prompt=question, response_model=ToolChoice,
    )
    trace.record({"trace": events}, "router", "completed", f"Selected tool '{choice.tool}'", t0)

    t1 = trace.start()
    data = _run_tool(choice.tool, choice.days, db)
    trace.record({"trace": events}, "analytics_query", "completed", f"Ran read-only query '{choice.tool}'", t1, tool=choice.tool)

    empty = (not data) or (isinstance(data, dict) and not any(data.values()))
    t2 = trace.start()
    if empty:
        text = "There is no booking data for that yet."
    else:
        ans: Answer = await llm.structured_call(
            system_prompt=("Answer the staff member's question in 2-3 plain sentences using ONLY the data "
                           "provided. Quote the actual numbers. If the data cannot answer the question, say so."),
            user_prompt=f"Question: {question}\nData ({choice.tool}): {data}", response_model=Answer,
        )
        text = ans.answer
    trace.record({"trace": events}, "summariser", "completed", "Summarised the returned data", t2)
    return {"answer": text, "tool": choice.tool, "data": data, "trace": events}
