"""Shared test fixtures."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_raw_bytes() -> bytes:
    """Raw bytes of sample BMF CSV data (ISO-8859-1 encoded)."""
    return (FIXTURES_DIR / "sample_raw.csv").read_bytes()


@pytest.fixture
def sample_result(sample_raw_bytes):  # type: ignore[no-untyped-def]
    """Parsed ParseResult from sample data."""
    from scheinfirmen_at.parse import parse_bmf_csv

    return parse_bmf_csv(sample_raw_bytes)
