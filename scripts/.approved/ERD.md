ERD — testchat M24: History Never Dies (erd_version 45)

What changes v44 -> v45

Four files change, each a small set of anchored edits. Four frontend
files remain no_edit_files (D-65). The DAG below is the required order.
No new stack imports; no new externals. The quarantine flag is
file-existence based (any `<data>.corrupt-*` beside the data file), so it
is idempotent across concurrent GETs and survives restarts until a human
removes or restores the quarantined file — that persistence is the
feature, not a bug.

File inventory (M24 build) — DAG order

1. src/services/storage.py — EDIT (two anchored edits, one task).

   Edit A — quarantine on corrupt load (AC-78). The load_snapshot except
   block currently reads exactly:
   ```
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Corrupt snapshot at %s: %s", path, exc)
        return []
   ```
   Replace it with:
   ```
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
   ```
   This needs `import time` added to the import block (stdlib, after
   `import tempfile`).

   Edit B — .bak rotation (AC-82) + quarantine listing helper (AC-79).
   The save_snapshot tail currently reads exactly:
   ```
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
   ```
   Replace it with:
   ```
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
   ```
   (Both renames are same-directory os.replace calls — O(1) metadata
   operations at any file size; the rotation must sit ABOVE the final
   os.replace so a crash between the two renames still leaves every byte
   under some name.)

2. src/api/threads.py — EDIT (two related edits, one task; depends on 1).
   The storage import line currently reads exactly:
   `from src.services.storage import load_snapshot, save_snapshot`
   Replace ONLY that line with:
   `from src.services.storage import load_snapshot, quarantine_files, save_snapshot`
   The GET handler's return currently reads exactly:
   `    return {"threads": load_snapshot()}`
   Replace ONLY that line with:
   `    return {"threads": load_snapshot(), "quarantined": bool(quarantine_files())}`
   Nothing else in the file changes (AC-79).

3. src/static/index.html — EDIT (one edit). The status strip currently
   contains exactly:
   `        <span id="status-save" data-testid="save-status"></span>`
   Insert directly BELOW that line:
   `        <span id="status-history" data-testid="history-status"></span>`
   Nothing else in the file changes.

4. src/static/threads.js — EDIT (two anchored edits) — the DAG's FINAL
   task: depends_on MUST list EVERY other task id (1, 2, 3, and all four
   no_edit tasks). D-64: browser tests are accepted only downstream of
   the whole inventory.

   Edit A — lock the bubble meta span (AC-83's observable surface). The
   addBubbleChrome function currently contains exactly:
   ```
      var meta = document.createElement('span');
      meta.className = 'bubble-meta';
   ```
   Replace it with:
   ```
      var meta = document.createElement('span');
      meta.className = 'bubble-meta';
      meta.setAttribute('data-testid', 'msg-meta');
   ```

   Edit B — history-status indicator (AC-80/81). The file ends exactly:
   ```
  };
})();
   ```
   Replace that ending with:
   ```
  };
})();

// AC-80/81: load-path failure visibility — ask the backend whether the
// saved history was quarantined at load. Runs at script eval (scripts sit
// at the end of <body>, DOM is parsed); file-existence flag makes the
// race with app.js's own hydrate GET harmless.
fetch('/api/v1/threads')
  .then(function (res) { return res.json(); })
  .then(function (data) {
    document.getElementById('status-history').textContent =
      data.quarantined ? 'history unreadable (backup kept)' : '';
  })
  .catch(function () { /* best-effort indicator: an unreachable backend
    already surfaces through the app's own load path */ });
   ```
   (Note: the fetch is OUTSIDE the IIFE — the el() helper is not in scope
   there; use document.getElementById as shown.)

no_edit_files (D-65 — never sent to the coder, acceptance still runs):
src/static/app.js, src/static/markdown.js, src/static/rain.js,
src/static/style.css

Contract ids per task: contracts = [] — an EMPTY list for ALL tasks.
NEVER invent module-style ids.

Oracle Mapping — seven NEW node-ids this milestone:
- tests/test_storage_service.py::test_corrupt_snapshot_is_quarantined
  -> maps to the src/services/storage.py task.
- tests/test_storage_service.py::test_save_rotates_previous_snapshot_to_bak
  -> maps to the src/services/storage.py task.
- tests/test_storage_service.py::test_first_save_creates_no_bak
  -> maps to the src/services/storage.py task.
- tests/test_threads_api.py::test_get_reports_quarantine_after_corrupt_snapshot
  -> maps to the src/api/threads.py task.
- tests/test_ui.py::test_history_quarantine_indicator_shows
  -> maps to the src/static/threads.js task (the DAG's final task).
- tests/test_ui.py::test_history_status_empty_when_healthy
  -> maps to the src/static/threads.js task.
- tests/test_ui.py::test_bubble_meta_includes_date_for_past_messages
  -> maps to the src/static/threads.js task (ratifies behavior already
  present in the tree via the committed 2026-07-15 hover-timestamp fix;
  the task's Edit A provides the msg-meta testid the test observes).
Transcribe the dependency edges literally; do not infer or omit any.
ALL other node-ids are carried forward — do NOT map them (the shell
auto-assigns regression, D-57).

Test dependencies: the browser tests observe history-status and msg-meta
(new testids, locked in contracts.ui) and PUT/GET /api/v1/threads
(already locked routes). Four frozen tests and conftest.py are amended
in this same freeze (exact-shape asserts extended for the quarantined
field and the .bak artifact; fixture sweeps quarantine files between
tests). No new externals; no new stack imports.
