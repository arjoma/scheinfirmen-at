# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""The central field table must stay in sync with the dataclass and docs."""

from dataclasses import fields
from pathlib import Path

from scheinfirmen_at.convert import CSV_HEADERS
from scheinfirmen_at.fields import FIELD_NAMES, FIELDS
from scheinfirmen_at.parse import EXPECTED_HEADERS, ScheinfirmaRecord
from scheinfirmen_at.schema import CSVW_METADATA, JSON_SCHEMA, XSD_CONTENT

README = Path(__file__).parent.parent / "README.md"


def test_dataclass_matches_field_table() -> None:
    assert tuple(f.name for f in fields(ScheinfirmaRecord)) == FIELD_NAMES


def test_derived_headers() -> None:
    assert EXPECTED_HEADERS[2] == "Veröffentlichung"
    assert CSV_HEADERS[3] == "Rechtskräftig"
    assert len(EXPECTED_HEADERS) == len(CSV_HEADERS) == len(FIELDS)


def test_schemas_cover_all_fields() -> None:
    props = JSON_SCHEMA["properties"]
    assert isinstance(props, dict)
    assert tuple(props) == FIELD_NAMES
    table = CSVW_METADATA["tableSchema"]
    assert isinstance(table, dict)
    assert tuple(c["name"] for c in table["columns"]) == FIELD_NAMES
    for name in FIELD_NAMES[1:]:  # name is the element text, not an attribute
        assert f'name="{name}"' in XSD_CONTENT


def test_readme_documents_all_fields() -> None:
    readme = README.read_text(encoding="utf-8")
    for name in FIELD_NAMES:
        assert f"| `{name}` |" in readme
