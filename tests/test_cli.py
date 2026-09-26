# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Tests for the CLI entry point."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scheinfirmen_at.cli import main

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_CSV = FIXTURES_DIR / "sample_raw.csv"

# Sample fixture has only 10 rows; override the default --min-rows=100.
MIN_ROWS = ["--min-rows", "1"]


def test_cli_happy_path(tmp_path: Path) -> None:
    """Full pipeline with --input produces all output files."""
    main(["--input", str(SAMPLE_CSV), "-o", str(tmp_path),
          "--skip-verify", *MIN_ROWS])

    assert (tmp_path / "scheinfirmen.csv").exists()
    assert (tmp_path / "scheinfirmen.jsonl").exists()
    assert (tmp_path / "scheinfirmen.xml").exists()
    assert (tmp_path / "scheinfirmen.json-schema.json").exists()
    assert (tmp_path / "scheinfirmen.xsd").exists()


def test_cli_output_row_counts(tmp_path: Path) -> None:
    """Output files contain the expected number of records."""
    import csv
    import json

    main(["--input", str(SAMPLE_CSV), "-o", str(tmp_path),
          "--skip-verify", *MIN_ROWS])

    # CSV: header + 10 data rows
    with open(tmp_path / "scheinfirmen.csv", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert len(rows) == 11  # 1 header + 10 data

    # JSONL: 1 metadata + 10 records
    with open(tmp_path / "scheinfirmen.jsonl", encoding="utf-8") as f:
        jsonl_lines = [json.loads(line) for line in f if line.strip()]
    assert len(jsonl_lines) == 11


def test_cli_creates_output_dir(tmp_path: Path) -> None:
    """CLI creates the output directory if it doesn't exist."""
    out = tmp_path / "subdir" / "output"
    main(["--input", str(SAMPLE_CSV), "-o", str(out),
          "--skip-verify", *MIN_ROWS])
    assert (out / "scheinfirmen.csv").exists()


def test_cli_with_verify(tmp_path: Path) -> None:
    """Full pipeline including verification step passes."""
    main(["--input", str(SAMPLE_CSV), "-o", str(tmp_path), *MIN_ROWS])


def test_cli_verbose(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """--verbose flag enables DEBUG-level log messages."""
    with caplog.at_level("DEBUG", logger="scheinfirmen_at"):
        main(["--input", str(SAMPLE_CSV), "-o", str(tmp_path),
              "--skip-verify", "-v", *MIN_ROWS])
    debug_messages = [r for r in caplog.records if r.levelname == "DEBUG"]
    assert len(debug_messages) > 0


def test_cli_nonexistent_input(tmp_path: Path) -> None:
    """Non-existent input file exits with code 1."""
    with pytest.raises(SystemExit, match="1"):
        main(["--input", "/no/such/file.csv", "-o", str(tmp_path)])


def test_cli_min_rows_too_high(tmp_path: Path) -> None:
    """--min-rows higher than actual count exits with code 1."""
    with pytest.raises(SystemExit, match="1"):
        main([
            "--input", str(SAMPLE_CSV),
            "-o", str(tmp_path),
            "--min-rows", "9999",
            "--skip-verify",
        ])


def test_cli_ok_message(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI prints OK summary with record count and Stand on stdout."""
    main(["--input", str(SAMPLE_CSV), "-o", str(tmp_path),
          "--skip-verify", *MIN_ROWS])
    captured = capsys.readouterr()
    assert captured.out.startswith("OK:")
    assert "10 records" in captured.out
    assert "Stand:" in captured.out


def test_cli_stats_writes_report(tmp_path: Path) -> None:
    """--stats writes a Markdown report next to the data files."""
    stats_path = tmp_path / "STATS.md"
    main([
        "--input", str(SAMPLE_CSV),
        "-o", str(tmp_path),
        "--skip-verify",
        "--stats", str(stats_path),
        *MIN_ROWS,
    ])
    assert (tmp_path / "scheinfirmen.csv").exists()
    assert "# Scheinfirmen Österreich" in stats_path.read_text(encoding="utf-8")


def test_cli_unusual_identifiers_do_not_abort(tmp_path: Path) -> None:
    """Odd Firmenbuch/UID values are validation *warnings*; the schema check
    in the verify step must not turn them into a fatal error."""
    header = (
        "Name~ Anschrift~ Veröffentlichung~ Rechtskraft Bescheid~"
        " Zeitpunkt als Scheinunternehmen~ Geburts-Datum~"
        " Firmenbuch-Nr~ UID-Nr.~ Kennziffer des UR "
    )
    rows = [
        "Odd GmbH~1010 Wien, Ring 1~01.01.2026~01.01.2026~ ~~FN 12345 x~AT-U1234~",
        "Stand: 02.01.2026 10:00:00",
    ]
    raw = tmp_path / "raw.csv"
    raw.write_bytes(("\r\n".join([header, *rows]) + "\r\n").encode("iso-8859-1"))

    out = tmp_path / "out"
    main(["--input", str(raw), "-o", str(out), *MIN_ROWS])  # verify enabled

    line = (out / "scheinfirmen.jsonl").read_text(encoding="utf-8").splitlines()[1]
    assert '"fbnr": "FN 12345 x"' in line
    assert '"uid": "AT-U1234"' in line


@patch("scheinfirmen_at.cli.download_csv")
def test_cli_download_path(mock_dl: MagicMock, tmp_path: Path) -> None:
    """CLI downloads from URL when --input is not provided."""
    mock_dl.return_value = SAMPLE_CSV.read_bytes()
    main(["-o", str(tmp_path), "--skip-verify", *MIN_ROWS])
    mock_dl.assert_called_once()
    assert (tmp_path / "scheinfirmen.csv").exists()


@patch("scheinfirmen_at.cli.download_csv")
def test_cli_download_failure_exits(mock_dl: MagicMock, tmp_path: Path) -> None:
    """CLI exits 1 when download raises RuntimeError."""
    mock_dl.side_effect = RuntimeError("connection refused")
    with pytest.raises(SystemExit, match="1"):
        main(["-o", str(tmp_path), "--skip-verify"])


@patch("scheinfirmen_at.cli.verify_outputs", return_value=["count mismatch"])
def test_cli_verify_failure_exits(mock_verify: MagicMock, tmp_path: Path) -> None:
    """CLI exits 1 when verification detects inconsistency."""
    with pytest.raises(SystemExit, match="1"):
        main(["--input", str(SAMPLE_CSV), "-o", str(tmp_path), *MIN_ROWS])


def _write_raw(path: Path, rows: list[str], stand: str) -> Path:
    header = (
        "Name~ Anschrift~ Veröffentlichung~ Rechtskraft Bescheid~"
        " Zeitpunkt als Scheinunternehmen~ Geburts-Datum~"
        " Firmenbuch-Nr~ UID-Nr.~ Kennziffer des UR "
    )
    text = "\r\n".join([header, *rows, f"Stand: {stand}"]) + "\r\n"
    path.write_bytes(text.encode("iso-8859-1"))
    return path


_ROW_A = "Alpha GmbH~1010 Wien, Ring 1~01.01.2021~01.12.2020~ ~~111111a~ATU11111111~"
_ROW_B = "Beta GmbH~8010 Graz, Platz 2~02.02.2024~01.02.2024~ ~~222222b~ATU22222222~"
_ROW_C = "Gamma GmbH~4020 Linz, Weg 3~03.03.2026~01.03.2026~ ~~333333c~ATU33333333~"


def _metadata(out: Path) -> dict[str, object]:
    import json

    line = (out / "scheinfirmen.jsonl").read_text(encoding="utf-8").splitlines()[0]
    meta = json.loads(line)["_metadata"]
    assert isinstance(meta, dict)
    return meta


def test_cli_tracks_changes_and_removals(tmp_path: Path) -> None:
    """Second run against the same output dir: geaendert is kept while the
    data is unchanged, removals are logged, and STATS.md lists them."""
    import json

    out = tmp_path / "out"
    raw1 = _write_raw(tmp_path / "r1.csv", [_ROW_A, _ROW_B], "01.04.2026 09:00:00")
    main(["--input", str(raw1), "-o", str(out), *MIN_ROWS])
    assert _metadata(out)["geaendert"] == "2026-04-01T09:00:00"

    # Same data, new download time → geaendert unchanged, stand updated
    raw2 = _write_raw(tmp_path / "r2.csv", [_ROW_A, _ROW_B], "02.04.2026 09:00:00")
    main(["--input", str(raw2), "-o", str(out), *MIN_ROWS])
    meta = _metadata(out)
    assert meta["stand"] == "2026-04-02T09:00:00"
    assert meta["geaendert"] == "2026-04-01T09:00:00"
    assert not (out / "scheinfirmen-entfernt.jsonl").exists()

    # Alpha removed, Gamma added
    raw3 = _write_raw(tmp_path / "r3.csv", [_ROW_B, _ROW_C], "03.04.2026 09:00:00")
    stats = out / "STATS.md"
    main(["--input", str(raw3), "-o", str(out), "--stats", str(stats), *MIN_ROWS])
    assert _metadata(out)["geaendert"] == "2026-04-03T09:00:00"
    removed = [
        json.loads(line)
        for line in (out / "scheinfirmen-entfernt.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [(r["name"], r["entfernt"]) for r in removed] == [("Alpha GmbH", "2026-04-03")]
    report = stats.read_text(encoding="utf-8")
    assert "## Entfernte Einträge" in report
    assert "| Alpha GmbH | ATU11111111 | 2021-01-01 | 2026-04-03 | 5.3 |" in report


def test_cli_max_removals_aborts_without_writing(tmp_path: Path) -> None:
    out = tmp_path / "out"
    raw1 = _write_raw(tmp_path / "r1.csv", [_ROW_A, _ROW_B, _ROW_C], "01.04.2026 09:00:00")
    main(["--input", str(raw1), "-o", str(out), *MIN_ROWS])
    before = (out / "scheinfirmen.jsonl").read_bytes()

    truncated = _write_raw(tmp_path / "r2.csv", [_ROW_A], "02.04.2026 09:00:00")
    with pytest.raises(SystemExit, match="1"):
        main(["--input", str(truncated), "-o", str(out), "--max-removals", "1", *MIN_ROWS])
    assert (out / "scheinfirmen.jsonl").read_bytes() == before
    assert not (out / "scheinfirmen-entfernt.jsonl").exists()

    # A higher limit lets a deliberate mass removal through
    main(["--input", str(truncated), "-o", str(out), "--max-removals", "2", *MIN_ROWS])
    assert _metadata(out)["count"] == 1
