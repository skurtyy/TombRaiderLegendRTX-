import sys
import os

# Ensure the root of the repository is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from livetools.analyze import _flatten
from hypothesis import given, strategies as st


def test_flatten_empty():
    assert _flatten({}) == {}


def test_flatten_flat():
    d = {"a": 1, "b": "hello", "c": True}
    assert _flatten(d) == d


def test_flatten_nested_dict():
    d = {"a": {"b": {"c": 1}}, "d": 2}
    expected = {"a.b.c": 1, "d": 2}
    assert _flatten(d) == expected


def test_flatten_with_prefix():
    d = {"a": 1, "b": {"c": 2}}
    expected = {"custom.a": 1, "custom.b.c": 2}
    assert _flatten(d, prefix="custom") == expected


# Define a recursive strategy for generating nested dictionaries
# We don't generate lists because the function _flatten doesn't recursively flatten lists.
def json_dict_strategy():
    return st.recursive(
        st.dictionaries(
            st.text(),
            st.integers()
            | st.text()
            | st.booleans()
            | st.none()
            | st.lists(st.integers()),
        ),
        lambda children: st.dictionaries(st.text(), children),
        max_leaves=10,
    )


@given(json_dict_strategy())
def test_flatten_property(d):
    flat = _flatten(d)

    # Property 1: The flattened dict should not contain any dict values
    for val in flat.values():
        assert not isinstance(val, dict)

    # Property 2: The flattened dict should be a dict
    assert isinstance(flat, dict)
