🧪 [testing improvement description]
Add tests for get_file_metrics in automation/build_validator.py

🎯 **What:** The testing gap addressed
The `get_file_metrics` function in `automation/build_validator.py` was missing test coverage. This function computes `ArtifactMetrics` from direct file I/O operations and is critical for artifact verification.

📊 **Coverage:** What scenarios are now tested
Tests cover the following scenarios:
*   Providing a valid `Path` object correctly returns `ArtifactMetrics` with matching file path, size, and md5 sum.
*   Providing a valid `str` path correctly returns `ArtifactMetrics` with correct contents.
*   Providing a non-existent file path correctly raises a `FileNotFoundError`.
*   Providing a directory path instead of a file correctly raises a `FileNotFoundError`.

✨ **Result:** The improvement in test coverage
`get_file_metrics` is now fully tested, ensuring that edge cases involving nonexistent files and directories do not result in silent failures or unhandled obscure errors further down the pipeline, and we can refactor file IO code in `get_file_metrics` more confidently.
