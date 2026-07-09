"""M8 storage service — snapshot persistence (AC-35/AC-37/AC-38 backend)."""
import json
import os

from src.services.storage import load_snapshot, save_snapshot

SAMPLE = [
    {"id": 1, "title": "First chat", "messages": [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "Hello there"},
    ], "model": "alpha-model", "locked": True},
    {"id": 2, "title": "New Chat", "messages": [], "model": "", "locked": False},
]


def _use(tmp_path, monkeypatch, name="threads.json"):
    path = tmp_path / name
    monkeypatch.setenv("TESTCHAT_DATA", str(path))
    return path


def test_roundtrip_preserves_snapshot(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch)
    save_snapshot(SAMPLE)
    assert load_snapshot() == SAMPLE


def test_missing_file_loads_empty(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch)
    assert load_snapshot() == []


def test_corrupt_file_loads_empty(tmp_path, monkeypatch):
    path = _use(tmp_path, monkeypatch)
    path.write_text("{not valid json!!")
    assert load_snapshot() == []


def test_save_creates_parent_directory(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch, name="nested/dir/threads.json")
    save_snapshot(SAMPLE)
    assert load_snapshot() == SAMPLE


def test_save_overwrites_atomically(tmp_path, monkeypatch):
    path = _use(tmp_path, monkeypatch)
    save_snapshot(SAMPLE)
    save_snapshot([])
    assert load_snapshot() == []
    # the stored artifact is plain JSON, one document, no temp residue
    assert json.loads(path.read_text()) == []
    assert [f for f in os.listdir(tmp_path) if f != "threads.json"] == []


def test_env_path_is_read_at_call_time(tmp_path, monkeypatch):
    a = _use(tmp_path, monkeypatch, name="a.json")
    save_snapshot(SAMPLE)
    monkeypatch.setenv("TESTCHAT_DATA", str(tmp_path / "b.json"))
    assert load_snapshot() == []          # b.json: nothing saved yet
    monkeypatch.setenv("TESTCHAT_DATA", str(a))
    assert load_snapshot() == SAMPLE      # a.json still intact
