"""Tests for the validate module."""

from scheinfirmen_at.parse import ParseResult, ScheinfirmaRecord
from scheinfirmen_at.validate import ValidationResult, validate_records


def _make_result(records: list[ScheinfirmaRecord], stand_datum: str = "2026-02-10") -> ParseResult:
    return ParseResult(
        records=records,
        stand_datum=stand_datum,
        stand_zeit="09:00:00",
    )


def _good_record(**kwargs) -> ScheinfirmaRecord:  # type: ignore[no-untyped-def]
    defaults = dict(
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


def test_validate_foreign_eu_vat_accepted_silently() -> None:
    # Foreign EU VAT numbers in the UID field are accepted without warning —
    # the BMF list occasionally publishes cross-border shell entities.
    for uid in ["RO38488384", "DE123456789", "IT12345678901"]:
        rec = _good_record(uid=uid)
        vr = validate_records(_make_result([rec]), min_rows=1)
        assert vr.ok
        uid_issues = [
            e for e in (*vr.errors, *vr.warnings) if e.field == "uid"
        ]
        assert not uid_issues, f"UID {uid} should be accepted as foreign EU VAT"


def test_validate_invalid_uid_is_warning_not_error() -> None:
    # Truly malformed UIDs (neither AT nor EU VAT pattern) become a warning,
    # not an error — the pipeline must keep flowing on BMF data quirks.
    rec = _good_record(uid="not-a-vat-number")
    vr = validate_records(_make_result([rec]), min_rows=1)
    assert vr.ok
    assert any(w.field == "uid" for w in vr.warnings)


def test_validate_valid_uid_formats() -> None:
    for uid in ["ATU12345678", "ATU00000000", "ATU99999999"]:
        rec = _good_record(uid=uid)
        vr = validate_records(_make_result([rec]), min_rows=1)
        uid_issues = [
            e for e in (*vr.errors, *vr.warnings) if e.field == "uid"
        ]
        assert not uid_issues, f"UID {uid} should be valid"


def test_validate_invalid_firmenbuch_is_warning_not_error() -> None:
    for bad in ["1234", "1234567a", "123456", "abcdef", "R120R501J"]:
        rec = _good_record(fbnr=bad)
        vr = validate_records(_make_result([rec]), min_rows=1)
        assert vr.ok, f"Bad Firmenbuch {bad!r} should not abort pipeline"
        fb_warnings = [w for w in vr.warnings if w.field == "fbnr"]
        assert fb_warnings, f"Firmenbuch {bad!r} should produce a warning"


def test_validate_valid_firmenbuch() -> None:
    for good in ["12345a", "123456A", "97531z"]:
        rec = _good_record(fbnr=good)
        vr = validate_records(_make_result([rec]), min_rows=1)
        fb_issues = [
            e for e in (*vr.errors, *vr.warnings) if e.field == "fbnr"
        ]
        assert not fb_issues, f"Firmenbuch {good!r} should be valid"


def test_validate_kennziffer_bad_format_is_warning_not_error() -> None:
    rec = _good_record(kennziffer="ATU12345678")  # BMF data error pattern
    vr = validate_records(_make_result([rec]), min_rows=1)
    assert vr.ok, "Bad Kennziffer should only be a warning"
    assert any("kennziffer" in w.field for w in vr.warnings)


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
    rec = _good_record(veroeffentlicht="14.12.2023")  # Wrong format (not ISO)
    vr = validate_records(_make_result([rec]), min_rows=1)
    assert not vr.ok
    assert any("veroeffentlicht" in e.field for e in vr.errors)


def test_validate_invalid_date_in_optional_field() -> None:
    rec = _good_record(seit="06.06.2024")  # Wrong format
    vr = validate_records(_make_result([rec]), min_rows=1)
    assert not vr.ok


def test_validate_returns_validation_result(sample_result: ParseResult) -> None:
    vr = validate_records(sample_result, min_rows=1)
    assert isinstance(vr, ValidationResult)
    assert isinstance(vr.errors, list)
    assert isinstance(vr.warnings, list)


def test_validate_impossible_calendar_date_is_error() -> None:
    result = _make_result([_good_record(seit="2024-02-30")])
    validation = validate_records(result, min_rows=1)
    assert [e.field for e in validation.errors] == ["seit"]


def test_validate_plausibility_warnings() -> None:
    records = [
        # Rechtskraft after Veröffentlichung (real case: probable year typo)
        _good_record(name="A", veroeffentlicht="2025-01-09", rechtskraeftig="2026-01-25"),
        # Zeitpunkt after Rechtskraft
        _good_record(name="B", seit="2024-06-01"),
        # 10 years old at publication
        _good_record(name="C", geburtsdatum="2014-01-01"),
    ]
    validation = validate_records(_make_result(records, stand_datum="2026-02-10"), min_rows=1)
    assert validation.ok
    got = {(w.row, w.field) for w in validation.warnings}
    # Row 1's Rechtskraft (2026-01-25) is before Stand 2026-02-10, so no future warning.
    assert got == {(1, "rechtskraeftig"), (2, "seit"), (3, "geburtsdatum")}


def test_validate_future_date_warning() -> None:
    records = [_good_record(veroeffentlicht="2026-03-01", rechtskraeftig="2026-02-01")]
    validation = validate_records(_make_result(records, stand_datum="2026-02-10"), min_rows=1)
    assert validation.ok
    assert [(w.field, w.value) for w in validation.warnings] == [("veroeffentlicht", "2026-03-01")]


def test_validate_duplicate_identifier_warning() -> None:
    records = [
        _good_record(name="BARATH Peter", uid="ATU79831167", geburtsdatum="1980-05-21"),
        _good_record(name="Andere GmbH"),
        _good_record(name="BARATH Peter", uid="ATU79831167", geburtsdatum="2003-09-27"),
    ]
    validation = validate_records(_make_result(records), min_rows=1)
    assert validation.ok
    [w] = validation.warnings
    assert (w.field, w.value, w.row) == ("uid", "ATU79831167", 1)
    assert "[1, 3]" in w.message
