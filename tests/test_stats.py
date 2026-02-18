# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Tests for the stats module."""

import json
from datetime import date
from pathlib import Path

from scheinfirmen_at.stats import (
    RecordInfo,
    WeekRow,
    compute_weekly_stats,
    find_recent_additions,
    generate_stats,
    parse_jsonl_records,
    render_stats_md,
)


def _make_record(
    name: str,
    veroeffentlicht: date | None,
    uid: str | None = None,
    anschrift: str = "1010 Wien, Testgasse 1",
) -> RecordInfo:
    """Helper to build a RecordInfo."""
    return RecordInfo(
        name=name,
        uid=uid,
        anschrift=anschrift,
        veroeffentlicht=veroeffentlicht,
    )


class TestComputeWeeklyStats:
    def test_empty(self) -> None:
        assert compute_weekly_stats([]) == []

    def test_all_null_dates(self) -> None:
        records = [_make_record("A", None), _make_record("B", None)]
        assert compute_weekly_stats(records) == []

    def test_single_record(self) -> None:
        records = [_make_record("A", date(2026, 2, 10))]
        rows = compute_weekly_stats(records)
        assert len(rows) == 1
        assert rows[0].additions == 1
        assert rows[0].total == 1
        assert rows[0].week_label == "2026-W07"

    def test_same_week_merged(self) -> None:
        records = [
            _make_record("A", date(2026, 2, 10)),  # W07
            _make_record("B", date(2026, 2, 12)),  # W07
        ]
        rows = compute_weekly_stats(records)
        assert len(rows) == 1
        assert rows[0].additions == 2
        assert rows[0].total == 2

    def test_two_weeks_cumulative(self) -> None:
        records = [
            _make_record("A", date(2026, 2, 9)),   # W07
            _make_record("B", date(2026, 2, 9)),   # W07
            _make_record("C", date(2026, 2, 16)),  # W08
        ]
        rows = compute_weekly_stats(records)
        assert len(rows) == 2
        assert rows[0].week_label == "2026-W07"
        assert rows[0].additions == 2
        assert rows[0].total == 2
        assert rows[1].week_label == "2026-W08"
        assert rows[1].additions == 1
        assert rows[1].total == 3  # cumulative

    def test_chronological_order(self) -> None:
        records = [
            _make_record("B", date(2026, 2, 16)),  # W08
            _make_record("A", date(2026, 2, 9)),   # W07
        ]
        rows = compute_weekly_stats(records)
        assert rows[0].week_label == "2026-W07"
        assert rows[1].week_label == "2026-W08"

    def test_skips_null_dates(self) -> None:
        records = [
            _make_record("A", date(2026, 2, 9)),
            _make_record("B", None),
        ]
        rows = compute_weekly_stats(records)
        assert len(rows) == 1
        assert rows[0].total == 1

    def test_cumulative_totals_sum_to_count(self) -> None:
        records = [
            _make_record("A", date(2026, 1, 5)),
            _make_record("B", date(2026, 1, 12)),
            _make_record("C", date(2026, 1, 12)),
            _make_record("D", date(2026, 1, 19)),
        ]
        rows = compute_weekly_stats(records)
        assert rows[-1].total == len(records)

    def test_week_start_is_monday(self) -> None:
        records = [_make_record("A", date(2026, 2, 11))]  # Wednesday W07
        rows = compute_weekly_stats(records)
        assert rows[0].week_start == date(2026, 2, 9)  # Monday of W07


class TestFindRecentAdditions:
    def test_empty(self) -> None:
        assert find_recent_additions([], days=30, today=date(2026, 2, 18)) == []

    def test_within_window(self) -> None:
        today = date(2026, 2, 18)
        records = [
            _make_record("A", date(2026, 2, 10)),  # 8 days ago
            _make_record("B", date(2026, 1, 1)),   # 48 days ago
        ]
        result = find_recent_additions(records, days=30, today=today)
        assert len(result) == 1
        assert result[0].name == "A"

    def test_cutoff_is_exclusive(self) -> None:
        today = date(2026, 2, 18)
        # exactly on cutoff (30 days ago) is NOT included (strictly >)
        records = [_make_record("A", today - __import__("datetime").timedelta(days=30))]
        result = find_recent_additions(records, days=30, today=today)
        assert result == []

    def test_sorted_alphabetically(self) -> None:
        today = date(2026, 2, 18)
        records = [
            _make_record("Zebra GmbH", date(2026, 2, 15)),
            _make_record("Alpha KG", date(2026, 2, 14)),
            _make_record("Mitte GmbH", date(2026, 2, 16)),
        ]
        result = find_recent_additions(records, days=30, today=today)
        assert [r.name for r in result] == ["Alpha KG", "Mitte GmbH", "Zebra GmbH"]

    def test_null_dates_excluded(self) -> None:
        today = date(2026, 2, 18)
        records = [
            _make_record("A", None),
            _make_record("B", date(2026, 2, 10)),
        ]
        result = find_recent_additions(records, days=30, today=today)
        assert len(result) == 1
        assert result[0].name == "B"

    def test_uses_today_by_default(self) -> None:
        # Just ensure it runs without error (today is dynamic)
        records = [_make_record("A", date(2026, 1, 1))]
        result = find_recent_additions(records, days=30)
        assert isinstance(result, list)


