from __future__ import annotations

import uuid

from app.engine.models import Category, Correction, Severity, Source
from app.engine.text import Token

_OURS = frozenset({"манай", "манайх", "бидний", "бид", "биднийх", "миний"})
_THEIRS = frozenset({"танай", "танайх", "таны", "тань"})
_ABLATIVE_ENDS = ("аас", "ээс", "оос", "өөс", "наас", "нээс", "ноос", "нөөс")
_DOCUMENT = frozenset(
    {
        "хүсэлт",
        "хүсэлтийг",
        "хүсэлтийн",
        "хүсэлтэд",
        "өргөдөл",
        "өргөдлийг",
        "өргөдлийн",
        "бичиг",
        "бичгийг",
        "бичгийн",
        "албан",
        "тайлан",
        "тайланг",
        "тайлангийн",
        "хариу",
        "хариуг",
        "хариуны",
        "тогтоол",
        "тогтоолыг",
        "тушаал",
        "тушаалыг",
        "санал",
        "саналыг",
        "хавсралт",
        "хавсралтыг",
        "томьёоллол",
        "мэдэгдэл",
        "мэдэгдлийг",
    }
)
_RECEIVE = {
    "авч": "хүлээн авч",
    "авсан": "хүлээн авсан",
    "авах": "хүлээн авах",
    "авлаа": "хүлээн авлаа",
    "авав": "хүлээн авав",
}
_SEND_YAVUUL = {
    "явуулсан": "илгээсэн",
    "явуулах": "илгээх",
    "явуулж": "илгээж",
    "явуулна": "илгээнэ",
    "явуулаарай": "илгээнэ үү",
    "явуул": "илгээ",
}
_SEE_DOC = {
    "үзэж": "танилцаж",
    "үзсэн": "танилцсан",
    "үзэх": "танилцах",
    "үзээд": "танилцан",
    "үзнэ": "танилцана",
}


def check_word_choice(tokens: list[Token], text: str) -> list[Correction]:
    corrections: list[Correction] = []
    for i, token in enumerate(tokens):
        folded = token.text.casefold()
        person = _source_person(tokens, i)
        outgoing = _to_outgoing(folded)
        incoming = _to_incoming(folded)
        if person == "ours" and outgoing:
            corrections.append(
                _hit(
                    token,
                    _cased(token.text, outgoing),
                    "Манай/бидний талаас илгээхэд «хүргүүлэх» гэж бичнэ. "
                    "«Ирүүлэх» нь бусдын бичгийг өөрт авахад хэрэглэнэ.",
                    "outgoing_delivery_verb",
                    Category.WORD_CHOICE,
                    Severity.ERROR,
                    0.88,
                )
            )
            continue
        if person == "theirs" and incoming:
            corrections.append(
                _hit(
                    token,
                    _cased(token.text, incoming),
                    "Бусдаас ирсэн бичигт «хүргүүлэх» биш «ирүүлэх» гэж бичнэ.",
                    "incoming_delivery_verb",
                    Category.WORD_CHOICE,
                    Severity.ERROR,
                    0.86,
                )
            )
            continue
        if (
            folded in _RECEIVE
            and _nearby_document(tokens, i)
            and not _previous_is(tokens, i, "хүлээн")
        ):
            corrections.append(
                _hit(
                    token,
                    _cased(token.text, _RECEIVE[folded]),
                    "Албан бичиг, хүсэлтийг «авах» биш «хүлээн авах» гэж бичнэ.",
                    "official_receive",
                    Category.WORD_CHOICE,
                    Severity.SUGGESTION,
                    0.87,
                )
            )
            continue
        if folded in _SEND_YAVUUL and _nearby_document(tokens, i):
            corrections.append(
                _hit(
                    token,
                    _cased(token.text, _SEND_YAVUUL[folded]),
                    "Албан бичигт «явуулах»-ын оронд «илгээх» гэж бичнэ.",
                    "official_send",
                    Category.WORD_CHOICE,
                    Severity.SUGGESTION,
                    0.86,
                )
            )
            continue
        if folded in _SEE_DOC and _nearby_document(tokens, i):
            corrections.append(
                _hit(
                    token,
                    _cased(token.text, _SEE_DOC[folded]),
                    "Бичиг баримттай «үзэх» биш «танилцах» гэж бичнэ.",
                    "official_review",
                    Category.WORD_CHOICE,
                    Severity.SUGGESTION,
                    0.86,
                )
            )
    return corrections


def _to_outgoing(word: str) -> str | None:
    if word.startswith("ирүүл") and len(word) > 5:
        return "хүргүүл" + word[5:]
    return None


def _to_incoming(word: str) -> str | None:
    if word.startswith("хүргүүл") and len(word) > 7:
        return "ирүүл" + word[7:]
    return None


def _source_person(tokens: list[Token], index: int) -> str | None:
    window = tokens[max(0, index - 8) : index]
    people: list[tuple[int, str]] = []
    ablative_at: int | None = None
    for j, token in enumerate(window):
        folded = token.text.casefold()
        if folded in _OURS or (folded.startswith("манай") and folded.endswith(_ABLATIVE_ENDS)):
            people.append((j, "ours"))
        elif folded in _THEIRS or (folded.startswith("танай") and folded.endswith(_ABLATIVE_ENDS)):
            people.append((j, "theirs"))
        if folded.endswith(_ABLATIVE_ENDS):
            ablative_at = j
    if ablative_at is not None:
        before = [person for idx, person in people if idx < ablative_at]
        if before:
            return before[-1]
    close = [person for idx, person in people if idx >= len(window) - 2]
    if close:
        return close[-1]
    return None


def _nearby_document(tokens: list[Token], index: int) -> bool:
    lo, hi = max(0, index - 4), min(len(tokens), index + 4)
    return any(tokens[j].text.casefold() in _DOCUMENT for j in range(lo, hi) if j != index)


def _previous_is(tokens: list[Token], index: int, word: str) -> bool:
    return index > 0 and tokens[index - 1].text.casefold() == word


def _cased(original: str, suggested: str) -> str:
    if not original[:1].isupper():
        return suggested
    head, sep, tail = suggested.partition(" ")
    return head[:1].upper() + head[1:] + sep + tail


def _hit(
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
