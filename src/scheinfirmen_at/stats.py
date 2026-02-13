# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Generate statistics report from git history of Scheinfirmen data."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
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


@dataclass
class Snapshot:
    """A point-in-time snapshot of the Scheinfirmen list."""

    date: date
    commit: str
    total: int
    names: set[str] = field(repr=False)
    records_by_name: dict[str, RecordInfo] = field(repr=False)


@dataclass
class WeekRow:
    """One row of the weekly changes table."""

    week_label: str  # e.g. "2026-W07"
    week_start: date
    additions: int
    removals: int
    total: int


def _git(args: list[str], cwd: Path) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _parse_jsonl_names(text: str) -> tuple[dict[str, RecordInfo], int]:
    """Parse JSONL text, return records_by_name dict and raw record count."""
    records: dict[str, RecordInfo] = {}
    raw_count = 0
    for line in text.strip().splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if "_metadata" in obj:
            continue
        raw_count += 1
        info = RecordInfo(
            name=obj["name"],
            uid=obj.get("uid"),
            anschrift=obj.get("anschrift", ""),
        )
        records[info.name] = info
    return records, raw_count


def get_data_history(jsonl_path: Path, repo_dir: Path) -> list[Snapshot]:
    """Extract data snapshots from git history of the JSONL file.

    Returns snapshots sorted chronologically (oldest first),
    deduplicated so only the first commit with a given record set is kept.
    """
    rel_path = jsonl_path.relative_to(repo_dir)
    log_output = _git(
        ["log", "--format=%H %aI", "--", str(rel_path)],
        cwd=repo_dir,
    )

    raw_snapshots: list[tuple[date, str, dict[str, RecordInfo], int]] = []
    for log_line in log_output.strip().splitlines():
        if not log_line.strip():
            continue
        parts = log_line.split(" ", 1)
        commit_hash = parts[0]
        commit_date = datetime.fromisoformat(parts[1]).date()

        try:
            content = _git(
                ["show", f"{commit_hash}:{rel_path}"],
                cwd=repo_dir,
            )
        except subprocess.CalledProcessError:
            continue

        records_by_name, count = _parse_jsonl_names(content)
        raw_snapshots.append((commit_date, commit_hash, records_by_name, count))

    # Reverse to chronological order (oldest first)
    raw_snapshots.reverse()

    # Deduplicate: keep only snapshots where the name set actually changed
    snapshots: list[Snapshot] = []
    prev_names: set[str] = set()
    for snap_date, commit, records_by_name, count in raw_snapshots:
        current_names = set(records_by_name.keys())
        if current_names != prev_names or not snapshots:
            snapshots.append(
                Snapshot(
                    date=snap_date,
                    commit=commit[:8],
                    total=count,
                    names=current_names,
                    records_by_name=records_by_name,
                )
            )
            prev_names = current_names

    return snapshots


def compute_weekly_changes(snapshots: list[Snapshot]) -> list[WeekRow]:
    """Compute weekly additions and removals from chronological snapshots."""
    if not snapshots:
        return []

    rows: list[WeekRow] = []
    for i, snap in enumerate(snapshots):
        iso_year, iso_week, _ = snap.date.isocalendar()
        week_label = f"{iso_year}-W{iso_week:02d}"

        # Monday of this ISO week
        week_start = date.fromisocalendar(iso_year, iso_week, 1)

        if i == 0:
            # First snapshot: everything is "added"
            rows.append(
                WeekRow(
                    week_label=week_label,
                    week_start=week_start,
                    additions=snap.total,
                    removals=0,
                    total=snap.total,
                )
            )
        else:
            added = len(snap.names - snapshots[i - 1].names)
            removed = len(snapshots[i - 1].names - snap.names)

            # Merge into existing week row if same week
            if rows and rows[-1].week_label == week_label:
                rows[-1].additions += added
                rows[-1].removals += removed
                rows[-1].total = snap.total
            else:
                rows.append(
                    WeekRow(
                        week_label=week_label,
                        week_start=week_start,
                        additions=added,
                        removals=removed,
                        total=snap.total,
                    )
                )

    return rows


