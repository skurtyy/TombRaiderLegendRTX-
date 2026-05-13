🧪 Added Unit Tests for `_resolve_field`

## 🎯 What
Added missing tests for the `_resolve_field` function in `livetools/analyze.py`. `_resolve_field` is a pure dict manipulation function that resolves dot-separated field paths with optional array indices. Being a pure function, it is an excellent candidate for unit tests to ensure its robustness when parsing potentially complex offline JSONL traces.

## 📊 Coverage
The new `tests/test_livetools_analyze.py` script introduces 9 focused unit test cases for `_resolve_field`, including:
- **Simple key retrieval** (e.g., `"addr"`)
- **Nested dict key retrieval** (e.g., `"leave.eax"`)
- **Array index path resolution** (e.g., `"enter.reads.0.value.1"`)
- **Tuple resolution**
- **Graceful handling of missing keys**
- **Graceful handling of array index out of bounds**
- **Graceful handling of invalid array index inputs**
- **Graceful handling of traversal attempts over primitives**
- **Graceful handling of `None` values in records**

## ✨ Result
The addition of `tests/test_livetools_analyze.py` brings 100% path coverage for the `_resolve_field` function, preventing regressions and validating its accuracy before the function is heavily relied upon by the offline trace analysis scripts.
