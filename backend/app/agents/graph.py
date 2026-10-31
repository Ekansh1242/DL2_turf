"""
booking -> (stop if input invalid/incomplete) -> scheduling_conflict
        -> commit only when the preferred slot is free; any conflict ends
           with a proposal the student must confirm.
"""
from __future__ import annotations

from functools import partial
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.agents.state import AIBookingState
from app.agents.nodes.booking_node import booking_node
from app.agents.nodes.scheduling_conflict_node import scheduling_conflict_node
from app.agents.nodes.commit_node import commit_node


def _after_booking(state: AIBookingState) -> str:
    return "end" if state.get("status") else "scheduling_conflict"


def _after_scheduling(state: AIBookingState) -> str:
    return "end" if state.get("status") else "commit"


def build_ai_booking_graph(db: Session):
    graph = StateGraph(AIBookingState)
    graph.add_node("booking", booking_node)
    graph.add_node("scheduling_conflict", partial(scheduling_conflict_node, db=db))
    graph.add_node("commit", partial(commit_node, db=db))

    graph.set_entry_point("booking")
    graph.add_conditional_edges("booking", _after_booking, {"scheduling_conflict": "scheduling_conflict", "end": END})
    graph.add_conditional_edges("scheduling_conflict", _after_scheduling, {"commit": "commit", "end": END})
    graph.add_edge("commit", END)
    return graph.compile()


GRAPH_RECURSION_LIMIT = 8
