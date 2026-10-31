from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.models.models import EquipmentCatalog, EquipmentLoan, LoanStatus, STANDARD_FINE_RUPEES


@dataclass
class CheckoutResult:
    success: bool
    loan_id: str | None = None
    message: str = ""


class EquipmentService:
    def __init__(self, db: Session):
        self.db = db

    def catalog_for_sport(self, sport: str) -> list[EquipmentCatalog]:
        stmt = select(EquipmentCatalog).where(EquipmentCatalog.sport == sport)
        return list(self.db.execute(stmt).scalars().all())

    def checkout(self, booking_id: str, user_id: str, catalog_id: str, quantity: int = 1) -> CheckoutResult:
        item = self.db.get(EquipmentCatalog, catalog_id)
        if item is None:
            return CheckoutResult(success=False, message="Equipment item not found.")
        if item.quantity_available < quantity:
            return CheckoutResult(success=False, message=f"Only {item.quantity_available} '{item.name}' available.")
        item.quantity_available -= quantity
        loan = EquipmentLoan(booking_id=booking_id, equipment_catalog_id=catalog_id, user_id=user_id,
                              quantity=quantity, status=LoanStatus.issued)
        self.db.add(loan)
        self.db.commit()
        self.db.refresh(loan)
        return CheckoutResult(success=True, loan_id=loan.id, message="Equipment issued.")

    def return_item(self, loan_id: str, condition: str = "ok"):
        loan = self.db.get(EquipmentLoan, loan_id)
        if loan is None or loan.status != LoanStatus.issued:
            return False, 0
        catalog_item = self.db.get(EquipmentCatalog, loan.equipment_catalog_id)
        fine = 0
        if condition == "ok":
            loan.status = LoanStatus.returned_ok
            catalog_item.quantity_available += loan.quantity
        elif condition == "damaged":
            loan.status = LoanStatus.returned_damaged
            fine = STANDARD_FINE_RUPEES
        elif condition == "lost":
            loan.status = LoanStatus.lost
            fine = STANDARD_FINE_RUPEES
        loan.fine_rupees = fine
        loan.returned_at = datetime.utcnow()
        self.db.commit()
        return True, fine
