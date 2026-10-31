from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.security import is_allowed_college_email, create_access_token
from app.db.session import get_db
from app.domain.models.models import User, UserRole, Campus

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: EmailStr
    name: str
    roll_no: str | None = None
    department: str | None = None


class LoginOut(BaseModel):
    access_token: str
    role: str
    user_id: str


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    if not is_allowed_college_email(body.email):
        raise HTTPException(status_code=403, detail="Access is restricted to RCOEM (@rknec.edu) email addresses.")
    user = db.query(User).filter(User.email == body.email).first()
    if user is None:
        campus = db.query(Campus).first()
        if campus is None:
            raise HTTPException(status_code=500, detail="No campus configured yet.")
        user = User(
            campus_id=campus.id, name=body.name, email=body.email,
            roll_no=body.roll_no, department=body.department, role=UserRole.student,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Your account is temporarily blocked due to repeated no-shows.")
    token = create_access_token(user.id, role=user.role.value)
    return LoginOut(access_token=token, role=user.role.value, user_id=user.id)
