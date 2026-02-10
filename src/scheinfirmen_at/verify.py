# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Cross-format verification: re-read all output files and check consistency."""

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def verify_outputs(
    csv_path: str | Path,
    jsonl_path: str | Path,
    xml_path: str | Path,
    expected_count: int,
    json_schema_path: str | Path | None = None,
    xsd_path: str | Path | None = None,
) -> list[str]:
    """Verify all output files for record counts, spot-checks, and schema compliance.

    Checks:
    1. CSV: count data rows (skip # comment lines and header row)
    2. JSONL: count non-metadata lines (skip lines with _metadata key)
    3. XML: count <scheinfirma> elements
    4. All three counts must equal expected_count
    5. Spot-check: first and last record's name must match across all formats
    6. If schema paths are provided, validate JSONL and XML against them.

    Returns a list of error messages. An empty list means all checks passed.
    """
    errors: list[str] = []

    csv_count, csv_names = _count_csv(Path(csv_path))
    jsonl_count, jsonl_names = _count_jsonl(Path(jsonl_path))
    xml_count, xml_names = _count_xml(Path(xml_path))

    # Count checks
    for fmt, count in [("CSV", csv_count), ("JSONL", jsonl_count), ("XML", xml_count)]:
        if count != expected_count:
            errors.append(f"{fmt}: expected {expected_count} records, found {count}")

    # Spot-check names
    if csv_names and jsonl_names and xml_names:
        for idx, label in [(0, "First"), (-1, "Last")]:
            names = {"CSV": csv_names[idx], "JSONL": jsonl_names[idx], "XML": xml_names[idx]}
            if len(set(names.values())) > 1:
                errors.append(f"{label} record name mismatch across formats: {names}")

    # Schema validation
    if json_schema_path and xsd_path:
        errors.extend(verify_schemas(jsonl_path, xml_path, json_schema_path, xsd_path))

    return errors


def verify_schemas(
    jsonl_path: str | Path,
    xml_path: str | Path,
    json_schema_path: str | Path,
    xsd_path: str | Path,
) -> list[str]:
    """Validate JSONL and XML files against their schemas.

    Requires 'jsonschema' and 'lxml' packages. If not installed, this check is skipped
    unless in a development/CI context.
    """
    errors: list[str] = []

    # XML Validation
    try:
        from lxml import etree  # type: ignore

        try:
            xsd_doc = etree.parse(str(xsd_path))
            xml_doc = etree.parse(str(xml_path))
            schema = etree.XMLSchema(xsd_doc)
            if not schema.validate(xml_doc):
                for err in schema.error_log:
                    errors.append(f"XML Schema Error: {err.message} (line {err.line})")
        except Exception as exc:
            errors.append(f"XML Validation failed to run: {exc}")
    except ImportError:
        pass  # Optional dependency

    # JSONL Validation
    try:
        import jsonschema  # type: ignore

        try:
            with open(json_schema_path, encoding="utf-8") as f:
                schema = json.load(f)
            with open(jsonl_path, encoding="utf-8") as f:
                for _i, line in enumerate(f, 1):
                    obj = json.loads(line)
                    if "$schema" in obj:
                        continue
                    jsonschema.validate(instance=obj, schema=schema)
        except Exception as exc:
            errors.append(f"JSONL Validation failed: {exc}")
    except ImportError:
        pass  # Optional dependency

    return errors


def _count_csv(path: Path) -> tuple[int, list[str]]:
    """Return (data row count, [first_name, last_name]) from a CSV output file."""
    names: list[str] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        # Filter out comment lines, pass remaining lines to csv.DictReader
        non_comment_lines = [line for line in f if not line.startswith("#")]
    reader = csv.DictReader(non_comment_lines)
    for row in reader:
        names.append(row.get("Name", ""))
    count = len(names)
    return count, ([names[0], names[-1]] if len(names) >= 2 else names)


def _count_jsonl(path: Path) -> tuple[int, list[str]]:
    """Return (data row count, [first_name, last_name]) from a JSONL output file."""
    names: list[str] = []
    count = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "_metadata" in obj:
                continue
            count += 1
            names.append(obj.get("name", ""))
    return count, ([names[0], names[-1]] if len(names) >= 2 else names)


def _count_xml(path: Path) -> tuple[int, list[str]]:
    """Return (data row count, [first_name, last_name]) from an XML output file."""
    tree = ET.parse(path)
    root = tree.getroot()
    entries = root.findall("scheinfirma")
    names: list[str] = [entry.text or "" for entry in entries]
    count = len(entries)
    return count, ([names[0], names[-1]] if len(names) >= 2 else names)
