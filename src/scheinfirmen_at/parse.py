# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Parse BMF tilde-delimited CSV into structured records."""

import html
import re
from dataclasses import dataclass
from datetime import datetime

# Expected column names after stripping whitespace
EXPECTED_HEADERS = [
    "Name",
    "Anschrift",
    "Veröffentlichung",
    "Rechtskraft Bescheid",
    "Zeitpunkt als Scheinunternehmen",
    "Geburts-Datum",
    "Firmenbuch-Nr",
    "UID-Nr.",
    "Kennziffer des UR",
]

_RE_STAND = re.compile(
    r"^Stand:\s+(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2}:\d{2})\s*$"
)


@dataclass
class ScheinfirmaRecord:
    """A single Scheinfirma (shell company or natural person) record."""

    name: str
    anschrift: str
    veroeffentlicht: str  # ISO 8601: YYYY-MM-DD
    rechtskraeftig: str  # ISO 8601: YYYY-MM-DD
    seit: str | None  # ISO 8601 or None
    geburtsdatum: str | None  # ISO 8601 or None (only for natural persons)
    fbnr: str | None
    uid: str | None  # ATUxxxxxxxx or None
    kennziffer: str | None


@dataclass
class ParseResult:
    """Result of parsing the BMF CSV."""

    records: list[ScheinfirmaRecord]
    stand_datum: str  # ISO 8601 date: YYYY-MM-DD
    stand_zeit: str  # HH:MM:SS
    raw_row_count: int  # number of data rows found (before validation)


def _convert_date(date_str: str) -> str:
    """Convert DD.MM.YYYY to YYYY-MM-DD. Raises ValueError on invalid date."""
    try:
        d = datetime.strptime(date_str.strip(), "%d.%m.%Y")
    except ValueError as exc:
        raise ValueError(
            f"Invalid date format (expected DD.MM.YYYY): {date_str!r}"
        ) from exc
    return d.strftime("%Y-%m-%d")


def _clean_field(value: str) -> str:
    """Strip whitespace and unescape HTML entities."""
    return html.unescape(value).strip()


def _clean_kennziffer(value: str) -> str | None:
    """Clean the Kennziffer field: unescape HTML, strip surrounding quotes."""
    cleaned = html.unescape(value).strip()
    # Handle &quot;...&quot; wrapping (becomes "..." after unescape)
    cleaned = cleaned.strip('"').strip()
    return cleaned if cleaned else None


def parse_bmf_csv(raw_data: bytes, encoding: str = "iso-8859-1") -> ParseResult:
    """Parse raw BMF CSV bytes into structured records.

    Steps:
    1. Decode from ISO-8859-1
    2. Normalize line endings (CRLF → LF)
    3. Validate header line against EXPECTED_HEADERS
    4. Parse each data row (split by ~, strip/clean fields)
    5. Extract Stand: timestamp from footer
    6. Convert dates from DD.MM.YYYY to YYYY-MM-DD

    Raises:
        ValueError: if header doesn't match, row has wrong field count, or
                    required dates cannot be parsed, or Stand line is missing.
    """
    text = raw_data.decode(encoding)

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    if not lines:
        raise ValueError("Empty input: no lines found")

    # --- Validate header ---
    raw_headers = lines[0].split("~")
    actual_headers = [h.strip() for h in raw_headers]
    if actual_headers != EXPECTED_HEADERS:
        raise ValueError(
            f"Unexpected CSV headers.\n"
            f"  Expected: {EXPECTED_HEADERS}\n"
            f"  Got:      {actual_headers}"
        )

    # --- Parse data rows and find Stand ---
    records: list[ScheinfirmaRecord] = []
    stand_datum: str | None = None
    stand_zeit: str | None = None

    for line_no, line in enumerate(lines[1:], start=2):
        stripped = line.strip()
        if not stripped:
            continue

        # Check for Stand: timestamp line
        m = _RE_STAND.match(stripped)
        if m:
            stand_datum = _convert_date(m.group(1))
            stand_zeit = m.group(2)
            continue

        # Data row — the BMF format uses a trailing tilde on rows with empty
        # Kennziffer, producing 10 parts when split. Strip the trailing empty part.
        fields = line.split("~")
        if len(fields) == 10 and fields[-1] == "":
            fields = fields[:9]
        if len(fields) != 9:
            raise ValueError(
                f"Line {line_no}: expected 9 fields, got {len(fields)}: {line!r}"
            )

        def opt(v: str) -> str | None:
            cleaned = _clean_field(v)
            return cleaned if cleaned else None

        def opt_date(v: str) -> str | None:
            cleaned = _clean_field(v)
            return _convert_date(cleaned) if cleaned else None

        record = ScheinfirmaRecord(
            name=_clean_field(fields[0]),
            anschrift=_clean_field(fields[1]),
            veroeffentlicht=_convert_date(_clean_field(fields[2])),
            rechtskraeftig=_convert_date(_clean_field(fields[3])),
            seit=opt_date(fields[4]),
            geburtsdatum=opt_date(fields[5]),
            fbnr=opt(fields[6]),
            uid=opt(fields[7]),
            kennziffer=_clean_kennziffer(fields[8]),
        )
        records.append(record)

    if stand_datum is None or stand_zeit is None:
        raise ValueError("Stand: timestamp line not found in CSV")

    return ParseResult(
        records=records,
        stand_datum=stand_datum,
        stand_zeit=stand_zeit,
        raw_row_count=len(records),
    )
