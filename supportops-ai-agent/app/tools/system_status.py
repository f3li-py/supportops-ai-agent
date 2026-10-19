from datetime import datetime, timezone
from typing import Any, Dict


# Simulação de monitor de status dos serviços da plataforma
SYSTEM_SERVICES = {
    "api_gateway": {"status": "operational", "latency_ms": 28},
    "authentication_service": {"status": "operational", "latency_ms": 45},
    "billing_webhooks": {
        "status": "operational",
        "latency_ms": 110,
        "recent_incident": "Manutenção programada concluída há 2 horas.",
    },
    "core_database": {"status": "operational", "latency_ms": 12},
    "cache_redis": {"status": "operational", "latency_ms": 3},
}


def check_system_health() -> Dict[str, Any]:
    """Verifica a integridade e disponibilidade atual dos microsserviços da plataforma.

    Returns:
        Relatório de integridade com status de cada serviço (operational, degraded, outage) e latência.
    """
    all_operational = all(svc["status"] == "operational" for svc in SYSTEM_SERVICES.values())

    return {
        "overall_status": "healthy" if all_operational else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": SYSTEM_SERVICES,
        "active_outages": [name for name, s in SYSTEM_SERVICES.items() if s["status"] != "operational"],
    }
