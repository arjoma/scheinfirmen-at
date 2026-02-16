"""Shared test fixtures."""

from pathlib import Path

import pytest

from scheinfirmen_at.parse import ParseResult, parse_bmf_csv

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_raw_bytes() -> bytes:
    """Raw bytes of sample BMF CSV data (ISO-8859-1 encoded)."""
    return (FIXTURES_DIR / "sample_raw.csv").read_bytes()


@pytest.fixture
def sample_result(sample_raw_bytes: bytes) -> ParseResult:
    """Parsed ParseResult from sample data."""
    return parse_bmf_csv(sample_raw_bytes)
