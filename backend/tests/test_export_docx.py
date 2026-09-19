from __future__ import annotations

import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient

from app.main import app

W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def _sect_text_direction(docx_bytes: bytes) -> str | None:
    with zipfile.ZipFile(BytesIO(docx_bytes)) as archive:
        xml = archive.read("word/document.xml")
    root = ET.fromstring(xml)
    node = root.find(".//w:sectPr/w:textDirection", W_NS)
    if node is None:
        return None
    return node.get(f"{{{W_NS['w']}}}val")


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
    # Mongolian vertical: top→bottom, columns left→right (not CJK tbRl).
    assert _sect_text_direction(response.content) == "tbLrV"


def test_export_docx_rejects_empty() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/export/docx", json={"text": "   ", "script": "bichig"})
    assert response.status_code == 400
