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


def test_admin_lists_feedback(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.feedback.persist_dir", lambda: tmp_path)
    monkeypatch.setattr("app.core.config.settings.admin_username", "admin")
    monkeypatch.setattr("app.core.config.settings.admin_password", "test-pass")
    monkeypatch.setattr("app.core.config.settings.secret_key", "test-secret")
    monkeypatch.setattr("app.core.config.settings.app_env", "development")
    client = TestClient(app)
    assert (
        client.post(
            "/api/v1/feedback",
            json={
                "category": "bichig",
                "message": "хэлтэс үгийг буруу хөрвүүлсэн",
                "word": "хэлтэс",
            },
        ).status_code
        == 200
    )
    bare = client.get("/api/v1/admin/feedback")
    assert bare.status_code == 401
    assert (
        client.post(
            "/api/v1/admin/login",
            json={"username": "admin", "password": "test-pass"},
        ).status_code
        == 200
    )
    listed = client.get("/api/v1/admin/feedback")
    assert listed.status_code == 200
    body = listed.json()
    assert body["count"] >= 1
    assert body["items"][0]["word"] == "хэлтэс"
    assert body["items"][0]["category"] == "bichig"
    assert "хэлтэс" in body["items"][0]["message"]
