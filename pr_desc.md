🎯 **What:** The testing gap in `retools/pyghidra_backend.py` has been addressed. The module was previously at ~83% coverage with multiple untested functions including environment path setups, error handling for decompilation, and CLI execution.

📊 **Coverage:**
* Added tests for `is_analyzed` to correctly check for empty representations (`.rep` dir empty or missing).
* Added tests for `_ensure_java_env` and `_ensure_ghidra_env` to verify proper detection and assignment of `JAVA_HOME` and `GHIDRA_INSTALL_DIR`.
* Added test for `_import_pyghidra` failing via `ImportError`.
* Added tests for `decompile` error paths (`pyghidra` missing, `GHIDRA_INSTALL_DIR` missing, and non-analyzed project).
* Added execution tests for the CLI (`__main__` entry point) via `runpy`.

✨ **Result:** The `retools/pyghidra_backend.py` module now has 100% test coverage, and its correctness has been comprehensively verified without introducing regressions.
