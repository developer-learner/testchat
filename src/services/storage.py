import json
import logging
import os
import shutil
import tempfile
import threading
import time

logger = logging.getLogger(__name__)

DEFAULT_PATH = "data/threads.json"

_lock = threading.Lock()


class SnapshotConflict(Exception):
    def __init__(self, current_revision: int):
        super().__init__("revision conflict")
        self.current_revision = current_revision


def _data_path() -> str:
    return os.environ.get("TESTCHAT_DATA", DEFAULT_PATH)


def _read_raw(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _read_any(path: str) -> object | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError):
        return None


def _extract_threads(data: dict) -> list[dict]:
    threads = data.get("threads")
    if not isinstance(threads, list):
        logger.warning("Snapshot at %s has no threads list", _data_path())
        return []
    return threads


def load_versioned_snapshot() -> tuple[list[dict], int]:
    path = _data_path()
    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return [], 0
        except (json.JSONDecodeError, ValueError, OSError):
            # Corrupt primary — quarantine and load empty.
            stamp = time.strftime("%Y%m%d-%H%M%S")
            corrupt_path = f"{path}.corrupt-{stamp}"
            try:
                os.rename(path, corrupt_path)
            except OSError as rename_exc:
                logger.warning(
                    "Could not quarantine corrupt snapshot: primary=%s corrupt=%s error=%s",
                    path, corrupt_path, rename_exc,
                )
            return [], 0
        if isinstance(data, list):
            # Legacy raw list — treat as revision 0.
            return data, 0
        if isinstance(data, dict):
            if "revision" in data:
                revision = data["revision"]
                if not isinstance(revision, int) or revision < 0:
                    logger.warning("Snapshot at %s has invalid revision", path)
                    revision = 0
                return _extract_threads(data), revision
            # Legacy raw list (no revision key) — treat as revision 0.
            return _extract_threads(data), 0
        # Unreadable shape — quarantine and load empty.
        stamp = time.strftime("%Y%m%d-%H%M%S")
        corrupt_path = f"{path}.corrupt-{stamp}"
        try:
            shutil.copy2(path, corrupt_path)
            os.unlink(path)
        except OSError as exc:
            logger.warning(
                "Could not quarantine corrupt snapshot: primary=%s corrupt=%s error=%s",
                path, corrupt_path, exc,
            )
        return [], 0


def load_snapshot() -> list[dict]:
    threads, _revision = load_versioned_snapshot()
    return threads


def _save_versioned_snapshot_locked(threads: list[dict], expected_revision: int) -> int:
    path = _data_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    data = _read_raw(path)
    current_revision = 0
    if data is not None:
        rev = data.get("revision")
        if isinstance(rev, int) and rev >= 0:
            current_revision = rev
    if current_revision != expected_revision:
        raise SnapshotConflict(current_revision)
    new_revision = current_revision + 1
    payload = {"revision": new_revision, "threads": threads}
    fd, tmp_path = tempfile.mkstemp(dir=parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        bak_path = f"{path}.bak"
        if os.path.exists(path):
            try:
                shutil.copy2(path, bak_path)
            except OSError as exc:
                logger.warning(
                    "Could not back up snapshot: primary=%s backup=%s error=%s",
                    path, bak_path, exc,
                )
                raise
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError as cleanup_exc:
            logger.warning(
                "temp cleanup failed: temp=%s error=%s", tmp_path, cleanup_exc,
            )
        raise
    return new_revision


def save_versioned_snapshot(threads: list[dict], expected_revision: int) -> int:
    with _lock:
        return _save_versioned_snapshot_locked(threads, expected_revision)


def save_snapshot(threads: list[dict]) -> None:
    with _lock:
        path = _data_path()
        data = _read_any(path)
        current = 0
        if isinstance(data, dict):
            rev = data.get("revision")
            if isinstance(rev, int) and rev >= 0:
                current = rev
        _save_versioned_snapshot_locked(threads, current)


def quarantine_files() -> list[str]:
    parent, name = os.path.split(_data_path())
    try:
        return sorted(
            f for f in os.listdir(parent or ".")
            if f.startswith(name + ".corrupt-")
        )
    except OSError:
        return []  # no data directory yet means nothing is quarantined