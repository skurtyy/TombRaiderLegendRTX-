import pytest
from livetools.analyze import _match_filter, _resolve_field, _parse_filter

def test_resolve_field():
    record = {
        "addr": "0x1000",
        "leave": {"eax": 42},
        "enter": {"reads": [{"value": [1, 2, 3]}]}
    }

    assert _resolve_field(record, "addr") == "0x1000"
    assert _resolve_field(record, "leave.eax") == 42
    assert _resolve_field(record, "enter.reads.0.value.1") == 2

    # Missing fields
    assert _resolve_field(record, "missing") is None
    assert _resolve_field(record, "leave.ebx") is None
    assert _resolve_field(record, "enter.reads.1.value") is None

    # Invalid index
    assert _resolve_field(record, "enter.reads.invalid.value") is None


def test_match_filter_equality():
    record = {"status": "ok", "count": 5}

    # == operator
    assert _match_filter(record, "status", "==", "ok") is True
    assert _match_filter(record, "status", "==", "error") is False
    assert _match_filter(record, "count", "==", 5) is True
    # The current code's equality for int != str does NOT fallback to str comparison unless a TypeError was raised.
    # So if rv is 5 (int) and val is "5" (str), 5 == "5" evaluates to False without raising TypeError,
    # so it does not reach the fallback `str(rv) == str(val)`. Let's test the actual behavior.
    assert _match_filter(record, "count", "==", "5") is False

    # != operator
    assert _match_filter(record, "status", "!=", "error") is True
    assert _match_filter(record, "status", "!=", "ok") is False
    assert _match_filter(record, "count", "!=", 10) is True


def test_match_filter_numeric():
    record = {"count": 10, "ratio": 0.5}

    # > operator
    assert _match_filter(record, "count", ">", 5) is True
    assert _match_filter(record, "count", ">", 10) is False

    # >= operator
    assert _match_filter(record, "count", ">=", 10) is True

    # < operator
    assert _match_filter(record, "count", "<", 20) is True
    assert _match_filter(record, "count", "<", 10) is False

    # <= operator
    assert _match_filter(record, "count", "<=", 10) is True

    # float comparisons
    assert _match_filter(record, "ratio", "<", 1.0) is True
    assert _match_filter(record, "ratio", ">", 0.1) is True


def test_match_filter_hex_conversion():
    record = {"addr": "0x1000", "flags": "0x10"}

    # Comparing a hex string in the record against an integer value
    # The code tries: int(rv, 16) if rv is a string
    assert _match_filter(record, "addr", "==", 4096) is True
    assert _match_filter(record, "addr", ">", 4000) is True
    assert _match_filter(record, "addr", "<", 5000) is True


def test_match_filter_missing_field():
    record = {"status": "ok"}
    assert _match_filter(record, "missing", "==", "value") is False
    assert _match_filter(record, "missing", "!=", "value") is False


def test_match_filter_type_error_fallback():
    # Comparing incompatible types like int > str might raise TypeError
    # The code handles TypeError and falls back to string comparison for == / !=
    record = {"count": 5}

    # "5" == "hello" is False
    assert _match_filter(record, "count", "==", "hello") is False
    # "5" != "hello" is True
    assert _match_filter(record, "count", "!=", "hello") is True

    record2 = {"status": "ok"}
    # The behavior of `str > int` raises TypeError.
    # The except block is:
    # except TypeError: pass
    # return str(rv) == str(val) if op == "==" else str(rv) != str(val)
    # Since op is ">", it returns "ok" != "5" which is True!
    assert _match_filter(record2, "status", ">", 5) is True

def test_parse_filter():
    assert _parse_filter("count==5") == ("count", "==", 5)
    assert _parse_filter("status!=ok") == ("status", "!=", "ok")
    assert _parse_filter("addr>=0x1000") == ("addr", ">=", 4096)
    assert _parse_filter("ratio<0.5") == ("ratio", "<", 0.5)
    assert _parse_filter("missing") == (None, None, None)
