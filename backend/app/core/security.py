"""Signed, expiring sessions. No default signing key or unverified login."""
import os
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.models.models import User, UserRole

JWT_SECRET = os.environ.get('JWT_SECRET', '')
if len(JWT_SECRET) < 32 or JWT_SECRET == 'dev-secret-change-me':
    raise RuntimeError('Set JWT_SECRET to a random secret of at least 32 characters in .env.')


def admin_emails():
    return {v.strip().lower() for v in os.environ.get('ADMIN_EMAILS', '').split(',') if v.strip()}


def is_allowed_college_email(email):
    domains = {v.strip().lower() for v in os.environ.get('ALLOWED_EMAIL_DOMAINS', 'rknec.edu').split(',') if v.strip()}
    normalized = email.strip().lower()
    return normalized in admin_emails() or normalized.rsplit('@', 1)[-1] in domains


def create_access_token(user_id, role='student'):
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub':user_id, 'role':role, 'iat':now, 'exp':now+timedelta(hours=1), 'jti':secrets.token_hex(16)}, JWT_SECRET, algorithm='HS256')


def get_current_user_id(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Missing bearer token')
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=['HS256'], options={'require':['sub','exp','iat','jti']})
        user = db.get(User, payload['sub'])
        if user is None or user.is_blocked:
            raise HTTPException(401, 'Account is unavailable.')
        return user.id
    except jwt.InvalidTokenError:
        raise HTTPException(401, 'Session expired or invalid. Sign in again.')


def get_current_admin_id(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user.role != UserRole.admin:
        raise HTTPException(403, 'Admin access required.')
    return user_id
