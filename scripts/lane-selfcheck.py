#!/usr/bin/env python3
"""lane-selfcheck.py — fail-closed environment drift tripwire for the browser lane.

Run at lane session start (after `pip install -r requirements.txt`). It asserts
that the container the lane was stamped from actually matches the repo's own
pins, and REFUSES to start (exit 1) on any mismatch — so a silent downgrade
(the chromium 1194-vs-1228 incident) can never go unnoticed mid-batch again.

Every expectation is READ from a pin in the repo, never hardcoded here, so a
version bump needs no edit to this file:

  * Python minor version  <- .github/workflows/ci.yml  (`python-version: "X.Y"`)
  * Chromium build         <- the INSTALLED playwright's driver browsers.json
                              (requirements.txt pins the playwright version;
                              that version determines the chromium revision)

Checks are independent and all run; each prints PASS/FAIL. Exit 0 only when
every check passes. Options (for testing / non-default layouts):
  --ci-config PATH        ci.yml to read the python pin from
  --browsers-path PATH    playwright browsers dir (default: $PLAYWRIGHT_BROWSERS_PATH
                          or ~/.cache/ms-playwright)
"""

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CI_CONFIG = REPO / ".github" / "workflows" / "ci.yml"


def _fail(check, msg, fix):
    print(f"  FAIL  {check}: {msg}")
    for line in fix.splitlines():
        print(f"        {line}")
    return False


def _ok(check, msg):
    print(f"  PASS  {check}: {msg}")
    return True


def check_python(ci_config: Path) -> bool:
    """Container python minor == the version CI pins."""
    try:
        text = ci_config.read_text()
    except OSError:
        return _fail("python", f"cannot read {ci_config}",
                     "point --ci-config at the workflow that pins python-version")
    pins = sorted(set(re.findall(r'python-version:\s*"?(\d+\.\d+)"?', text)))
    if not pins:
        return _fail("python", f"no `python-version:` pin found in {ci_config}",
                     "add a python-version pin to CI, or --ci-config the right file")
    if len(pins) > 1:
        return _fail("python", f"CI pins inconsistent python versions: {pins}",
                     "make every job's python-version agree before trusting a lane")
    pin = pins[0]
    actual = f"{sys.version_info.major}.{sys.version_info.minor}"
    if actual != pin:
        return _fail("python", f"container python {actual} != pinned {pin}",
                     "refresh the lane image to python "
                     f"{pin}, or align CI's pin to the image on purpose")
    return _ok("python", f"{actual} matches the CI pin")


def _expected_chromium_revision():
    spec = importlib.util.find_spec("playwright")
    if spec is None or not spec.submodule_search_locations:
        return None, "playwright is not installed (run: pip install -r requirements.txt)"
    base = Path(list(spec.submodule_search_locations)[0])
    for cand in (base / "driver" / "package" / "browsers.json",
                 base / "driver" / "browsers.json"):
        if cand.exists():
            data = json.loads(cand.read_text())
            for b in data.get("browsers", []):
                if b.get("name") == "chromium":
                    return b.get("revision"), None
            return None, f"no chromium entry in {cand}"
    return None, "playwright browsers.json not found under the installed package"


def check_browser(browsers_path: Path) -> bool:
    """A chromium-<rev> matching the installed playwright's pin is present."""
    rev, err = _expected_chromium_revision()
    if err:
        return _fail("browser", err,
                     "the setup script must `pip install -r requirements.txt` before this check")
    present = sorted(p.name for p in browsers_path.glob("chromium-*") if p.is_dir())
    if (browsers_path / f"chromium-{rev}").is_dir():
        return _ok("browser", f"chromium-{rev} present (matches the playwright pin)")
    return _fail(
        "browser",
        f"pinned chromium-{rev} absent; present: {present or 'none'} (path {browsers_path})",
        "add 'cdn.playwright.dev' to this environment's network allowlist so\n"
        "`playwright install chromium` can fetch the pinned build, OR bake\n"
        f"chromium-{rev} into the base image. Do NOT downgrade playwright to\n"
        "match the image silently — that is the drift this tripwire exists to catch.")


def main(argv):
    ap = argparse.ArgumentParser(description="browser-lane drift tripwire")
    ap.add_argument("--ci-config", type=Path, default=CI_CONFIG)
    ap.add_argument("--browsers-path", type=Path,
                    default=Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
                                 or (Path.home() / ".cache" / "ms-playwright")))
    args = ap.parse_args(argv)

    print("lane-selfcheck: asserting the container matches the repo's pins")
    results = [
        check_python(args.ci_config),
        check_browser(args.browsers_path),
    ]
    if all(results):
        print("lane-selfcheck: OK — environment matches every pin.")
        return 0
    print("lane-selfcheck: FAIL — environment drift; refusing to start the lane.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