class TestRenderStatsMd:
    def _make_weekly(self) -> list[WeekRow]:
        return [
            WeekRow("2026-W01", date(2026, 1, 5), 10, 10),
            WeekRow("2026-W02", date(2026, 1, 12), 5, 15),
        ]

    def test_contains_title(self) -> None:
        md = render_stats_md([], [], "2026-01-12", 15)
        assert "# Scheinfirmen Österreich — Statistik" in md

    def test_header_shows_stand_and_total(self) -> None:
        md = render_stats_md([], [], "2026-01-12T10:00:00", 42)
        assert "Gesamt: 42" in md
        assert "Stand: 2026-01-12T10:00:00" in md

    def test_header_shows_oldest_date(self) -> None:
        md = render_stats_md([], [], "2026-01-12", 1, oldest_date=date(2016, 4, 5))
        assert "Erster Eintrag: 2016-04-05" in md

    def test_no_chart_with_single_week(self) -> None:
        weekly = [WeekRow("2026-W01", date(2026, 1, 5), 10, 10)]
        md = render_stats_md(weekly, [], "2026-01-05", 10)
        assert "mermaid" not in md

    def test_chart_with_two_weeks(self) -> None:
        md = render_stats_md(self._make_weekly(), [], "2026-01-12", 15)
        assert "```mermaid" in md
        assert "xychart-beta" in md
        assert "line [10, 15]" in md

    def test_chart_year_labels(self) -> None:
        weekly = [
            WeekRow("2025-W52", date(2025, 12, 22), 5, 5),
            WeekRow("2026-W01", date(2025, 12, 29), 3, 8),
            WeekRow("2026-W02", date(2026, 1, 5), 2, 10),
        ]
        md = render_stats_md(weekly, [], "2026-01-05", 10)
        # Year 2025 label at first week, 2026 label at first week of that year
        assert '"2025"' in md
        assert '"2026"' in md
        # Subsequent weeks of same year use empty label
        assert '""' in md

    def test_recent_additions_section(self) -> None:
        recent = [
            RecordInfo("Firma A", "ATU12345678", "1010 Wien", date(2026, 2, 10)),
            RecordInfo("Firma B", None, "1020 Wien", date(2026, 2, 11)),
        ]
        md = render_stats_md([], recent, "2026-02-18", 100)
        assert "## Neueste Scheinfirmen (letzte 30 Tage)" in md
        assert "| Firma A | ATU12345678 | 1010 Wien |" in md
        assert "| Firma B |  | 1020 Wien |" in md
        assert "2 Einträge hinzugefügt" in md

    def test_no_recent_additions_message(self) -> None:
        md = render_stats_md([], [], "2026-01-05", 1)
        assert "Keine neuen Einträge" in md

    def test_chart_before_recent_section(self) -> None:
        recent = [RecordInfo("A", None, "Wien", date(2026, 2, 10))]
        md = render_stats_md(self._make_weekly(), recent, "2026-01-12", 15)
        chart_pos = md.index("mermaid")
        recent_pos = md.index("Neueste Scheinfirmen")
        assert chart_pos < recent_pos


class TestParseJsonlRecords:
    def test_basic(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "sf.jsonl"
        jsonl.write_text(
            json.dumps({"_metadata": {"stand": "2026-01-12T02:00:00", "count": 2}})
            + "\n"
            + json.dumps(
                {
                    "name": "Firma A",
                    "uid": "ATU11111111",
                    "anschrift": "Wien",
                    "veroeffentlicht": "2025-06-01",
                }
            )
            + "\n"
            + json.dumps(
                {
                    "name": "Firma B",
                    "uid": None,
                    "anschrift": "Graz",
                    "veroeffentlicht": None,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        records, stand, total = parse_jsonl_records(jsonl)
        assert len(records) == 2
        assert stand == "2026-01-12T02:00:00"
        assert total == 2
        assert records[0].name == "Firma A"
        assert records[0].veroeffentlicht == date(2025, 6, 1)
        assert records[0].uid == "ATU11111111"
        assert records[1].name == "Firma B"
        assert records[1].veroeffentlicht is None

    def test_empty_file(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "sf.jsonl"
        jsonl.write_text("", encoding="utf-8")
        records, stand, total = parse_jsonl_records(jsonl)
        assert records == []
        assert stand == "?"
        assert total == 0

    def test_metadata_only(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "sf.jsonl"
        jsonl.write_text(
            json.dumps({"_metadata": {"stand": "2026-01-01", "count": 0}}) + "\n",
            encoding="utf-8",
        )
        records, stand, total = parse_jsonl_records(jsonl)
        assert records == []
        assert stand == "2026-01-01"
        assert total == 0

    def test_total_fallback_to_record_count(self, tmp_path: Path) -> None:
        # No _metadata → total falls back to len(records)
        jsonl = tmp_path / "sf.jsonl"
        record = {"name": "A", "uid": None, "anschrift": "Wien", "veroeffentlicht": "2025-01-01"}
        jsonl.write_text(json.dumps(record) + "\n", encoding="utf-8")
        records, stand, total = parse_jsonl_records(jsonl)
        assert total == 1


class TestGenerateStats:
    def test_writes_output(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "scheinfirmen.jsonl"
        jsonl.write_text(
            json.dumps({"_metadata": {"stand": "2026-01-12T02:00:00", "count": 2}})
            + "\n"
            + json.dumps(
                {
                    "name": "Firma A",
                    "uid": "ATU11111111",
                    "anschrift": "1010 Wien",
                    "veroeffentlicht": "2025-06-01",
                }
            )
            + "\n"
            + json.dumps(
                {
                    "name": "Firma B",
                    "uid": None,
                    "anschrift": "1020 Wien",
                    "veroeffentlicht": "2025-06-15",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        output = tmp_path / "STATS.md"
        generate_stats(jsonl, output)

        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "# Scheinfirmen Österreich — Statistik" in content
        assert "Gesamt: 2" in content

    def test_no_records_skips(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "sf.jsonl"
        jsonl.write_text("", encoding="utf-8")
        output = tmp_path / "STATS.md"
        generate_stats(jsonl, output)
        assert not output.exists()
