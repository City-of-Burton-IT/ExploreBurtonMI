# ArcGIS REST query paging, replacing the hand-rolled resultOffset loops in the
# extract_* scripts.
from __future__ import annotations

from collections.abc import Iterator

from lib.httpio import get_json


def paged_query(
    url: str,
    base_params: dict,
    page_size: int = 1000,
    timeout: int = 90,
    attempts: int = 4,
) -> Iterator[dict]:
    """Yield every feature from an ArcGIS /query endpoint, one page at a time.

    base_params must not include resultOffset/resultRecordCount; paging stops on
    the first short page. page_size should be <= the layer's maxRecordCount.
    """
    offset = 0
    while True:
        params = dict(base_params)
        params["resultOffset"] = str(offset)
        params["resultRecordCount"] = str(page_size)
        fc = get_json(url, params, attempts=attempts, timeout=timeout)
        page = fc.get("features", [])
        yield from page
        if len(page) < page_size:
            return
        offset += page_size
