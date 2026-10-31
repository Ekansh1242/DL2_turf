from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

BOOKING_WINDOW_OPENS_BEFORE = timedelta(minutes=30)
DAY_START_HOUR = 8
DAY_END_HOUR = 19


@dataclass
class SlotWindow:
    slot_start: datetime
    slot_end: datetime

    @property
    def window_opens_at(self) -> datetime:
        return self.slot_start - BOOKING_WINDOW_OPENS_BEFORE

    def is_bookable_at(self, now: datetime) -> bool:
        return self.window_opens_at <= now < self.slot_end

    def effective_start_for_booking_at(self, now: datetime) -> datetime:
        return max(self.slot_start, now)


def generate_daily_slots(date: datetime) -> list[SlotWindow]:
    day = date.replace(hour=0, minute=0, second=0, microsecond=0)
    slots = []
    for hour in range(DAY_START_HOUR, DAY_END_HOUR):
        start = day.replace(hour=hour)
        end = start + timedelta(hours=1)
        slots.append(SlotWindow(slot_start=start, slot_end=end))
    return slots
