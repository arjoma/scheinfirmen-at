# Copyright 2026 Harald Schilly <info@arjoma.at>, ARJOMA FlexCo.
# SPDX-License-Identifier: Apache-2.0

"""Tests for the download module."""

import urllib.error
from importlib.metadata import PackageNotFoundError
from unittest.mock import MagicMock, patch

import pytest

from scheinfirmen_at.download import _get_user_agent, download_csv


class TestGetUserAgent:
    def test_contains_package_name(self) -> None:
        ua = _get_user_agent()
        assert "scheinfirmen-at/" in ua

    def test_contains_github_url(self) -> None:
        ua = _get_user_agent()
        assert "github.com/arjoma/scheinfirmen-at" in ua

    @patch("scheinfirmen_at.download.get_version", side_effect=PackageNotFoundError)
    def test_fallback_version(self, _mock: MagicMock) -> None:
        ua = _get_user_agent()
        assert "0.0.0-dev" in ua


class TestDownloadCsv:
    @patch("scheinfirmen_at.download.urllib.request.urlopen")
    def test_success(self, mock_urlopen: MagicMock) -> None:
        expected = b"Name~Anschrift\r\nTest~Wien\r\n"
        mock_resp = MagicMock()
        mock_resp.read.return_value = expected
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = download_csv(url="https://example.com/test.csv")
        assert result == expected
        mock_urlopen.assert_called_once()

    @patch("scheinfirmen_at.download.urllib.request.urlopen")
    def test_user_agent_header(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"data"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        download_csv(url="https://example.com/test.csv")
        req = mock_urlopen.call_args[0][0]
        assert "scheinfirmen-at/" in req.get_header("User-agent")

    @patch("scheinfirmen_at.download.time.sleep")
    @patch("scheinfirmen_at.download.urllib.request.urlopen")
    def test_retry_on_transient_error(
        self, mock_urlopen: MagicMock, mock_sleep: MagicMock
    ) -> None:
        # Fail first two attempts, succeed on third
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"ok"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.side_effect = [
            urllib.error.URLError("timeout"),
            urllib.error.URLError("connection reset"),
            mock_resp,
        ]

        result = download_csv(url="https://example.com/test.csv", retries=3, delay=1.0)
        assert result == b"ok"
        assert mock_urlopen.call_count == 3
        assert mock_sleep.call_count == 2  # sleep before attempt 2 and 3

    @patch("scheinfirmen_at.download.time.sleep")
    @patch("scheinfirmen_at.download.urllib.request.urlopen")
    def test_raises_after_all_retries_exhausted(
        self, mock_urlopen: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")

        with pytest.raises(RuntimeError, match="Failed to download.*after 3 attempt"):
            download_csv(url="https://example.com/test.csv", retries=3, delay=0.0)
        assert mock_urlopen.call_count == 3

    @patch("scheinfirmen_at.download.time.sleep")
    @patch("scheinfirmen_at.download.urllib.request.urlopen")
    def test_exponential_backoff(
        self, mock_urlopen: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_urlopen.side_effect = OSError("network error")

        with pytest.raises(RuntimeError):
            download_csv(url="https://example.com/test.csv", retries=3, delay=2.0)

        # attempt 0: no sleep
        # attempt 1: sleep(2.0 * 2^0) = 2.0
        # attempt 2: sleep(2.0 * 2^1) = 4.0
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2.0)
        mock_sleep.assert_any_call(4.0)
