from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.sports import router as sports_router
from app.api.v1.slots import router as slots_router
from app.api.v1.bookings import router as bookings_router
from app.api.v1.equipment import router as equipment_router
from app.api.v1.ai_booking import router as ai_booking_router
from app.api.v1.admin import router as admin_router
from app.api.v1.admin_agent import router as admin_agent_router
from app.db.session import engine
from app.domain.models.models import Base

from app.api.v1.model_evaluation import router as evaluation_router

app = FastAPI(title="CampusSphere AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[v.strip() for v in __import__("os").environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if v.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(evaluation_router)
app.include_router(auth_router)
app.include_router(sports_router)
app.include_router(slots_router)
app.include_router(bookings_router)
app.include_router(equipment_router)
app.include_router(ai_booking_router)
app.include_router(admin_router)
app.include_router(admin_agent_router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}
