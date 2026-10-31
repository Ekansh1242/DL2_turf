from datetime import datetime
import pytest
from app.core.booking_dates import normalize_date

NOW = datetime(2026, 10, 31, 12)

@pytest.mark.parametrize('text,expected', [
    ('football at 6pm on 1st NOV','2026-11-01'),
    ('Book football on 1 November at 6pm','2026-11-01'),
    ('Nov 1st, 2027','2027-11-01'),
    ('on 1st of November 2026','2026-11-01'),
    ('2027-02-28','2027-02-28'),
    ('tomorrow','2026-11-01'),
    ('day after tomorrow','2026-11-02'),
    ('today','2026-10-31'),
    ('play football at 6 pm',None),
    ('on 1 January','2026-01-01'),
    ('today on 31 October','2026-10-31'),
])
def test_explicit_formats(text, expected):
    assert normalize_date(text, NOW) == expected

@pytest.mark.parametrize('text', ['31st November', '2026-02-30', 'today or tomorrow', '1 November or 2 November'])
def test_invalid_or_ambiguous_dates_not_guessed(text):
    with pytest.raises(ValueError): normalize_date(text, NOW)


def test_screenshot_request_with_real_trained_model():
    from app.core.local_nlu import parse_booking
    intent, parsed = parse_booking('football at 6pm on 1st NOV', NOW)
    assert intent == 'book'
    assert parsed.sport == 'football'
    assert parsed.date_iso == '2026-11-01'
    assert parsed.preferred_hour == 18


def test_invalid_date_does_not_fall_back_to_model_guess():
    from unittest.mock import patch, MagicMock
    from app.core.local_nlu import parse_booking
    model = MagicMock()
    model.predict.return_value = {'intent': 'book', 'fields': {'sport':'football','date':'tomorrow','time':'6 pm','players':None}}
    with patch('app.core.local_nlu.predictor', return_value=model):
        _, parsed = parse_booking('Book football on 31 November at 6pm', NOW)
    assert parsed.date_iso is None
