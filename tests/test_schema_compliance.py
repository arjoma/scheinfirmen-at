"""Tests to verify that output files comply with their respective schemas."""

import json
from typing import Any

import jsonschema  # type: ignore
import pytest
from lxml import etree  # type: ignore

from scheinfirmen_at.convert import write_jsonl, write_xml
from scheinfirmen_at.parse import ParseResult, ScheinfirmaRecord
from scheinfirmen_at.schema import write_json_schema, write_xsd


@pytest.fixture

def sample_result() -> ParseResult:

    """Create a sample ParseResult with valid data."""

    records = [

        ScheinfirmaRecord(

            name="Musterfirma GmbH",

            anschrift="1010 Wien, Graben 1",

            veroeffentlichung="2023-01-01",

            rechtskraeftig="2023-01-01",

            seit="2022-12-01",

            geburtsdatum=None,

            firmenbuch_nr="123456x",

            uid_nr="ATU12345678",

            kennziffer_ur="K123456",

        ),

        ScheinfirmaRecord(

            name="Max Mustermann",

            anschrift="8010 Graz, Hauptplatz 1",

            veroeffentlichung="2023-02-01",

            rechtskraeftig="2023-02-15",

            seit=None,

            geburtsdatum="1980-05-20",

            firmenbuch_nr=None,

            uid_nr=None,

            kennziffer_ur=None,

        )

    ]

    return ParseResult(

        records=records,

        stand_datum="2023-05-01",

        stand_zeit="03:00:00",

        raw_row_count=len(records)

    )



def test_xml_matches_xsd(tmp_path: Any, sample_result: ParseResult) -> None:

    """Generate XML and XSD, then validate using lxml."""

    xml_file = tmp_path / "data.xml"

    xsd_file = tmp_path / "schema.xsd"



    # Generate files

    write_xml(sample_result, xml_file)

    write_xsd(xsd_file)



    # Load Schema

    xmlschema_doc = etree.parse(str(xsd_file))

    xmlschema = etree.XMLSchema(xmlschema_doc)



    # Load XML

    doc = etree.parse(str(xml_file))



    # Validate

    xmlschema.assertValid(doc)

    assert xmlschema.validate(doc) is True



def test_jsonl_matches_json_schema(tmp_path: Any, sample_result: ParseResult) -> None:

    """Generate JSONL and JSON Schema, then validate using jsonschema."""

    jsonl_file = tmp_path / "data.jsonl"

    schema_file = tmp_path / "schema.json"



    # Generate files

    write_jsonl(sample_result, jsonl_file)

    write_json_schema(schema_file)



    # Load Schema

    with open(schema_file, encoding="utf-8") as f:

        schema = json.load(f)



    # Validate each line

    with open(jsonl_file, encoding="utf-8") as f:

        # First line is metadata - check if it looks correct, but it's not the Record schema

        meta_line = f.readline()

        meta = json.loads(meta_line)

        assert "_metadata" in meta

        assert "$schema" in meta

        assert meta["$schema"] == "https://raw.githubusercontent.com/arjoma/scheinfirmen-at/main/data/scheinfirmen.json-schema.json"



        # Subsequent lines are records

        for line in f:

            record = json.loads(line)

            # This throws ValidationError if invalid

            jsonschema.validate(instance=record, schema=schema)


