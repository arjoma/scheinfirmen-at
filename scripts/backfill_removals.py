# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Rebuild data/scheinfirmen-entfernt.jsonl from the git history.

One-off maintenance script: walks every committed version of
data/scheinfirmen.jsonl (oldest first), diffs consecutive versions with the
same logic as the nightly pipeline, and writes all removals with the date
of the version in which they disappeared.

Usage (needs full history, e.g. after ``git fetch --unshallow``):

    uv run python scripts/backfill_removals.py [REV]   # default REV: HEAD
"""

import json
import subprocess
import sys
from pathlib import Path

from scheinfirmen_at.fields import FIELD_NAMES
from scheinfirmen_at.history import REMOVALS_FILENAME, Record, append_removals, diff_records

DATA_FILE = "data/scheinfirmen.jsonl"

# Field names used by the very first versions of the JSONL output.
_LEGACY_NAMES = {
    "veroeffentlichung": "veroeffentlicht",
    "firmenbuch_nr": "fbnr",
    "uid_nr": "uid",
    "kennziffer_ur": "kennziffer",
}


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8")


def _load_version(rev: str) -> tuple[str, list[Record]]:
    stand = ""
    records: list[Record] = []
    for line in _git("show", f"{rev}:{DATA_FILE}").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if "_metadata" in obj:
            stand = obj["_metadata"].get("stand", "")
            continue
        obj = {_LEGACY_NAMES.get(k, k): v for k, v in obj.items()}
        records.append({name: obj.get(name) for name in FIELD_NAMES})
    return stand, records


def main() -> None:
    head = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    revs = _git("log", "--format=%H", "--reverse", head, "--", DATA_FILE).split()
    out = Path("data") / REMOVALS_FILENAME
    out.unlink(missing_ok=True)

    previous: list[Record] | None = None
    total = 0
    for rev in revs:
        try:
            stand, records = _load_version(rev)
        except subprocess.CalledProcessError:
            continue  # file deleted in this revision
        if previous is not None:
            diff = diff_records(previous, records)
            append_removals(out, diff.removed, stand[:10])
            total += len(diff.removed)
            for old, new in diff.changed:
                print(f"{stand[:10]} changed: {old['name']!r} -> {new['name']!r}")
        previous = records
    print(f"{total} removal(s) written to {out}")


if __name__ == "__main__":
    main()
