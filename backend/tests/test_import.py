from io import BytesIO

from app.main import app
from docx import Document
from fastapi.testclient import TestClient

client = TestClient(app)


def test_import_txt() -> None:
    response = client.post(
        "/api/v1/import/file",
        files={"file": ("alban.txt", "Хүлээн авч танилцана уу.".encode(), "text/plain")},
    )
    assert response.status_code == 200
    assert "танилцана" in response.json()["text"]


def test_import_docx() -> None:
    document = Document()
    document.add_paragraph("Хүлээн авч танилцана уу.")
    buffer = BytesIO()
    document.save(buffer)
    response = client.post(
        "/api/v1/import/file",
        files={
            "file": (
                "alban.docx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 200
    assert "танилцана" in response.json()["text"]


def test_import_rejects_other_types() -> None:
    response = client.post(
        "/api/v1/import/file",
        files={"file": ("photo.png", b"not-a-doc", "image/png")},
    )
    assert response.status_code == 400
