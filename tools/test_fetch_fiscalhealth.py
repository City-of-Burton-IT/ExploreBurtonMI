# Tests for fetch_fiscalhealth pure helpers. No network.
# Run: python -m pytest tools/test_fetch_fiscalhealth.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fetch_fiscalhealth as fh  # noqa: E402


def test_population_matches_named_decennial_source():
    assert fh.POPULATION == 29_715


def test_percentile_rank_one_is_healthiest():
    # Rank 1 of 261 -> healthier than ~all cities.
    assert fh._percentile(1, 261) == 100
    # Worst rank -> healthier than none.
    assert fh._percentile(261, 261) == 0
    # Burton's verified ranks.
    assert fh._percentile(81, 261) == 69
    assert fh._percentile(125, 261) == 52
    assert fh._percentile(147, 263) == 44


def test_latest_returns_last_nonnull_with_year():
    snap = {
        "years": [2023, 2024, 2025],
        "data": [
            {"dimension": {"name": "Long Term Debt"}, "values": [10, 20, None]},
            {"dimension": {"name": "Empty"}, "values": [None, None, None]},
        ],
    }
    assert fh._latest(snap, "Long Term Debt") == (20, 2024)
    assert fh._latest(snap, "Empty") == (None, None)
    assert fh._latest(snap, "Missing") == (None, None)


def test_rank_index_keys_by_entity():
    analytics = [{"key_entity": "general_fund_ratio", "value": 0.53, "rank": 125, "total": 261}]
    idx = fh._rank_index(analytics)
    assert idx["general_fund_ratio"]["rank"] == 125
