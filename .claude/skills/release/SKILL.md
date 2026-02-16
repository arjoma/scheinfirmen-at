---
name: release
description: Create a new PyPI release with semantic versioning. Bumps version, writes changelog, waits for CI, tags and publishes.
argument-hint: major|minor|patch
disable-model-invocation: true
allowed-tools:
  - Bash(git *)
  - Bash(gh *)
  - Bash(uv *)
---

# Release scheinfirmen-at to PyPI

Create a release of the `scheinfirmen-at` package. The argument must be one of: `major`, `minor`, or `patch`.

## Steps

### 1. Validate argument

`$ARGUMENTS` must be exactly one of `major`, `minor`, or `patch`. If missing or invalid, stop and ask.

### 2. Compute new version

- Read the current version from `pyproject.toml` (the `version = "X.Y.Z"` line).
- Bump according to `$ARGUMENTS`:
  - `patch`: X.Y.Z → X.Y.(Z+1)
  - `minor`: X.Y.Z → X.(Y+1).0
  - `major`: X.Y.Z → (X+1).0.0

### 3. Gather changes since last release

- Run `git log --oneline v<current>..HEAD` to see all commits since the last tag.
- Ignore automated "Update Scheinfirmen data" commits — those are not release-worthy.

### 4. Write changelog entry

- Edit `CHANGELOG.md` and insert a new section after the header block, **before** the previous release entry.
- Follow the existing format exactly: German language, [Keep a Changelog](https://keepachangelog.com/de/) style.
- Use sections like `### Hinzugefuegt`, `### Geaendert`, `### Behoben` as appropriate.
- Today's date in `YYYY-MM-DD` format.
- Be concise — one line per change, matching the tone and detail level of existing entries.

### 5. Update version in pyproject.toml

- Change the `version = "..."` line in `pyproject.toml` to the new version.

### 6. Run local checks

- Run `uv run ruff check src/ tests/` — must pass.
- Run `uv run mypy src/` — must pass.
- Run `uv run pytest tests/ -v` — must pass.
- If any check fails, stop and fix the issue before continuing.

### 7. Commit and push

- Stage `pyproject.toml` and `CHANGELOG.md` (and any other changed files from fixes).
- Commit with message: `chore: release v<new-version>`
- Push to `main`.

### 8. Wait for CI

- Use `gh run list --branch main --limit 1` to find the CI workflow run.
- Poll with `gh run watch <run-id>` or check status until it completes.
- If CI fails, stop and report the failure. Do **not** tag a broken build.

### 9. Tag and push tag

- `git tag v<new-version>`
- `git push origin v<new-version>`
- This triggers the `release.yml` workflow which publishes to PyPI via Trusted Publishing.

### 10. Verify

- Use `gh run list --workflow=release.yml --limit 1` to confirm the release workflow started.
- Report the expected PyPI URL: `https://pypi.org/project/scheinfirmen-at/<new-version>/`

## Important

- Never skip the CI check. A broken tag means a broken PyPI release.
- The changelog must be in German, matching the existing style.
- Ask the user for confirmation before pushing the tag (step 9) — this is the point of no return.
