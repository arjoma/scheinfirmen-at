"""JSON Schema and XSD definitions for Scheinfirma data."""

import json
from pathlib import Path

# JSON Schema (Draft 2020-12)
JSON_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": (
        "https://raw.githubusercontent.com/arjoma/"
        "scheinfirmen-at/main/data/scheinfirmen.json-schema.json"
    ),
    "title": "Scheinfirma",
    "description": (
        "A company or person listed on the Austrian BMF Scheinfirmen "
        "(shell company) list"
    ),
    "type": "object",
    "required": ["name", "anschrift", "veroeffentlichung", "rechtskraeftig"],
    "additionalProperties": False,
    "properties": {
        "name": {
            "type": "string",
            "description": "Name of the company or natural person",
            "minLength": 1,
        },
        "anschrift": {
            "type": "string",
            "description": "Address (PLZ Ort, Strasse Nr)",
            "minLength": 1,
        },
        "veroeffentlichung": {
            "type": "string",
            "format": "date",
            "description": "Publication date (ISO 8601)",
        },
        "rechtskraeftig": {
            "type": "string",
            "format": "date",
            "description": "Date the decree became legally binding (ISO 8601)",
        },
        "seit": {
            "type": ["string", "null"],
            "format": "date",
            "description": "Date designated as shell company (ISO 8601)",
        },
        "geburtsdatum": {
            "type": ["string", "null"],
            "format": "date",
            "description": "Birth date for natural persons (ISO 8601)",
        },
        "firmenbuch_nr": {
            "type": ["string", "null"],
            "description": "Company register number (Firmenbuchnummer)",
            "pattern": r"^\d{5,6}[a-zA-Z]$",
        },
        "uid_nr": {
            "type": ["string", "null"],
            "description": "VAT identification number (UID-Nummer)",
            "pattern": r"^ATU\d{8}$",
        },
        "kennziffer_ur": {
            "type": ["string", "null"],
            "description": (
                "Register reference code (Kennziffer des Unternehmensregisters)"
            ),
        },
    },
}

# XSD schema
XSD_CONTENT = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">

  <xs:element name="scheinfirmen">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="eintrag" type="EintragType" maxOccurs="unbounded"/>
      </xs:sequence>
      <xs:attribute name="stand"   type="xs:date"         use="required"/>
      <xs:attribute name="zeit"    type="xs:time"         use="required"/>
      <xs:attribute name="quelle"  type="xs:anyURI"       use="required"/>
      <xs:attribute name="anzahl"  type="xs:positiveInteger" use="required"/>
    </xs:complexType>
  </xs:element>

  <xs:complexType name="EintragType">
    <xs:all>
      <xs:element name="name"                        type="xs:string"/>
      <xs:element name="anschrift"                   type="xs:string"/>
      <xs:element name="veroeffentlichung"           type="xs:date"/>
      <xs:element name="rechtskraeftig"             type="xs:date"/>
      <xs:element name="seit"                        type="OptionalDate"  minOccurs="0"/>
      <xs:element name="geburtsdatum"                type="OptionalDate"  minOccurs="0"/>
      <xs:element name="firmenbuch_nr"               type="OptionalString" minOccurs="0"/>
      <xs:element name="uid_nr"                      type="OptionalString" minOccurs="0"/>
      <xs:element name="kennziffer_ur"               type="OptionalString" minOccurs="0"/>
    </xs:all>
  </xs:complexType>

  <xs:complexType name="OptionalDate">
    <xs:simpleContent>
      <xs:extension base="xs:string">
        <xs:anyAttribute namespace="##other" processContents="lax"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:simpleType name="OptionalString">
    <xs:restriction base="xs:string"/>
  </xs:simpleType>

</xs:schema>
"""


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
