# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Compare a new download with the previous output (snapshot diff).

The BMF "Stand" footer is generated per request, so it says nothing about
when the list last changed. Comparing against the previous JSONL output
gives us three things:

- the time the record data actually last changed (``geaendert``),
- a sanity guard against truncated downloads (too many removals),
- a log of removed entries (``scheinfirmen-entfernt.jsonl``).
"""

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from scheinfirmen_at.fields import FIELD_NAMES

logger = logging.getLogger("scheinfirmen_at")

Record = dict[str, str | None]

REMOVALS_FILENAME = "scheinfirmen-entfernt.jsonl"


@dataclass
class Snapshot:
    """Records and metadata of a previously written JSONL file."""

    records: list[Record]
    stand: str | None = None
    geaendert: str | None = None


@dataclass
class RecordDiff:
    """Difference between two record lists."""

    added: list[Record] = field(default_factory=list)
    removed: list[Record] = field(default_factory=list)
    changed: list[tuple[Record, Record]] = field(default_factory=list)  # (old, new)

    @property
    def empty(self) -> bool:
        return not (self.added or self.removed or self.changed)


def load_snapshot(jsonl_path: Path) -> Snapshot | None:
    """Load a previous JSONL output. Returns None if missing or unreadable."""
    if not jsonl_path.exists():
        return None
    records: list[Record] = []
    snap = Snapshot(records=records)
    try:
        with jsonl_path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                if "_metadata" in obj:
                    snap.stand = obj["_metadata"].get("stand")
                    snap.geaendert = obj["_metadata"].get("geaendert")
                    continue
                records.append({name: obj.get(name) for name in FIELD_NAMES})
    except (OSError, ValueError, AttributeError) as exc:
        logger.warning("Cannot read previous output %s (ignored): %s", jsonl_path, exc)
        return None
    return snap


def _full_key(rec: Record) -> tuple[str | None, ...]:
    return tuple(rec.get(name) for name in FIELD_NAMES)


def _same_entity(old: Record, new: Record) -> bool:
    """Heuristic: is ``new`` an edited version of ``old``?

    Edits seen in practice are name corrections (e.g. an encoding fix) or
    corrected identifiers. Publication and legal-force dates never change,
    so they must match, plus at least one identifying field.
    """
    if (old["veroeffentlicht"], old["rechtskraeftig"]) != (
        new["veroeffentlicht"],
        new["rechtskraeftig"],
    ):
        return False
    for name in ("name", "anschrift", "uid", "fbnr", "kennziffer"):
        if old[name] is not None and old[name] == new[name]:
            return True
    return False


def diff_records(old: list[Record], new: list[Record]) -> RecordDiff:
    """Compute added, removed and changed records (order-insensitive)."""
    old_counts = Counter(_full_key(r) for r in old)
    new_counts = Counter(_full_key(r) for r in new)
    gone_keys = old_counts - new_counts
    fresh_keys = new_counts - old_counts

    gone: list[Record] = []
    for rec in old:
        k = _full_key(rec)
        if gone_keys[k] > 0:
            gone_keys[k] -= 1
            gone.append(rec)
    fresh: list[Record] = []
    for rec in new:
        k = _full_key(rec)
        if fresh_keys[k] > 0:
            fresh_keys[k] -= 1
            fresh.append(rec)

    diff = RecordDiff()
    for old_rec in gone:
        match = next((n for n in fresh if _same_entity(old_rec, n)), None)
        if match is None:
            diff.removed.append(old_rec)
        else:
            fresh.remove(match)
            diff.changed.append((old_rec, match))
    diff.added = fresh
    return diff


def resolve_geaendert(
    previous: Snapshot | None, new_records: list[Record], stand: str
) -> str:
    """Timestamp of the last change of the record data.

    Unchanged data keeps the previous value. Older outputs without a
    ``geaendert`` field fall back to their ``stand`` — the nightly workflow
    only commits on data changes, so that was the time of the last change.
    """
    if previous is None or previous.records != new_records:
        return stand
    return previous.geaendert or previous.stand or stand


def append_removals(path: Path, removed: list[Record], date: str) -> None:
    """Append removed records, tagged with the removal date, to a JSONL log."""
    if not removed:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for rec in removed:
            f.write(json.dumps({**rec, "entfernt": date}, ensure_ascii=False) + "\n")


def load_removals(path: Path) -> list[Record]:
    """Read the removals log (empty list if missing)."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
