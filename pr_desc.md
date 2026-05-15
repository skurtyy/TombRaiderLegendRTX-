🎯 **What:** The code health issue addressed
Refactored the excessively long `build_parser()` function in `livetools/__main__.py` (which was ~430 lines) by extracting logical subcommand groupings into smaller helper functions.

💡 **Why:** How this improves maintainability
The original `build_parser()` function was difficult to read and maintain due to its massive size. By breaking the argument definitions out into modular, well-named helper functions (e.g., `_add_session_parsers`, `_add_trace_parsers`), the code is significantly more readable and easier to extend in the future.

✅ **Verification:** How you confirmed the change is safe
- Executed `python -m livetools --help` and `python -m livetools analyze --help` to verify the CLI topology and options remained completely unchanged.
- Ran the full `pytest` suite locally (`python -m pytest tests/`), ensuring no existing tests failed (228 passed, 19 skipped).
- Ensured 100% feature parity without modifying behavior.

✨ **Result:** The improvement achieved
A clean and modular `build_parser()` definition, completely eliminating the 400+ line monolithic block, making `livetools` simpler to navigate and modify.
