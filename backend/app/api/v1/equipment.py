from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.domain.services.equipment_service import EquipmentService

router = APIRouter(prefix="/api/v1/equipment", tags=["equipment"])


class EquipmentItemOut(BaseModel):
    id: str
    name: str
    quantity_available: int


class CheckoutIn(BaseModel):
    booking_id: str
    catalog_id: str
    quantity: int = 1


class CheckoutOut(BaseModel):
    success: bool
    loan_id: str | None = None
    message: str


@router.get("/catalog", response_model=list[EquipmentItemOut])
def get_catalog(sport: str, db: Session = Depends(get_db)):
    service = EquipmentService(db)
    items = service.catalog_for_sport(sport)
    return [EquipmentItemOut(id=i.id, name=i.name, quantity_available=i.quantity_available) for i in items]


@router.post("/checkout", response_model=CheckoutOut)
def checkout(body: CheckoutIn, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    service = EquipmentService(db)
    result = service.checkout(body.booking_id, user_id, body.catalog_id, body.quantity)
    return CheckoutOut(success=result.success, loan_id=result.loan_id, message=result.message)


class ReturnIn(BaseModel):
    condition: str = "ok"  # 'ok' | 'damaged' | 'lost'


class ReturnOut(BaseModel):
    success: bool
    fine_rupees: int


@router.post("/loans/{loan_id}/return", response_model=ReturnOut)
def return_item(loan_id: str, body: ReturnIn, db: Session = Depends(get_db), _: str = Depends(get_current_user_id)):
    service = EquipmentService(db)
    success, fine = service.return_item(loan_id, condition=body.condition)
    if not success:
        raise HTTPException(status_code=404, detail="Loan not found or already returned.")
    return ReturnOut(success=success, fine_rupees=fine)
