"""End-to-end demonstration: how the parse → normalize → validate pipeline
handles the four real-world BMF data quirks observed in the live data.

Each row in the synthetic CSV below mirrors a concrete row from the BMF
list (Stand 2026-04-28). The test exercises the full pipeline and asserts:

1. Parsing succeeds (raw values preserved).
2. ``normalize_field_swaps`` reports exactly the expected fix per row.
3. After normalization, the records hold the corrected values.
4. Validation succeeds with no errors (the goal: nothing aborts the
   daily update workflow because of these BMF data-entry mistakes).
"""

from scheinfirmen_at.normalize import normalize_field_swaps
from scheinfirmen_at.parse import parse_bmf_csv
from scheinfirmen_at.validate import validate_records


def _build_csv() -> bytes:
    """Build a tilde-delimited, ISO-8859-1 BMF-style CSV with problem rows."""
    header = (
        "Name~ Anschrift~ Veröffentlichung~ Rechtskraft Bescheid~"
        " Zeitpunkt als Scheinunternehmen~ Geburts-Datum~"
        " Firmenbuch-Nr~ UID-Nr.~ Kennziffer des UR "
    )
    rows = [
        # 1. Clean control row — should pass through untouched.
        "Saubere GmbH~1010 Wien, Hauptstr 1~"
        "01.01.2026~15.12.2025~ ~~111111a~ATU11111111~R100A1234",

        # 2. Real-world Row 75 (Aran Bike GmbH): Kennziffer == fbnr (duplicate).
        "Aran Bike GmbH~4810 Gmunden, Badgasse 1~"
        "12.03.2026~05.03.2026~11.09.2025 ~~636821b~ATU81293903~636821b",

        # 3. Real-world Row 555 (HORVAT Monika): Kennziffer == uid (duplicate).
        "HORVAT Monika~1170 Wien, Frauenfelderstraße 15~"
        "28.03.2025~20.03.2025~12.11.2023 ~24.04.1982~~ATU80457319~ATU80457319",

        # 4. Real-world Row 635 (Jovanluka SRL): foreign Romanian VAT in Kennziffer.
        "Jovanluka SRL~6844 Altach, Bauern 65/3~"
        "30.11.2018~07.11.2018~ ~~~~RO38488384",

        # 5. Real-world Row 1378 (Wikri): Kennziffer-shaped value in UID column.
        "Wikri Alpha Projektmanagement Gesellschaft m.b.H.~"
        "1060 Wien, Eisvogelgasse 6~"
        "27.04.2026~18.03.2026~13.08.2024 ~~580355p~R134I594W~",

        "Stand: 28.04.2026 07:00:00",
    ]
    text = "\r\n".join([header, *rows]) + "\r\n"
    return text.encode("iso-8859-1")


def test_problem_rows_full_pipeline() -> None:
    raw = _build_csv()

    # --- Step 1: parse ---
    result = parse_bmf_csv(raw)
    assert len(result.records) == 5
    clean, aran, horvat, jovanluka, wikri = result.records

    # Sanity: raw parse keeps values exactly as the BMF supplied them.
    assert aran.kennziffer == "636821b"
    assert horvat.kennziffer == "ATU80457319"
    assert jovanluka.kennziffer == "RO38488384"
    assert wikri.uid == "R134I594W" and wikri.kennziffer is None

    # --- Step 2: normalize ---
    fixes = normalize_field_swaps(result)
    by_name = {f.name: f for f in fixes}

    assert "Saubere GmbH" not in by_name, "Clean row must not trigger a fix"
    assert by_name["Aran Bike GmbH"].rule == "clear-duplicate-fbnr"
    assert by_name["HORVAT Monika"].rule == "clear-duplicate-uid"
    assert by_name["Jovanluka SRL"].rule == "promote-foreign-vat"
    assert (
        by_name["Wikri Alpha Projektmanagement Gesellschaft m.b.H."].rule
        == "swap-uid-kennziffer"
    )
    assert len(fixes) == 4

    # --- Step 3: post-normalize state ---
    # Clean row untouched.
    assert clean.uid == "ATU11111111"
    assert clean.kennziffer == "R100A1234"

    # Duplicates cleared, original UID/fbnr preserved.
    assert aran.fbnr == "636821b"
    assert aran.uid == "ATU81293903"
    assert aran.kennziffer is None

    assert horvat.uid == "ATU80457319"
    assert horvat.kennziffer is None

    # Foreign VAT promoted into UID, kennziffer cleared.
    assert jovanluka.uid == "RO38488384"
    assert jovanluka.kennziffer is None

    # Misplaced Kennziffer-shaped value moved out of UID into Kennziffer.
    assert wikri.uid is None
    assert wikri.kennziffer == "R134I594W"

    # --- Step 4: validation passes (no errors, no warnings) ---
    validation = validate_records(result, min_rows=1)
    assert validation.ok, f"Unexpected errors: {validation.errors}"
    assert validation.warnings == [], (
        f"All four problem rows should validate cleanly after normalization, "
        f"but got: {validation.warnings}"
    )
