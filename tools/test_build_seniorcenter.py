# Tests for build_seniorcenter data integrity. No network/files.
# Run: python -m pytest tools/test_build_seniorcenter.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_seniorcenter as sc  # noqa: E402


def test_age_bands_sum_to_membership():
    # Catches a transcription error when the yearly export is refreshed.
    assert sum(v for _, v in sc.AGE_BANDS) == sc.MEMBERS


def test_residence_split_sums_to_membership():
    assert sc.IN_TOWN + sc.OUT_OF_TOWN == sc.MEMBERS


def test_twelve_months_present():
    assert len(sc.MONTHLY) == 12


def test_program_categories_nonempty_and_descending():
    vals = [v for _, v in sc.PROGRAMS]
    assert vals and all(v > 0 for v in vals)
    assert vals == sorted(vals, reverse=True)  # largest first for the bar chart
