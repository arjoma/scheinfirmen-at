# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Convert Scheinfirma records to CSV, JSONL, and XML output formats."""

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from scheinfirmen_at.download import BMF_URL
from scheinfirmen_at.fields import FIELDS
from scheinfirmen_at.parse import ParseResult
from scheinfirmen_at.schema import JSON_SCHEMA_URL, XSD_URL

# Human-readable German header names for CSV output
CSV_HEADERS = [f.csv_title for f in FIELDS]


def write_csv(result: ParseResult, output: str | Path) -> int:
    """Write records to a UTF-8 CSV file (with BOM for Excel compatibility).

    Format:
    - Line 1: header row (German column names)
    - Lines 2+: data rows, comma-delimited, quoted as needed
    - None fields are written as empty strings

    Returns number of data rows written.
    """
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(CSV_HEADERS)

        for rec in result.records:
            writer.writerow(["" if v is None else v for v in rec.to_dict().values()])

    return len(result.records)


def write_jsonl(
    result: ParseResult, output: str | Path, geaendert: str | None = None
) -> int:
    """Write records to a JSONL file (one JSON object per line).

    Format:
    - Line 1: metadata object with ``$schema`` and ``_metadata`` keys.
      ``stand`` is the BMF timestamp (= download time); ``geaendert`` is the
      time the record data last changed (defaults to ``stand``).
    - Lines 2+: one compact JSON object per record (None → null)

    Returns number of data rows written.
    """
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        metadata = {
            "$schema": JSON_SCHEMA_URL,
            "_metadata": {
                "stand": result.stand,
                "geaendert": geaendert or result.stand,
                "source": BMF_URL,
                "count": len(result.records),
            },
        }
        f.write(json.dumps(metadata, ensure_ascii=False) + "\n")

        for rec in result.records:
            f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

    return len(result.records)


def write_xml(
    result: ParseResult, output: str | Path, geaendert: str | None = None
) -> int:
    """Write records to a pretty-printed XML file.

    Structure:
        <scheinfirmen xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                      xsi:noNamespaceSchemaLocation="..."
                      stand="YYYY-MM-DD" zeit="HH:MM:SS"
                      geaendert="YYYY-MM-DDTHH:MM:SS"
                      quelle="..." anzahl="N">
          <scheinfirma anschrift="..." veroeffentlicht="..." ...>Name</scheinfirma>
        </scheinfirmen>

    Each record is a <scheinfirma> element with the name as text content
    and all other fields as attributes. Null fields are omitted.

    Returns number of records written.
    """
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element("scheinfirmen")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xsi:noNamespaceSchemaLocation", XSD_URL)
    root.set("stand", result.stand_datum)
    root.set("zeit", result.stand_zeit)
    root.set("geaendert", geaendert or result.stand)
    root.set("quelle", BMF_URL)
    root.set("anzahl", str(len(result.records)))

    for rec in result.records:
        attribs = {k: v for k, v in rec.to_dict().items() if k != "name" and v is not None}
        elem = ET.SubElement(root, "scheinfirma", attribs)
        elem.text = rec.name

    ET.indent(root, space="  ")
    tree = ET.ElementTree(root)

    with path.open("wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

    return len(result.records)
