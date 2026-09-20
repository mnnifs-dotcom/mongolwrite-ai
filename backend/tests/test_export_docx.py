from __future__ import annotations

import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient

from app.api.routes_export import _obfuscate_font, build_bichig_docx
from app.main import app

W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
R_NS = {"r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


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
        json={
            "text": "ᠮᠣᠩᠭᠣᠯ\nᠶᠡᠷᠦᠩᢈᠡᠶᠢᠯᠡᢉᠴᠢ",
            "filename": "test-bichig.docx",
            "script": "bichig",
        },
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

    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        assert "word/fonts/font1.odttf" in names
        assert "word/_rels/fontTable.xml.rels" in names
        font_table = archive.read("word/fontTable.xml").decode("utf-8")
        assert "MongolianScript" in font_table
        assert "embedRegular" in font_table
        settings = archive.read("word/settings.xml").decode("utf-8")
        assert "embedTrueTypeFonts" in settings
        document = archive.read("word/document.xml").decode("utf-8")
        assert "MongolianScript" in document
        assert "ᢈ" in document  # Ali Gali preserved for Bolorsoft faces
        # Embedded face is larger than a bare docx shell.
        assert len(archive.read("word/fonts/font1.odttf")) > 100_000


def test_export_docx_rejects_empty() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/export/docx", json={"text": "   ", "script": "bichig"})
    assert response.status_code == 400


def test_obfuscate_font_roundtrip() -> None:
    payload = b"\x00" * 40 + b"rest-of-font"
    key = "{302EE813-EB4A-4642-A93A-89EF99B2457E}"
    once = _obfuscate_font(payload, key)
    twice = _obfuscate_font(once, key)
    assert once != payload
    assert twice == payload


def test_build_bichig_docx_embeds_mongolian_script() -> None:
    data = build_bichig_docx("ᠮᠣᠩᠭᠣᠯ ᢈᠦᠴᠦᠨ")
    with zipfile.ZipFile(BytesIO(data)) as archive:
        assert "word/fonts/font1.odttf" in archive.namelist()
        rels = archive.read("word/_rels/fontTable.xml.rels").decode("utf-8")
        assert "fonts/font1.odttf" in rels
        document = archive.read("word/document.xml").decode("utf-8")
        assert 'w:ascii="MongolianScript"' in document
