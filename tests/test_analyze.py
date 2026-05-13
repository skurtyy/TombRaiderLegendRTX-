import pytest
from livetools.analyze import _match_filter

def test_match_filter_missing_field():
    record = {"a": 1}
    assert _match_filter(record, "b", "==", 1) is False
    assert _match_filter(record, "a.b", "==", 1) is False

def test_match_filter_hex_conversion():
    # The code attempts to parse strings as base-16 integers:
    # try: rv = int(rv, 16)
    record = {"a": "0x10", "b": "10", "c": "nothex", "d": "10.5"}

    # "0x10" -> 16
    assert _match_filter(record, "a", "==", 16) is True
    # "10" -> 16
    assert _match_filter(record, "b", "==", 16) is True
    # "nothex" -> remains "nothex"
    assert _match_filter(record, "c", "==", "nothex") is True
    # "10.5" -> ValueError, remains "10.5"
    assert _match_filter(record, "d", "==", "10.5") is True

def test_match_filter_operators():
    record = {"val": 10}
    assert _match_filter(record, "val", "==", 10) is True
    assert _match_filter(record, "val", "!=", 5) is True
    assert _match_filter(record, "val", ">", 5) is True
    assert _match_filter(record, "val", "<", 15) is True
    assert _match_filter(record, "val", ">=", 10) is True
    assert _match_filter(record, "val", "<=", 10) is True

    assert _match_filter(record, "val", "==", 5) is False
    assert _match_filter(record, "val", "!=", 10) is False
    assert _match_filter(record, "val", ">", 15) is False
    assert _match_filter(record, "val", "<", 5) is False
    assert _match_filter(record, "val", ">=", 15) is False
    assert _match_filter(record, "val", "<=", 5) is False

def test_match_filter_type_error_fallback():
    # Comparing types that can't be ordered (e.g. string vs int for >, <) raises TypeError
    # The code catches it and does a string equality/inequality comparison fallback
    record = {"val": 10}

    # "hello" > 5 raises TypeError (in python 3). It then evaluates `str(rv) != str(val)`
    # str(10) != "5" -> "10" != "5" -> True
    assert _match_filter(record, "val", ">", "5") is True

    # "hello" == 10 falls back to str(rv) == str(val) if it was raised (but == doesn't raise TypeError)
    record2 = {"val": "hello"}
    assert _match_filter(record2, "val", "==", "hello") is True
    assert _match_filter(record2, "val", "!=", "hello") is False

def test_match_filter_nested_field():
    record = {"enter": {"reads": [{"value": [42]}]}}
    assert _match_filter(record, "enter.reads.0.value.0", "==", 42) is True
    assert _match_filter(record, "enter.reads.1.value.0", "==", 42) is False
