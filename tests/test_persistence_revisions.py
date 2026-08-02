"""M33 backend oracle: revisioned, conflict-safe history persistence."""
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from src.main import app
from src.services.storage import (
    load_snapshot,
    load_versioned_snapshot,
    save_versioned_snapshot,
)


def _threads(title: str) -> list[dict]:
    return [{
        "id": 1,
        "title": title,
        "messages": [
            {"role": "user", "content": "keep me", "ts": 1.0, "model": "alpha"},
            {"role": "assistant", "content": "kept", "ts": 2.0, "model": "alpha"},
        ],
        "model": "alpha",
        "locked": False,
    }]


def _put_body(title: str, revision: int) -> dict:
    return {"revision": revision, "threads": _threads(title)}


# AC-137 — legacy primary/restored backup reads losslessly at revision zero.
def test_legacy_raw_primary_and_restored_backup_read_at_revision_zero(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "threads.json"
    backup = tmp_path / "threads.json.bak"
    legacy = _threads("legacy")
    monkeypatch.setenv("TESTCHAT_DATA", str(path))

    path.write_text(json.dumps(legacy))
    assert load_versioned_snapshot() == (legacy, 0)
    assert load_snapshot() == legacy

    os.replace(path, backup)
    os.replace(backup, path)  # the supported human restore operation
    assert load_versioned_snapshot() == (legacy, 0)
    assert load_snapshot() == legacy


# AC-138 — an accepted write migrates legacy/restored bytes to the envelope.
def test_accepted_write_migrates_legacy_primary_and_restored_backup(
    tmp_path, monkeypatch
) -> None:
    legacy = _threads("legacy")
    for case, restored in (("primary", False), ("restored", True)):
        directory = tmp_path / case
        directory.mkdir()
        path = directory / "threads.json"
        backup = directory / "threads.json.bak"
        monkeypatch.setenv("TESTCHAT_DATA", str(path))
        if restored:
            backup.write_text(json.dumps(legacy))
            os.replace(backup, path)
        else:
            path.write_text(json.dumps(legacy))

        assert load_versioned_snapshot() == (legacy, 0)
        assert save_versioned_snapshot(legacy, expected_revision=0) == 1
        assert json.loads(path.read_text()) == {"revision": 1, "threads": legacy}
        assert json.loads(backup.read_text()) == legacy


# AC-139 — PUT requires an explicit revision.
def test_put_without_revision_is_422_and_writes_nothing(tmp_path, monkeypatch) -> None:
    path = tmp_path / "threads.json"
    monkeypatch.setenv("TESTCHAT_DATA", str(path))
    client = TestClient(app, raise_server_exceptions=False)

    assert client.put("/api/v1/threads", json={"threads": _threads("x")}).status_code == 422
    assert not path.exists()


# AC-140 — DELETE requires an explicit revision.
def test_delete_without_revision_is_422_and_writes_nothing(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "threads.json"
    monkeypatch.setenv("TESTCHAT_DATA", str(path))
    client = TestClient(app, raise_server_exceptions=False)

    assert client.request("DELETE", "/api/v1/threads").status_code == 422
    assert not path.exists()


# AC-141 — accepted PUT advances even for an equal snapshot.
def test_each_accepted_put_advances_revision(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TESTCHAT_DATA", str(tmp_path / "threads.json"))
    client = TestClient(app, raise_server_exceptions=False)

    first = client.put("/api/v1/threads", json=_put_body("same", 0))
    assert first.json() == {"status": "ok", "revision": 1}
    identical = client.put("/api/v1/threads", json=_put_body("same", 1))
    assert identical.json() == {"status": "ok", "revision": 2}
    state = client.get("/api/v1/threads").json()
    assert state["revision"] == 2
    assert state["threads"] == _threads("same")


# AC-142 — accepted DELETE advances even when already empty.
def test_each_accepted_delete_advances_revision(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TESTCHAT_DATA", str(tmp_path / "threads.json"))
    client = TestClient(app, raise_server_exceptions=False)

    first = client.request("DELETE", "/api/v1/threads", json={"revision": 0})
    assert first.json() == {"status": "ok", "revision": 1}
    second = client.request("DELETE", "/api/v1/threads", json={"revision": 1})
    assert second.json() == {"status": "ok", "revision": 2}
    assert client.get("/api/v1/threads").json() == {
        "threads": [], "revision": 2, "quarantined": False
    }


def _two_generations(client: TestClient, path) -> tuple[bytes, bytes]:
    assert client.put("/api/v1/threads", json=_put_body("one", 0)).status_code == 200
    assert client.put("/api/v1/threads", json=_put_body("two", 1)).status_code == 200
    return path.read_bytes(), path.with_name(path.name + ".bak").read_bytes()


# AC-143 — stale PUT is 409 and changes neither generation.
def test_stale_put_leaves_primary_and_backup_unchanged(tmp_path, monkeypatch) -> None:
    path = tmp_path / "threads.json"
    monkeypatch.setenv("TESTCHAT_DATA", str(path))
    client = TestClient(app, raise_server_exceptions=False)
    before = _two_generations(client, path)

    response = client.put("/api/v1/threads", json=_put_body("stale", 1))
    assert response.status_code == 409
    assert response.json() == {"error": "revision_conflict", "current_revision": 2}
    assert (path.read_bytes(), path.with_name(path.name + ".bak").read_bytes()) == before


# AC-144 — stale DELETE is 409 and changes neither generation.
def test_stale_delete_leaves_primary_and_backup_unchanged(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "threads.json"
    monkeypatch.setenv("TESTCHAT_DATA", str(path))
    client = TestClient(app, raise_server_exceptions=False)
    before = _two_generations(client, path)

    response = client.request(
        "DELETE", "/api/v1/threads", json={"revision": 1}
    )
    assert response.status_code == 409
    assert response.json() == {"error": "revision_conflict", "current_revision": 2}
    assert (path.read_bytes(), path.with_name(path.name + ".bak").read_bytes()) == before


# AC-145 — one lock makes same-generation concurrent writes single-winner.
def test_two_concurrent_same_revision_puts_have_one_winner(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("TESTCHAT_DATA", str(tmp_path / "threads.json"))
    gate = threading.Barrier(2)

    def write(title: str):
        client = TestClient(app, raise_server_exceptions=False)
        gate.wait()
        response = client.put("/api/v1/threads", json=_put_body(title, 0))
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, ["alpha", "beta"]))

    assert sorted(status for status, _ in results) == [200, 409]
    conflict = next(body for status, body in results if status == 409)
    assert conflict == {"error": "revision_conflict", "current_revision": 1}
    state = TestClient(app).get("/api/v1/threads").json()
    assert state["revision"] == 1
    assert state["threads"][0]["title"] in {"alpha", "beta"}
