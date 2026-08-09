"""Snapshot persistence: M8 compatibility plus M33 revision envelopes.

M24 (AC-78/AC-82): corrupt snapshots are quarantined, never destroyed;
every save keeps the previous snapshot as <file>.bak.
"""
import json
import logging
import os
import shutil

import pytest

import src.services.storage as storage_mod
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


# AC-75 + AC-82 correction [v73 — failed backup means failed save]
def test_backup_rotation_failure_preserves_primary_and_is_logged(
    tmp_path, monkeypatch, caplog
):
    path = _use(tmp_path, monkeypatch)
    bak = tmp_path / "threads.json.bak"
    save_snapshot(SAMPLE)
    primary_before = path.read_bytes()

    backup_error = OSError("backup rotation denied")

    def fail_backup_copy(primary, backup):
        raise backup_error

    monkeypatch.setattr(shutil, "copy2", fail_backup_copy)
    with caplog.at_level(logging.WARNING):
        with pytest.raises(OSError) as excinfo:
            save_snapshot([])

    assert excinfo.value is backup_error
    assert path.read_bytes() == primary_before
    assert json.loads(path.read_text())["revision"] == 1
    assert not bak.exists()
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert str(path) in log_text
    assert str(bak) in log_text
    assert "backup rotation denied" in log_text


# AC-75 correction [v73 — cleanup diagnostics cannot mask the save error]
def test_cleanup_failure_does_not_mask_original_save_error(
    tmp_path, monkeypatch, caplog
):
    path = _use(tmp_path, monkeypatch)
    primary_error = OSError("primary replace failed")
    cleanup_error = OSError("temp cleanup failed")
    cleanup_paths = []

    def fail_primary_replace(source, destination):
        raise primary_error

    def fail_temp_unlink(temp_path):
        cleanup_paths.append(os.fspath(temp_path))
        raise cleanup_error

    monkeypatch.setattr(storage_mod.os, "replace", fail_primary_replace)
    monkeypatch.setattr(storage_mod.os, "unlink", fail_temp_unlink)
    with caplog.at_level(logging.WARNING):
        with pytest.raises(OSError) as excinfo:
            save_snapshot(SAMPLE)

    assert excinfo.value is primary_error
    assert not path.exists()
    assert len(cleanup_paths) == 1
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert cleanup_paths[0] in log_text
    assert "temp cleanup failed" in log_text


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


# AC-161 [v99 — a quarantine rename failure is surfaced, never reported
# healthy-empty: broken storage must read as unavailable, not as an empty
# history, or the browser treats corruption as a clean slate]
def test_quarantine_rename_failure_is_unavailable(tmp_path, monkeypatch):
    path = _use(tmp_path, monkeypatch)

    def _validator(data):
        if not isinstance(data, dict):
            raise ValueError("no envelope")
        threads = data.get("threads")
        if not isinstance(threads, list):
            raise ValueError("threads not a list")
        return all(
            isinstance(t, dict) and t.get("role") != "system" for t in threads
        )

    def _failing_rename(src, dst):
        raise OSError("simulated quarantine rename failure")

    monkeypatch.setattr(storage_mod.os, "rename", _failing_rename)

    # unreadable JSON
    path.write_text("{not valid json!!")
    with pytest.raises(storage_mod.SnapshotUnavailableError):
        storage_mod.load_versioned_snapshot()

    # validator raises
    path.write_text('{"revision": 0, "threads": "nope"}')
    with pytest.raises(storage_mod.SnapshotUnavailableError):
        storage_mod.load_versioned_snapshot(validator=_validator)

    # validator returns False
    path.write_text('{"revision": 0, "threads": [{"role": "system"}]}')
    with pytest.raises(storage_mod.SnapshotUnavailableError):
        storage_mod.load_versioned_snapshot(validator=_validator)

    # unreadable shape
    path.write_text('"just a string"')
    with pytest.raises(storage_mod.SnapshotUnavailableError):
        storage_mod.load_versioned_snapshot()

    # the corrupt primary was never silently moved — it stays put
    assert path.exists()
