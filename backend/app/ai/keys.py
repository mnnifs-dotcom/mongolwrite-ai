from __future__ import annotations

from pathlib import Path

from app.core.config import settings


def _key_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / ".openai_key"


def get_api_key() -> str:
    stored = _key_path()
    if stored.exists():
        value = stored.read_text(encoding="utf-8").strip()
        if value:
            return value
    return settings.openai_api_key.strip()


def save_api_key(key: str) -> None:
    path = _key_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = key.strip()
    if cleaned:
        path.write_text(cleaned + "\n", encoding="utf-8")
        path.chmod(0o600)
    elif path.exists():
        path.unlink()


def ai_enabled() -> bool:
    return bool(get_api_key())
