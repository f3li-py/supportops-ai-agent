from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TicketCategory(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    SECURITY = "security"
    FEATURE_REQUEST = "feature_request"
    OTHER = "other"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResolutionType(str, Enum):
    RESOLVED_AUTOMATICALLY = "resolved_automatically"
    ESCALATED_TO_HUMAN = "escalated_to_human"
    NEED_MORE_INFO = "need_more_info"


# --- Request & Response Models ---

class TicketProcessRequest(BaseModel):
    user_id: str = Field(
        ...,
        description="Unique customer user ID, e.g. USR-101",
        json_schema_extra={"example": "USR-101"},
    )
    message: str = Field(
        ...,
        min_length=5,
        description="The customer support message/question",
        json_schema_extra={"example": "Minhas chamadas de API estão falhando com erro 429!"},
    )


class ToolCallLog(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    output: Any


class TriageOutput(BaseModel):
    """Structured output expected from the LLM after reasoning and tool execution."""
    category: TicketCategory = Field(..., description="Classified category of the problem")
    priority: TicketPriority = Field(..., description="Assessed priority/severity level")
    resolution_type: ResolutionType = Field(..., description="Action determination: resolved or escalated")
    summary: str = Field(..., description="Concise 1-2 sentence engineering summary of the case")
    action_taken: str = Field(..., description="What actions/tools were used or recommended")
    customer_reply: str = Field(..., description="Empathetic, clear, and professional response sent directly to the customer")


class TicketProcessResponse(BaseModel):
    ticket_id: str
    user_id: str
    triage: TriageOutput
    tool_calls: List[ToolCallLog]
    execution_time_seconds: float
    created_at: datetime


class UserAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    name: str
    email: str
    plan: str
    status: str
    mfa_enabled: bool
    api_calls_this_month: int
    api_limit: int


class TicketRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: str
    user_id: str
    raw_message: str
    category: str
    priority: str
    status: str
    resolution_summary: str
    customer_reply: str
    created_at: datetime
