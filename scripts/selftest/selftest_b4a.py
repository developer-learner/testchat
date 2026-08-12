"""Selftests for the B4a pack-only ERD-DELTA strip (tpm-pack.sh).

The TPM chat bundle exists to START intake of the NEXT feature. The current
milestone's execution-side decomposition — the verbatim coder briefs, the DAG,
and the task scheduling — is dead weight there (~8 KB of the delta) and the TPM
re-authors all of it when it writes the next delta. tpm-pack.sh therefore ships
a stripped delta view: coder briefs, `A` depends on `B` lines, and any
`Task order:` chain removed; ACs, supersessions, changed files, and the
test-to-file mapping kept.

HARD CONSTRAINT: this is pack-only. The execution lane (orchestrate.sh plan
assembly) must keep reading the FULL ERD-DELTA.md on disk — the strip lives
entirely inside tpm-pack.sh and never writes back.

This file is deliberately named selftest_b4a.py (not selftest_gates.py, which
belongs to another lane) and carries only the strip's pins.
"""

import shutil
import subprocess
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent


DELTA_WITH_DECOMPOSITION = """\
# ERD-DELTA M99

## Changed acceptance criteria

* **AC-99:** change app.js

## Superseded acceptance criteria

None.

## Changed files

* `src/static/app.js`

## Test-to-file mapping

* `tests/test_ui.py::test_widget` -> `src/static/app.js`

## Coder briefs (verbatim)

### T1 — src/static/app.js (feature)

Add the widget. Keep `renderThread`. Self-verify: the widget appears.
SENTINEL_BRIEF_BODY that must never reach the TPM bundle.

## Task DAG

`src/static/app.js` depends on `src/api/chat.py`
Task order: T1 (app) -> T2 (api)
"""


def _build_repo(tmp_path):
    """A controlled repo tree that runs the REAL tpm-pack.sh against a spec
    whose ERD-DELTA carries coder briefs + DAG + task scheduling."""
    repo = tmp_path / "repo"
    (repo / "scripts" / ".approved").mkdir(parents=True)
    (repo / "scripts" / "schemas").mkdir(parents=True)
    (repo / "docs").mkdir(parents=True)
    for name in ("tpm-pack.sh", "spec_artifacts.py", "standing-summary.py"):
        shutil.copy(SCRIPTS / name, repo / "scripts" / name)
    approved = repo / "scripts" / ".approved"
    (approved / "VERSION").write_text("99\n")
    (approved / "PRD.md").write_text(
        "# PRD\n\n## What fixture is\n\n"
        "Fixture is a local product with one current milestone, described in "
        "enough standing prose that the generated capsule is smaller than its "
        "source artifact.\n\n## Acceptance criteria\n\n"
        "* **AC-99:** change app.js\n")
    (approved / "ERD.md").write_text(
        "## Rule\n\nkeep\n\n## As-built architecture — front end\n\n"
        "* **`src/static/app.js`** — accumulated milestone detail that runs on "
        "well past the truncation threshold with no informational value left.\n")
    (approved / "ERD-DELTA.md").write_text(DELTA_WITH_DECOMPOSITION)
    (approved / "contracts.json").write_text(
        '{"files": ["src/static/app.js"], "smoke_checks": [], '
        '"test_mapping": {}}\n')
    (repo / "docs" / "TPM-ROLE.md").write_text("# TPM role\n")
    (repo / "scripts" / "schemas" / "contracts.schema.json").write_text("{}\n")
    return repo


def _delta_region(bundle: str) -> str:
    """The ERD-DELTA CONTEXT FILE block of the packed bundle."""
    marker = "=== CONTEXT FILE: scripts/.approved/ERD-DELTA.md ==="
    start = bundle.index(marker)
    end = bundle.index("=== END CONTEXT FILE ===", start)
    return bundle[start:end]


def test_tpm_pack_strips_decomposition_but_keeps_spec_slice(tmp_path):
    repo = _build_repo(tmp_path)
    r = subprocess.run(
        ["bash", "scripts/tpm-pack.sh"], cwd=str(repo),
        capture_output=True, text=True,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    region = _delta_region(r.stdout)

    # kept: ACs, supersessions, changed files, test-to-file mapping
    assert "## Changed acceptance criteria" in region
    assert "AC-99" in region
    assert "## Superseded acceptance criteria" in region
    assert "## Changed files" in region
    assert "## Test-to-file mapping" in region
    assert "`tests/test_ui.py::test_widget` -> `src/static/app.js`" in region

    # stripped: coder briefs section (heading + body), DAG lines, Task order
    assert "Coder briefs (verbatim)" not in region
    assert "SENTINEL_BRIEF_BODY" not in region
    assert "depends on" not in region
    assert "Task order:" not in region
    # the emptied dedicated DAG heading must not survive as an orphan title
    assert "## Task DAG" not in region


def test_tpm_pack_strip_is_pack_only_orchestrate_reads_full_delta():
    """HARD CONSTRAINT: the strip is confined to tpm-pack.sh. The execution
    lane must not gain the strip — orchestrate.sh keeps assembling the full
    ERD-DELTA.md, and only tpm-pack.sh defines generate_delta_slice."""
    orch = (SCRIPTS / "orchestrate.sh").read_text()
    assert "generate_delta_slice" not in orch
    pack = (SCRIPTS / "tpm-pack.sh").read_text()
    assert "generate_delta_slice" in pack
