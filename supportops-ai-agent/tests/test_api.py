import pytest
from fastapi.testclient import TestClient
from app.database import init_db
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "gemini_model" in data


def test_list_users_endpoint():
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 3
    user_ids = [u["user_id"] for u in users]
    assert "USR-101" in user_ids


def test_system_status_endpoint():
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "healthy"


def test_process_ticket_end_to_end():
    payload = {
        "user_id": "USR-103",
        "message": "Minhas chamadas de API falham com erro 429 Too Many Requests.",
    }
    response = client.post("/api/v1/tickets/process", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["ticket_id"].startswith("TCK-")
    assert data["user_id"] == "USR-103"
    assert "triage" in data
    assert "tool_calls" in data
    assert len(data["tool_calls"]) > 0


def test_list_tickets_endpoint_after_process():
    # Process a ticket first
    payload = {
        "user_id": "USR-102",
        "message": "Problemas de pagamento da minha assinatura mensal.",
    }
    client.post("/api/v1/tickets/process", json=payload)

    # Now verify it appears in the tickets list
    response = client.get("/api/v1/tickets")
    assert response.status_code == 200
    tickets = response.json()
    assert len(tickets) > 0
    assert any(t["user_id"] == "USR-102" for t in tickets)
