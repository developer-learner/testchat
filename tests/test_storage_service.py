"""Snapshot persistence: M8 compatibility plus M33 revision envelopes.

M24 (AC-78/AC-82): corrupt snapshots are quarantined, never destroyed;
every save keeps the previous snapshot as <file>.bak.
"""
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
    # the stored artifact is plain JSON, one document, no temp residue.
    # M24 amendment: the deliberate .bak rotation artifact (AC-82) is the
    # ONLY residue allowed beside the data file.
    assert json.loads(path.read_text()) == {"revision": 2, "threads": []}
    residue = sorted(f for f in os.listdir(tmp_path) if f != "threads.json")
    assert residue == ["threads.json.bak"]


# AC-78 [M24 — corrupt history is quarantined, never destroyed]
def test_corrupt_snapshot_is_quarantined(tmp_path, monkeypatch):
    path = _use(tmp_path, monkeypatch)
    garbage = "{not valid json!!"
    path.write_text(garbage)
    assert load_snapshot() == []
    # the unreadable file moved aside — bytes preserved, original gone
    assert not path.exists()
    quarantined = sorted(tmp_path.glob("threads.json.corrupt-*"))
    assert len(quarantined) == 1
    assert quarantined[0].read_text() == garbage
    # the save that used to destroy the evidence now leaves it intact
    save_snapshot(SAMPLE)
    assert quarantined[0].read_text() == garbage
    assert load_snapshot() == SAMPLE


# AC-82 [M24 — every save keeps the previous snapshot as .bak]
def test_save_rotates_previous_snapshot_to_bak(tmp_path, monkeypatch):
    path = _use(tmp_path, monkeypatch)
    bak = tmp_path / "threads.json.bak"
    save_snapshot(SAMPLE)
    save_snapshot([])
    assert json.loads(path.read_text()) == {"revision": 2, "threads": []}
    assert json.loads(bak.read_text()) == {"revision": 1, "threads": SAMPLE}
    save_snapshot(SAMPLE)
    # rotation overwrites: .bak always holds exactly the previous snapshot
    assert json.loads(bak.read_text()) == {"revision": 2, "threads": []}


# AC-82 boundary [M24 — nothing to rotate on the very first save]
def test_first_save_creates_no_bak(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch)
    save_snapshot(SAMPLE)
    assert not (tmp_path / "threads.json.bak").exists()


def test_env_path_is_read_at_call_time(tmp_path, monkeypatch):
    a = _use(tmp_path, monkeypatch, name="a.json")
    save_snapshot(SAMPLE)
    monkeypatch.setenv("TESTCHAT_DATA", str(tmp_path / "b.json"))
    assert load_snapshot() == []          # b.json: nothing saved yet
    monkeypatch.setenv("TESTCHAT_DATA", str(a))
    assert load_snapshot() == SAMPLE      # a.json still intact
