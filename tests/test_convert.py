"""Tests for the convert module."""

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from scheinfirmen_at.convert import write_csv, write_jsonl, write_xml
from scheinfirmen_at.parse import ParseResult


def test_write_csv_row_count(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.csv"
    n = write_csv(sample_result, path)
    assert n == sample_result.raw_row_count

    with path.open(encoding="utf-8-sig", newline="") as f:
        lines = f.readlines()

    # Skip comment line and header
    data_lines = [ln for ln in lines if not ln.startswith("#") and ln.strip()]
    assert len(data_lines) == sample_result.raw_row_count + 1  # +1 for header row


def test_write_csv_utf8_bom(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.csv"
    write_csv(sample_result, path)
    raw = path.read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf", "CSV file must start with UTF-8 BOM"


def test_write_csv_stand_comment(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.csv"
    write_csv(sample_result, path)
    with path.open(encoding="utf-8-sig") as f:
        first_line = f.readline()
    assert first_line.startswith("# Stand:")
    assert sample_result.stand_datum in first_line


def test_write_csv_valid_csv(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.csv"
    write_csv(sample_result, path)
    with path.open(encoding="utf-8-sig", newline="") as f:
        # Skip comment
        reader = csv.reader(ln for ln in f if not ln.startswith("#"))
        rows = list(reader)
    assert len(rows) == sample_result.raw_row_count + 1  # header + data


def test_write_csv_german_headers(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.csv"
    write_csv(sample_result, path)
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(ln for ln in f if not ln.startswith("#"))
        header = next(reader)
    assert "Name" in header
    assert "UID-Nr." in header
    assert "Anschrift" in header


def test_write_csv_umlaut_preserved(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.csv"
    write_csv(sample_result, path)
    content = path.read_text(encoding="utf-8-sig")
    assert "Öhlinger" in content or "Bäcker" in content


def test_write_csv_empty_optional_as_empty_string(
    sample_result: ParseResult, tmp_path: Path
) -> None:
    path = tmp_path / "out.csv"
    write_csv(sample_result, path)
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(ln for ln in f if not ln.startswith("#"))
        rows = list(reader)
    # At least one row should have empty optional fields
    has_empty = any(row["Geburts-Datum"] == "" for row in rows)
    assert has_empty


def test_write_jsonl_row_count(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.jsonl"
    n = write_jsonl(sample_result, path)
    assert n == sample_result.raw_row_count

    with path.open(encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    data_lines = [ln for ln in lines if "_metadata" not in ln]
    assert len(data_lines) == sample_result.raw_row_count


def test_write_jsonl_metadata_first_line(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.jsonl"
    write_jsonl(sample_result, path)
    with path.open(encoding="utf-8") as f:
        first = json.loads(f.readline())
    assert "_metadata" in first
    assert "stand" in first["_metadata"]
    assert "count" in first["_metadata"]
    assert first["_metadata"]["count"] == sample_result.raw_row_count


def test_write_jsonl_valid_json_per_line(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.jsonl"
    write_jsonl(sample_result, path)
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                obj = json.loads(line)  # Must not raise
                assert isinstance(obj, dict)


def test_write_jsonl_null_for_none_fields(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.jsonl"
    write_jsonl(sample_result, path)
    with path.open(encoding="utf-8") as f:
        records = [
            json.loads(ln)
            for ln in f
            if ln.strip() and "_metadata" not in ln
        ]
    # At least one record should have null geburtsdatum
    has_null = any(r.get("geburtsdatum") is None for r in records)
    assert has_null


def test_write_jsonl_umlaut_preserved(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.jsonl"
    write_jsonl(sample_result, path)
    content = path.read_text(encoding="utf-8")
    assert "Öhlinger" in content or "Bäcker" in content


def test_write_xml_row_count(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.xml"
    n = write_xml(sample_result, path)
    assert n == sample_result.raw_row_count

    tree = ET.parse(path)
    root = tree.getroot()
    assert len(root.findall("eintrag")) == sample_result.raw_row_count


def test_write_xml_root_attributes(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.xml"
    write_xml(sample_result, path)
    tree = ET.parse(path)
    root = tree.getroot()
    assert root.tag == "scheinfirmen"
    assert root.get("stand") == sample_result.stand_datum
    assert root.get("zeit") == sample_result.stand_zeit
    assert root.get("anzahl") == str(sample_result.raw_row_count)


def test_write_xml_well_formed(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.xml"
    write_xml(sample_result, path)
    # ET.parse raises xml.etree.ElementTree.ParseError on malformed XML
    tree = ET.parse(path)
    assert tree is not None


def test_write_xml_empty_optional_elements(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.xml"
    write_xml(sample_result, path)
    tree = ET.parse(path)
    root = tree.getroot()
    # At least one eintrag should have an empty geburtsdatum element
    has_empty = any(
        (e := entry.find("geburtsdatum")) is not None and (e.text is None or e.text == "")
        for entry in root.findall("eintrag")
    )
    assert has_empty


def test_write_xml_umlaut_preserved(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.xml"
    write_xml(sample_result, path)
    content = path.read_bytes().decode("utf-8")
    assert "Öhlinger" in content or "Bäcker" in content


def test_write_xml_declaration(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "out.xml"
    write_xml(sample_result, path)
    raw = path.read_bytes()
    assert raw.startswith(b"<?xml")


def test_write_csv_creates_parent_dir(sample_result: ParseResult, tmp_path: Path) -> None:
    path = tmp_path / "subdir" / "out.csv"
    write_csv(sample_result, path)
    assert path.exists()
