from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.ai.keys import get_api_key
from app.ai.locate import locate_corrections
from app.core.config import settings
from app.engine.models import Correction

_CHECK_SYSTEM = """Чи монгол хэлний мэргэжлийн редактор. Өгүүлбэрийг бүхэлд нь уншиж, утгыг нь ойлгоод засна.

Хийх:
- Зөв бичих, дүрэм, цэг таслал, үгийн сонголт, албан найруулгын алдааг ол.
- Зөв бичсэн ч ярианы, илүүц, давхардсан, сул найруулгыг STYLE, CLARITY, FORMALITY, REDUNDANCY гэж санал болго. severity=suggestion.
- Санал болгох үг, хэллэг өөрөө зөв, бүрэн, албан байх ёстой.
- Нэг алдаатай үгэнд 1–5 засах үг өг. Эхнийх нь хамгийн зөв.
- Найруулгын саналд original нь текстэд яг байгаа үг, хэллэг эсвэл өгүүлбэр байна.

Бүү хий:
- Зөв үгийг бүү тасал, бүү задла (хуралдаа, шаардлагатай гэх мэт).
- Нэр, тоо, огноо, байгууллагын нэр, ишлэлийг бүү өөрчил, бүү нэм.
- Кирилл монгол хэлийг оросоор бүү бод.
- о/ө, у/ү-ийг зөвхөн үнэхээр буруу үед засаарай.
- Аль хэдийн албан, цэвэрхэн өгүүлбэрийг бүү өөрчил.
- original текстэд яг байх ёстой.

Өгүүлбэрийн утгаар нь зөв үгийг сонго. Толийн ойролцоо хог үг бүү өг (орчино, уусны, иенээ гэх мэт).
Жишээ: эхэлээгүй→эхлээгүй; одөр→өдөр; орчиноо→орчноо; уены→үеийн; шаардлагтай→шаардлагатай; ажилтангууд→ажилтнууд.
Хариу зөвхөн JSON:
{"corrections":[{"original":"...","suggested":"...","alternatives":["..."],"category":"SPELLING|GRAMMAR|PUNCTUATION|WORD_CHOICE|STYLE|FORMALITY|CLARITY|REDUNDANCY","explanation":"монгол тайлбар","severity":"error|warning|suggestion"}]}"""

_REWRITE_SYSTEM = """Чи монгол албан бичгийн редактор. Текстийг уншиж, утгыг нь ойлгоод зөв, цэвэрхэн, албан найруулгатай бич.

Ярианы үг, илүүц үг, давхардал, сул өгүүлбэрийг засаарай.
Утга, нэр, тоо, огноо, байгууллагын нэрийг бүү өөрчил, бүү нэм.
Зөв үгийг бүү тасал. Кирилл монгол хэлийг оросоор бүү бод.
Хариу зөвхөн JSON:
{"improved_text":"бүтэн засагдсан эх"}"""


class OpenAIProvider:
    def __init__(self) -> None:
        self._check_cache: dict[tuple[str, str], list[Correction]] = {}

    def check_text(self, text: str, style: str = "government_official") -> list[Correction]:
        cache_key = (text, style)
        cached = self._check_cache.get(cache_key)
        if cached is not None:
            return cached
        data = self._complete(_CHECK_SYSTEM, text, style)
        raw = data.get("corrections")
        if not isinstance(raw, list):
            return []
        found = locate_corrections(text, [row for row in raw if isinstance(row, dict)])
        self._check_cache[cache_key] = found
        if len(self._check_cache) > 32:
            self._check_cache.pop(next(iter(self._check_cache)))
        return found

    def rewrite_text(self, text: str, style: str = "government_official") -> str:
        data = self._complete(_REWRITE_SYSTEM, text, style)
        improved = data.get("improved_text")
        if isinstance(improved, str) and improved.strip():
            return improved.strip()
        return text

    def _complete(self, system: str, text: str, style: str) -> dict[str, Any]:
        key = get_api_key()
        if not key:
            return {}
        body = {
            "model": settings.openai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Найруулга: {style}\n\nТекст:\n{text}",
                },
            ],
        }
        last_error: Exception | None = None
        models = [settings.openai_model]
        if settings.openai_model != "gpt-4o-mini":
            models.append("gpt-4o-mini")
        for model in models:
            body["model"] = model
            for _ in range(2):
                try:
                    return _parse_json(_request(key, body))
                except httpx.HTTPStatusError as exc:
                    last_error = exc
                    if exc.response.status_code in {401, 403, 429}:
                        raise
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
        if last_error:
            raise last_error
        return {}


def _request(key: str, body: dict[str, Any]) -> str:
    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    with httpx.Client(timeout=45.0) as client:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()
        payload = response.json()
    return str(payload["choices"][0]["message"]["content"])


def _parse_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    data = json.loads(text)
    return data if isinstance(data, dict) else {}
