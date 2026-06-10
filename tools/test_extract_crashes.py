# Tests for extract_crashes helpers/config. No network.
# Run: python -m pytest tools/test_extract_crashes.py -q
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import extract_crashes as ec  # noqa: E402


def test_yes_is_case_insensitive():
    assert ec._yes("Yes") is True
    assert ec._yes("yes") is True
    assert ec._yes("No") is False
    assert ec._yes(None) is False
    assert ec._yes("Uncoded & Errors") is False


def test_severity_order_and_colors():
    assert ec.SEV_ORDER[0] == "Fatal"  # most severe first
    for s in ec.SEV_ORDER:
        assert s in ec.SEV_COLOR
    assert ec.SEV_COLOR["Fatal"] != ec.SEV_COLOR["Property Damage Only"]
