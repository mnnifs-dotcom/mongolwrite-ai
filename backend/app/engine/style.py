from __future__ import annotations

import uuid

from app.engine.models import Category, Correction, Severity, Source
from app.engine.text import Token


def _aad(spoken: str, official: str) -> tuple[str, str]:
    return official, f"Албан найруулгад «{spoken}»-ыг «{official}» гэж бичдэг."


OFFICIAL_REPLACEMENTS: dict[str, tuple[str, str]] = {
    "танилцаад": (
        "танилцан",
        "Албан бичигт -аад хэлбэрийн оронд -н хэлбэрийг илүүд үздэг.",
    ),
    "аваад": _aad("аваад", "авч"),
    "хийгээд": _aad("хийгээд", "хийж"),
    "үзээд": _aad("үзээд", "үзэж"),
    "уншаад": _aad("уншаад", "уншиж"),
    "шалгаад": _aad("шалгаад", "шалгаж"),
    "хэлээд": _aad("хэлээд", "хэлж"),
    "бичээд": _aad("бичээд", "бичиж"),
    "яриад": _aad("яриад", "ярьж"),
    "гаргаад": _aad("гаргаад", "гаргаж"),
    "оруулаад": _aad("оруулаад", "оруулж"),
    "шийдээд": _aad("шийдээд", "шийдэж"),
    "тооцоод": _aad("тооцоод", "тооцож"),
    "илгээгээд": _aad("илгээгээд", "илгээж"),
    "хүлээлгээд": _aad("хүлээлгээд", "хүлээлгэж"),
}

_CLAUSE_END_PARTICLES = frozenset({"уу", "үү", "юу", "бэ", "вэ"})
_FILLER_PREV = frozenset(
    {"байна", "болно", "байх", "гэсэн", "ирсэн", "ирүүлсэн", "авсан", "хийсэн"}
)

# Official phrasing only. Spoken/redundant → school-standard written form.
_PHRASES: tuple[tuple[tuple[str, ...], str, str, str, Category], ...] = (
    (
        ("тийм", "болохоор"),
        "иймд",
        "Албан найруулгад «тийм болохоор»-ыг «иймд» гэж товчилдог.",
        "spoken_tiim_bolohor",
        Category.STYLE,
    ),
    (
        ("ийм", "болохоор"),
        "иймд",
        "Албан найруулгад «ийм болохоор»-ыг «иймд» гэж товчилдог.",
        "spoken_im_bolohor",
        Category.STYLE,
    ),
    (
        ("яагаад", "гэвэл"),
        "учир нь",
        "Албан өгүүлбэрт «яагаад гэвэл»-ийн оронд «учир нь» гэж бичнэ.",
        "official_uchir_ni",
        Category.STYLE,
    ),
    (
        ("гэх", "зэргээр"),
        "гэх мэт",
        "Жишээлэхэд «гэх зэргээр» биш «гэх мэт» гэж бичнэ.",
        "official_geh_met",
        Category.STYLE,
    ),
    (
        ("гэж", "бодож"),
        "гэж үзэж",
        "Албан бичигт «бодох» биш «үзэх» гэж бичнэ.",
        "official_uzeh",
        Category.STYLE,
    ),
    (
        ("хийх", "хэрэгтэй"),
        "хийх шаардлагатай",
        "Үүрэг, шаардлагыг «хэрэгтэй» биш «шаардлагатай» гэж бичнэ.",
        "official_shaardlagatai",
        Category.STYLE,
    ),
    (
        ("байх", "хэрэгтэй"),
        "байх шаардлагатай",
        "Үүрэг, шаардлагыг «хэрэгтэй» биш «шаардлагатай» гэж бичнэ.",
        "official_shaardlagatai",
        Category.STYLE,
    ),
    (
        ("болгох", "хэрэгтэй"),
        "болгох шаардлагатай",
        "Үүрэг, шаардлагыг «хэрэгтэй» биш «шаардлагатай» гэж бичнэ.",
        "official_shaardlagatai",
        Category.STYLE,
    ),
    (
        ("авах", "хэрэгтэй"),
        "авах шаардлагатай",
        "Үүрэг, шаардлагыг «хэрэгтэй» биш «шаардлагатай» гэж бичнэ.",
        "official_shaardlagatai",
        Category.STYLE,
    ),
    (
        ("дахин", "шинээр"),
        "дахин",
        "«Дахин» болон «шинээр» ижил утгатай тул нэгийг нь үлдээв.",
        "redundant_again",
        Category.REDUNDANCY,
    ),
    (
        ("шинээр", "дахин"),
        "дахин",
        "«Шинээр» болон «дахин» ижил утгатай тул нэгийг нь үлдээв.",
        "redundant_again",
        Category.REDUNDANCY,
    ),
    (
        ("бүрэн", "гүйцэд"),
        "бүрэн",
        "«Бүрэн гүйцэд» давхардсан утгатай тул «бүрэн» гэж бичнэ.",
        "redundant_full",
        Category.REDUNDANCY,
    ),
    (
        ("урьдчилан", "өмнө"),
        "урьдчилан",
        "«Урьдчилан өмнө» давхардсан тул «урьдчилан» гэж бичнэ.",
        "redundant_before",
        Category.REDUNDANCY,
    ),
    (
        ("байгаа", "юм"),
        "байна",
        "Албан өгүүлбэрт «байгаа юм»-ыг «байна» гэж бичнэ.",
        "spoken_baigaa_yum",
        Category.STYLE,
    ),
    (
        ("гэж", "байгаа"),
        "гэж байна",
        "Албан өгүүлбэрт «байгаа»-г «байна» гэж бичнэ.",
        "official_baina",
        Category.FORMALITY,
    ),
    (
        ("яаж",),
        "хэрхэн",
        "Албан найруулгад «яаж»-ийн оронд «хэрхэн» гэж бичнэ.",
        "official_kherkhen",
        Category.STYLE,
    ),
    (
        ("тэгээд",),
        "улмаар",
        "Албан найруулгад ярианы «тэгээд»-ийн оронд «улмаар» гэж бичнэ.",
        "official_ulmaar",
        Category.STYLE,
    ),
    (
        ("гээд",),
        "гэж",
        "Албан найруулгад «гээд»-ийн оронд «гэж» гэж бичнэ.",
        "official_gej",
        Category.STYLE,
    ),
)

