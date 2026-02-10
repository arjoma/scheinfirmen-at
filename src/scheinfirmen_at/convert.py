"""Convert Scheinfirma records to CSV, JSONL, and XML output formats."""

import csv
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

from scheinfirmen_at.download import BMF_URL
from scheinfirmen_at.parse import ParseResult, ScheinfirmaRecord

# Human-readable German header names for CSV output
CSV_HEADERS = [
    "Name",
    "Anschrift",
    "Veröffentlichung",
    "Rechtskräftig",
    "Seit",
    "Geburts-Datum",
    "Firmenbuch-Nr",
    "UID-Nr.",
    "Kennziffer des UR",
]

# Mapping from dataclass field names to CSV/JSON keys
_FIELD_ORDER = [
    "name",
    "anschrift",
    "veroeffentlicht",
    "rechtskraeftig",
    "seit",
    "geburtsdatum",
    "fbnr",
    "uid",
    "kennziffer",
]


def _record_to_dict(rec: ScheinfirmaRecord) -> dict[str, str | None]:
    """Convert a ScheinfirmaRecord to an ordered dict."""
    d = asdict(rec)
    return {k: d[k] for k in _FIELD_ORDER}


def write_csv(result: ParseResult, output: str | Path) -> int:
    """Write records to a UTF-8 CSV file (with BOM for Excel compatibility).

    Format:
    - Line 1: # Stand: YYYY-MM-DD HH:MM:SS  (comment)
    - Line 2: header row (German column names)
    - Lines 3+: data rows, comma-delimited, quoted as needed
    - None fields are written as empty strings

    Returns number of data rows written.
    """
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        # Write Stand comment (utf-8-sig adds BOM automatically before this)
        f.write(f"# Stand: {result.stand_datum} {result.stand_zeit}\n")

        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(CSV_HEADERS)

        for rec in result.records:
            row = [v if v is not None else "" for v in _record_to_dict(rec).values()]
            writer.writerow(row)

    return len(result.records)


def write_jsonl(result: ParseResult, output: str | Path) -> int:
    """Write records to a JSONL file (one JSON object per line).

    Format:
    - Line 1: metadata object with _metadata key
    - Lines 2+: one compact JSON object per record (None → null)

    Returns number of data rows written.
    """
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        metadata = {
            "$schema": "https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.json-schema.json",
            "_metadata": {
                "stand": f"{result.stand_datum}T{result.stand_zeit}",
                "source": BMF_URL,
                "count": result.raw_row_count,
            },
        }
        f.write(json.dumps(metadata, ensure_ascii=False) + "\n")

        for rec in result.records:
            obj = _record_to_dict(rec)
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    return len(result.records)


def write_xml(result: ParseResult, output: str | Path) -> int:
    """Write records to a pretty-printed XML file.

    Structure:
        <scheinfirmen xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                      xsi:noNamespaceSchemaLocation="..."
                      stand="YYYY-MM-DD" zeit="HH:MM:SS"
                      quelle="..." anzahl="N">
          <scheinfirma anschrift="..." published="..." ...>Name</scheinfirma>
        </scheinfirmen>

    Each record is a <scheinfirma> element with the name as text content
    and all other fields as attributes. Null fields are omitted.

    Returns number of records written.
    """
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element("scheinfirmen")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set(
        "xsi:noNamespaceSchemaLocation",
        "https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.xsd",
    )
    root.set("stand", result.stand_datum)
    root.set("zeit", result.stand_zeit)
    root.set("quelle", BMF_URL)
    root.set("anzahl", str(result.raw_row_count))

    for rec in result.records:
        attribs = {}
        for field_name, value in _record_to_dict(rec).items():
            if field_name == "name" or value is None:
                continue
            attribs[field_name] = value
        elem = ET.SubElement(root, "scheinfirma", attribs)
        elem.text = rec.name

    ET.indent(root, space="  ")
    tree = ET.ElementTree(root)

    with path.open("wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

    return len(result.records)
