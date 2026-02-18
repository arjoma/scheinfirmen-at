# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Generate statistics report from Scheinfirmen data using Veröffentlichung dates."""

from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger("scheinfirmen_at")

MONTH_NAMES_DE = {
    1: "Jän",
    2: "Feb",
    3: "Mär",
    4: "Apr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Okt",
    11: "Nov",
    12: "Dez",
}


@dataclass
class RecordInfo:
    """Minimal record info for stats display."""

    name: str
    uid: str | None
    anschrift: str
    veroeffentlicht: date | None


@dataclass
class WeekRow:
    """One row of the weekly additions table."""

    week_label: str  # e.g. "2026-W07"
    week_start: date  # Monday of the ISO week
    additions: int  # new companies published this week
    total: int  # cumulative total through this week


def parse_jsonl_records(jsonl_path: Path) -> tuple[list[RecordInfo], str, int]:
    """Parse JSONL file, return all records, stand timestamp, and total count."""
    records: list[RecordInfo] = []
    stand = "?"
    total = 0

    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "_metadata" in obj:
                stand = obj["_metadata"].get("stand", "?")
                total = obj["_metadata"].get("count", 0)
                continue

            veroeffentlicht: date | None = None
            v = obj.get("veroeffentlicht")
            if v:
                with contextlib.suppress(ValueError):
                    veroeffentlicht = date.fromisoformat(v)

            records.append(
                RecordInfo(
                    name=obj["name"],
                    uid=obj.get("uid"),
                    anschrift=obj.get("anschrift", ""),
                    veroeffentlicht=veroeffentlicht,
                )
            )

    if total == 0:
        total = len(records)
    return records, stand, total


def compute_weekly_stats(records: list[RecordInfo]) -> list[WeekRow]:
    """Group records by ISO week of veroeffentlicht, compute cumulative totals.

    Only records with a veroeffentlicht date are included.
    Returns rows sorted chronologically (oldest first).
    """
    week_counts: dict[tuple[int, int], int] = {}
    for rec in records:
        if rec.veroeffentlicht is None:
            continue
        iso_year, iso_week, _ = rec.veroeffentlicht.isocalendar()
        key = (iso_year, iso_week)
        week_counts[key] = week_counts.get(key, 0) + 1

    if not week_counts:
        return []

    rows: list[WeekRow] = []
    cumulative = 0
    for iso_year, iso_week in sorted(week_counts.keys()):
        additions = week_counts[(iso_year, iso_week)]
        cumulative += additions
        week_start = date.fromisocalendar(iso_year, iso_week, 1)
        rows.append(
            WeekRow(
                week_label=f"{iso_year}-W{iso_week:02d}",
                week_start=week_start,
                additions=additions,
                total=cumulative,
            )
        )

    return rows


def find_recent_additions(
    records: list[RecordInfo],
    days: int = 30,
    today: date | None = None,
) -> list[RecordInfo]:
    """Find records with veroeffentlicht in the last N days, sorted alphabetically."""
    if today is None:
        today = date.today()
    cutoff = today - timedelta(days=days)

    recent = [
        rec
        for rec in records
        if rec.veroeffentlicht is not None and rec.veroeffentlicht > cutoff
    ]
    return sorted(recent, key=lambda r: r.name)


def _format_date_short(d: date) -> str:
    """Format date as short German label, e.g. 'Feb 10'."""
    return f"{MONTH_NAMES_DE[d.month]} {d.day}"


def render_stats_md(
    weekly: list[WeekRow],
    recent: list[RecordInfo],
    stand: str,
    total: int,
    oldest_date: date | None = None,
) -> str:
    """Render the full STATS.md Markdown report.

    Order:
    1. Title + explanation + totals
    2. Mermaid chart (temporal progression by week)
    3. Last 30 days section (recent additions, alphabetical)
    """
    lines: list[str] = []

    first_date = oldest_date.isoformat() if oldest_date else "—"
    lines.append("# Scheinfirmen Österreich — Statistik\n")
    lines.append(
        f"> Stand: {stand} | Gesamt: {total} "
        f"| Erster Eintrag: {first_date}\n"
    )

    # --- Mermaid chart (temporal progression) ---
    if len(weekly) >= 2:
        lines.append("## Verlauf\n")

        # Build x-axis labels: show year at the first week of each new year,
        # empty string for all other weeks so the axis stays readable.
        prev_year: int | None = None
        x_label_parts: list[str] = []
        for row in weekly:
            year = row.week_start.year
            if year != prev_year:
                x_label_parts.append(f'"{year}"')
                prev_year = year
            else:
                x_label_parts.append('""')

        x_labels = ", ".join(x_label_parts)
        y_values = ", ".join(str(row.total) for row in weekly)

        totals = [row.total for row in weekly]
        y_min = max(0, min(totals) - 50)
        y_max = max(totals) + 50

        lines.append("```mermaid")
        lines.append("xychart-beta")
        lines.append('    title "Scheinfirmen: Gesamtanzahl"')
        lines.append(f"    x-axis [{x_labels}]")
        lines.append(f'    y-axis "Anzahl" {y_min} --> {y_max}')
        lines.append(f"    line [{y_values}]")
        lines.append("```\n")

    # --- Recent additions (last 30 days) ---
    lines.append("## Neueste Scheinfirmen (letzte 30 Tage)\n")
    if recent:
        lines.append("| Name | UID | Anschrift |")
        lines.append("|------|-----|-----------|")
        for rec in recent:
            uid = rec.uid or ""
            lines.append(f"| {rec.name} | {uid} | {rec.anschrift} |")
        lines.append(f"\n*{len(recent)} Einträge hinzugefügt.*\n")
    else:
        lines.append("*Keine neuen Einträge in den letzten 30 Tagen.*\n")

    return "\n".join(lines)


def generate_stats(jsonl_path: Path, output_path: Path) -> None:
    """Main entry point: generate STATS.md from current data file."""
    logger.info("Generating stats from %s", jsonl_path)

    records, stand, total = parse_jsonl_records(jsonl_path)
    if not records:
        logger.warning("No records found in %s — skipping stats", jsonl_path)
        return

    weekly = compute_weekly_stats(records)
    today = date.today()
    recent = find_recent_additions(records, days=30, today=today)

    oldest_date = weekly[0].week_start if weekly else None

    md = render_stats_md(weekly, recent, stand, total, oldest_date)
    output_path.write_text(md, encoding="utf-8")
    logger.info("Wrote stats report to %s", output_path)
