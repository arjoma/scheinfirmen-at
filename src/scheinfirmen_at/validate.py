# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Validate parsed Scheinfirma records."""

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from scheinfirmen_at.parse import ParseResult, ScheinfirmaRecord

# Plausible age range (years) of a natural person at publication.
_MIN_AGE, _MAX_AGE = 14, 100

# Compiled validation regexes
_RE_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_UID = re.compile(r"^ATU\d{8}$")
# Foreign EU VAT-style identifier: 2 country letters + alphanumeric tail.
# Loose on purpose: used to accept non-Austrian VAT numbers (e.g. RO, DE)
# that the BMF occasionally publishes for cross-border shell entities, and
# by normalize.py to recognize them in the Kennziffer column.
_RE_FOREIGN_VAT = re.compile(r"^[A-Z]{2}[A-Z0-9]{6,12}$")
_RE_FIRMENBUCH = re.compile(r"^\d{5,6}[a-zA-Z]$")
_RE_KENNZIFFER = re.compile(r"^R\d{3}[A-Z]\d{3,4}[A-Z0-9]?$")


@dataclass
class ValidationError:
    """A single validation issue (error or warning)."""

    row: int  # 1-based row number
    field: str
    value: str | None
    message: str

    def __str__(self) -> str:
        return f"Row {self.row} [{self.field}]: {self.message} (value={self.value!r})"


@dataclass
class ValidationResult:
    """Result of validating a ParseResult."""

    errors: list[ValidationError]
    warnings: list[ValidationError]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def validate_records(
    result: ParseResult, min_rows: int = 100  # safe lower bound; BMF list has ~1000+ entries
) -> ValidationResult:
    """Validate all records from a ParseResult.

    Validation rules (errors halt the pipeline, warnings are reported but continue):

    Errors:
    - Row count >= min_rows (sanity check against truncated/empty response)
    - Name and Anschrift must be non-empty
    - Veröffentlichung and Rechtskraft must be valid ISO dates (YYYY-MM-DD)
    - Zeitpunkt and Geburts-Datum: if present, must be valid ISO dates

    Warnings (format — known BMF data quality issues):
    - Firmenbuch-Nr: if present and doesn't match digits + letter
    - Kennziffer: if present and doesn't match expected pattern
    - UID-Nr: if present and matches neither the Austrian pattern
      (ATU + 8 digits) nor a generic EU VAT pattern (e.g. RO…, DE…).

    Warnings (plausibility):
    - Rechtskraft after Veröffentlichung, or Zeitpunkt after Rechtskraft
    - A date after the Stand date (i.e. in the future)
    - Age at publication outside 14..100 years (natural persons)
    - The same UID, Firmenbuch-Nr or Kennziffer on several records
    """
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []

    # Row count sanity check
    if len(result.records) < min_rows:
        errors.append(
            ValidationError(
                row=0,
                field="row_count",
                value=str(len(result.records)),
                message=f"Too few records: {len(result.records)} < {min_rows}",
            )
        )

    stand = _to_date(result.stand_datum)
    for row_idx, rec in enumerate(result.records, start=1):
        row_errors, row_warnings = _validate_record(row_idx, rec, stand)
        errors.extend(row_errors)
        warnings.extend(row_warnings)

    warnings.extend(_duplicate_identifier_warnings(result.records))

    return ValidationResult(errors=errors, warnings=warnings)


def _to_date(value: str | None) -> date | None:
    """Parse a strict ISO date (YYYY-MM-DD); None if absent or invalid."""
    if value is None or not _RE_ISO_DATE.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _duplicate_identifier_warnings(
    records: list[ScheinfirmaRecord],
) -> list[ValidationError]:
    """Warn about UID/Firmenbuch/Kennziffer values shared by several rows."""
    warnings: list[ValidationError] = []
    for field_name in ("uid", "fbnr", "kennziffer"):
        rows_by_value: dict[str, list[int]] = defaultdict(list)
        for row_idx, rec in enumerate(records, start=1):
            value = getattr(rec, field_name)
            if value is not None:
                rows_by_value[value].append(row_idx)
        for value, rows in rows_by_value.items():
            if len(rows) > 1:
                warnings.append(
                    ValidationError(
                        row=rows[0],
                        field=field_name,
                        value=value,
                        message=f"Same value on {len(rows)} rows: {rows}",
                    )
                )
    return warnings


