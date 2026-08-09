"""Frozen API oracle for schema-invalid snapshot quarantine in v88."""

import json
import urllib.request
from pathlib import Path


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read())


def test_valid_json_with_invalid_thread_schema_is_quarantined(
    app_url: str,
    app_data_path: Path,
) -> None:
    malformed = {
        "revision": 7,
        "threads": [
            {
                "id": 1301,
                "title": "syntactically valid, structurally unsafe",
                "messages": [
                    {
                        "role": "system",
                        "content": "must never reach the browser",
                        "ts": "2026-08-08T12:00:00Z",
                        "model": "alpha-model",
                    }
                ],
                "model": "alpha-model",
                "locked": False,
            }
        ],
    }
    original = json.dumps(malformed, separators=(",", ":")).encode()
    app_data_path.write_bytes(original)

    loaded = _get_json(f"{app_url}/api/v1/threads")
    quarantines = sorted(app_data_path.parent.glob(app_data_path.name + ".corrupt-*"))

    assert (
        loaded,
        app_data_path.exists(),
        len(quarantines),
        quarantines[0].read_bytes() if quarantines else b"",
    ) == (
        {"threads": [], "revision": 0, "quarantined": True},
        False,
        1,
        original,
    )
