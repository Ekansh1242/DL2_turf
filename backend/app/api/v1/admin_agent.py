from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.analytics_agent import run_analytics_agent
from app.core.security import get_current_admin_id
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin/analytics", tags=["admin-agent"])


class AskIn(BaseModel):
    question: str


@router.post("/ask")
async def ask(body: AskIn, db: Session = Depends(get_db), _: str = Depends(get_current_admin_id)):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Ask a question about bookings.")
    try:
        return await run_analytics_agent(body.question.strip(), db)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        logger.exception("Analytics agent failed")
        raise HTTPException(status_code=502, detail="The analytics assistant had a problem. Please try again.")
