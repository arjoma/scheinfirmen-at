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


@dataclass
class RecordInfo:
    """Minimal record info for stats display."""

    name: str
    uid: str | None
    anschrift: str
    veroeffentlicht: date | None


@dataclass
class MonthRow:
    """One row of the monthly additions table."""

    month_label: str  # e.g. "2026-02"
    month_start: date  # first day of the month
    additions: int  # new companies published this month
    total: int  # cumulative total through this month


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


def compute_monthly_stats(records: list[RecordInfo]) -> list[MonthRow]:
    """Group records by calendar month of veroeffentlicht, compute cumulative totals.

    Only records with a veroeffentlicht date are included.
    Returns rows sorted chronologically (oldest first).
    """
    month_counts: dict[tuple[int, int], int] = {}
    for rec in records:
        if rec.veroeffentlicht is None:
            continue
        key = (rec.veroeffentlicht.year, rec.veroeffentlicht.month)
        month_counts[key] = month_counts.get(key, 0) + 1

    if not month_counts:
        return []

    rows: list[MonthRow] = []
    cumulative = 0
    for year, month in sorted(month_counts.keys()):
        additions = month_counts[(year, month)]
        cumulative += additions
        rows.append(
            MonthRow(
                month_label=f"{year}-{month:02d}",
                month_start=date(year, month, 1),
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


def render_stats_md(
    monthly: list[MonthRow],
    recent: list[RecordInfo],
    stand: str,
    total: int,
    oldest_date: date | None = None,
) -> str:
    """Render the full STATS.md Markdown report.

    Order:
    1. Title + explanation + totals
    2. Mermaid chart (temporal progression by month)
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
    if len(monthly) >= 2:
        lines.append("## Verlauf\n")

        # X-axis: numeric year range avoids Mermaid rendering issues with
        # many categorical entries (zigzag artefacts on GitHub).
        first_year = monthly[0].month_start.year
        last_year = monthly[-1].month_start.year
        y_values = ", ".join(str(row.total) for row in monthly)

        totals = [row.total for row in monthly]
        y_max = max(totals) + 50

        lines.append("```mermaid")
        lines.append("---")
        lines.append("config:")
        lines.append("  themeVariables:")
        lines.append("    xyChart:")
        lines.append('      plotColorPalette: "#111111"')
        lines.append("---")
        lines.append("xychart-beta")
        lines.append('    title "Scheinfirmen: Gesamtanzahl"')
        lines.append(f'    x-axis "Jahr" {first_year} --> {last_year}')
        lines.append(f'    y-axis "Anzahl" 0 --> {y_max}')
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

    monthly = compute_monthly_stats(records)
    today = date.today()
    recent = find_recent_additions(records, days=30, today=today)

    oldest_date = monthly[0].month_start if monthly else None

    md = render_stats_md(monthly, recent, stand, total, oldest_date)
    output_path.write_text(md, encoding="utf-8")
    logger.info("Wrote stats report to %s", output_path)
