from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domain.models.models import Resource, SportType

router = APIRouter(prefix="/api/v1/sports", tags=["sports"])


class SportOut(BaseModel):
    sport: str
    resource_id: str
    resource_name: str


@router.get("", response_model=list[SportOut])
def list_sports(db: Session = Depends(get_db)):
    resources = db.query(Resource).filter(Resource.type.in_(list(SportType))).all()
    return [SportOut(sport=r.type.value, resource_id=r.id, resource_name=r.name) for r in resources]