def _validate_record(
    row: int, rec: ScheinfirmaRecord, stand: date | None = None
) -> tuple[list[ValidationError], list[ValidationError]]:
    """Validate a single record. Returns (errors, warnings)."""
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []

    def err(field: str, value: str | None, msg: str) -> None:
        errors.append(ValidationError(row=row, field=field, value=value, message=msg))

    def warn(field: str, value: str | None, msg: str) -> None:
        warnings.append(ValidationError(row=row, field=field, value=value, message=msg))

    # Required string fields
    if not rec.name:
        err("name", rec.name, "Name must not be empty")
    if not rec.anschrift:
        err("anschrift", rec.anschrift, "Anschrift must not be empty")

    # Date fields: required ones must be valid, optional ones valid if present
    dates: dict[str, date | None] = {}
    for field_name, value, required in [
        ("veroeffentlicht", rec.veroeffentlicht, True),
        ("rechtskraeftig", rec.rechtskraeftig, True),
        ("seit", rec.seit, False),
        ("geburtsdatum", rec.geburtsdatum, False),
    ]:
        dates[field_name] = parsed = _to_date(value)
        if parsed is None and (required or value is not None):
            err(field_name, value, f"Expected ISO date YYYY-MM-DD, got {value!r}")

    # Plausibility of dates (warnings only — BMF data is authoritative)
    veroeff, rk, seit = dates["veroeffentlicht"], dates["rechtskraeftig"], dates["seit"]
    geb = dates["geburtsdatum"]
    if veroeff and rk and rk > veroeff:
        warn("rechtskraeftig", rec.rechtskraeftig,
             f"Rechtskraft after Veröffentlichung ({rec.veroeffentlicht})")
    if seit and rk and seit > rk:
        warn("seit", rec.seit, f"Zeitpunkt after Rechtskraft ({rec.rechtskraeftig})")
    if stand:
        for field_name in ("veroeffentlicht", "rechtskraeftig", "seit"):
            d = dates[field_name]
            if d and d > stand:
                warn(field_name, d.isoformat(), f"Date is after Stand ({stand.isoformat()})")
    if geb and veroeff:
        age = (veroeff - geb).days / 365.25
        if not _MIN_AGE <= age <= _MAX_AGE:
            warn("geburtsdatum", rec.geburtsdatum,
                 f"Implausible age at publication: {age:.0f} years")

    # UID-Nr format. Austrian (ATU + 8 digits) is the norm; foreign EU VAT
    # numbers (e.g. RO, DE) are accepted silently. Anything else → warning.
    if (
        rec.uid is not None
        and not _RE_UID.match(rec.uid)
        and not _RE_FOREIGN_VAT.match(rec.uid)
    ):
        warn(
            "uid",
            rec.uid,
            "Expected Austrian UID (ATU + 8 digits) or EU VAT format",
        )

    # Firmenbuch-Nr format — warning only. BMF occasionally publishes
    # non-standard values (e.g. foreign register IDs) that we must pass
    # through verbatim rather than abort the pipeline.
    if rec.fbnr is not None and not _RE_FIRMENBUCH.match(rec.fbnr):
        warn(
            "fbnr",
            rec.fbnr,
            "Expected 5-6 digits followed by a letter",
        )

    # Kennziffer — warning only (BMF data has known inconsistencies)
    if rec.kennziffer is not None and not _RE_KENNZIFFER.match(rec.kennziffer):
        warn(
            "kennziffer",
            rec.kennziffer,
            "Unexpected Kennziffer format (expected R + digits + letter pattern)",
        )

    return errors, warnings
