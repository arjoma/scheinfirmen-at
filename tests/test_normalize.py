"""Tests for the normalize module."""

from scheinfirmen_at.normalize import normalize_field_swaps
from scheinfirmen_at.parse import ParseResult, ScheinfirmaRecord


def _make_result(records: list[ScheinfirmaRecord]) -> ParseResult:
    return ParseResult(
        records=records,
        stand_datum="2026-04-28",
        stand_zeit="07:00:00",
        raw_row_count=len(records),
    )


def _rec(**kwargs: object) -> ScheinfirmaRecord:
    defaults: dict[str, object] = dict(
        name="Test GmbH",
        anschrift="1010 Wien, Testgasse 1",
        veroeffentlicht="2024-01-01",
        rechtskraeftig="2023-12-31",
        seit=None,
        geburtsdatum=None,
        fbnr=None,
        uid=None,
        kennziffer=None,
    )
    defaults.update(kwargs)
    return ScheinfirmaRecord(**defaults)  # type: ignore[arg-type]


# --- Swap rule -----------------------------------------------------------


def test_move_kennziffer_value_from_uid_column() -> None:
    """Real-world case: Row 1377 had a Kennziffer-shaped value in UID column."""
    rec = _rec(name="Wikri", fbnr="580355p", uid="R134I594W", kennziffer=None)
    fixes = normalize_field_swaps(_make_result([rec]))
    assert len(fixes) == 1
    assert fixes[0].rule == "swap-uid-kennziffer"
    assert rec.uid is None
    assert rec.kennziffer == "R134I594W"


def test_move_uid_value_from_kennziffer_column() -> None:
    rec = _rec(uid=None, kennziffer="ATU12345678")
    fixes = normalize_field_swaps(_make_result([rec]))
    assert len(fixes) == 1
    assert fixes[0].rule == "swap-uid-kennziffer"
    assert rec.uid == "ATU12345678"
    assert rec.kennziffer is None


def test_true_swap_both_columns_misplaced() -> None:
    rec = _rec(uid="R100A200", kennziffer="ATU12345678")
    fixes = normalize_field_swaps(_make_result([rec]))
    assert len(fixes) == 1
    assert rec.uid == "ATU12345678"
    assert rec.kennziffer == "R100A200"


def test_no_swap_when_both_valid_in_place() -> None:
    rec = _rec(uid="ATU12345678", kennziffer="R100A200")
    fixes = normalize_field_swaps(_make_result([rec]))
    assert fixes == []
    assert rec.uid == "ATU12345678"
    assert rec.kennziffer == "R100A200"


def test_no_swap_when_only_uid_valid_and_kennziffer_garbage() -> None:
    rec = _rec(uid="ATU12345678", kennziffer="garbage")
    fixes = normalize_field_swaps(_make_result([rec]))
    assert fixes == []


# --- Duplicate-clear rule ------------------------------------------------


def test_clear_kennziffer_duplicates_uid() -> None:
    """Real-world case: Row 555 (HORVAT Monika)."""
    rec = _rec(name="HORVAT", uid="ATU80457319", kennziffer="ATU80457319")
    fixes = normalize_field_swaps(_make_result([rec]))
    assert len(fixes) == 1
    assert fixes[0].rule == "clear-duplicate-uid"
    assert rec.uid == "ATU80457319"
    assert rec.kennziffer is None


def test_clear_kennziffer_duplicates_fbnr() -> None:
    """Real-world case: Row 75 (Aran Bike GmbH)."""
    rec = _rec(name="Aran Bike", fbnr="636821b", uid="ATU81293903", kennziffer="636821b")
    fixes = normalize_field_swaps(_make_result([rec]))
    assert len(fixes) == 1
    assert fixes[0].rule == "clear-duplicate-fbnr"
    assert rec.fbnr == "636821b"
    assert rec.uid == "ATU81293903"
    assert rec.kennziffer is None


def test_no_duplicate_clear_when_kennziffer_differs() -> None:
    rec = _rec(fbnr="636821b", uid="ATU81293903", kennziffer="R100A200")
    fixes = normalize_field_swaps(_make_result([rec]))
    assert fixes == []


# --- Foreign VAT promotion -----------------------------------------------


def test_promote_foreign_vat_from_kennziffer_to_uid() -> None:
    """Real-world case: Row 635 (Jovanluka SRL, Romanian VAT)."""
    rec = _rec(name="Jovanluka", uid=None, kennziffer="RO38488384")
    fixes = normalize_field_swaps(_make_result([rec]))
    assert len(fixes) == 1
    assert fixes[0].rule == "promote-foreign-vat"
    assert rec.uid == "RO38488384"
    assert rec.kennziffer is None


def test_no_foreign_vat_promotion_when_uid_already_present() -> None:
    rec = _rec(uid="ATU12345678", kennziffer="RO38488384")
    fixes = normalize_field_swaps(_make_result([rec]))
    # No fix: the kennziffer is suspicious but uid is taken; leave for validator warning.
    assert fixes == []


def test_no_foreign_vat_promotion_for_random_string() -> None:
    rec = _rec(uid=None, kennziffer="not a vat")
    fixes = normalize_field_swaps(_make_result([rec]))
    assert fixes == []


# --- General -------------------------------------------------------------


def test_no_fixes_for_clean_record() -> None:
    rec = _rec(fbnr="123456a", uid="ATU12345678", kennziffer="R100A200")
    fixes = normalize_field_swaps(_make_result([rec]))
    assert fixes == []


def test_only_one_rule_per_row() -> None:
    """Each row should trigger at most one rule per pass."""
    rec_swap = _rec(uid="R100A200", kennziffer=None)
    rec_dup = _rec(uid="ATU12345678", kennziffer="ATU12345678")
    rec_foreign = _rec(uid=None, kennziffer="DE123456789")
    fixes = normalize_field_swaps(_make_result([rec_swap, rec_dup, rec_foreign]))
    assert [f.rule for f in fixes] == [
        "swap-uid-kennziffer",
        "clear-duplicate-uid",
        "promote-foreign-vat",
    ]
