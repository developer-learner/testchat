"""Per-thread saving — backend oracle (AC-189..AC-198).

Each thread carries its own revision. A save or delete names one thread and
that thread's revision, so edits to different threads never conflict; only a
stale edit to the SAME thread is refused. Surface: the per-thread routes, the
carried GET route, and the storage entry points save_thread_snapshot /
delete_thread_snapshot / SnapshotConflict / SnapshotUnavailableError.
"""
import json
import threading

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.storage import (
    SnapshotConflict,
    SnapshotUnavailableError,
    delete_thread_snapshot,
    save_thread_snapshot,
)


def _thread(thread_id: int, title: str) -> dict:
    return {
        "id": thread_id,
        "title": title,
        "messages": [
            {"role": "user", "content": f"q {title}", "ts": 1.0, "model": "alpha"},
            {"role": "assistant", "content": f"a {title}", "ts": 2.0, "model": "alpha"},
        ],
        "model": "alpha",
        "locked": False,
    }


@pytest.fixture
def data_path(tmp_path, monkeypatch):
    path = tmp_path / "threads.json"
    monkeypatch.setenv("TESTCHAT_DATA", str(path))
    return path


@pytest.fixture
def client(data_path):
    return TestClient(app)


def _seed(data_path, threads: list[dict], revision: int = 4) -> None:
    data_path.write_text(json.dumps({"revision": revision, "threads": threads}))


def _stored(client) -> dict:
    response = client.get("/api/v1/threads")
    assert response.status_code == 200
    return response.json()


def _by_id(body: dict) -> dict:
    return {t["id"]: t for t in body["threads"]}


def _files(data_path) -> tuple[bytes, bytes | None]:
    backup = data_path.with_name(data_path.name + ".bak")
    return data_path.read_bytes(), backup.read_bytes() if backup.exists() else None


# --- storage entry points ---------------------------------------------------


# AC-189 — a thread not yet stored is created at revision 1.
def test_storage_saves_a_new_thread_at_revision_one(data_path) -> None:
    _seed(data_path, [_thread(1, "keep")])
    assert save_thread_snapshot(_thread(2, "new"), 0) == 1
    stored = json.loads(data_path.read_text())
    ids = [t["id"] for t in stored["threads"]]
    assert ids == [1, 2]
    assert stored["threads"][1]["revision"] == 1
    assert stored["threads"][0]["title"] == "keep"


# AC-190 — a stale thread revision raises the conflict with the current one.
def test_storage_stale_thread_revision_raises_conflict(data_path) -> None:
    _seed(data_path, [{**_thread(1, "current"), "revision": 3}])
    before = data_path.read_bytes()
    with pytest.raises(SnapshotConflict) as exc:
        save_thread_snapshot(_thread(1, "stale"), 2)
    assert exc.value.current_revision == 3
    assert data_path.read_bytes() == before


# AC-194 — deleting with the current revision removes only that thread.
def test_storage_deletes_only_the_named_thread(data_path) -> None:
    _seed(data_path, [{**_thread(1, "go"), "revision": 2}, _thread(2, "stay")])
    assert delete_thread_snapshot(1, 2) is True
    stored = json.loads(data_path.read_text())
    assert [t["id"] for t in stored["threads"]] == [2]


# AC-197 — an unreadable primary is never overwritten by a per-thread save.
def test_storage_refuses_to_save_over_an_unreadable_primary(data_path) -> None:
    data_path.write_text("{not json")
    with pytest.raises(SnapshotUnavailableError):
        save_thread_snapshot(_thread(1, "x"), 0)
    assert data_path.read_text() == "{not json"


# --- routes -------------------------------------------------------------------


# AC-189 — PUT with the thread's current revision stores it and leaves the rest.
def test_put_thread_with_current_revision_is_accepted(data_path, client) -> None:
    _seed(data_path, [{**_thread(1, "one"), "revision": 2}, _thread(2, "two")])
    response = client.put(
        "/api/v1/threads/1", json={"revision": 2, "thread": _thread(1, "one edited")}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "revision": 3}
    stored = _by_id(_stored(client))
    assert stored[1]["title"] == "one edited"
    assert stored[1]["revision"] == 3
    assert stored[2] == _thread(2, "two")


# AC-189 — a thread with no stored revision (legacy) is at revision 0.
def test_put_thread_treats_a_legacy_thread_as_revision_zero(data_path, client) -> None:
    _seed(data_path, [_thread(1, "legacy")])
    response = client.put(
        "/api/v1/threads/1", json={"revision": 0, "thread": _thread(1, "upgraded")}
    )
    assert response.json() == {"status": "ok", "revision": 1}
    assert _by_id(_stored(client))[1]["title"] == "upgraded"


