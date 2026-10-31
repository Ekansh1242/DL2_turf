"""Email ownership verification with expiring single-use OTPs and DB-backed limits."""
from datetime import datetime, timedelta
import hashlib
import hmac
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.models.models import Base, Campus, User, UserRole
from app.core.security import JWT_SECRET, admin_emails, create_access_token, is_allowed_college_email
from app.services.email_service import send_plain_email, is_email_configured

router = APIRouter(prefix='/api/v1/auth', tags=['auth'])

class LoginChallenge(Base):
    __tablename__ = 'login_challenges'
    email = Column(String, primary_key=True)
    digest = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    sent_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, nullable=False, default=0)

class LoginThrottle(Base):
    __tablename__ = 'login_throttles'
    key = Column(String, primary_key=True)
    started_at = Column(DateTime, nullable=False)
    count = Column(Integer, nullable=False, default=0)

class RequestOTP(BaseModel):
    email: EmailStr

class VerifyOTP(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r'^\d{6}$')
    name: str = Field(min_length=1, max_length=100)
    roll_no: str | None = Field(default=None, max_length=80)
    department: str | None = Field(default=None, max_length=100)

    @field_validator('name')
    @classmethod
    def meaningful_name(cls, value):
        if not value.strip():
            raise ValueError('Enter your name.')
        return value.strip()

class LoginOut(BaseModel):
    access_token: str
    role: str
    user_id: str


def digest(email, code):
    return hmac.new(JWT_SECRET.encode(), f'{email}:{code}'.encode(), hashlib.sha256).hexdigest()


def throttle(db, key, limit, now):
    row = db.query(LoginThrottle).filter_by(key=key).with_for_update().first()
    if row is None:
        row = LoginThrottle(key=key, started_at=now, count=0)
        db.add(row)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(429, 'Please retry shortly.')
    if now - row.started_at >= timedelta(hours=1):
        row.started_at, row.count = now, 0
    if row.count >= limit:
        db.commit()
        raise HTTPException(429, 'Too many attempts. Try again in an hour.')
    row.count += 1


@router.post('/request-otp')
def request_otp(body: RequestOTP, request: Request, db: Session = Depends(get_db)):
    email = str(body.email).strip().lower()
    if not is_allowed_college_email(email):
        raise HTTPException(403, 'Use an allowed college email or a configured admin email.')
    if not is_email_configured():
        raise HTTPException(503, 'Email login is not configured. Contact the administrator.')
    now = datetime.utcnow()
    # Do not trust client-supplied X-Forwarded-For. Configure proxy trust at deployment.
    host = request.client.host if request.client else 'unknown'
    ip_key = digest('request-ip', host)
    throttle(db, ip_key, 20, now)
    row = db.query(LoginChallenge).filter_by(email=email).with_for_update().first()
    if row and (now - row.sent_at).total_seconds() < 60:
        db.commit()
        raise HTTPException(429, 'Wait 60 seconds before requesting another code.')
    throttle(db, digest('request-email', email), 10, now)
    code = f'{secrets.randbelow(1000000):06}'
    if row is None:
        row = LoginChallenge(email=email)
        db.add(row)
    row.digest, row.sent_at, row.expires_at, row.attempts = digest(email, code), now, now+timedelta(minutes=5), 0
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(429, 'Please retry shortly.')
    if not send_plain_email(email, 'Your CampusSphere sign-in code', f'Your sign-in code is {code}.\nIt expires in 5 minutes and can be used once.\nIf you did not request it, ignore this message.'):
        raise HTTPException(503, 'Could not send the sign-in email. Please try again after 60 seconds.')
    return {'message':'Check your inbox for a six-digit code.', 'expires_in':300, 'resend_after':60}


@router.post('/verify-otp', response_model=LoginOut)
def verify_otp(body: VerifyOTP, request: Request, db: Session = Depends(get_db)):
    email = str(body.email).strip().lower()
    if not is_allowed_college_email(email):
        raise HTTPException(403, 'Email is not allowed.')
    now = datetime.utcnow()
    host = request.client.host if request.client else 'unknown'
    throttle(db, digest('verify-ip', host), 60, now)
    row = db.query(LoginChallenge).filter_by(email=email).with_for_update().first()
    if row is None or row.expires_at <= now or row.attempts >= 5:
        db.commit()
        raise HTTPException(400, 'Code is invalid or expired. Request a new code.')
    row.attempts += 1
    if not hmac.compare_digest(row.digest, digest(email, body.code)):
        db.commit()
        raise HTTPException(400, 'Code is invalid or expired.')
    user = db.query(User).filter_by(email=email).first()
    if user and user.is_blocked:
        db.delete(row)
        db.commit()
        raise HTTPException(403, 'Account is blocked. Contact the sports desk.')
    if user is None:
        campus = db.query(Campus).first()
        if campus is None:
            db.rollback()
            raise HTTPException(503, 'Campus has not been configured.')
        user = User(campus_id=campus.id, email=email, name=body.name.strip(), roll_no=body.roll_no or None, department=body.department or None, role=UserRole.student)
        db.add(user)
    if email in admin_emails():
        user.role = UserRole.admin
    db.delete(row)  # consumed in the same transaction as account creation
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Account details conflict with an existing account. Contact the administrator.')
    return LoginOut(access_token=create_access_token(user.id, user.role.value), role=user.role.value, user_id=user.id)
