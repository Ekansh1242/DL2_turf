from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

# CampusSphere currently serves a single campus in Nagpur, India.
# All slot/booking datetimes are stored as NAIVE local (IST) wall-clock
# values -- so every "now" used to compare against them must also be
# IST wall-clock, not UTC. Mixing the two is what caused slots to
# appear open/closed several hours off from the real local time.
APP_TZ = ZoneInfo("Asia/Kolkata")


def now_local() -> datetime:
    """Current wall-clock time in the campus's local timezone (IST), naive."""
    return datetime.now(APP_TZ).replace(tzinfo=None)


def to_local_naive(value: datetime) -> datetime:
    """Normalize a possibly timezone-aware datetime to naive IST wall-clock time.

    If the value has no tzinfo, it's assumed to already be local wall-clock
    (e.g. a plain "YYYY-MM-DD" date sent by the frontend) and is returned as-is.
    """
    if value.tzinfo is not None:
        return value.astimezone(APP_TZ).replace(tzinfo=None)
    return value
