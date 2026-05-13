🧪 [testing improvement] Add tests for _match_filter

🎯 **What:** The testing gap addressed
This PR addresses the lack of test coverage for the filter logic in `livetools/analyze.py`. Specifically, the `_match_filter`, `_resolve_field`, and `_parse_filter` functions lacked dedicated unit tests, leaving simple logic comparisons vulnerable to regressions.

📊 **Coverage:** What scenarios are now tested
- **`_resolve_field`**: Tests standard object path resolution, handling of missing fields, and dealing with invalid array indices.
- **`_match_filter`**:
  - **Equality (`==`, `!=`)**: Standard comparisons, including the precise behavior of mismatched types without exception raising.
  - **Numeric (`>`, `<`, `>=`, `<=`)**: Integer and float comparisons.
  - **Hex conversion**: Validation that fields formatted as hex strings correctly parse and compare against integer parameters.
  - **Missing fields**: Ensure comparison operators fail gracefully on fields that `_resolve_field` evaluates to `None`.
  - **Type Error Fallback**: Validates that comparing incompatible types (like applying `<` to `int` and `str`), which trigger a `TypeError`, correctly falls back to string-based equality or inequality evaluation.
- **`_parse_filter`**: Standard scenarios covering numeric and equality operations parsing accurately into `(field, operator, value)`.

✨ **Result:** The improvement in test coverage
`tests/test_analyze.py` now provides solid, focused unit tests covering the core logic used when applying traces filters. This enables safer future iterations of the CLI analytics components.
