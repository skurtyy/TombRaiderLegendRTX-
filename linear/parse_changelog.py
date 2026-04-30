"""Parse CHANGELOG.md into structured build records for Linear sync.

Supports TRL headings:
  ## [2026-04-13] BUILDS-076-077 -- title
  ## [2026-04-13] BUILDS-077 -- title

Build number is the highest in a range (077 from BUILDS-076-077).
Non-build headings (TERRAIN-ANALYSIS, BOOTSTRAP, etc.) are skipped.
"""
import re
from pathlib import Path
from typing import Any

# Matches: ## [DATE] BUILDS-NNN  or  ## [DATE] BUILDS-NNN-MMM
_BUILD_RE = re.compile(
    r"^##\s+\[[^\]]+\]\s+BUILDS?-(\d+)(?:-(\d+))?",
    re.IGNORECASE,
)


def parse_changelog(path: str = "CHANGELOG.md") -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    builds: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in text.splitlines():
        m = _BUILD_RE.match(line)
        if m:
            if current:
                builds.append(current)
            # Use the upper bound of a range (e.g. 077 from BUILDS-076-077)
            build_num = int(m.group(2) if m.group(2) else m.group(1))
            current = {
                "build": build_num,
                "lines": [],
                "result": "unknown",
                "dead_ends": [],
                "blockers": [],
            }
            continue
        if current is None:
            continue
        current["lines"].append(line)
        low = line.lower()
        if any(w in low for w in ("pass", "working", "visible", "fixed", "confirmed", "stable")):
            current["result"] = "pass"
        if any(w in low for w in ("fail", "broken", "regression", "black screen", "crash")):
            current["result"] = "fail"
        if "dead end" in low or "dead-end" in low:
            current["dead_ends"].append(line.strip())
        if "blocker" in low:
            current["blockers"].append(line.strip())

    if current:
        builds.append(current)
    return builds


if __name__ == "__main__":
    import json
    builds = parse_changelog()
    print(json.dumps([{"build": b["build"], "result": b["result"]} for b in builds], indent=2))
