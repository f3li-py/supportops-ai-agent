import pytest
from pydantic import ValidationError
from app.schemas import (
    ResolutionType,
    TicketCategory,
    TicketPriority,
    TicketProcessRequest,
    TriageOutput,
)


def test_valid_ticket_process_request():
    req = TicketProcessRequest(
        user_id="USR-101",
        message="Mensagem válida com mais de 5 caracteres.",
    )
    assert req.user_id == "USR-101"


def test_short_message_validation_error():
    with pytest.raises(ValidationError):
        TicketProcessRequest(
            user_id="USR-101",
            message="Oi",  # Less than 5 characters min_length
        )


def test_valid_triage_output_schema():
    triage = TriageOutput(
        category=TicketCategory.TECHNICAL,
        priority=TicketPriority.CRITICAL,
        resolution_type=ResolutionType.ESCALATED_TO_HUMAN,
        summary="Problema de conectividade no gateway de pagamentos.",
        action_taken="Escalado para a equipe de engenharia.",
        customer_reply="Estamos cuidando do seu caso.",
    )
    assert triage.category == TicketCategory.TECHNICAL
    assert triage.priority == TicketPriority.CRITICAL
