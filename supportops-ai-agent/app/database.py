import json
from datetime import datetime, timezone
from typing import Generator
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserAccount(Base):
    """Database model for customer accounts."""
    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(120), nullable=False)
    plan = Column(String(30), nullable=False, default="Free")  # Free, Pro, Enterprise
    status = Column(String(30), nullable=False, default="active")  # active, past_due, suspended
    mfa_enabled = Column(Boolean, default=False)
    api_calls_this_month = Column(Integer, default=0)
    api_limit = Column(Integer, default=1000)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Ticket(Base):
    """Database model for customer support tickets and agent triage records."""
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(String(50), nullable=False)
    raw_message = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    priority = Column(String(30), nullable=False)
    status = Column(String(50), nullable=False)  # resolved_by_ai, escalated, pending_user
    resolution_summary = Column(Text, nullable=False)
    customer_reply = Column(Text, nullable=False)
    tools_called = Column(Text, default="[]")  # JSON string with list of tool invocations
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining a database session in FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables and seed initial demo accounts if not present."""
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing_users = db.query(UserAccount).count()
        if existing_users == 0:
            seed_users = [
                UserAccount(
                    user_id="USR-101",
                    name="Carlos Silva",
                    email="carlos@techcorp.com",
                    plan="Enterprise",
                    status="active",
                    mfa_enabled=True,
                    api_calls_this_month=48200,
                    api_limit=500000,
                ),
                UserAccount(
                    user_id="USR-102",
                    name="Mariana Souza",
                    email="mariana@startup.io",
                    plan="Pro",
                    status="past_due",
                    mfa_enabled=False,
                    api_calls_this_month=49500,
                    api_limit=50000,
                ),
                UserAccount(
                    user_id="USR-103",
                    name="Lucas Ferreira",
                    email="lucas@devmail.com",
                    plan="Free",
                    status="active",
                    mfa_enabled=False,
                    api_calls_this_month=980,
                    api_limit=1000,
                ),
            ]
            db.add_all(seed_users)
            db.commit()
