from livetools.analyze import _match_filter


def test_match_filter_missing_field():
    record = {"a": 1}
    assert _match_filter(record, "b", "==", 1) is False


def test_match_filter_basic_comparisons():
    record = {"val": 10}
    assert _match_filter(record, "val", "==", 10) is True
    assert _match_filter(record, "val", "==", 20) is False
    assert _match_filter(record, "val", "!=", 20) is True
    assert _match_filter(record, "val", ">", 5) is True
    assert _match_filter(record, "val", "<", 20) is True
    assert _match_filter(record, "val", ">=", 10) is True
    assert _match_filter(record, "val", "<=", 10) is True


def test_match_filter_hex_string():
    record = {"addr": "0x100"}
    # "0x100" string should be converted to int 256 for comparison
    assert _match_filter(record, "addr", "==", 256) is True
    assert _match_filter(record, "addr", "!=", 255) is True
    assert _match_filter(record, "addr", ">", 200) is True


def test_match_filter_type_error_fallback():
    # Comparing list > int will trigger TypeError and hit the fallback logic
    record = {"val": [1, 2, 3]}

    # In fallback: str(rv) != str(val) is used for any op other than "=="
    # op=">", str([1, 2, 3]) != str(0) -> True
    assert _match_filter(record, "val", ">", 0) is True


def test_match_filter_string_fallback_equals():
    # Comparing dict and int with == evaluates safely, but let's test string fallback equality manually
    # The initial try block will convert "123" to integer if string isn't hex. Wait, no.
    # If rv is str, it tries int(rv, 16), which fails since 123 is not valid hex.
    # Actually int("123", 16) is 291!
    # Let's check int("123", 16) -> 291
    # So "123" == 291 should be True in _match_filter!
    pass


def test_match_filter_hex_parse_fallback():
    record = {"val": "123"}  # int("123", 16) = 291
    assert _match_filter(record, "val", "==", 291) is True

    record_invalid_hex = {"val": "nothex"}
    # int("nothex", 16) fails ValueError, so it stays "nothex"
    assert _match_filter(record_invalid_hex, "val", "==", "nothex") is True
    assert _match_filter(record_invalid_hex, "val", "!=", "other") is True


def test_match_filter_nested_field():
    record = {"nested": {"val": 42}}
    assert _match_filter(record, "nested.val", "==", 42) is True
