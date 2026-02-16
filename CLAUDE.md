# CLAUDE.md

## Project: Scheinfirmen Österreich

Austrian BMF Scheinfirmen data downloader and converter.

## Commands

```bash
uv sync                                           # Install dependencies (incl. lxml, jsonschema)
uv run pytest tests/ -v                           # Run tests (incl. schema compliance)
uv run ruff check src/ tests/                     # Lint
uv run mypy src/                                  # Type check
uv run scheinfirmen-at --help                     # Show CLI help
uv run scheinfirmen-at -o data/ -v                # Download, convert and validate (verbose)
uv run scheinfirmen-at --input path/to/local.csv -o data/  # Convert local file
```

## Architecture

- `src/scheinfirmen_at/` — Main package (zero runtime dependencies, stdlib only)
- `download.py` — HTTP download from BMF with retry/backoff
- `parse.py` — Tilde-CSV parsing, ISO-8859-1 decode, date conversion, HTML entity cleanup
- `validate.py` — Strict field validation with errors/warnings
- `convert.py` — Output to CSV (UTF-8 BOM), JSONL ($schema), XML
- `schema.py` — JSON Schema dict and XSD string constants + write functions
- `verify.py` — Cross-format verification & schema validation (XSD/JSON Schema)
- `cli.py` — argparse CLI orchestrating the full pipeline

## Data Source

- URL: https://service.bmf.gv.at/service/allg/lsu/__Gen_Csv.asp
- Encoding: ISO-8859-1, Delimiter: ~, Line endings: CRLF
- ~1270 rows, 9 columns
- Footer line: Stand: DD.MM.YYYY HH:MM:SS

## Known Data Quirks (BMF quality issues)

- Header names have leading/trailing spaces — strip them
- Column 4 (Zeitpunkt) has a trailing space in every value — strip
- One Kennziffer field contains HTML-encoded &quot; wrapping — unescape + strip quotes
- One row has a UID as its Kennziffer value (data error from BMF, accepted as warning)
- One Kennziffer has unusual format RO38488384 — accepted as warning

## Output Formats

- **CSV**: UTF-8 with BOM, comma delimiter, # Stand: comment first line
- **JSONL**: metadata object on first line (incl. `$schema` link), then one JSON object per record
- **XML**: `<scheinfirmen>` root with stand/zeit/quelle/anzahl attributes, `<scheinfirma>` children (name as text content, all other fields as attributes)
- Dates converted to ISO 8601 (YYYY-MM-DD)
- Empty/null fields: empty string in CSV, null in JSON, attribute omitted in XML

## Release Process

To publish a new release to PyPI:

1. **Update version** in `pyproject.toml` (`version = "X.Y.Z"`)
2. **Write changelog entry** in `CHANGELOG.md` (German, following existing format)
3. **Commit and push** to `main`
4. **Wait for CI** — check that the CI workflow on `main` passes (ruff, mypy, pytest on 3.10/3.11/3.12). Do not tag a broken build.
5. **Tag and push** — `git tag v<X.Y.Z> && git push origin v<X.Y.Z>`
   - The `release.yml` workflow triggers on `v*` tags
   - It runs tests again, builds the wheel, and publishes to PyPI via Trusted Publishing (OIDC)
   - No secrets or tokens needed — PyPI trusts the GitHub Actions OIDC identity

**Note:** The tag push requires write access. User `haraldschilly` can push tags via SSH.
Check the release at https://pypi.org/p/scheinfirmen-at after the workflow completes.

## Development Dependencies

- **pytest**: Test runner
- **lxml**: Used for XSD validation in tests and CLI `verify`
- **jsonschema**: Used for JSON Schema validation in tests and CLI `verify`

## Microsoft Excel Compatibility

The CSV output is intentionally compatible with Microsoft Excel:
- **UTF-8 BOM** (`\ufeff`, `utf-8-sig` encoding) — Excel uses this to auto-detect UTF-8;
  without it, Excel on Windows opens the file as Windows-1252 and mangles German umlauts
- The `# Stand:` comment line appears before the header; Excel will treat it as a data row,
  but this is acceptable since the file is primarily for programmatic use
- Note: the BOM prefix is not part of the CSV standard (RFC 4180), but is the de-facto
  standard for Excel-compatible UTF-8 CSVs
