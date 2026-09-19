from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_export_bichig_docx() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/export/docx",
        json={"text": "ᠮᠣᠩᠭᠣᠯ\nᠪᠢᠴᠢᠭ", "filename": "test-bichig.docx", "script": "bichig"},
    )
    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "attachment" in response.headers.get("content-disposition", "")
    assert response.content[:2] == b"PK"  # zip/docx
    assert len(response.content) > 1000


def test_export_docx_rejects_empty() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/export/docx", json={"text": "   ", "script": "bichig"})
    assert response.status_code == 400
