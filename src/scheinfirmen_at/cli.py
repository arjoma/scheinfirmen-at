# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Command-line interface for scheinfirmen-at."""

import argparse
import logging
import sys
from pathlib import Path

from scheinfirmen_at import __version__
from scheinfirmen_at.convert import write_csv, write_jsonl, write_xml
from scheinfirmen_at.download import BMF_URL, download_csv
from scheinfirmen_at.history import (
    REMOVALS_FILENAME,
    append_removals,
    diff_records,
    load_removals,
    load_snapshot,
    resolve_geaendert,
)
from scheinfirmen_at.normalize import normalize_field_swaps
from scheinfirmen_at.parse import parse_bmf_csv
from scheinfirmen_at.schema import write_csvw_metadata, write_json_schema, write_xsd
from scheinfirmen_at.stats import write_stats_for_result
from scheinfirmen_at.validate import validate_records
from scheinfirmen_at.verify import verify_outputs

logger = logging.getLogger("scheinfirmen_at")


def main(argv: list[str] | None = None) -> None:
    """Main entry point for the scheinfirmen-at CLI."""
    parser = argparse.ArgumentParser(
        prog="scheinfirmen-at",
        description=(
            "Scheinfirmen Österreich: Download and convert Austrian BMF shell company "
            "data to CSV, JSONL, and XML."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        metavar="DIR",
        help="Output directory for converted files (default: data/)",
    )
    parser.add_argument(
        "--url",
        default=BMF_URL,
        help="URL to download CSV from (default: BMF URL)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        metavar="FILE",
        help="Use a local file instead of downloading",
    )
    parser.add_argument(
        "--min-rows",
        type=int,
        default=100,
        metavar="N",
        help="Minimum expected record count (default: 100)",
    )
    parser.add_argument(
        "--max-removals",
        type=int,
        default=25,
        metavar="N",
        help=(
            "Abort if more than N entries disappeared compared to the previous "
            "output in DIR — guards against truncated downloads (default: 25; "
            "the BMF list usually loses 0-2 entries per day)"
        ),
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip cross-format verification step",
    )
    parser.add_argument(
        "--stats",
        type=Path,
        default=None,
        metavar="FILE",
        help="Generate a Markdown statistics report (e.g. data/STATS.md)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    # --- Step 1: Acquire raw CSV data ---
    if args.input is not None:
        logger.info("Reading from local file: %s", args.input)
        try:
            raw_data = args.input.read_bytes()
        except OSError as exc:
            logger.error("Cannot read input file: %s", exc)
            sys.exit(1)
    else:
        logger.info("Downloading from %s", args.url)
        try:
            raw_data = download_csv(url=args.url)
        except RuntimeError as exc:
            logger.error("Download failed: %s", exc)
            sys.exit(1)
    logger.debug("Downloaded %d bytes", len(raw_data))

    # --- Step 2: Parse ---
    logger.info("Parsing CSV data...")
    try:
        result = parse_bmf_csv(raw_data)
    except ValueError as exc:
        logger.error("Parse error: %s", exc)
        sys.exit(1)
    logger.info(
        "Parsed %d records (Stand: %s %s)",
        len(result.records),
        result.stand_datum,
        result.stand_zeit,
    )

    # --- Step 2b: Normalize known BMF data-entry quirks ---
    fixes = normalize_field_swaps(result)
    for f in fixes:
        logger.warning("NORMALIZE: %s", f)
    if fixes:
        logger.warning(
            "Auto-corrected %d row(s) with misplaced UID/Kennziffer/Firmenbuch values",
            len(fixes),
        )

    # --- Step 3: Validate ---
    logger.info("Validating records...")
    validation = validate_records(result, min_rows=args.min_rows)

    if validation.warnings:
        for w in validation.warnings:
            logger.warning("WARN: %s", w)
        logger.warning("%d validation warning(s)", len(validation.warnings))

    if not validation.ok:
        for e in validation.errors:
            logger.error("ERROR: %s", e)
        logger.error("%d validation error(s) — aborting", len(validation.errors))
        sys.exit(1)

    logger.info("Validation passed (%d warnings)", len(validation.warnings))

    # --- Step 4: Compare with previous output (if any) ---
    out = args.output_dir
    csv_path = out / "scheinfirmen.csv"
    jsonl_path = out / "scheinfirmen.jsonl"
    xml_path = out / "scheinfirmen.xml"
    json_schema_path = out / "scheinfirmen.json-schema.json"
    csvw_path = out / "scheinfirmen.csv-metadata.json"
    xsd_path = out / "scheinfirmen.xsd"
    removals_path = out / REMOVALS_FILENAME

    new_records = [rec.to_dict() for rec in result.records]
    previous = load_snapshot(jsonl_path)
    removed: list[dict[str, str | None]] = []
    if previous is not None:
        diff = diff_records(previous.records, new_records)
        logger.info(
            "Changes vs. previous output: %d added, %d removed, %d changed",
            len(diff.added),
            len(diff.removed),
            len(diff.changed),
        )
        for old, new in diff.changed:
            changed = {k: (old[k], new[k]) for k in old if old[k] != new[k]}
            logger.info("CHANGED: %r: %s", old["name"], changed)
        for rec in diff.removed:
            logger.info("REMOVED: %r (veröffentlicht %s)", rec["name"], rec["veroeffentlicht"])
        removed = diff.removed
        if len(removed) > args.max_removals:
            logger.error(
                "%d entries disappeared (limit --max-removals=%d) — possibly a "
                "truncated download; aborting without writing outputs",
                len(removed),
                args.max_removals,
            )
            sys.exit(1)
    geaendert = resolve_geaendert(previous, new_records, result.stand)
    logger.info("Data last changed: %s", geaendert)

    # --- Step 5: Write outputs ---
    logger.info("Writing outputs to %s/", out)
    n_csv = write_csv(result, csv_path)
    logger.debug("Wrote %d rows to %s", n_csv, csv_path)

    n_jsonl = write_jsonl(result, jsonl_path, geaendert=geaendert)
    logger.debug("Wrote %d rows to %s", n_jsonl, jsonl_path)

    n_xml = write_xml(result, xml_path, geaendert=geaendert)
    logger.debug("Wrote %d rows to %s", n_xml, xml_path)

    write_json_schema(json_schema_path)
    logger.debug("Wrote JSON Schema to %s", json_schema_path)

    write_csvw_metadata(csvw_path)
    logger.debug("Wrote CSVW metadata to %s", csvw_path)

    write_xsd(xsd_path)
    logger.debug("Wrote XSD to %s", xsd_path)

    if removed:
        append_removals(removals_path, removed, result.stand_datum)
        logger.info("Logged %d removal(s) to %s", len(removed), removals_path)

    # --- Step 6: Cross-format verification ---
    if not args.skip_verify:
        logger.info("Verifying output consistency and schemas...")
        verify_errors = verify_outputs(
            csv_path,
            jsonl_path,
            xml_path,
            len(result.records),
            json_schema_path=json_schema_path,
            xsd_path=xsd_path,
        )
        if verify_errors:
            for ve in verify_errors:
                logger.error("VERIFY ERROR: %s", ve)
            logger.error("Cross-format verification failed — outputs may be inconsistent")
            sys.exit(1)
        logger.info("Verification passed: all formats contain %d records", len(result.records))

    # --- Step 7: Stats report (optional) ---
    if args.stats is not None:
        try:
            removals = load_removals(removals_path) if removals_path.exists() else None
            write_stats_for_result(result, args.stats, geaendert=geaendert, removals=removals)
        except Exception as exc:
            logger.warning("Stats generation failed (non-fatal): %s", exc)

    # --- Done ---
    print(
        f"OK: wrote {len(result.records)} records to {out}/ "
        f"(Stand: {result.stand_datum} {result.stand_zeit})"
    )
