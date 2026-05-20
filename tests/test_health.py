from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "docs" in response.json()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "academic-context-api"


def test_copilot_requires_api_key():
    response = client.post(
        "/copilot/students/upsert",
        json={"copilot_user_id": "test-user"},
    )
    assert response.status_code == 422


def test_copilot_rejects_invalid_api_key():
    response = client.post(
        "/copilot/students/upsert",
        json={"copilot_user_id": "test-user"},
        headers={"x-copilot-api-key": "wrong-key"},
    )
    assert response.status_code == 401
