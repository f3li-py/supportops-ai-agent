import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.agent.engine import SupportAgentEngine
from app.config import get_settings
from app.database import Ticket, UserAccount, get_db, init_db
from app.schemas import (
    TicketProcessRequest,
    TicketProcessResponse,
    TicketRecordResponse,
    UserAccountResponse,
)
from app.tools.system_status import check_system_health

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event to initialize database on startup."""
    init_db()
    yield


app = FastAPI(
    title="SupportOps AI Agent",
    description="Autonomous Ticket Triage & Technical Support Engine powered by Google Gemini",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local development and demos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files for the Web UI
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Shared Agent Engine instance
agent_engine = SupportAgentEngine()


@app.get("/", include_in_schema=False)
async def serve_home():
    """Serves the interactive frontend dashboard."""
    return FileResponse("app/static/index.html")


@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "gemini_model": settings.gemini_model,
        "api_key_configured": bool(settings.gemini_api_key),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/system/status", tags=["Monitoring"])
async def system_status():
    """Retrieve platform microservices health status."""
    return check_system_health()


@app.get("/api/v1/users", response_model=List[UserAccountResponse], tags=["Accounts"])
async def list_users(db: Session = Depends(get_db)):
    """List sample demo customer accounts from the database."""
    return db.query(UserAccount).all()


@app.get("/api/v1/tickets", response_model=List[TicketRecordResponse], tags=["Tickets"])
async def list_tickets(limit: int = 20, db: Session = Depends(get_db)):
    """List recent support tickets and their triage history."""
    tickets = db.query(Ticket).order_by(Ticket.id.desc()).limit(limit).all()
    return tickets


@app.post(
    "/api/v1/tickets/process",
    response_model=TicketProcessResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Tickets"],
)
async def process_ticket(
    payload: TicketProcessRequest,
    db: Session = Depends(get_db),
):
    """Processes an incoming customer support ticket through the autonomous Gemini agent."""
    ticket_id = f"TCK-{uuid.uuid4().hex[:6].upper()}"

    triage, tool_logs, execution_time = agent_engine.process_ticket(
        ticket_id=ticket_id,
        user_id=payload.user_id,
        message=payload.message,
    )

    # Persist ticket record into SQLite
    ticket_record = Ticket(
        ticket_id=ticket_id,
        user_id=payload.user_id,
        raw_message=payload.message,
        category=triage.category.value,
        priority=triage.priority.value,
        status=triage.resolution_type.value,
        resolution_summary=triage.summary,
        customer_reply=triage.customer_reply,
        tools_called=json.dumps([t.model_dump() for t in tool_logs]),
    )
    db.add(ticket_record)
    db.commit()
    db.refresh(ticket_record)

    return TicketProcessResponse(
        ticket_id=ticket_id,
        user_id=payload.user_id,
        triage=triage,
        tool_calls=tool_logs,
        execution_time_seconds=execution_time,
        created_at=ticket_record.created_at,
    )
