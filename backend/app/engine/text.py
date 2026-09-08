from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

CYRILLIC_MN = (
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    "ӨҮөү"
)


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int


_WORD_RE = re.compile(
    r"[A-Za-zÀ-ÿА-Яа-яЁёӨөҮү]+(?:['’-][A-Za-zА-Яа-яЁёӨөҮү]+)*",
)


def to_nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def is_cyrillic_letter(ch: str) -> bool:
    return ch in CYRILLIC_MN or "CYRILLIC" in unicodedata.name(ch, "")


def tokenize(text: str) -> list[Token]:
    return [Token(m.group(0), m.start(), m.end()) for m in _WORD_RE.finditer(text)]
