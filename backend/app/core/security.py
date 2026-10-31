import os
import jwt
from fastapi import Header, HTTPException

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
ALLOWED_EMAIL_DOMAIN = "rknec.edu"


def is_allowed_college_email(email: str) -> bool:
    return email.lower().strip().endswith(f"@{ALLOWED_EMAIL_DOMAIN}")


def get_current_user_id(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["sub"]


def get_current_admin_id(authorization: str = Header(...)) -> str:
    """Same as get_current_user_id but rejects non-admin tokens. Staff
    (teachers running the sports desk) log in with the same student
    login flow -- they're just users whose role is 'admin'."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return payload["sub"]


def create_access_token(user_id: str, role: str = "student") -> str:
    return jwt.encode({"sub": user_id, "role": role}, JWT_SECRET, algorithm="HS256")
