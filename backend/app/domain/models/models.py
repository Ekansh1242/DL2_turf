"""
Core SQLAlchemy models for CampusSphere AI, matching RCOEM's real rules.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, ForeignKey, Enum, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class SportType(str, enum.Enum):
    football = "football"
    cricket = "cricket"
    basketball = "basketball"
    badminton = "badminton"
    pickleball = "pickleball"
    table_tennis = "table_tennis"
    lawn_tennis = "lawn_tennis"
    chess = "chess"


ResourceType = SportType


class ResourceStatus(str, enum.Enum):
    active = "active"
    maintenance = "maintenance"
    closed = "closed"


class UserRole(str, enum.Enum):
    student = "student"
    admin = "admin"


class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"
    no_show = "no_show"


class CreatedVia(str, enum.Enum):
    agent = "agent"
    manual = "manual"
    admin_override = "admin_override"


class LoanStatus(str, enum.Enum):
    issued = "issued"
    returned_ok = "returned_ok"
    returned_damaged = "returned_damaged"
    lost = "lost"


STANDARD_FINE_RUPEES = 250


class University(Base):
    __tablename__ = "universities"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    config_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    campuses = relationship("Campus", back_populates="university")


class Campus(Base):
    __tablename__ = "campuses"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    university_id = Column(UUID(as_uuid=False), ForeignKey("universities.id"), nullable=False)
    name = Column(String, nullable=False)
    timezone = Column(String, default="UTC")

    university = relationship("University", back_populates="campuses")


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    campus_id = Column(UUID(as_uuid=False), ForeignKey("campuses.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    roll_no = Column(String, unique=True, nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.student)
    department = Column(String, nullable=True)
    no_show_count = Column(Integer, default=0)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Resource(Base):
    __tablename__ = "resources"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    campus_id = Column(UUID(as_uuid=False), ForeignKey("campuses.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(Enum(SportType), nullable=False)
    capacity = Column(Integer, default=1)
    is_outdoor = Column(Boolean, default=False)
    status = Column(Enum(ResourceStatus), default=ResourceStatus.active)
    config_json = Column(JSON, default=dict)


class EquipmentCatalog(Base):
    __tablename__ = "equipment_catalog"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    sport = Column(Enum(SportType), nullable=False)
    name = Column(String, nullable=False)
    quantity_total = Column(Integer, default=0)
    quantity_available = Column(Integer, default=0)


class EquipmentLoan(Base):
    __tablename__ = "equipment_loans"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    booking_id = Column(UUID(as_uuid=False), ForeignKey("bookings.id"), nullable=False)
    equipment_catalog_id = Column(UUID(as_uuid=False), ForeignKey("equipment_catalog.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    quantity = Column(Integer, default=1)
    status = Column(Enum(LoanStatus), default=LoanStatus.issued)
    fine_rupees = Column(Integer, default=0)
    issued_at = Column(DateTime, default=datetime.utcnow)
    returned_at = Column(DateTime, nullable=True)


class Group(Base):
    __tablename__ = "groups"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    campus_id = Column(UUID(as_uuid=False), ForeignKey("campuses.id"), nullable=False)
    name = Column(String, nullable=False)
    captain_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    resource_id = Column(UUID(as_uuid=False), ForeignKey("resources.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    group_id = Column(UUID(as_uuid=False), ForeignKey("groups.id"), nullable=True)
    # Set when a staff/admin member books on a student's behalf (e.g. the
    # student has no phone/internet access). Null for self-service bookings.
    booked_by_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    checked_in_at = Column(DateTime, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.pending)
    recurrence_rule = Column(String, nullable=True)
    created_via = Column(Enum(CreatedVia), default=CreatedVia.agent)
    created_at = Column(DateTime, default=datetime.utcnow)


class NoShowRecord(Base):
    __tablename__ = "no_show_records"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    booking_id = Column(UUID(as_uuid=False), ForeignKey("bookings.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class WaitlistStatus(str, enum.Enum):
    waiting = "waiting"
    notified = "notified"
    expired = "expired"
    cancelled = "cancelled"


class WaitlistEntry(Base):
    """A student who wants a slot that's currently taken. If the
    original booking is cancelled, the earliest 'waiting' entry for
    that exact resource+time is notified (email) that the slot opened
    up -- first come, first served on the waitlist too."""
    __tablename__ = "waitlist_entries"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    resource_id = Column(UUID(as_uuid=False), ForeignKey("resources.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    slot_start = Column(DateTime, nullable=False)
    slot_end = Column(DateTime, nullable=False)
    status = Column(Enum(WaitlistStatus), default=WaitlistStatus.waiting)
    created_at = Column(DateTime, default=datetime.utcnow)
    notified_at = Column(DateTime, nullable=True)


class ConflictResolution(Base):
    __tablename__ = "conflict_resolutions"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    booking_request_id = Column(String, nullable=False)
    conflicting_booking_id = Column(UUID(as_uuid=False), ForeignKey("bookings.id"), nullable=True)
    resolution_type = Column(String, nullable=False)
    proposed_alternative_id = Column(UUID(as_uuid=False), ForeignKey("bookings.id"), nullable=True)
    reasoning_text = Column(Text, nullable=True)
    resolved_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentTrace(Base):
    __tablename__ = "agent_traces"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    request_id = Column(String, nullable=False, index=True)
    node_name = Column(String, nullable=False)
    graph_state_snapshot = Column(JSON, default=dict)
    tool_calls = Column(JSON, default=list)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class EventOutbox(Base):
    __tablename__ = "event_outbox"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, default=dict)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
