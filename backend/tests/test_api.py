from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_check_endpoint_detects_repeat() -> None:
    response = client.post(
        "/api/v1/check/deterministic",
        json={"text": "Хүсэлт хүсэлт ирүүлсэн."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["word_count"] == 3
    rules = {item["rule_id"] for item in body["corrections"]}
    assert "repeated_word" in rules


def test_ai_without_key_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes_check.ai_enabled", lambda: False)
    monkeypatch.setattr("app.api.routes_ai.ai_enabled", lambda: False)
    response = client.post("/api/v1/check/ai", json={"text": "тест"})
    assert response.status_code == 503
    assert client.get("/api/v1/settings").json()["ai_enabled"] is False
