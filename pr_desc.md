🧹 [Remove unused import from dx9/tracer/__init__.py and fix CI tests]

🎯 **What:** The code health issue addressed
Removed the unused `main` import from `graphics/directx/dx9/tracer/__init__.py` and resolved a CI test failure due to the `numpy` version in `requirements.txt`.

💡 **Why:** How this improves maintainability
The static analysis tools correctly indicated that `from .cli import main` in `__init__.py` was unused. Removing it improves code readability and prevents unnecessary coupling. The module is executed via `python -m graphics.directx.dx9.tracer`, which goes through `__main__.py`, where `main` is properly imported from `.cli`. Removing it from `__init__.py` resolves the dead code without breaking existing functionality. In addition, the `numpy>=2.4.4` requirement was causing CI checks on Python 3.10 to fail, so it was relaxed to `numpy>=1.26.4` which works.

✅ **Verification:** How you confirmed the change is safe
1. Emptied `graphics/directx/dx9/tracer/__init__.py`.
2. Verified there are no external dependencies on this specific import across the codebase (checked with grep).
3. Ran `ruff check` on `__init__.py` successfully.
4. Installed dependencies locally (including the relaxed `numpy`).
5. Ran the full pytest suite (`python -m pytest tests/ -v`), and all 228 tests passed successfully.

✨ **Result:** The improvement achieved
A cleaner `__init__.py` file and a functional test suite fixing the CI pipeline on older python versions.
