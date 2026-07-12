"""M10 settings — API roundtrip (AC-50) and system-prompt precedence (AC-51)."""
from fastapi.testclient import TestClient

from src.main import app
from src.services.settings import get_system_prompt, load_settings, save_settings

client = TestClient(app)


def _isolate(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setenv("TESTCHAT_SETTINGS", str(path))
    return path


def test_get_default_is_empty_prompt(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    r = client.get("/api/v1/settings")
    assert r.status_code == 200
    assert r.json() == {"system_prompt": ""}


def test_put_then_get_roundtrips(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    r = client.put("/api/v1/settings", json={"system_prompt": "You are terse."})
    assert r.status_code == 200
    assert client.get("/api/v1/settings").json() == {"system_prompt": "You are terse."}


def test_corrupt_settings_file_reads_as_empty(tmp_path, monkeypatch):
    path = _isolate(tmp_path, monkeypatch)
    path.write_text("{broken json!!")
    assert client.get("/api/v1/settings").json() == {"system_prompt": ""}
    assert load_settings() == {}


def test_save_and_load_service_roundtrip(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    save_settings({"system_prompt": "abc", "extra": 1})
    assert load_settings() == {"system_prompt": "abc", "extra": 1}


def test_env_var_precedence_set_wins(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    save_settings({"system_prompt": "from the UI"})
    monkeypatch.setenv("LLM_SYSTEM_PROMPT", "from the env")
    assert get_system_prompt() == "from the env"


def test_env_var_precedence_empty_still_wins(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    save_settings({"system_prompt": "from the UI"})
    monkeypatch.setenv("LLM_SYSTEM_PROMPT", "")
    assert get_system_prompt() == ""


def test_env_var_unset_falls_back_to_saved(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    save_settings({"system_prompt": "from the UI"})
    monkeypatch.delenv("LLM_SYSTEM_PROMPT", raising=False)
    assert get_system_prompt() == "from the UI"
