#!/usr/bin/env python3
"""contracts-delta.py — the EM's contracts context, the milestone slice (D-120).

contracts.json accumulates every milestone's routes, schemas, and errors.
The EM plans deltas against the current ERD-DELTA.md (authoritative, D-107);
it needs contract bodies for the files this milestone touches, not the full
accumulated load. Entries pin their owning file (schema "file" field, D-120):
this generator ships pinned entries whose file is in this milestone's
contracts.files inventory, drops pins pointing outside the inventory, and
always ships unpinned entries — a missing pin is a conservative carry, never
a silent drop. entry_points are self-pinning: "src.module:app" derives to
src/module.py, kept only when that module is in the inventory.

While NO entry carries a file pin (the backfill is TPM-seat and pending), the
output is byte-identical to the input — the slice activates inertly the
moment pins land.

Usage: contracts-delta.py [path-to-contracts.json] > contracts-delta.json
Exit 0 with the slice; exit 1 when the contracts file is missing, unreadable,
or not the expected shape (the shell falls back to the full contracts file).
"""
import json
import sys
from pathlib import Path

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("scripts/.approved/contracts.json")
if not path.is_file():
    sys.exit(1)
raw = path.read_text()
try:
    contracts = json.loads(raw)
except (OSError, json.JSONDecodeError):
    sys.exit(1)
if not isinstance(contracts, dict):
    sys.exit(1)

PINNED_KEYS = ("routes", "schemas", "errors")


def entry_pin(entry):
    return entry.get("file") if isinstance(entry, dict) else ""


def entry_point_file(entry_point):
    if not isinstance(entry_point, str) or not entry_point.startswith("src."):
        return ""
    module = entry_point.split(":", 1)[0]
    return module.replace(".", "/") + ".py"


any_pinned = any(
    entry_pin(e) for key in PINNED_KEYS for e in contracts.get(key, [])
)
if not any_pinned:
    sys.stdout.write(raw)
    sys.exit(0)

files = set(contracts.get("files", []))
sliced = dict(contracts)
for key in PINNED_KEYS:
    kept = []
    for entry in contracts.get(key, []):
        pin = entry_pin(entry)
        if not pin or pin in files:
            kept.append(entry)
    sliced[key] = kept

kept_points = []
for entry_point in contracts.get("entry_points", []):
    derived = entry_point_file(entry_point)
    if not derived or derived in files:
        kept_points.append(entry_point)
sliced["entry_points"] = kept_points

sys.stdout.write(json.dumps(sliced, indent=2) + "\n")
