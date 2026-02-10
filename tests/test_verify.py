"""Tests for the cross-format verification module."""

from pathlib import Path

from scheinfirmen_at.convert import write_csv, write_jsonl, write_xml
from scheinfirmen_at.parse import ParseResult
from scheinfirmen_at.schema import write_json_schema, write_xsd
from scheinfirmen_at.verify import verify_outputs


def _write_all(result: ParseResult, out: Path) -> tuple[Path, Path, Path, Path, Path]:
    csv_p = out / "scheinfirmen.csv"
    jsonl_p = out / "scheinfirmen.jsonl"
    xml_p = out / "scheinfirmen.xml"
    js_p = out / "scheinfirmen.json-schema.json"
    xsd_p = out / "scheinfirmen.xsd"

    write_csv(result, csv_p)
    write_jsonl(result, jsonl_p)
    write_xml(result, xml_p)
    write_json_schema(js_p)
    write_xsd(xsd_p)

    return csv_p, jsonl_p, xml_p, js_p, xsd_p


def test_verify_matching_counts(sample_result: ParseResult, tmp_path: Path) -> None:
    csv_p, jsonl_p, xml_p, js_p, xsd_p = _write_all(sample_result, tmp_path)
    errors = verify_outputs(
        csv_p, jsonl_p, xml_p, sample_result.raw_row_count, json_schema_path=js_p, xsd_path=xsd_p
    )
    assert errors == [], f"Unexpected errors: {errors}"


def test_verify_detects_wrong_expected_count(
    sample_result: ParseResult, tmp_path: Path
) -> None:
    csv_p, jsonl_p, xml_p, js_p, xsd_p = _write_all(sample_result, tmp_path)
    # Claim we expect more rows than actually written
    errors = verify_outputs(
        csv_p,
        jsonl_p,
        xml_p,
        sample_result.raw_row_count + 100,
        json_schema_path=js_p,
        xsd_path=xsd_p,
    )
    assert len(errors) > 0


def test_verify_spot_check_names(sample_result: ParseResult, tmp_path: Path) -> None:
    csv_p, jsonl_p, xml_p, js_p, xsd_p = _write_all(sample_result, tmp_path)
    errors = verify_outputs(
        csv_p, jsonl_p, xml_p, sample_result.raw_row_count, json_schema_path=js_p, xsd_path=xsd_p
    )
    # Spot-check errors should not appear when data is consistent
    spot_errors = [e for e in errors if "name mismatch" in e]
    assert spot_errors == []
