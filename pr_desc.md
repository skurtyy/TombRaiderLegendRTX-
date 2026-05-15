🧹 [code health] fix unused import in health.py

🎯 **What:** The code health issue addressed
Fixed unused import of `find_hwnd_by_exe` in `gamepilot/health.py` by adding a dummy assignment `_ = find_hwnd_by_exe`. Also removed an unused `os` import and ran code formatting.

💡 **Why:** How this improves maintainability
Improves code maintainability by clearing static analysis warnings, while preserving the intended dynamic import check for the `livetools` requirement.

✅ **Verification:** How you confirmed the change is safe
Ran `ruff check` which showed 0 issues, and executed the full `pytest` suite ensuring all 228 tests pass with 0 regressions.

✨ **Result:** The improvement achieved
Cleaned up code health warning in `health.py` safely.
