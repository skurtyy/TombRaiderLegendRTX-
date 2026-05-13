import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from livetools.analyze import _resolve_field


def test_resolve_field_simple_key():
    record = {"addr": 0x1234}
    assert _resolve_field(record, "addr") == 0x1234


def test_resolve_field_nested_dict():
    record = {"leave": {"eax": 0x5678}}
    assert _resolve_field(record, "leave.eax") == 0x5678


def test_resolve_field_array_index():
    record = {
        "enter": {
            "reads": [
                {"value": [10, 20]},
                {"value": [30, 40]}
            ]
        }
    }
    assert _resolve_field(record, "enter.reads.0.value.1") == 20
    assert _resolve_field(record, "enter.reads.1.value.0") == 30


def test_resolve_field_missing_key():
    record = {"addr": 0x1234}
    assert _resolve_field(record, "not_exist") is None
    assert _resolve_field(record, "addr.missing") is None


def test_resolve_field_array_out_of_bounds():
    record = {"items": [1, 2, 3]}
    assert _resolve_field(record, "items.5") is None


def test_resolve_field_invalid_array_index():
    record = {"items": [1, 2, 3]}
    assert _resolve_field(record, "items.invalid") is None


def test_resolve_field_traverse_primitive():
    record = {"addr": 0x1234}
    assert _resolve_field(record, "addr.0") is None


def test_resolve_field_none_value():
    record = {"addr": None}
    assert _resolve_field(record, "addr") is None
    assert _resolve_field(record, "addr.subfield") is None


def test_resolve_field_tuple():
    record = {"items": (1, 2, 3)}
    assert _resolve_field(record, "items.1") == 2
