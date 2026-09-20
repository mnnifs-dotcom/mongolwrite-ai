from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_feedback_requires_message(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.feedback.persist_dir", lambda: tmp_path)
    client = TestClient(app)
    short = client.post(
        "/api/v1/feedback",
        json={"category": "spelling", "message": "богино", "word": "тест"},
    )
    assert short.status_code == 422


def test_feedback_stores_report(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.feedback.persist_dir", lambda: tmp_path)
    client = TestClient(app)
    response = client.post(
        "/api/v1/feedback",
        json={
            "category": "spelling",
            "message": "Энэ үгийг буруу тэмдэглэсэн байна",
            "word": "төгөлдөр",
            "email": "user@example.com",
            "page": "/aldaa-medegdeh",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["id"]

    saved = (tmp_path / "feedback.json").read_text(encoding="utf-8")
    assert "төгөлдөр" in saved
    assert "user@example.com" in saved