def find_recent_additions(
    snapshots: list[Snapshot], days: int = 30
) -> list[RecordInfo]:
    """Find records added in the last N days.

    If all history is within the window, uses the first snapshot as
    baseline (so the initial bulk load is not shown as "new").
    """
    if len(snapshots) < 2:
        return []

    current = snapshots[-1]
    cutoff = current.date - timedelta(days=days)

    # Find the latest snapshot at or before the cutoff
    baseline: Snapshot | None = None
    for snap in snapshots:
        if snap.date <= cutoff:
            baseline = snap

    if baseline is None:
        # All history is within the window — use the first snapshot
        # so initial bulk load isn't counted as "new additions"
        baseline = snapshots[0]

    added_names = current.names - baseline.names
    result = [current.records_by_name[name] for name in sorted(added_names)]
    return result


def _format_date_short(d: date) -> str:
    """Format date as short German label, e.g. 'Feb 10'."""
    return f"{MONTH_NAMES_DE[d.month]} {d.day}"


def render_stats_md(
    snapshots: list[Snapshot],
    weekly: list[WeekRow],
    recent: list[RecordInfo],
    stand: str,
    total: int,
) -> str:
    """Render the full STATS.md Markdown report."""
    lines: list[str] = []

    first_date = snapshots[0].date.isoformat() if snapshots else "—"
    lines.append("# Scheinfirmen Österreich — Statistik\n")
    lines.append(
        f"> Stand: {stand} | Gesamt: {total} "
        f"| Tracking seit: {first_date}\n"
    )

    # --- Recent additions ---
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

    # --- Weekly changes table ---
    lines.append("## Wöchentliche Änderungen\n")
    if weekly:
        lines.append("| Woche | Datum | Zugänge | Abgänge | Gesamt |")
        lines.append("|-------|-------|---------|---------|--------|")
        for row in weekly:
            date_label = _format_date_short(row.week_start)
            if row == weekly[0]:
                # First row: initial load
                lines.append(
                    f"| {row.week_label} | {date_label} | "
                    f"*{row.additions} (initial)* | — | {row.total} |"
                )
            else:
                add_str = f"+{row.additions}" if row.additions else "0"
                rem_str = f"-{row.removals}" if row.removals else "0"
                lines.append(
                    f"| {row.week_label} | {date_label} | "
                    f"{add_str} | {rem_str} | {row.total} |"
                )
    lines.append("")

    # --- Mermaid chart ---
    if len(weekly) >= 2:
        lines.append("## Verlauf\n")

        x_labels = ", ".join(
            f'"{_format_date_short(row.week_start)}"' for row in weekly
        )
        y_values = ", ".join(str(row.total) for row in weekly)

        # Compute y-axis range with padding
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

    return "\n".join(lines)


def generate_stats(jsonl_path: Path, output_path: Path, repo_dir: Path) -> None:
    """Main entry point: generate STATS.md from git history."""
    logger.info("Generating stats from git history of %s", jsonl_path)

    snapshots = get_data_history(jsonl_path, repo_dir)
    if not snapshots:
        logger.warning("No git history found for %s — skipping stats", jsonl_path)
        return

    weekly = compute_weekly_changes(snapshots)
    recent = find_recent_additions(snapshots, days=30)

    # Read current stand from JSONL metadata
    with open(jsonl_path, encoding="utf-8") as f:
        meta = json.loads(f.readline())
    stand = meta.get("_metadata", {}).get("stand", "?")
    total = meta.get("_metadata", {}).get("count", snapshots[-1].total)

    md = render_stats_md(snapshots, weekly, recent, stand, total)
    output_path.write_text(md, encoding="utf-8")
    logger.info("Wrote stats report to %s", output_path)
