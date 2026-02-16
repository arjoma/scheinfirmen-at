# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""JSON Schema, XSD, and CSVW metadata definitions for Scheinfirma data."""

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
    "required": ["name", "anschrift", "veroeffentlicht", "rechtskraeftig"],
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
        "veroeffentlicht": {
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
        "fbnr": {
            "type": ["string", "null"],
            "description": "Company register number (Firmenbuchnummer)",
            "pattern": r"^\d{5,6}[a-zA-Z]$",
        },
        "uid": {
            "type": ["string", "null"],
            "description": "VAT identification number (UID-Nummer)",
            "pattern": r"^ATU\d{8}$",
        },
        "kennziffer": {
            "type": ["string", "null"],
            "description": (
                "Register reference code (Kennziffer des Unternehmensregisters)"
            ),
        },
    },
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
    "dc:license": {"@id": "https://creativecommons.org/publicdomain/mark/1.0/"},
    "dialect": {
        "encoding": "utf-8",
        "lineTerminators": ["\r\n", "\n"],
        "header": True,
        "skipRows": 0,
    },
    "tableSchema": {
        "columns": [
            {
                "name": "name",
                "titles": "Name",
                "datatype": "string",
                "required": True,
                "dc:description": "Name des Unternehmens oder der natürlichen Person",
            },
            {
                "name": "anschrift",
                "titles": "Anschrift",
                "datatype": "string",
                "required": True,
                "dc:description": "Adresse (PLZ Ort, Straße Nr)",
            },
            {
                "name": "veroeffentlicht",
                "titles": "Veröffentlichung",
                "datatype": {"base": "date", "format": "yyyy-MM-dd"},
                "required": True,
                "dc:description": "Veröffentlichungsdatum",
            },
            {
                "name": "rechtskraeftig",
                "titles": "Rechtskräftig",
                "datatype": {"base": "date", "format": "yyyy-MM-dd"},
                "required": True,
                "dc:description": "Datum der Rechtskraft des Bescheids",
            },
            {
                "name": "seit",
                "titles": "Seit",
                "datatype": {"base": "date", "format": "yyyy-MM-dd"},
                "required": False,
                "dc:description": "Zeitpunkt als Scheinunternehmen",
            },
            {
                "name": "geburtsdatum",
                "titles": "Geburts-Datum",
                "datatype": {"base": "date", "format": "yyyy-MM-dd"},
                "required": False,
                "dc:description": "Geburtsdatum (nur bei natürlichen Personen)",
            },
            {
                "name": "fbnr",
                "titles": "Firmenbuch-Nr",
                "datatype": "string",
                "required": False,
                "dc:description": "Firmenbuchnummer",
            },
            {
                "name": "uid",
                "titles": "UID-Nr.",
                "datatype": "string",
                "required": False,
                "dc:description": "UID-Nummer (Umsatzsteuer-Identifikationsnummer)",
            },
            {
                "name": "kennziffer",
                "titles": "Kennziffer des UR",
                "datatype": "string",
                "required": False,
                "dc:description": "Kennziffer des Unternehmensregisters",
            },
        ],
    },
}

# XSD schema
XSD_CONTENT = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">

  <xs:element name="scheinfirmen">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="scheinfirma" type="ScheinfirmaType" maxOccurs="unbounded"/>
      </xs:sequence>
      <xs:attribute name="stand"   type="xs:date"            use="required"/>
      <xs:attribute name="zeit"    type="xs:time"            use="required"/>
      <xs:attribute name="quelle"  type="xs:anyURI"          use="required"/>
      <xs:attribute name="anzahl"  type="xs:positiveInteger" use="required"/>
    </xs:complexType>
  </xs:element>

  <xs:complexType name="ScheinfirmaType">
    <xs:simpleContent>
      <xs:extension base="xs:string">
        <xs:attribute name="anschrift"      type="xs:string" use="required"/>
        <xs:attribute name="veroeffentlicht"      type="xs:date"   use="required"/>
        <xs:attribute name="rechtskraeftig" type="xs:date"   use="required"/>
        <xs:attribute name="seit"           type="xs:date"/>
        <xs:attribute name="geburtsdatum"   type="xs:date"/>
        <xs:attribute name="fbnr"           type="xs:string"/>
        <xs:attribute name="uid"            type="xs:string"/>
        <xs:attribute name="kennziffer"     type="xs:string"/>
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