# AC-190 — PUT with a stale revision is refused and changes nothing.
def test_put_thread_with_stale_revision_conflicts(data_path, client) -> None:
    _seed(data_path, [{**_thread(1, "current"), "revision": 5}])
    before = _files(data_path)
    response = client.put(
        "/api/v1/threads/1", json={"revision": 4, "thread": _thread(1, "stale")}
    )
    assert response.status_code == 409
    assert response.json() == {"error": "revision_conflict", "current_revision": 5}
    assert _files(data_path) == before


# AC-190 — saving a thread another tab deleted is a conflict, not a silent revive.
def test_put_thread_that_was_deleted_elsewhere_conflicts(data_path, client) -> None:
    _seed(data_path, [_thread(2, "other")])
    before = _files(data_path)
    response = client.put(
        "/api/v1/threads/1", json={"revision": 3, "thread": _thread(1, "revived")}
    )
    assert response.status_code == 409
    assert response.json() == {"error": "revision_conflict", "current_revision": 0}
    assert _files(data_path) == before


# AC-191 — two tabs, two different threads, each from the same starting state.
def test_edits_to_different_threads_from_the_same_state_both_persist(
    data_path, client
) -> None:
    _seed(data_path, [_thread(1, "a"), _thread(2, "b")])
    tab_a = client.put(
        "/api/v1/threads/1", json={"revision": 0, "thread": _thread(1, "a by tab A")}
    )
    tab_b = client.put(
        "/api/v1/threads/2", json={"revision": 0, "thread": _thread(2, "b by tab B")}
    )
    assert (tab_a.status_code, tab_b.status_code) == (200, 200)
    stored = _by_id(_stored(client))
    assert (stored[1]["title"], stored[2]["title"]) == ("a by tab A", "b by tab B")


# AC-192 — PUT without a revision is rejected and changes nothing.
def test_put_thread_without_revision_is_rejected(data_path, client) -> None:
    _seed(data_path, [_thread(1, "keep")])
    before = _files(data_path)
    response = client.put("/api/v1/threads/1", json={"thread": _thread(1, "x")})
    assert response.status_code == 422
    assert _files(data_path) == before


# AC-193 — a body thread id that differs from the path id is rejected.
def test_put_thread_with_mismatched_id_is_rejected(data_path, client) -> None:
    _seed(data_path, [_thread(1, "keep"), _thread(2, "keep too")])
    before = _files(data_path)
    response = client.put(
        "/api/v1/threads/1", json={"revision": 0, "thread": _thread(2, "wrong")}
    )
    assert response.status_code == 422
    assert _files(data_path) == before


# AC-194 — DELETE with the current revision removes exactly that thread.
def test_delete_thread_with_current_revision_removes_only_it(data_path, client) -> None:
    _seed(data_path, [_thread(1, "go"), _thread(2, "stay"), _thread(3, "stay too")])
    response = client.request("DELETE", "/api/v1/threads/1", json={"revision": 0})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    stored = _by_id(_stored(client))
    assert sorted(stored) == [2, 3]
    assert stored[2] == _thread(2, "stay")


# AC-195 — DELETE with a stale revision is refused and changes nothing.
def test_delete_thread_with_stale_revision_conflicts(data_path, client) -> None:
    _seed(data_path, [{**_thread(1, "edited elsewhere"), "revision": 2}])
    before = _files(data_path)
    response = client.request("DELETE", "/api/v1/threads/1", json={"revision": 1})
    assert response.status_code == 409
    assert response.json() == {"error": "revision_conflict", "current_revision": 2}
    assert _files(data_path) == before


# AC-196 — deleting a thread that is already gone succeeds and changes nothing.
def test_delete_thread_already_gone_is_ok_and_changes_nothing(data_path, client) -> None:
    _seed(data_path, [_thread(2, "stay")])
    before = _files(data_path)
    response = client.request("DELETE", "/api/v1/threads/1", json={"revision": 0})
    assert response.status_code == 200
    assert _files(data_path) == before


# AC-197 — the route reports an unreadable primary instead of overwriting it.
def test_put_thread_over_unreadable_primary_returns_503(data_path, client) -> None:
    data_path.write_text("{not json")
    response = client.put(
        "/api/v1/threads/1", json={"revision": 0, "thread": _thread(1, "x")}
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "snapshot unavailable"}
    assert data_path.read_text() == "{not json"


# AC-198 — two concurrent saves of the same thread: exactly one wins.
def test_concurrent_saves_of_one_thread_accept_exactly_one(data_path, client) -> None:
    _seed(data_path, [_thread(1, "start")])
    barrier = threading.Barrier(2)
    results: dict[str, int] = {}

    def save(title: str) -> None:
        barrier.wait()
        response = client.put(
            "/api/v1/threads/1", json={"revision": 0, "thread": _thread(1, title)}
        )
        results[title] = response.status_code

    workers = [threading.Thread(target=save, args=(t,)) for t in ("left", "right")]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    assert sorted(results.values()) == [200, 409]
    winner = next(title for title, code in results.items() if code == 200)
    stored = _by_id(_stored(client))[1]
    assert (stored["title"], stored["revision"]) == (winner, 1)
