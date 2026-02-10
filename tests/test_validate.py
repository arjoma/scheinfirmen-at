"""Tests for the validate module."""

from scheinfirmen_at.parse import ParseResult, ScheinfirmaRecord
from scheinfirmen_at.validate import ValidationResult, validate_records


def _make_result(records: list[ScheinfirmaRecord], stand_datum: str = "2026-02-10") -> ParseResult:
    return ParseResult(
        records=records,
        stand_datum=stand_datum,
        stand_zeit="09:00:00",
        raw_row_count=len(records),
    )


def _good_record(**kwargs) -> ScheinfirmaRecord:  # type: ignore[no-untyped-def]
    defaults = dict(
        name="Test GmbH",
        anschrift="1010 Wien, Testgasse 1",
        veroeffentlichung="2024-01-01",
        rechtskraeftig="2023-12-31",
        seit=None,
        geburtsdatum=None,
        firmenbuch_nr=None,
        uid_nr=None,
        kennziffer_ur=None,
    )
    defaults.update(kwargs)
    return ScheinfirmaRecord(**defaults)  # type: ignore[arg-type]


def test_validate_valid_record(sample_result: ParseResult) -> None:
    vr = validate_records(sample_result, min_rows=1)
    assert vr.ok, f"Unexpected errors: {vr.errors}"


def test_validate_empty_name() -> None:
    rec = _good_record(name="")
    vr = validate_records(_make_result([rec]), min_rows=1)
    assert not vr.ok
    assert any("name" in e.field for e in vr.errors)


def test_validate_empty_anschrift() -> None:
    rec = _good_record(anschrift="")
    vr = validate_records(_make_result([rec]), min_rows=1)
    assert not vr.ok
    assert any("anschrift" in e.field for e in vr.errors)


def test_validate_invalid_uid() -> None:
    rec = _good_record(uid_nr="DE123456789")  # German format, not ATU
    vr = validate_records(_make_result([rec]), min_rows=1)
    assert not vr.ok
    assert any("uid_nr" in e.field for e in vr.errors)


def test_validate_valid_uid_formats() -> None:
    for uid in ["ATU12345678", "ATU00000000", "ATU99999999"]:
        rec = _good_record(uid_nr=uid)
        vr = validate_records(_make_result([rec]), min_rows=1)
        uid_errors = [e for e in vr.errors if e.field == "uid_nr"]
        assert not uid_errors, f"UID {uid} should be valid"


def test_validate_invalid_firmenbuch() -> None:
    for bad in ["1234", "1234567a", "123456", "abcdef"]:
        rec = _good_record(firmenbuch_nr=bad)
        vr = validate_records(_make_result([rec]), min_rows=1)
        fb_errors = [e for e in vr.errors if e.field == "firmenbuch_nr"]
        assert fb_errors, f"Firmenbuch {bad!r} should be invalid"


def test_validate_valid_firmenbuch() -> None:
    for good in ["12345a", "123456A", "97531z"]:
        rec = _good_record(firmenbuch_nr=good)
        vr = validate_records(_make_result([rec]), min_rows=1)
        fb_errors = [e for e in vr.errors if e.field == "firmenbuch_nr"]
        assert not fb_errors, f"Firmenbuch {good!r} should be valid"


def test_validate_kennziffer_bad_format_is_warning_not_error() -> None:
    rec = _good_record(kennziffer_ur="ATU12345678")  # BMF data error pattern
    vr = validate_records(_make_result([rec]), min_rows=1)
    assert vr.ok, "Bad Kennziffer should only be a warning"
    assert any("kennziffer_ur" in w.field for w in vr.warnings)


def test_validate_min_rows_fail() -> None:
    records = [_good_record() for _ in range(5)]
    vr = validate_records(_make_result(records), min_rows=100)
    assert not vr.ok
    assert any("row_count" in e.field for e in vr.errors)


def test_validate_min_rows_pass() -> None:
    records = [_good_record(name=f"Firma {i}") for i in range(10)]
    vr = validate_records(_make_result(records), min_rows=10)
    assert vr.ok


def test_validate_invalid_date_in_required_field() -> None:
    rec = _good_record(veroeffentlichung="14.12.2023")  # Wrong format (not ISO)
    vr = validate_records(_make_result([rec]), min_rows=1)
    assert not vr.ok
    assert any("veroeffentlichung" in e.field for e in vr.errors)


def test_validate_invalid_date_in_optional_field() -> None:
    rec = _good_record(seit="06.06.2024")  # Wrong format
    vr = validate_records(_make_result([rec]), min_rows=1)
    assert not vr.ok


def test_validate_returns_validation_result(sample_result: ParseResult) -> None:
    vr = validate_records(sample_result, min_rows=1)
    assert isinstance(vr, ValidationResult)
    assert isinstance(vr.errors, list)
    assert isinstance(vr.warnings, list)
