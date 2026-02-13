# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Tests for the CLI entry point."""

from pathlib import Path

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

    # CSV: header + 10 data rows (plus comment line)
    with open(tmp_path / "scheinfirmen.csv", encoding="utf-8-sig") as f:
        lines = f.readlines()
    # First line is "# Stand:..." comment, second is header, rest is data
    reader = csv.reader(line for line in lines if not line.startswith("#"))
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


def test_cli_stats_nonfatal_without_git(tmp_path: Path) -> None:
    """--stats in a non-git directory logs a warning but doesn't abort."""
    stats_path = tmp_path / "STATS.md"
    # tmp_path is not a git repo, so generate_stats will fail —
    # but the CLI should still complete successfully
    main([
        "--input", str(SAMPLE_CSV),
        "-o", str(tmp_path),
        "--skip-verify",
        "--stats", str(stats_path),
        *MIN_ROWS,
    ])
    # Pipeline completed (didn't crash)
    assert (tmp_path / "scheinfirmen.csv").exists()
