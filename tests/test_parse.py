"""Tests for the parse module."""

import pytest

from scheinfirmen_at.parse import (
    EXPECTED_HEADERS,
    ParseResult,
    _convert_date,
    parse_bmf_csv,
)


def test_parse_returns_parse_result(sample_raw_bytes: bytes) -> None:
    result = parse_bmf_csv(sample_raw_bytes)
    assert isinstance(result, ParseResult)


def test_parse_record_count(sample_raw_bytes: bytes) -> None:
    result = parse_bmf_csv(sample_raw_bytes)
    assert result.raw_row_count == 10
    assert len(result.records) == 10


def test_parse_stand_extraction(sample_raw_bytes: bytes) -> None:
    result = parse_bmf_csv(sample_raw_bytes)
    assert result.stand_datum == "2026-02-10"
    assert result.stand_zeit == "09:51:32"


def test_parse_date_conversion(sample_raw_bytes: bytes) -> None:
    result = parse_bmf_csv(sample_raw_bytes)
    # First row: Veröffentlichung 14.12.2023 → 2023-12-14
    assert result.records[0].veroeffentlichung == "2023-12-14"
    assert result.records[0].rechtskraeftig == "2023-12-12"


def test_parse_optional_fields_none(sample_raw_bytes: bytes) -> None:
    result = parse_bmf_csv(sample_raw_bytes)
    # First row: has firmenbuch_nr and uid_nr, but no Zeitpunkt, Geburts-Datum, Kennziffer
    rec = result.records[0]
    assert rec.seit is None
    assert rec.geburtsdatum is None
    assert rec.firmenbuch_nr == "597821z"
    assert rec.uid_nr == "ATU79209223"
    assert rec.kennziffer_ur is None


def test_parse_optional_fields_filled(sample_raw_bytes: bytes) -> None:
    result = parse_bmf_csv(sample_raw_bytes)
    # Second row (index 1) has Zeitpunkt, Firmenbuch-Nr, UID, Kennziffer
    rec = result.records[1]
    assert rec.seit == "2024-06-06"
    assert rec.firmenbuch_nr == "575302h"
    assert rec.uid_nr == "ATU78016816"
    assert rec.kennziffer_ur == "R133R5574"


def test_parse_natural_person_with_geburtsdatum(sample_raw_bytes: bytes) -> None:
    result = parse_bmf_csv(sample_raw_bytes)
    # Third row is a natural person with Geburts-Datum 15.05.1975
    rec = result.records[2]
    assert rec.geburtsdatum == "1975-05-15"


def test_parse_html_entity_kennziffer(sample_raw_bytes: bytes) -> None:
    result = parse_bmf_csv(sample_raw_bytes)
    # Row with &quot;R567Z890&quot; → should become R567Z890
    kennziffer_values = [r.kennziffer_ur for r in result.records]
    assert "R567Z890" in kennziffer_values


def test_parse_utf8_umlaut_in_name(sample_raw_bytes: bytes) -> None:
    result = parse_bmf_csv(sample_raw_bytes)
    names = [r.name for r in result.records]
    # Check umlauts are decoded correctly
    assert any("Öhlinger" in n for n in names)
    assert any("Bäcker" in n for n in names)


def test_parse_trailing_space_in_seit_stripped(sample_raw_bytes: bytes) -> None:
    result = parse_bmf_csv(sample_raw_bytes)
    # Second row: Seit is "06.06.2024 " (trailing space) → 2024-06-06
    rec = result.records[1]
    assert rec.seit == "2024-06-06"


def test_parse_empty_all_optionals(sample_raw_bytes: bytes) -> None:
    result = parse_bmf_csv(sample_raw_bytes)
    # Row index 5 has all optional fields empty
    rec = result.records[5]
    assert rec.seit is None
    assert rec.geburtsdatum is None
    assert rec.firmenbuch_nr is None
    assert rec.uid_nr is None
    assert rec.kennziffer_ur is None


def test_parse_wrong_header_raises() -> None:
    bad_csv = b"Wrong~Headers~Here\r\ndata row\r\nStand:  10.02.2026 09:51:32\r\n"
    with pytest.raises(ValueError, match="Unexpected CSV headers"):
        parse_bmf_csv(bad_csv)


def test_parse_wrong_column_count_raises() -> None:
    header = "~".join(EXPECTED_HEADERS).encode("iso-8859-1") + b"\r\n"
    bad_row = b"only~four~fields~here\r\n"
    footer = b"Stand:  10.02.2026 09:51:32\r\n"
    with pytest.raises(ValueError, match="expected 9 fields"):
        parse_bmf_csv(header + bad_row + footer)


def test_parse_missing_stand_raises() -> None:
    header = "~".join(EXPECTED_HEADERS).encode("iso-8859-1") + b"\r\n"
    # No Stand line at all
    with pytest.raises(ValueError, match="Stand:.*not found"):
        parse_bmf_csv(header)


def test_parse_invalid_date_raises() -> None:
    header = "~".join(EXPECTED_HEADERS).encode("iso-8859-1") + b"\r\n"
    bad_date_row = "Bad Name~Addr~99.99.9999~01.01.2024~~~ ~~\r\n".encode("iso-8859-1")
    footer = b"Stand:  10.02.2026 09:51:32\r\n"
    with pytest.raises(ValueError, match="Invalid date format"):
        parse_bmf_csv(header + bad_date_row + footer)


def test_convert_date_valid() -> None:
    assert _convert_date("01.01.2024") == "2024-01-01"
    assert _convert_date("31.12.1999") == "1999-12-31"
    assert _convert_date("  14.12.2023  ") == "2023-12-14"


def test_convert_date_invalid() -> None:
    with pytest.raises(ValueError):
        _convert_date("2024-01-01")  # wrong format
    with pytest.raises(ValueError):
        _convert_date("32.01.2024")  # impossible day
    with pytest.raises(ValueError):
        _convert_date("not-a-date")


def test_parse_firmenbuch_5digit(sample_raw_bytes: bytes) -> None:
    result = parse_bmf_csv(sample_raw_bytes)
    # Row index 4: Firmenbuch-Nr 12345c (5 digits)
    rec = result.records[4]
    assert rec.firmenbuch_nr == "12345c"
