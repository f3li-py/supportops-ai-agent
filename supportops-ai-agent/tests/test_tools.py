import pytest
from app.database import init_db
from app.tools.escalation import escalate_to_human_tier
from app.tools.knowledge_base import search_knowledge_base
from app.tools.system_status import check_system_health
from app.tools.user_service import get_user_account_info


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure database tables and seeds are initialized before running tests."""
    init_db()


def test_search_knowledge_base_finds_rate_limit():
    results = search_knowledge_base("Estou recebendo erro 429 de rate limit")
    assert len(results) > 0
    top_article = results[0]
    assert "429" in top_article["title"] or "Taxa" in top_article["title"]


def test_search_knowledge_base_finds_billing():
    results = search_knowledge_base("problemas com pagamento e fatura atrasada")
    assert len(results) > 0
    titles = [a["title"] for a in results]
    assert any("Faturas" in t or "Pagamento" in t for t in titles)


def test_get_user_account_info_existing_user():
    user = get_user_account_info("USR-101")
    assert user["found"] is True
    assert user["name"] == "Carlos Silva"
    assert user["plan"] == "Enterprise"
    assert user["status"] == "active"


def test_get_user_account_info_non_existing_user():
    user = get_user_account_info("USR-999")
    assert user["found"] is False


def test_check_system_health():
    health = check_system_health()
    assert "overall_status" in health
    assert "services" in health
    assert "api_gateway" in health["services"]


def test_escalate_to_human_tier():
    res = escalate_to_human_tier(
        ticket_id="TCK-TEST",
        department="engineering",
        urgency="critical",
        reason="Teste de escalonamento",
    )
    assert res["success"] is True
    assert res["escalation_protocol"].startswith("ESC-")
    assert "15 minutos" in res["sla_target"]
