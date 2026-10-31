"""Deterministic normalization of explicitly stated booking dates.

This is a parsing layer, not a claim that the trained BiLSTM learned new formats.
Dates without a year use the reference year; no automatic rollover is inferred.
"""
import re
from datetime import date, timedelta

MONTHS = {}
for number, name in enumerate(('january','february','march','april','may','june',
                              'july','august','september','october','november','december'), 1):
    MONTHS[name] = MONTHS[name[:3]] = number
MONTHS['sept'] = 9
MONTH_PATTERN = '(?:' + '|'.join(sorted(MONTHS, key=len, reverse=True)) + ')'
DAY_FIRST = re.compile(r'\b(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?P<month>' + MONTH_PATTERN + r')\b(?:[ ,]+(?P<year>\d{4})\b)?', re.I)
MONTH_FIRST = re.compile(r'\b(?P<month>' + MONTH_PATTERN + r')\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?\b(?:[ ,]+(?P<year>\d{4})\b)?', re.I)


def normalize_date(text, now):
    """Return an ISO date, None if absent; reject invalid or conflicting dates."""
    dates = set()
    for match in re.finditer(r'\b(day after tomorrow|tomorrow|today)\b', text, re.I):
        offset = {'today': 0, 'tomorrow': 1, 'day after tomorrow': 2}[match.group().lower()]
        dates.add((now.date() + timedelta(days=offset)).isoformat())
    for match in re.finditer(r'(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)', text):
        dates.add(date.fromisoformat(match.group()).isoformat())
    for pattern in (DAY_FIRST, MONTH_FIRST):
        for match in pattern.finditer(text):
            year = int(match['year']) if match['year'] else now.year
            dates.add(date(year, MONTHS[match['month'].lower()], int(match['day'])).isoformat())
    if len(dates) > 1:
        raise ValueError('Specify one booking date.')
    return next(iter(dates), None)
