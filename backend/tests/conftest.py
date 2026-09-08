import pytest


@pytest.fixture(autouse=True)
def disable_live_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.ai.keys.get_api_key", lambda: "")
    monkeypatch.setattr("app.ai.keys.ai_enabled", lambda: False)
    monkeypatch.setattr("app.api.routes_check.ai_enabled", lambda: False)
    monkeypatch.setattr("app.api.routes_ai.ai_enabled", lambda: False)
