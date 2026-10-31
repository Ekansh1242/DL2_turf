"""Truthful execution trace: every event is appended by the node that
actually ran, with a measured duration -- nothing is pre-scripted."""
from __future__ import annotations

import time


def start() -> float:
    return time.perf_counter()


def record(state: dict, node: str, status: str, summary: str, started: float, **extra) -> None:
    state.setdefault("trace", []).append({
        "node": node,
        "status": status,  # completed | skipped | failed | fallback
        "summary": summary,
        "duration_ms": int((time.perf_counter() - started) * 1000),
        **extra,
    })
