"""App-wide user settings, persisted next to the thread snapshot."""

import json
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

DEFAULT_PATH = "data/settings.json"


def _settings_path() -> str:
    return os.environ.get("TESTCHAT_SETTINGS", DEFAULT_PATH)


def load_settings() -> dict:
    path = _settings_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning("Settings at %s is not a JSON object", path)
            return {}
        return data
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Corrupt settings at %s: %s", path, exc)
        return {}
    except OSError as exc:
        logger.warning("Cannot read settings at %s: %s", path, exc)
        return {}


def save_settings(settings: dict) -> None:
    path = _settings_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass  # best-effort cleanup; the primary write exception is re-raised below
        raise


def get_system_prompt() -> str:
    """System prompt for every chat request.

    The LLM_SYSTEM_PROMPT env var, when present, is authoritative — even
    when empty (the frozen suite pins that semantics). The UI-saved prompt
    applies only when the env var is unset, i.e. normal app launches.
    """
    env = os.environ.get("LLM_SYSTEM_PROMPT")
    if env is not None:
        return env
    prompt = load_settings().get("system_prompt", "")
    return prompt if isinstance(prompt, str) else ""
