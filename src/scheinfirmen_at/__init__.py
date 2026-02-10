# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""scheinfirmen-at: Austrian BMF shell company data in machine-readable formats."""

from importlib.metadata import version as _version

__version__ = _version("scheinfirmen-at")

from scheinfirmen_at.convert import write_csv, write_jsonl, write_xml
from scheinfirmen_at.download import download_csv
from scheinfirmen_at.parse import parse_bmf_csv
from scheinfirmen_at.validate import validate_records

__all__ = [
    "__version__",
    "download_csv",
    "parse_bmf_csv",
    "validate_records",
    "write_csv",
    "write_jsonl",
    "write_xml",
]
