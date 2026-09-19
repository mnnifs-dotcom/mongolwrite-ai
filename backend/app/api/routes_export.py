"""Export converted text as downloadable Word (.docx)."""

from __future__ import annotations

from io import BytesIO

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/export", tags=["export"])

_MAX_CHARS = 200_000
# Primary OpenType Mongolian fonts; Word picks the first installed face.
_BICHIG_FONTS = ("Mongolian Baiti", "Noto Sans Mongolian", "Menksoft Qagan")
# Traditional Mongolian: top→bottom within a column, columns left→right.
# Matches CSS writing-mode: vertical-lr. Do NOT use tbRl (CJK right→left columns).
_BICHIG_TEXT_DIRECTION = "tbLrV"


class DocxExportRequest(BaseModel):
    text: str = Field(default="", max_length=_MAX_CHARS)
    filename: str = Field(default="mongol-bichig.docx", max_length=120)
    script: str = Field(default="bichig", max_length=20)


def _safe_filename(name: str) -> str:
    cleaned = "".join(ch for ch in name if ch.isalnum() or ch in "._- ").strip() or "mongol-bichig"
    if not cleaned.lower().endswith(".docx"):
        cleaned = f"{cleaned}.docx"
    return cleaned[:120]


def _set_run_font(run, *, fonts: tuple[str, ...], size_pt: float) -> None:
    primary = fonts[0]
    run.font.name = primary
    run.font.size = Pt(size_pt)
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:ascii"), primary)
    r_fonts.set(qn("w:hAnsi"), primary)
    r_fonts.set(qn("w:eastAsia"), primary)
    r_fonts.set(qn("w:cs"), primary)
    # Hint Word/LibreOffice that this run is traditional Mongolian.
    lang = OxmlElement("w:lang")
    lang.set(qn("w:val"), "mn-Mong")
    lang.set(qn("w:eastAsia"), "mn-Mong")
    lang.set(qn("w:bidi"), "mn-Mong")
    r_pr.append(lang)


def _set_section_mongolian_vertical(document: Document) -> None:
    """Top-to-bottom columns progressing left-to-right — Mongolian layout in Word."""
    section = document.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    sect_pr = section._sectPr
    for child in list(sect_pr):
        if child.tag == qn("w:textDirection"):
            sect_pr.remove(child)
    text_direction = OxmlElement("w:textDirection")
    text_direction.set(qn("w:val"), _BICHIG_TEXT_DIRECTION)
    sect_pr.append(text_direction)


def build_bichig_docx(text: str) -> bytes:
    document = Document()
    _set_section_mongolian_vertical(document)
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not any(line.strip() for line in lines):
        lines = [""]
    for line in lines:
        paragraph = document.add_paragraph()
        run = paragraph.add_run(line if line else " ")
        _set_run_font(run, fonts=_BICHIG_FONTS, size_pt=18)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@router.post("/docx")
def export_docx(body: DocxExportRequest) -> Response:
    text = body.text.strip("\ufeff")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Текст хоосон байна")
    if body.script not in {"bichig", "mongol"}:
        raise HTTPException(status_code=400, detail="Зөвхөн монгол бичиг экспортлоно")
    payload = build_bichig_docx(text)
    filename = _safe_filename(body.filename)
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
