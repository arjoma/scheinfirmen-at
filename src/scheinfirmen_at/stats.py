# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Generate statistics report from Scheinfirmen data using Veröffentlichung dates."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from scheinfirmen_at.history import REMOVALS_FILENAME, Record, load_removals
from scheinfirmen_at.parse import ParseResult

logger = logging.getLogger("scheinfirmen_at")


@dataclass
class RecordInfo:
    """Minimal record info for stats display."""

    name: str
    uid: str | None
    anschrift: str
    veroeffentlicht: date | None


    @classmethod
    def from_dict(cls, obj: Record) -> RecordInfo:
        return cls(
            name=obj.get("name") or "",
            uid=obj.get("uid"),
            anschrift=obj.get("anschrift") or "",
            veroeffentlicht=_parse_date(obj.get("veroeffentlicht")),
        )


@dataclass
class RemovalInfo:
    """A record that disappeared from the BMF list."""

    name: str
    uid: str | None
    veroeffentlicht: date | None
    entfernt: date

    @property
    def years_listed(self) -> float | None:
        if self.veroeffentlicht is None:
            return None
        return (self.entfernt - self.veroeffentlicht).days / 365.25


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _removal_infos(rows: list[Record]) -> list[RemovalInfo]:
    infos: list[RemovalInfo] = []
    for row in rows:
        entfernt = _parse_date(row.get("entfernt"))
        if entfernt is None:
            continue
        infos.append(
            RemovalInfo(
                name=row.get("name") or "",
                uid=row.get("uid"),
                veroeffentlicht=_parse_date(row.get("veroeffentlicht")),
                entfernt=entfernt,
            )
        )
    return infos


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

            records.append(RecordInfo.from_dict(obj))

    if total == 0:
        total = len(records)
    return records, stand, total


def compute_monthly_stats(records: list[RecordInfo]) -> list[MonthRow]:
    """Group records by calendar month of veroeffentlicht, compute cumulative totals.

    Only records with a veroeffentlicht date are included. Months without
    additions between the first and last month are included with 0.
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

    # Walk every calendar month from first to last (including months without
    # additions) so the chart's x-axis is linear in time.
    rows: list[MonthRow] = []
    cumulative = 0
    year, month = min(month_counts)
    last = max(month_counts)
    while (year, month) <= last:
        additions = month_counts.get((year, month), 0)
        cumulative += additions
        rows.append(
            MonthRow(
                month_label=f"{year}-{month:02d}",
                month_start=date(year, month, 1),
                additions=additions,
                total=cumulative,
            )
        )
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)

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


def _md_cell(value: str) -> str:
    """Escape a value for use inside a Markdown table cell."""
    return value.replace("|", "\\|")


def render_stats_md(
    monthly: list[MonthRow],
    recent: list[RecordInfo],
    stand: str,
    total: int,
    oldest_date: date | None = None,
    geaendert: str | None = None,
    removals: list[RemovalInfo] | None = None,
    reference: date | None = None,
) -> str:
    """Render the full STATS.md Markdown report.

    Order:
    1. Title + totals (last data change, download time, count, first entry)
    2. Mermaid chart (temporal progression by month)
    3. Last 30 days: additions (alphabetical)
    4. Last 30 days: removals (only if a removals log is available)
    """
    lines: list[str] = []

    first_date = oldest_date.isoformat() if oldest_date else "—"
    lines.append("# Scheinfirmen Österreich — Statistik\n")
    lines.append("| Letzte Änderung | Abgerufen | Gesamt | Erster Eintrag |")
    lines.append("|-----------------|-----------|-------:|----------------|")
    lines.append(f"| {geaendert or stand} | {stand} | {total} | {first_date} |\n")

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
            cells = [_md_cell(rec.name), _md_cell(rec.uid or ""), _md_cell(rec.anschrift)]
            lines.append(f"| {' | '.join(cells)} |")
    else:
        lines.append("*Keine neuen Einträge in den letzten 30 Tagen.*\n")

    if removals is not None:
        lines.extend(_render_removals(removals, reference))

    return "\n".join(lines)


def _render_removals(removals: list[RemovalInfo], reference: date | None) -> list[str]:
    lines = ["", "## Entfernte Einträge (letzte 30 Tage)\n"]
    if reference is None:
        reference = max((r.entfernt for r in removals), default=date.today())
    cutoff = reference - timedelta(days=30)
    recent = sorted(
        (r for r in removals if r.entfernt > cutoff),
        key=lambda r: (r.entfernt, r.name),
        reverse=True,
    )
    if recent:
        lines.append("| Name | UID | Veröffentlicht | Entfernt | Jahre gelistet |")
        lines.append("|------|-----|----------------|----------|---------------:|")
        for r in recent:
            listed = "" if r.years_listed is None else f"{r.years_listed:.1f}"
            pub = r.veroeffentlicht.isoformat() if r.veroeffentlicht else ""
            cells = [_md_cell(r.name), _md_cell(r.uid or ""), pub, r.entfernt.isoformat(), listed]
            lines.append(f"| {' | '.join(cells)} |")
        lines.append("")
    else:
        lines.append("*Keine entfernten Einträge in den letzten 30 Tagen.*\n")
    if removals:
        since = min(r.entfernt for r in removals).isoformat()
        lines.append(
            f"*Insgesamt {len(removals)} entfernte Einträge seit {since} "
            f"(vollständiges Protokoll: `{REMOVALS_FILENAME}`).*\n"
        )
    return lines


def write_stats(
    records: list[RecordInfo],
    stand: str,
    total: int,
    output_path: Path,
    geaendert: str | None = None,
    removals: list[Record] | None = None,
) -> None:
    """Render STATS.md from in-memory records and write it."""
    monthly = compute_monthly_stats(records)
    # Anchor the "last 30 days" window at the data's Stand date rather than
    # the wall clock, so the report is a pure function of the data.
    reference = _parse_date(stand) or date.today()
    recent = find_recent_additions(records, days=30, today=reference)

    dates = [r.veroeffentlicht for r in records if r.veroeffentlicht is not None]
    oldest_date = min(dates) if dates else None

    md = render_stats_md(
        monthly,
        recent,
        stand,
        total,
        oldest_date,
        geaendert=geaendert,
        removals=None if removals is None else _removal_infos(removals),
        reference=reference,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")
    logger.info("Wrote stats report to %s", output_path)


def write_stats_for_result(
    result: ParseResult,
    output_path: Path,
    geaendert: str | None = None,
    removals: list[Record] | None = None,
) -> None:
    """Write STATS.md for a parsed (and normalized) result."""
    records = [RecordInfo.from_dict(rec.to_dict()) for rec in result.records]
    write_stats(records, result.stand, len(records), output_path, geaendert, removals)


def generate_stats(jsonl_path: Path, output_path: Path) -> None:
    """Generate STATS.md from a JSONL output file (and the removals log
    next to it, if present)."""
    logger.info("Generating stats from %s", jsonl_path)

    records, stand, total = parse_jsonl_records(jsonl_path)
    if not records:
        logger.warning("No records found in %s — skipping stats", jsonl_path)
        return

    geaendert: str | None = None
    with open(jsonl_path, encoding="utf-8") as f:
        first = json.loads(f.readline())
        if "_metadata" in first:
            geaendert = first["_metadata"].get("geaendert")

    removals_path = jsonl_path.parent / REMOVALS_FILENAME
    removals = load_removals(removals_path) if removals_path.exists() else None
    write_stats(records, stand, total, output_path, geaendert, removals)
