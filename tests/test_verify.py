"""Tests for the cross-format verification module."""

import json
from pathlib import Path

from scheinfirmen_at.convert import write_csv, write_jsonl, write_xml
from scheinfirmen_at.parse import ParseResult, ScheinfirmaRecord
from scheinfirmen_at.schema import write_json_schema, write_xsd
from scheinfirmen_at.verify import verify_outputs, verify_schemas


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


def test_verify_spot_check_single_record(tmp_path: Path) -> None:
    """Spot-check works with only 1 record (only checks first, not last)."""
    result = ParseResult(
        records=[
            ScheinfirmaRecord(
                name="Solo GmbH",
                anschrift="1010 Wien",
                veroeffentlicht="2024-01-01",
                rechtskraeftig="2024-01-01",
                seit=None,
                geburtsdatum=None,
                fbnr=None,
                uid=None,
                kennziffer=None,
            ),
        ],
        stand_datum="2024-01-01",
        stand_zeit="10:00:00",
        raw_row_count=1,
    )
    csv_p, jsonl_p, xml_p, js_p, xsd_p = _write_all(result, tmp_path)
    errors = verify_outputs(csv_p, jsonl_p, xml_p, 1, json_schema_path=js_p, xsd_path=xsd_p)
    assert errors == []


def test_verify_name_mismatch_detected(sample_result: ParseResult, tmp_path: Path) -> None:
    """Spot-check detects when CSV has a different first name than JSONL/XML."""
    csv_p, jsonl_p, xml_p, js_p, xsd_p = _write_all(sample_result, tmp_path)

    # Tamper with CSV: replace the first record name
    content = csv_p.read_text(encoding="utf-8-sig")
    first_name = sample_result.records[0].name
    content = content.replace(first_name, "TAMPERED NAME", 1)
    csv_p.write_text(content, encoding="utf-8-sig")

    errors = verify_outputs(csv_p, jsonl_p, xml_p, sample_result.raw_row_count)
    mismatch = [e for e in errors if "name mismatch" in e]
    assert len(mismatch) > 0


def test_verify_schemas_invalid_xml(tmp_path: Path) -> None:
    """XSD validation reports errors for invalid XML."""
    xsd_p = tmp_path / "schema.xsd"
    xml_p = tmp_path / "bad.xml"
    write_xsd(xsd_p)

    # Write XML missing required 'stand' attribute
    xml_p.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<scheinfirmen>\n'
        '  <scheinfirma anschrift="Wien" veroeffentlicht="2024-01-01" '
        'rechtskraeftig="2024-01-01">Test</scheinfirma>\n'
        '</scheinfirmen>\n',
        encoding="utf-8",
    )

    # Write a valid JSONL so only XML fails
    jsonl_p = tmp_path / "ok.jsonl"
    schema_p = tmp_path / "schema.json"
    write_json_schema(schema_p)
    with jsonl_p.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"_metadata": {"stand": "2024-01-01"}}) + "\n")
        f.write(json.dumps({
            "name": "Test", "anschrift": "Wien",
            "veroeffentlicht": "2024-01-01", "rechtskraeftig": "2024-01-01",
            "seit": None, "geburtsdatum": None, "fbnr": None, "uid": None,
            "kennziffer": None,
        }) + "\n")

    errors = verify_schemas(jsonl_p, xml_p, schema_p, xsd_p)
    xml_errors = [e for e in errors if "XML" in e]
    assert len(xml_errors) > 0


def test_verify_schemas_invalid_jsonl(tmp_path: Path) -> None:
    """JSON Schema validation reports errors for invalid JSONL records."""
    schema_p = tmp_path / "schema.json"
    xsd_p = tmp_path / "schema.xsd"
    write_json_schema(schema_p)
    write_xsd(xsd_p)

    # Write JSONL with invalid record (missing required 'anschrift')
    jsonl_p = tmp_path / "bad.jsonl"
    with jsonl_p.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"_metadata": {"stand": "2024-01-01"}}) + "\n")
        f.write(json.dumps({"name": "Test"}) + "\n")  # missing required fields

    # Write valid XML so only JSONL fails
    xml_p = tmp_path / "ok.xml"
    xml_p.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<scheinfirmen xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:noNamespaceSchemaLocation="scheinfirmen.xsd" '
        'stand="2024-01-01" zeit="10:00:00" '
        'quelle="https://example.com" anzahl="1">\n'
        '  <scheinfirma anschrift="Wien" veroeffentlicht="2024-01-01" '
        'rechtskraeftig="2024-01-01">Test</scheinfirma>\n'
        '</scheinfirmen>\n',
        encoding="utf-8",
    )

    errors = verify_schemas(jsonl_p, xml_p, schema_p, xsd_p)
    jsonl_errors = [e for e in errors if "JSONL" in e]
    assert len(jsonl_errors) > 0
