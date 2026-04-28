# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Repair known BMF data-entry mistakes after parsing.

The Austrian BMF Scheinfirmen list is hand-maintained and contains a small
but recurring set of data-entry quirks in the UID/Firmenbuch/Kennziffer
fields. This module detects and repairs them so downstream consumers
(e.g. UID-based lookups) work correctly.

Rules applied (in order):

1. **Swap UID ↔ Kennziffer**: when each column holds a value matching the
   *other* column's pattern (or one is empty and the other is misplaced),
   swap them. Handles both true swaps and "move one over" cases.
2. **Clear duplicate Kennziffer**: when the Kennziffer field is an exact
   duplicate of the UID or Firmenbuch field, clear it (BMF sometimes
   re-types the same value into both columns).
3. **Promote foreign VAT to UID**: when the Kennziffer field holds a
   non-Austrian EU VAT number (e.g. ``RO38488384``) and the UID column is
   empty, move it into UID.
"""

import re
from dataclasses import dataclass

from scheinfirmen_at.parse import ParseResult, ScheinfirmaRecord
from scheinfirmen_at.validate import _RE_KENNZIFFER, _RE_UID

# Generic EU-style VAT identifier: 2 country letters + digit/letter mix.
# Loose on purpose — we only use it to *recognize* a foreign VAT placed in
# the Kennziffer column. Strict per-country validation is out of scope.
_RE_FOREIGN_VAT = re.compile(r"^[A-Z]{2}[A-Z0-9]{6,12}$")


@dataclass
class FieldFix:
    """A single normalization fix applied to one row."""

    row: int  # 1-based row number
    name: str  # company/person name, for log context
    rule: str  # short identifier of the rule that fired
    description: str  # human-readable explanation

    def __str__(self) -> str:
        return f"Row {self.row} ({self.name!r}) [{self.rule}]: {self.description}"


def normalize_field_swaps(result: ParseResult) -> list[FieldFix]:
    """Apply all normalization rules to ``result.records`` in place.

    Returns the list of fixes performed (empty if none).
    """
    fixes: list[FieldFix] = []
    for row_idx, rec in enumerate(result.records, start=1):
        fix = _apply_swap(rec, row_idx)
        if fix is not None:
            fixes.append(fix)
            continue

        fix = _apply_duplicate_clear(rec, row_idx)
        if fix is not None:
            fixes.append(fix)
            continue

        fix = _apply_foreign_vat_promote(rec, row_idx)
        if fix is not None:
            fixes.append(fix)

    return fixes


def _apply_swap(rec: ScheinfirmaRecord, row: int) -> FieldFix | None:
    """Swap UID ↔ Kennziffer when each value is in the wrong column.

    Also handles the "move" case where one column is empty and the other
    holds a misplaced value.
    """
    uid_valid = rec.uid is not None and _RE_UID.match(rec.uid) is not None
    kz_valid = (
        rec.kennziffer is not None
        and _RE_KENNZIFFER.match(rec.kennziffer) is not None
    )
    # If either column already holds a value valid for its own type, we
    # cannot safely disambiguate via swap.
    if uid_valid or kz_valid:
        return None

    uid_looks_like_kz = (
        rec.uid is not None and _RE_KENNZIFFER.match(rec.uid) is not None
    )
    kz_looks_like_uid = (
        rec.kennziffer is not None and _RE_UID.match(rec.kennziffer) is not None
    )
    if not (uid_looks_like_kz or kz_looks_like_uid):
        return None

    before_uid, before_kz = rec.uid, rec.kennziffer
    rec.uid, rec.kennziffer = rec.kennziffer, rec.uid
    return FieldFix(
        row=row,
        name=rec.name,
        rule="swap-uid-kennziffer",
        description=(
            f"swapped UID/Kennziffer (was uid={before_uid!r}, "
            f"kennziffer={before_kz!r}; now uid={rec.uid!r}, "
            f"kennziffer={rec.kennziffer!r})"
        ),
    )


def _apply_duplicate_clear(rec: ScheinfirmaRecord, row: int) -> FieldFix | None:
    """Clear the Kennziffer field when it duplicates UID or Firmenbuch-Nr."""
    if rec.kennziffer is None:
        return None
    if rec.kennziffer == rec.uid:
        before = rec.kennziffer
        rec.kennziffer = None
        return FieldFix(
            row=row,
            name=rec.name,
            rule="clear-duplicate-uid",
            description=f"cleared Kennziffer={before!r} (duplicate of UID)",
        )
    if rec.kennziffer == rec.fbnr:
        before = rec.kennziffer
        rec.kennziffer = None
        return FieldFix(
            row=row,
            name=rec.name,
            rule="clear-duplicate-fbnr",
            description=f"cleared Kennziffer={before!r} (duplicate of Firmenbuch-Nr)",
        )
    return None


def _apply_foreign_vat_promote(
    rec: ScheinfirmaRecord, row: int
) -> FieldFix | None:
    """Move a foreign EU VAT number from Kennziffer into the UID field."""
    if rec.uid is not None or rec.kennziffer is None:
        return None
    if not _RE_FOREIGN_VAT.match(rec.kennziffer):
        return None
    # Don't promote Austrian-shaped Kennziffer values (those are handled by swap).
    if _RE_UID.match(rec.kennziffer):
        return None
    before = rec.kennziffer
    rec.uid = rec.kennziffer
    rec.kennziffer = None
    return FieldFix(
        row=row,
        name=rec.name,
        rule="promote-foreign-vat",
        description=(
            f"moved foreign VAT {before!r} from Kennziffer into UID "
            f"(non-Austrian EU VAT — accepted as valid UID)"
        ),
    )
