# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Tests for the stats module."""

import json
import subprocess
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from scheinfirmen_at.stats import (
    RecordInfo,
    Snapshot,
    _parse_jsonl_names,
    compute_weekly_changes,
    find_recent_additions,
    generate_stats,
    get_data_history,
    render_stats_md,
)


def _make_snapshot(
    d: date, names: list[str], commit: str = "abcd1234"
) -> Snapshot:
    """Helper to build a Snapshot from a list of names."""
    records = {
        n: RecordInfo(name=n, uid=f"ATU{i:08d}", anschrift=f"1010 Wien, Str {i}")
        for i, n in enumerate(names)
    }
    return Snapshot(
        date=d,
        commit=commit,
        total=len(names),
        names=set(names),
        records_by_name=records,
    )


class TestComputeWeeklyChanges:
    def test_empty(self) -> None:
        assert compute_weekly_changes([]) == []

    def test_single_snapshot(self) -> None:
        snap = _make_snapshot(date(2026, 2, 10), ["A", "B", "C"])
        rows = compute_weekly_changes([snap])
        assert len(rows) == 1
        assert rows[0].additions == 3
        assert rows[0].removals == 0
        assert rows[0].total == 3

    def test_two_snapshots_same_week(self) -> None:
        s1 = _make_snapshot(date(2026, 2, 10), ["A", "B"])
        s2 = _make_snapshot(date(2026, 2, 12), ["A", "B", "C"])
        rows = compute_weekly_changes([s1, s2])
        # Same ISO week → merged into one row
        assert len(rows) == 1
        assert rows[0].total == 3
        assert rows[0].additions == 2 + 1  # initial 2 + 1 added

    def test_two_snapshots_different_weeks(self) -> None:
        s1 = _make_snapshot(date(2026, 2, 9), ["A", "B"])  # W07
        s2 = _make_snapshot(date(2026, 2, 16), ["A", "C", "D"])  # W08
        rows = compute_weekly_changes([s1, s2])
        assert len(rows) == 2
        assert rows[0].week_label == "2026-W07"
        assert rows[0].total == 2
        assert rows[1].week_label == "2026-W08"
        assert rows[1].additions == 2  # C, D added
        assert rows[1].removals == 1  # B removed
        assert rows[1].total == 3

    def test_three_weeks(self) -> None:
        s1 = _make_snapshot(date(2026, 1, 5), ["A", "B"])
        s2 = _make_snapshot(date(2026, 1, 12), ["A", "B", "C"])
        s3 = _make_snapshot(date(2026, 1, 19), ["B", "C"])
        rows = compute_weekly_changes([s1, s2, s3])
        assert len(rows) == 3
        assert rows[1].additions == 1  # C
        assert rows[1].removals == 0
        assert rows[2].additions == 0
        assert rows[2].removals == 1  # A removed


class TestFindRecentAdditions:
    def test_no_additions(self) -> None:
        s1 = _make_snapshot(date(2026, 1, 1), ["A", "B"])
        s2 = _make_snapshot(date(2026, 1, 15), ["A", "B"])
        assert find_recent_additions([s1, s2], days=30) == []

    def test_with_additions(self) -> None:
        s1 = _make_snapshot(date(2026, 1, 1), ["A", "B"])
        s2 = _make_snapshot(date(2026, 1, 15), ["A", "B", "C", "D"])
        result = find_recent_additions([s1, s2], days=30)
        names = [r.name for r in result]
        assert names == ["C", "D"]

    def test_all_within_window_uses_first_as_baseline(self) -> None:
        # Both snapshots within 30 days → use first as baseline
        s1 = _make_snapshot(date(2026, 2, 1), ["A", "B"])
        s2 = _make_snapshot(date(2026, 2, 10), ["A", "B", "C"])
        result = find_recent_additions([s1, s2], days=30)
        assert len(result) == 1
        assert result[0].name == "C"

    def test_single_snapshot(self) -> None:
        s1 = _make_snapshot(date(2026, 1, 1), ["A"])
        assert find_recent_additions([s1], days=30) == []

    def test_baseline_beyond_cutoff(self) -> None:
        s1 = _make_snapshot(date(2026, 1, 1), ["A", "B"])
        s2 = _make_snapshot(date(2026, 1, 20), ["A", "B", "C"])
        s3 = _make_snapshot(date(2026, 2, 15), ["A", "B", "C", "D"])
        # cutoff = Feb 15 - 30 = Jan 16; baseline = s1 (Jan 1)
        # Wait, s2 (Jan 20) is > cutoff (Jan 16), so baseline = s1
        result = find_recent_additions([s1, s2, s3], days=30)
        names = [r.name for r in result]
        assert names == ["C", "D"]


class TestRenderStatsMd:
    def test_contains_sections(self) -> None:
        s1 = _make_snapshot(date(2026, 1, 5), ["A", "B"])
        s2 = _make_snapshot(date(2026, 1, 12), ["A", "B", "C"])
        weekly = compute_weekly_changes([s1, s2])
        recent = [RecordInfo("C", "ATU123", "1010 Wien")]
        md = render_stats_md([s1, s2], weekly, recent, "2026-01-12", 3)

        assert "# Scheinfirmen Österreich — Statistik" in md
        assert "Neueste Scheinfirmen" in md
        assert "Wöchentliche Änderungen" in md
        assert "| C | ATU123 | 1010 Wien |" in md

    def test_mermaid_chart_with_two_weeks(self) -> None:
        s1 = _make_snapshot(date(2026, 1, 5), ["A", "B"])
        s2 = _make_snapshot(date(2026, 1, 12), ["A", "B", "C"])
        weekly = compute_weekly_changes([s1, s2])
        md = render_stats_md([s1, s2], weekly, [], "2026-01-12", 3)

        assert "```mermaid" in md
        assert "xychart-beta" in md
        assert "line [" in md

    def test_no_chart_with_single_week(self) -> None:
        s1 = _make_snapshot(date(2026, 1, 5), ["A"])
        weekly = compute_weekly_changes([s1])
        md = render_stats_md([s1], weekly, [], "2026-01-05", 1)

        assert "mermaid" not in md

    def test_no_recent_additions_message(self) -> None:
        s1 = _make_snapshot(date(2026, 1, 5), ["A"])
        weekly = compute_weekly_changes([s1])
        md = render_stats_md([s1], weekly, [], "2026-01-05", 1)

        assert "Keine neuen Einträge" in md


