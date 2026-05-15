🧹 [Remove unused import from dx9/tracer/__init__.py]

🎯 **What:** The code health issue addressed
Removed the unused `main` import from `graphics/directx/dx9/tracer/__init__.py`.

💡 **Why:** How this improves maintainability
The static analysis tools correctly indicated that `from .cli import main` in `__init__.py` was unused. Removing it improves code readability and prevents unnecessary coupling. The module is executed via `python -m graphics.directx.dx9.tracer`, which goes through `__main__.py`, where `main` is properly imported from `.cli`. Removing it from `__init__.py` resolves the dead code without breaking existing functionality.

✅ **Verification:** How you confirmed the change is safe
1. Emptied `graphics/directx/dx9/tracer/__init__.py`.
2. Verified there are no external dependencies on this specific import across the codebase (checked with grep).
3. Ran `ruff check` on `__init__.py` successfully.
4. Ran the full pytest suite (`python -m pytest tests/ -v`), and all 228 tests passed successfully.

✨ **Result:** The improvement achieved
A cleaner `__init__.py` file and resolution of the dead code issue.
