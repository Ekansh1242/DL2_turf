"""CPU inference; learned extraction followed by explicit value normalization."""
import os
import re
from app.core.booking_dates import normalize_date
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def predictor():
    from ml.model import Predictor
    path = os.environ.get('BOOKING_MODEL_PATH') or str(Path(__file__).resolve().parents[2] / 'ml/artifacts/booking_model.pt')
    return Predictor(path)

def parse_booking(text, now):
    from app.agents.nodes.booking_node import ParsedBookingIntent
    result = predictor().predict(text)
    if result['intent'] != 'book':
        return result['intent'], ParsedBookingIntent()
    fields = result['fields']
    try:
        # Prefer a date explicitly present in the request. The normalizer also
        # resolves formats the small synthetic training set did not cover.
        day = normalize_date(text, now) or normalize_date(fields['date'] or '', now)
    except ValueError:
        day = None
    hour = None
    if fields['time']:
        m = re.fullmatch(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', fields['time'])
        if m and 1 <= int(m[1]) <= 12 and m[2] in (None, '00'):
            hour = int(m[1]) % 12 + (12 if m[3] == 'pm' else 0)
    players = int(fields['players']) if fields['players'] and fields['players'].isdigit() else None
    sport = fields['sport'].replace(' ','_') if fields['sport'] else None
    return result['intent'], ParsedBookingIntent(sport=sport,date_iso=day,preferred_hour=hour,players=players)
