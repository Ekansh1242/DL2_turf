from __future__ import annotations

import logging
import os
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
        if os.environ.get('ANALYTICS_BACKEND', 'local') == 'local':
            from app.agents.local_analytics import run_local_analytics
            return run_local_analytics(body.question.strip(), db)
        return await run_analytics_agent(body.question.strip(), db)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        logger.exception("Analytics agent failed")
        raise HTTPException(status_code=502, detail="The analytics assistant had a problem. Please try again.")
