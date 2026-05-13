🧪 Add tests for _extract_json markdown failure paths

🎯 **What:** The testing gap addressed
This adds tests covering the markdown failure paths in `_extract_json`, specifically what happens when an invalid markdown JSON block is supplied, or when an invalid JSON markdown block is supplied but there is a fallback to the next block which is valid.

📊 **Coverage:** What scenarios are now tested
- Handling of an invalid json block markdown format.
- Fallback loop handling in `_extract_json` to correctly jump to the next code block when `json.loads` fails on the current code block.

✨ **Result:** The improvement in test coverage
The test coverage of `gamepilot/vision.py` went from 79% to 81%, and the `test_vision.py` module maintains 100% test coverage.