FORMAL_STYLES = frozenset({"government_official", "formal"})


def check_official_style(
    tokens: list[Token],
    text: str = "",
    style: str = "government_official",
) -> list[Correction]:
    if style not in FORMAL_STYLES:
        return []
    corrections: list[Correction] = []
    for i, token in enumerate(tokens):
        key = token.text.casefold()
        if key in OFFICIAL_REPLACEMENTS:
            suggested, explanation = OFFICIAL_REPLACEMENTS[key]
            replacement = suggested
            if token.text[:1].isupper():
                replacement = suggested[:1].upper() + suggested[1:]
            corrections.append(
                _style_hit(
                    token,
                    replacement,
                    explanation,
                    "official_converb",
                    Category.FORMALITY,
                    Severity.SUGGESTION,
                    0.7,
                )
            )
            continue
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if key == "байгаа" and _clause_end(token, text, nxt):
            replacement = "байна"
            if token.text[:1].isupper():
                replacement = "Байна"
            corrections.append(
                _style_hit(
                    token,
                    replacement,
                    "Албан өгүүлбэрийн төгсгөлд «байгаа»-г «байна» гэж бичнэ.",
                    "official_baina",
                    Category.FORMALITY,
                    Severity.SUGGESTION,
                    0.72,
                )
            )
            continue
        if key == "юм" and i > 0 and tokens[i - 1].text.casefold() in _FILLER_PREV:
            start = token.start - 1 if token.start and text[token.start - 1] == " " else token.start
            corrections.append(
                Correction(
                    id=str(uuid.uuid4()),
                    category=Category.STYLE,
                    original_text=text[start : token.end],
                    suggested_text="",
                    explanation="Албан бичигт дүүргэгч «юм»-ыг хасна.",
                    confidence=0.8,
                    start=start,
                    end=token.end,
                    source=Source.RULE,
                    rule_id="informal_yum",
                    severity=Severity.SUGGESTION,
                )
            )
            continue
        if key == "бна":
            corrections.append(
                _style_hit(
                    token,
                    "байна" if token.text.islower() else "Байна",
                    "«бна» нь албан бичигт «байна» гэж бичигдэнэ.",
                    "informal_bna",
                    Category.STYLE,
                    Severity.ERROR,
                    0.9,
                )
            )
    corrections.extend(_phrase_suggestions(tokens, text))
    return corrections


def _phrase_suggestions(tokens: list[Token], text: str) -> list[Correction]:
    corrections: list[Correction] = []
    used: list[tuple[int, int]] = []
    for words, suggested, explanation, rule_id, category in sorted(
        _PHRASES, key=lambda row: len(row[0]), reverse=True
    ):
        n = len(words)
        for i in range(len(tokens) - n + 1):
            if any(tokens[i + j].text.casefold() != words[j] for j in range(n)):
                continue
            start, end = tokens[i].start, tokens[i + n - 1].end
            if any(not (end <= left or start >= right) for left, right in used):
                continue
            original = text[start:end]
            replacement = suggested
            if original[:1].isupper():
                replacement = suggested[:1].upper() + suggested[1:]
            if original == replacement:
                continue
            used.append((start, end))
            corrections.append(
                Correction(
                    id=str(uuid.uuid4()),
                    category=category,
                    original_text=original,
                    suggested_text=replacement,
                    explanation=explanation,
                    confidence=0.74,
                    start=start,
                    end=end,
                    source=Source.RULE,
                    rule_id=rule_id,
                    severity=Severity.SUGGESTION,
                )
            )
    return corrections


def _clause_end(token: Token, text: str, nxt: Token | None) -> bool:
    if nxt is not None and nxt.text.casefold() in _CLAUSE_END_PARTICLES:
        return True
    rest = text[token.end :].lstrip()
    return not rest or rest[:1] in ".!?;"


def _style_hit(
    token: Token,
    suggested: str,
    explanation: str,
    rule_id: str,
    category: Category,
    severity: Severity,
    confidence: float,
) -> Correction:
    return Correction(
        id=str(uuid.uuid4()),
        category=category,
        original_text=token.text,
        suggested_text=suggested,
        explanation=explanation,
        confidence=confidence,
        start=token.start,
        end=token.end,
        source=Source.RULE,
        rule_id=rule_id,
        severity=severity,
    )
