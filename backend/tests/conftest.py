import os
from unittest.mock import MagicMock
import pytest

# Tests use a dedicated key and NEVER send real email, even with a local .env.
os.environ['JWT_SECRET'] = 'test-only-key-not-for-deployment-' + 'x' * 32

@pytest.fixture(autouse=True)
def isolated_test_configuration(monkeypatch):
    from app.services import email_service
    monkeypatch.setenv('BOOKING_NLU_BACKEND', 'llm')
    monkeypatch.setattr(email_service.smtplib, 'SMTP', MagicMock())
