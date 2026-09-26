# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Single source of truth for the Scheinfirma record fields.

Parser headers, CSV column titles, JSON Schema, CSVW metadata and XSD are
all derived from :data:`FIELDS`, so adding or renaming a field happens here
and nowhere else (plus the :class:`~scheinfirmen_at.parse.ScheinfirmaRecord`
dataclass, which a test keeps in sync).
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Field:
    """Definition of one output field."""

    name: str  # key in JSON/XML, attribute name in dataclass
    bmf_header: str  # column header in the BMF source CSV (after strip)
    csv_title: str  # column header in our CSV output
    kind: Literal["string", "date"]
    required: bool
    description_en: str  # JSON Schema description
    description_de: str  # CSVW description


FIELDS: tuple[Field, ...] = (
    Field(
        name="name",
        bmf_header="Name",
        csv_title="Name",
        kind="string",
        required=True,
        description_en="Name of the company or natural person",
        description_de="Name des Unternehmens oder der natürlichen Person",
    ),
    Field(
        name="anschrift",
        bmf_header="Anschrift",
        csv_title="Anschrift",
        kind="string",
        required=True,
        description_en="Address (PLZ Ort, Strasse Nr)",
        description_de="Adresse (PLZ Ort, Straße Nr)",
    ),
    Field(
        name="veroeffentlicht",
        bmf_header="Veröffentlichung",
        csv_title="Veröffentlichung",
        kind="date",
        required=True,
        description_en="Publication date (ISO 8601)",
        description_de="Veröffentlichungsdatum",
    ),
    Field(
        name="rechtskraeftig",
        bmf_header="Rechtskraft Bescheid",
        csv_title="Rechtskräftig",
        kind="date",
        required=True,
        description_en="Date the decree became legally binding (ISO 8601)",
        description_de="Datum der Rechtskraft des Bescheids",
    ),
    Field(
        name="seit",
        bmf_header="Zeitpunkt als Scheinunternehmen",
        csv_title="Seit",
        kind="date",
        required=False,
        description_en="Date designated as shell company (ISO 8601)",
        description_de="Zeitpunkt als Scheinunternehmen",
    ),
    Field(
        name="geburtsdatum",
        bmf_header="Geburts-Datum",
        csv_title="Geburts-Datum",
        kind="date",
        required=False,
        description_en="Birth date for natural persons (ISO 8601)",
        description_de="Geburtsdatum (nur bei natürlichen Personen)",
    ),
    Field(
        name="fbnr",
        bmf_header="Firmenbuch-Nr",
        csv_title="Firmenbuch-Nr",
        kind="string",
        required=False,
        description_en=(
            "Company register number (Firmenbuchnummer), normally 5-6 "
            "digits followed by a lowercase check letter. Not enforced "
            "by pattern: the BMF list is authoritative and unusual "
            "values are passed through (reported as validation warnings)."
        ),
        description_de="Firmenbuchnummer",
    ),
    Field(
        name="uid",
        bmf_header="UID-Nr.",
        csv_title="UID-Nr.",
        kind="string",
        required=False,
        description_en=(
            "VAT identification number (UID-Nummer). Normally Austrian "
            "(ATU + 8 digits), but the BMF list occasionally contains "
            "foreign EU VAT numbers (e.g. RO…, DE…) which the "
            "normalization step preserves in this field. Not enforced "
            "by pattern: unusual values are passed through (reported "
            "as validation warnings)."
        ),
        description_de="UID-Nummer (Umsatzsteuer-Identifikationsnummer)",
    ),
    Field(
        name="kennziffer",
        bmf_header="Kennziffer des UR",
        csv_title="Kennziffer des UR",
        kind="string",
        required=False,
        description_en="Register reference code (Kennziffer des Unternehmensregisters)",
        description_de="Kennziffer des Unternehmensregisters",
    ),
)

FIELD_NAMES: tuple[str, ...] = tuple(f.name for f in FIELDS)
