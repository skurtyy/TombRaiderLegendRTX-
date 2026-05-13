from livetools.analyze import _flatten


class TestAnalyzeFlatten:
    def test_flatten_empty(self):
        assert _flatten({}) == {}

    def test_flatten_flat(self):
        d = {"a": 1, "b": "two", "c": True}
        assert _flatten(d) == d

    def test_flatten_nested_dict(self):
        d = {"a": {"b": {"c": 1}}, "d": 2}
        expected = {"a.b.c": 1, "d": 2}
        assert _flatten(d) == expected

    def test_flatten_list(self):
        d = {"a": [1, 2, 3]}
        expected = {"a.0": 1, "a.1": 2, "a.2": 3}
        assert _flatten(d) == expected

    def test_flatten_nested_list_of_dicts(self):
        d = {"a": [{"b": 1}, {"c": 2}]}
        expected = {"a.0.b": 1, "a.1.c": 2}
        assert _flatten(d) == expected

    def test_flatten_complex(self):
        d = {
            "name": "john",
            "info": {"age": 30, "address": {"city": "NY", "zip": "10001"}},
            "tags": ["user", "active"],
            "roles": [{"id": 1, "name": "admin"}, {"id": 2, "name": "editor"}],
        }
        expected = {
            "name": "john",
            "info.age": 30,
            "info.address.city": "NY",
            "info.address.zip": "10001",
            "tags.0": "user",
            "tags.1": "active",
            "roles.0.id": 1,
            "roles.0.name": "admin",
            "roles.1.id": 2,
            "roles.1.name": "editor",
        }
        assert _flatten(d) == expected
