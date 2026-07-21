import json
import logging
import os
import tempfile
import time

logger = logging.getLogger(__name__)

DEFAULT_PATH = "data/threads.json"


def _data_path() -> str:
    return os.environ.get("TESTCHAT_DATA", DEFAULT_PATH)


def load_snapshot() -> list[dict]:
    path = _data_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            logger.warning("Snapshot at %s is not a JSON list", path)
            return []
        return data
    except FileNotFoundError:
        # save_snapshot has a brief window between renaming path→.bak and
        # tmp→path; a crash there leaves only .bak. Recover automatically.
        bak = f"{path}.bak"
        try:
            with open(bak, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                logger.warning("Recovered snapshot from %s (path missing)", bak)
                return data
        except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError):
            pass  # no usable backup either — fall through to empty
        return []
    except (json.JSONDecodeError, ValueError) as exc:
        quarantine = f"{path}.corrupt-{int(time.time())}"
        try:
            os.replace(path, quarantine)
            logger.warning(
                "Corrupt snapshot at %s quarantined to %s: %s",
                path, quarantine, exc,
            )
        except OSError as move_exc:
            logger.warning(
                "Corrupt snapshot at %s could not be quarantined: %s",
                path, move_exc,
            )
        return []
    except OSError as exc:
        logger.warning("Cannot read snapshot at %s: %s", path, exc)
        return []


def save_snapshot(threads: list[dict]) -> None:
    path = _data_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(threads, f, ensure_ascii=False, indent=2)
        if os.path.exists(path):
            os.replace(path, f"{path}.bak")
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass  # tmp file already gone; nothing to clean
        raise


def quarantine_files() -> list[str]:
    parent, name = os.path.split(_data_path())
    try:
        return sorted(
            f for f in os.listdir(parent or ".")
            if f.startswith(name + ".corrupt-")
        )
    except OSError:
        return []  # no data directory yet means nothing is quarantined