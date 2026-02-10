"""Validate parsed Scheinfirma records."""

import re
from dataclasses import dataclass

from scheinfirmen_at.parse import ParseResult, ScheinfirmaRecord

# Compiled validation regexes
_RE_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_UID = re.compile(r"^ATU\d{8}$")
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


def validate_records(result: ParseResult, min_rows: int = 100) -> ValidationResult:
    """Validate all records from a ParseResult.

    Validation rules (errors halt the pipeline, warnings are reported but continue):

    Errors:
    - Row count >= min_rows (sanity check against truncated/empty response)
    - Name must be non-empty
    - Anschrift must be non-empty
    - Veröffentlichung must be a valid ISO date (YYYY-MM-DD)
    - Rechtskraft Bescheid must be a valid ISO date
    - Zeitpunkt: if present, must be valid ISO date
    - Geburts-Datum: if present, must be valid ISO date
    - UID-Nr: if present, must match ATU + 8 digits
    - Firmenbuch-Nr: if present, must match digits + letter

    Warnings (known BMF data quality issues):
    - Kennziffer: if present and doesn't match expected pattern
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

    for row_idx, rec in enumerate(result.records, start=1):
        row_errors, row_warnings = _validate_record(row_idx, rec)
        errors.extend(row_errors)
        warnings.extend(row_warnings)

    return ValidationResult(errors=errors, warnings=warnings)


def _validate_record(
    row: int, rec: ScheinfirmaRecord
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

    # Required date fields
    for field_name, value in [
        ("veroeffentlichung", rec.veroeffentlichung),
        ("rechtskraeftig", rec.rechtskraeftig),
    ]:
        if not _RE_ISO_DATE.match(value):
            err(field_name, value, f"Expected ISO date YYYY-MM-DD, got {value!r}")

    # Optional date fields
    for field_name, opt_value in [
        ("seit", rec.seit),
        ("geburtsdatum", rec.geburtsdatum),
    ]:
        if opt_value is not None and not _RE_ISO_DATE.match(opt_value):
            err(field_name, opt_value, f"Expected ISO date YYYY-MM-DD, got {opt_value!r}")

    # UID-Nr format
    if rec.uid_nr is not None and not _RE_UID.match(rec.uid_nr):
        err("uid_nr", rec.uid_nr, "Expected format ATU followed by 8 digits")

    # Firmenbuch-Nr format
    if rec.firmenbuch_nr is not None and not _RE_FIRMENBUCH.match(rec.firmenbuch_nr):
        err(
            "firmenbuch_nr",
            rec.firmenbuch_nr,
            "Expected 5-6 digits followed by a letter",
        )

    # Kennziffer — warning only (BMF data has known inconsistencies)
    if rec.kennziffer_ur is not None and not _RE_KENNZIFFER.match(rec.kennziffer_ur):
        warn(
            "kennziffer_ur",
            rec.kennziffer_ur,
            "Unexpected Kennziffer format (expected R + digits + letter pattern)",
        )

    return errors, warnings
