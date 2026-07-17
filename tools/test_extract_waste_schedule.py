from types import SimpleNamespace

import pytest

import extract_waste_schedule


class FakeZip:
    def __init__(self, *, file_size, compress_size, payload=b"payload"):
        self.info = SimpleNamespace(file_size=file_size, compress_size=compress_size)
        self.payload = payload
        self.read_called = False

    def getinfo(self, _name):
        return self.info

    def read(self, _name):
        self.read_called = True
        return self.payload


def test_bounded_zip_read_rejects_oversized_xml_before_reading():
    archive = FakeZip(
        file_size=extract_waste_schedule.MAX_XML_ENTRY_BYTES + 1,
        compress_size=1024,
    )

    with pytest.raises(ValueError, match="too large"):
        extract_waste_schedule._read_bounded(archive, "xl/sharedStrings.xml")

    assert archive.read_called is False


def test_bounded_zip_read_rejects_suspicious_compression_ratio():
    archive = FakeZip(file_size=1_000_000, compress_size=1)

    with pytest.raises(ValueError, match="compression ratio"):
        extract_waste_schedule._read_bounded(archive, "xl/worksheets/sheet1.xml")

    assert archive.read_called is False
