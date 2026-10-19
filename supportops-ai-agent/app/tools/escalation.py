import uuid
from datetime import datetime, timezone
from typing import Any, Dict


def escalate_to_human_tier(
    ticket_id: str,
    department: str,
    urgency: str,
    reason: str,
) -> Dict[str, Any]:
    """Escala o chamado para uma equipe humana especializada quando a IA não pode resolver ou quando o caso é crítico.

    Args:
        ticket_id: Identificador do ticket que está sendo atendido.
        department: Departamento de destino ('engineering', 'billing', 'security', 'customer_success').
        urgency: Nível de urgência ('low', 'medium', 'high', 'critical').
        reason: Motivo técnico ou de negócio pelo qual a intervenção humana é mandatória.

    Returns:
        Confirmação de escalonamento contendo protocolo de plantão, SLA estimado e equipe notificada.
    """
    sla_map = {
        "critical": "15 minutos (Plantão P1)",
        "high": "2 horas",
        "medium": "8 horas úteis",
        "low": "24 horas úteis",
    }

    routing_id = f"ESC-{uuid.uuid4().hex[:6].upper()}"
    sla_target = sla_map.get(urgency.lower(), "8 horas úteis")

    return {
        "success": True,
        "escalation_protocol": routing_id,
        "ticket_id": ticket_id,
        "assigned_department": department,
        "urgency": urgency,
        "sla_target": sla_target,
        "reason": reason,
        "notified_at": datetime.now(timezone.utc).isoformat(),
        "status": "queued_for_human_agent",
    }
