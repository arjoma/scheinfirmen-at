# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Tests for the snapshot diff (history) module."""

import json
from pathlib import Path

from scheinfirmen_at.history import (
    Record,
    Snapshot,
    append_removals,
    diff_records,
    load_removals,
    load_snapshot,
    resolve_geaendert,
)


def _rec(name: str, **kw: str | None) -> Record:
    base: Record = {
        "name": name, "anschrift": "1010 Wien", "veroeffentlicht": "2024-01-01",
        "rechtskraeftig": "2023-12-01", "seit": None, "geburtsdatum": None,
        "fbnr": None, "uid": None, "kennziffer": None,
    }
    base.update(kw)
    return base


class TestDiffRecords:
    def test_identical(self) -> None:
        recs = [_rec("A"), _rec("B")]
        assert diff_records(recs, list(reversed(recs))).empty

    def test_added_and_removed(self) -> None:
        old = [_rec("A", anschrift="Graz"), _rec("B", anschrift="Linz")]
        new = [_rec("A", anschrift="Graz"), _rec("C", anschrift="Salzburg")]
        diff = diff_records(old, new)
        assert [r["name"] for r in diff.added] == ["C"]
        assert [r["name"] for r in diff.removed] == ["B"]
        assert diff.changed == []

    def test_name_correction_is_a_change_not_a_removal(self) -> None:
        # Real case: an encoding fix of the company name.
        old = [_rec("Dani¿s Clean Service e.U.", uid="ATU11111111")]
        new = [_rec("Dani€s Clean Service e.U.", uid="ATU11111111")]
        diff = diff_records(old, new)
        assert diff.removed == [] and diff.added == []
        assert diff.changed == [(old[0], new[0])]

    def test_corrected_rechtskraft_is_a_change(self) -> None:
        # Real case (TRENDOV Dragi, 2026-08-12): Rechtskraft and Zeitpunkt corrected.
        old = [_rec("TRENDOV Dragi", rechtskraeftig="2025-05-15", seit="2025-05-15")]
        new = [_rec("TRENDOV Dragi", rechtskraeftig="2026-03-05", seit="2025-05-15")]
        diff = diff_records(old, new)
        assert diff.removed == [] and diff.added == []
        assert len(diff.changed) == 1

    def test_name_completion_is_a_change(self) -> None:
        # Real case: "DJORDJEVIC" -> "DJORDJEVIC Anastasia"
        old = [_rec("DJORDJEVIC", anschrift="1100 Wien, Gasse 1")]
        new = [_rec("DJORDJEVIC Anastasia", anschrift="1100 Wien, Gasse 1")]
        assert len(diff_records(old, new).changed) == 1

    def test_same_name_different_person_is_not_a_change(self) -> None:
        old = [_rec("HORVATH Daniel", geburtsdatum="1985-10-21", anschrift="Graz")]
        new = [_rec("HORVATH Daniel", geburtsdatum="1992-03-31", anschrift="Linz")]
        diff = diff_records(old, new)
        assert len(diff.removed) == 1 and len(diff.added) == 1

    def test_unrelated_records_are_not_matched(self) -> None:
        old = [_rec("A", anschrift="Graz")]
        new = [_rec("B", anschrift="Linz", veroeffentlicht="2025-05-05")]
        diff = diff_records(old, new)
        assert len(diff.removed) == 1 and len(diff.added) == 1

    def test_duplicate_records_counted(self) -> None:
        old = [_rec("A"), _rec("A")]
        new = [_rec("A")]
        diff = diff_records(old, new)
        assert len(diff.removed) == 1


class TestResolveGeaendert:
    def test_no_previous(self) -> None:
        assert resolve_geaendert(None, [_rec("A")], "2026-09-27T01:00:00") == "2026-09-27T01:00:00"

    def test_changed_data_uses_stand(self) -> None:
        prev = Snapshot([_rec("A")], stand="2026-09-01T09:00:00", geaendert="2026-09-01T09:00:00")
        assert resolve_geaendert(prev, [_rec("B")], "2026-09-27T01:00:00") == "2026-09-27T01:00:00"

    def test_unchanged_keeps_previous(self) -> None:
        prev = Snapshot([_rec("A")], stand="2026-09-26T09:00:00", geaendert="2026-09-01T09:00:00")
        assert resolve_geaendert(prev, [_rec("A")], "2026-09-27T01:00:00") == "2026-09-01T09:00:00"

    def test_unchanged_legacy_file_falls_back_to_previous_stand(self) -> None:
        prev = Snapshot([_rec("A")], stand="2026-09-25T09:43:28")
        assert resolve_geaendert(prev, [_rec("A")], "2026-09-27T01:00:00") == "2026-09-25T09:43:28"


class TestSnapshotIO:
    def test_missing(self, tmp_path: Path) -> None:
        assert load_snapshot(tmp_path / "nope.jsonl") is None

    def test_corrupt_is_ignored(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.jsonl"
        p.write_text("{not json\n", encoding="utf-8")
        assert load_snapshot(p) is None

    def test_roundtrip(self, tmp_path: Path) -> None:
        p = tmp_path / "sf.jsonl"
        meta = {"$schema": "x", "_metadata": {"stand": "S", "geaendert": "G"}}
        p.write_text(json.dumps(meta) + "\n" + json.dumps(_rec("A")) + "\n", encoding="utf-8")
        snap = load_snapshot(p)
        assert snap is not None
        assert (snap.stand, snap.geaendert, snap.records) == ("S", "G", [_rec("A")])

    def test_removals_append_and_load(self, tmp_path: Path) -> None:
        p = tmp_path / "entfernt.jsonl"
        append_removals(p, [_rec("A")], "2026-09-01")
        append_removals(p, [], "2026-09-02")  # no-op
        append_removals(p, [_rec("B")], "2026-09-03")
        rows = load_removals(p)
        got = [(r["name"], r["entfernt"]) for r in rows]
        assert got == [("A", "2026-09-01"), ("B", "2026-09-03")]
        assert load_removals(tmp_path / "missing.jsonl") == []
