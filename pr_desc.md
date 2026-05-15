🧹 [Code Health] Remove unused `revert_runtime` and `shutil` imports

🎯 **What:** Removed unused imports `revert_runtime` from `autopatch.patcher` and `shutil` from `autopatch/orchestrator.py`. Also fixed the `ruff` module level import check on line 13.

💡 **Why:** To improve code health by removing dead code, adhering to linting rules, and reducing clutter.

✅ **Verification:** Verified safe by running `ruff check autopatch/orchestrator.py` which returns `All checks passed!` and `PYTHONPATH=. python -m pytest tests/` which returns `228 passed, 19 skipped`. Also ensured git workspace is clean of any test artifacts like `.coverage` or `retools/data/signatures.db`.

✨ **Result:** A cleaner `autopatch/orchestrator.py` module with 0 linter errors and safe removal of unused functionality.