class TestParseJsonlNames:
    def test_basic(self) -> None:
        text = (
            '{"_metadata": {"stand": "2026-01-01"}}\n'
            '{"name": "Firma A", "uid": "ATU11111111", "anschrift": "Wien"}\n'
            '{"name": "Firma B", "uid": null, "anschrift": "Graz"}\n'
        )
        records, count = _parse_jsonl_names(text)
        assert count == 2
        assert "Firma A" in records
        assert "Firma B" in records
        assert records["Firma A"].uid == "ATU11111111"
        assert records["Firma B"].uid is None

    def test_empty(self) -> None:
        records, count = _parse_jsonl_names("")
        assert count == 0
        assert records == {}

    def test_metadata_only(self) -> None:
        text = '{"_metadata": {"stand": "2026-01-01"}}\n'
        records, count = _parse_jsonl_names(text)
        assert count == 0


class TestGetDataHistory:
    @patch("scheinfirmen_at.stats._git")
    def test_basic_history(self, mock_git: MagicMock) -> None:
        jsonl_v1 = (
            '{"_metadata": {"stand": "2026-01-01"}}\n'
            '{"name": "A", "uid": null, "anschrift": "Wien"}\n'
        )
        jsonl_v2 = (
            '{"_metadata": {"stand": "2026-01-08"}}\n'
            '{"name": "A", "uid": null, "anschrift": "Wien"}\n'
            '{"name": "B", "uid": null, "anschrift": "Graz"}\n'
        )
        mock_git.side_effect = [
            # git log output (newest first)
            "bbbb2222 2026-01-08T02:00:00+01:00\naaaa1111 2026-01-01T02:00:00+01:00\n",
            # git show for commit bbbb (newest)
            jsonl_v2,
            # git show for commit aaaa (oldest)
            jsonl_v1,
        ]

        repo = Path("/fake/repo")
        snapshots = get_data_history(repo / "data" / "sf.jsonl", repo)

        assert len(snapshots) == 2
        assert snapshots[0].total == 1  # oldest first
        assert snapshots[1].total == 2
        assert "B" in snapshots[1].names

    @patch("scheinfirmen_at.stats._git")
    def test_deduplicates_unchanged(self, mock_git: MagicMock) -> None:
        jsonl = (
            '{"_metadata": {"stand": "2026-01-01"}}\n'
            '{"name": "A", "uid": null, "anschrift": "Wien"}\n'
        )
        mock_git.side_effect = [
            "bbbb 2026-01-02T02:00:00+01:00\naaaa 2026-01-01T02:00:00+01:00\n",
            jsonl,  # same content
            jsonl,  # same content
        ]

        repo = Path("/fake/repo")
        snapshots = get_data_history(repo / "data" / "sf.jsonl", repo)
        # Both have identical name sets, so only first kept
        assert len(snapshots) == 1

    @patch("scheinfirmen_at.stats._git")
    def test_skips_failed_show(self, mock_git: MagicMock) -> None:
        mock_git.side_effect = [
            "aaaa 2026-01-01T02:00:00+01:00\n",
            subprocess.CalledProcessError(1, "git show"),
        ]
        repo = Path("/fake/repo")
        snapshots = get_data_history(repo / "data" / "sf.jsonl", repo)
        assert len(snapshots) == 0

    @patch("scheinfirmen_at.stats._git")
    def test_empty_log(self, mock_git: MagicMock) -> None:
        mock_git.return_value = ""
        repo = Path("/fake/repo")
        snapshots = get_data_history(repo / "data" / "sf.jsonl", repo)
        assert len(snapshots) == 0


class TestGenerateStats:
    @patch("scheinfirmen_at.stats.get_data_history")
    def test_writes_output(self, mock_history: MagicMock, tmp_path: Path) -> None:
        s1 = _make_snapshot(date(2026, 1, 5), ["A", "B"])
        s2 = _make_snapshot(date(2026, 1, 12), ["A", "B", "C"])
        mock_history.return_value = [s1, s2]

        jsonl_path = tmp_path / "scheinfirmen.jsonl"
        meta = {"_metadata": {"stand": "2026-01-12T02:00:00", "count": 3}}
        jsonl_path.write_text(
            json.dumps(meta) + "\n",
            encoding="utf-8",
        )

        output = tmp_path / "STATS.md"
        generate_stats(jsonl_path, output, tmp_path)

        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "Scheinfirmen Österreich" in content
        assert "Wöchentliche Änderungen" in content

    @patch("scheinfirmen_at.stats.get_data_history", return_value=[])
    def test_no_history_skips(self, _mock: MagicMock, tmp_path: Path) -> None:
        output = tmp_path / "STATS.md"
        generate_stats(tmp_path / "sf.jsonl", output, tmp_path)
        assert not output.exists()
