🧪 [Testing] Add unit tests for `_match_filter` in `livetools/analyze.py`

🎯 **What:**
The `_match_filter` function in `livetools/analyze.py` is responsible for parsing and matching values against parsed trace records. It handles edge cases around field resolution, hexadecimal conversion, Python type mismatches (like string/int comparisons falling back to string inequalities), and boolean operator routing. However, this critical function previously lacked unit test coverage.

📊 **Coverage:**
A new test file `tests/test_analyze.py` has been created, covering:
*   Resolution of missing root and nested fields defaulting to `False`.
*   Handling of base-16 conversions specifically targeted by the tool's implementation (`0x10` and `10` -> `16`).
*   Standard comparison operators (`==`, `!=`, `<`, `>`, `<=`, `>=`).
*   Verification of the `TypeError` fallback behavior when comparing unorderable types (e.g. integer versus string falls back safely).

✨ **Result:**
The test suite's coverage has improved substantially for `livetools/analyze.py`. These assertions act as a strong regression safety net, ensuring the offline trace evaluation logic remains deterministic against diverse trace input sources.

🛠️ **CI Fixes:**
Fixed CI warnings and errors that appeared in the previous commits:
1. Updated `actions/checkout@v4` to `actions/checkout@v4.2.2` in all `.github/workflows` to address Node 20 deprecation warnings.
2. Updated `.github/workflows/_auto-label.yml` to use `actions/labeler@v5` instead of the broken `peter-evans/create-or-update-labels@v4` which caused "repository not found".
3. Removed the custom CodeQL workflow files (`.github/workflows/codeql.yml` and `.github/workflows/_codeql.yml`) as GitHub's Default Setup for Code Scanning is enabled on the repository and causes advanced configurations to fail to upload SARIF results.
4. Catch `urllib` exception during Anthropic API requests in `.github/workflows/_claude-pr-risk.yml` and fallback gracefully to `high` risk instead of failing the workflow when there are API errors (like 400 Bad Request).
