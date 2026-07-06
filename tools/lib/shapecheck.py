# Fail-loud shape assertions for fetched rows, modeled on pipeline/src/validate.py:
# a source column rename/reorder should stop the build, never silently emit
# mis-coordinated data.
from __future__ import annotations

from collections.abc import Iterable, Sequence


def assert_shape(rows: Sequence[dict], required_keys: Iterable[str], label: str = "rows"):
    """Require every row to carry required_keys; raise SystemExit otherwise.

    Returns rows unchanged so it can be used inline:
        rows = assert_shape(fetch(), ["GEOID", "NAME"], "census rows")
    """
    keys = list(required_keys)
    if not rows:
        raise SystemExit(f"{label}: no rows returned")
    bad = [(i, [k for k in keys if k not in row]) for i, row in enumerate(rows)]
    bad = [(i, missing) for i, missing in bad if missing]
    if bad:
        i, missing = bad[0]
        raise SystemExit(
            f"{label}: {len(bad)} row(s) missing required keys "
            f"(first: row {i} missing {missing}) - source schema changed?"
        )
    return rows
