"""Download BMF Scheinfirmen CSV data."""

import time
import urllib.error
import urllib.request

BMF_URL = "https://service.bmf.gv.at/service/allg/lsu/__Gen_Csv.asp"
_USER_AGENT = (
    "scheinfirmen-at/0.1 (https://github.com/haraldschilly/scheinfirmen-at)"
)


def download_csv(
    url: str = BMF_URL,
    retries: int = 3,
    delay: float = 5.0,
    timeout: float = 30.0,
) -> bytes:
    """Download raw CSV bytes from the given URL.

    Returns raw bytes (ISO-8859-1 encoded as served by BMF).
    Raises RuntimeError after all retries are exhausted.
    """
    last_error: Exception | None = None
    for attempt in range(retries):
        if attempt > 0:
            wait = delay * (2 ** (attempt - 1))
            time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()  # type: ignore[no-any-return]
        except (urllib.error.URLError, OSError) as exc:
            last_error = exc
    raise RuntimeError(
        f"Failed to download {url} after {retries} attempt(s): {last_error}"
    )
