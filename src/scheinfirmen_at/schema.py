# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""JSON Schema, XSD, and CSVW metadata definitions for Scheinfirma data."""

import json
from pathlib import Path

from scheinfirmen_at.fields import FIELDS, Field

JSON_SCHEMA_URL = (
    "https://raw.githubusercontent.com/arjoma/"
    "scheinfirmen-at/main/data/scheinfirmen.json-schema.json"
)
XSD_URL = "https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.xsd"

# The BMF states no licence for the list. It is published under a statutory
# obligation (§ 8 SBBG); as an official announcement it is most likely not
# protected by copyright (§ 7 UrhG). We state exactly that — no more.
DATA_RIGHTS_DE = (
    "Amtliche Veröffentlichung des BMF gemäß § 8 SBBG. Das BMF gibt keine "
    "ausdrückliche Lizenz an; als amtliche Bekanntmachung genießt die Liste "
    "voraussichtlich keinen urheberrechtlichen Schutz (§ 7 UrhG). "
    "Rechtsverbindlich ist ausschließlich die Liste auf der BMF-Website."
)


def _json_property(f: Field) -> dict[str, object]:
    prop: dict[str, object] = {"type": "string" if f.required else ["string", "null"]}
    if f.kind == "date":
        prop["format"] = "date"
    prop["description"] = f.description_en
    if f.required and f.kind == "string":
        prop["minLength"] = 1
    return prop


def _csvw_column(f: Field) -> dict[str, object]:
    datatype: object = (
        {"base": "date", "format": "yyyy-MM-dd"} if f.kind == "date" else "string"
    )
    return {
        "name": f.name,
        "titles": f.csv_title,
        "datatype": datatype,
        "required": f.required,
        "dc:description": f.description_de,
    }


def _xsd_attribute(f: Field) -> str:
    xs_type = "xs:date" if f.kind == "date" else "xs:string"
    use = ' use="required"' if f.required else ""
    return f'        <xs:attribute name="{f.name}" type="{xs_type}"{use}/>'


# JSON Schema (Draft 2020-12)
JSON_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": JSON_SCHEMA_URL,
    "title": "Scheinfirma",
    "description": (
        "A company or person listed on the Austrian BMF Scheinfirmen "
        "(shell company) list"
    ),
    "type": "object",
    "required": [f.name for f in FIELDS if f.required],
    "additionalProperties": False,
    "properties": {f.name: _json_property(f) for f in FIELDS},
}

# CSVW metadata (W3C CSV on the Web)
# See: https://www.w3.org/TR/tabular-data-primer/
CSVW_METADATA: dict[str, object] = {
    "@context": "http://www.w3.org/ns/csvw",
    "url": "scheinfirmen.csv",
    "dc:title": "Scheinfirmenliste Österreich",
    "dc:description": (
        "Liste der Scheinunternehmen gemäß § 8 SBBG, "
        "veröffentlicht vom BMF Österreich"
    ),
    "dc:source": "https://service.bmf.gv.at/service/allg/lsu/",
    "dc:rights": DATA_RIGHTS_DE,
    "dialect": {
        "encoding": "utf-8",
        "lineTerminators": ["\r\n", "\n"],
        "header": True,
        "skipRows": 0,
    },
    "tableSchema": {"columns": [_csvw_column(f) for f in FIELDS]},
}

# XSD schema. The first field (name) is the element's text content; all
# other fields are attributes.
_XSD_ATTRIBUTES = "\n".join(_xsd_attribute(f) for f in FIELDS[1:])
XSD_CONTENT = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">

  <xs:element name="scheinfirmen">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="scheinfirma" type="ScheinfirmaType" maxOccurs="unbounded"/>
      </xs:sequence>
      <xs:attribute name="stand" type="xs:date" use="required"/>
      <xs:attribute name="zeit" type="xs:time" use="required"/>
      <xs:attribute name="geaendert" type="xs:dateTime"/>
      <xs:attribute name="quelle" type="xs:anyURI" use="required"/>
      <xs:attribute name="anzahl" type="xs:positiveInteger" use="required"/>
    </xs:complexType>
  </xs:element>

  <xs:complexType name="ScheinfirmaType">
    <xs:simpleContent>
      <xs:extension base="xs:string">
{_XSD_ATTRIBUTES}
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

</xs:schema>
"""


def write_csvw_metadata(output: str | Path) -> None:
    """Write the CSVW metadata to a file."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(CSVW_METADATA, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_json_schema(output: str | Path) -> None:
    """Write the JSON Schema to a file."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(JSON_SCHEMA, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_xsd(output: str | Path) -> None:
    """Write the XSD schema to a file."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(XSD_CONTENT, encoding="utf-8")
