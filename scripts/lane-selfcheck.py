#!/usr/bin/env python3
"""lane-selfcheck.py — assert the running environment matches its pins.

Fails closed: every check must actively confirm environment == pin. Any check
that cannot read its source of truth, or finds a mismatch, prints FAIL and the
script exits non-zero. There is no "skip" and no "assume": an unreadable pin is
a FAIL, not a pass.

Sources of truth (never hardcoded — that is the whole point of the check):
  - python major.minor          <- .python-version
  - pytest package version      <- requirements.txt pin  vs installed package
  - playwright package version  <- requirements.txt pin  vs installed package
  - expected browser revision   <- the INSTALLED playwright wheel's
                                    driver/package/browsers.json (chromium
                                    revision) vs the chromium build present on
                                    disk under PLAYWRIGHT_BROWSERS_PATH

This is a lane guard: in the hermetic cloud lane the interpreter is 3.11 and
playwright is 1.56.0 (browser 1194), so python and playwright will FAIL here on
purpose while the browser check still PASSes (installed wheel 1.56.0 declares
1194 and the baked browser is 1194). In the pinned container (3.12,
playwright 1.61.0, browser 1228) all four PASS.
"""
from __future__ import annotations

import json
import os
import re
import sys
from importlib import metadata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = REPO_ROOT / "requirements.txt"
PYTHON_VERSION_FILE = REPO_ROOT / ".python-version"


class CheckError(Exception):
    """A pin source could not be read — the check fails closed."""


def _requirement_pin(package: str) -> str:
    """Read the exact `<package>==<version>` pin from requirements.txt.

    Matches the package name exactly so `pytest` never picks up `pytest-xdist`
    and `playwright` never picks up `pytest-playwright`.
    """
    if not REQUIREMENTS.is_file():
        raise CheckError(f"requirements.txt not found at {REQUIREMENTS}")
    pattern = re.compile(rf"^{re.escape(package)}==(\S+)\s*$")
    for line in REQUIREMENTS.read_text().splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group(1)
    raise CheckError(f"no `{package}==` pin in requirements.txt")


def _installed_version(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError as exc:
        raise CheckError(f"{package} is not installed") from exc


def check_python() -> tuple[bool, str]:
    if not PYTHON_VERSION_FILE.is_file():
        raise CheckError(".python-version not found")
    expected = PYTHON_VERSION_FILE.read_text().strip()
    actual = f"{sys.version_info.major}.{sys.version_info.minor}"
    return actual == expected, f"expected {expected}, running {actual}"


def check_pytest() -> tuple[bool, str]:
    expected = _requirement_pin("pytest")
    actual = _installed_version("pytest")
    return actual == expected, f"requirements pin {expected}, installed {actual}"


def check_playwright_package() -> tuple[bool, str]:
    expected = _requirement_pin("playwright")
    actual = _installed_version("playwright")
    return actual == expected, f"requirements pin {expected}, installed {actual}"


def _expected_browser_revision() -> str:
    """Chromium revision declared by the INSTALLED playwright wheel.

    Read from the wheel's own browsers.json so the expectation tracks whatever
    playwright is actually installed — never a hardcoded number.
    """
    import playwright  # local import: absence is a FAIL, handled by caller

    browsers_json = (
        Path(playwright.__file__).resolve().parent
        / "driver"
        / "package"
        / "browsers.json"
    )
    if not browsers_json.is_file():
        raise CheckError(f"browsers.json not found in playwright wheel ({browsers_json})")
    data = json.loads(browsers_json.read_text())
    for browser in data.get("browsers", []):
        if browser.get("name") == "chromium":
            revision = browser.get("revision")
            if not revision:
                raise CheckError("chromium entry in browsers.json has no revision")
            return str(revision)
    raise CheckError("no chromium entry in playwright browsers.json")


def _installed_browser_revision() -> str:
    """Chromium build present on disk under PLAYWRIGHT_BROWSERS_PATH."""
    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if not browsers_path:
        raise CheckError("PLAYWRIGHT_BROWSERS_PATH is not set")
    root = Path(browsers_path)
    if not root.is_dir():
        raise CheckError(f"PLAYWRIGHT_BROWSERS_PATH is not a directory ({root})")
    # Directories look like `chromium-<rev>`; exclude `chromium_headless_shell-*`.
    revisions = sorted(
        {
            match.group(1)
            for entry in root.iterdir()
            if (match := re.fullmatch(r"chromium-(\d+)", entry.name))
        }
    )
    if not revisions:
        raise CheckError(f"no chromium-<rev> build found under {root}")
    if len(revisions) > 1:
        raise CheckError(f"multiple chromium builds on disk: {revisions}")
    return revisions[0]


def check_browser_revision() -> tuple[bool, str]:
    try:
        import playwright  # noqa: F401
    except ImportError as exc:
        raise CheckError("playwright is not installed") from exc
    expected = _expected_browser_revision()
    actual = _installed_browser_revision()
    return actual == expected, f"wheel wants chromium {expected}, on disk {actual}"


CHECKS = [
    ("python", check_python),
    ("pytest", check_pytest),
    ("playwright-package", check_playwright_package),
    ("browser-revision", check_browser_revision),
]


def main() -> int:
    all_ok = True
    for name, check in CHECKS:
        try:
            ok, detail = check()
        except CheckError as exc:
            ok, detail = False, str(exc)
        status = "PASS" if ok else "FAIL"
        print(f"{status} {name}: {detail}")
        all_ok = all_ok and ok
    print("RESULT: " + ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
