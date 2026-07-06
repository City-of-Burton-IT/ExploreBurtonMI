# HTTP JSON fetch with retry/backoff. Several of the civic APIs the tools hit
# (Urban Institute, FEMA, county ArcGIS) 522 or time out under load, so every
# fetch gets the same escalating-timeout retry that fetch_schools pioneered.
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

USER_AGENT = "Mozilla/5.0"


def get_json(
    url: str,
    params: dict | None = None,
    attempts: int = 4,
    timeout: int = 60,
) -> dict:
    """GET a JSON document, retrying transient failures.

    The read timeout grows by 20 s per retry (a slow API under load gets more
    room, not the same doomed deadline) with a short sleep between attempts.
    Raises RuntimeError once all attempts fail.
    """
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    last: Exception | None = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout + i * 20) as resp:
                return json.load(resp)
        except Exception as exc:  # noqa: BLE001 - transient; retry then give up
            last = exc
            if i < attempts - 1:
                time.sleep(2 + i * 2)
    raise RuntimeError(f"all {attempts} attempts failed for {url}: {last}")


def get_bytes(
    url: str,
    params: dict | None = None,
    attempts: int = 4,
    timeout: int = 60,
) -> bytes:
    """GET a raw document (zip/CSV downloads), with the same retry as get_json."""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    last: Exception | None = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout + i * 20) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - transient; retry then give up
            last = exc
            if i < attempts - 1:
                time.sleep(2 + i * 2)
    raise RuntimeError(f"all {attempts} attempts failed for {url}: {last}")


def post_json(
    url: str,
    payload: dict,
    attempts: int = 4,
    timeout: int = 60,
) -> dict:
    """POST a JSON payload and return the JSON response, with the same
    escalating-timeout retry as get_json."""
    data = json.dumps(payload).encode()
    last: Exception | None = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout + i * 20) as resp:
                return json.load(resp)
        except Exception as exc:  # noqa: BLE001 - transient; retry then give up
            last = exc
            if i < attempts - 1:
                time.sleep(2 + i * 2)
    raise RuntimeError(f"all {attempts} attempts failed for {url}: {last}")
