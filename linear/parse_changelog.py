"""Parse CHANGELOG.md into structured build records for Linear sync."""
import re
from pathlib import Path
from typing import Any


def parse_changelog(path: str = "CHANGELOG.md") -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    builds: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in text.splitlines():
        m = re.match(r"^##\s+Build\s+(\d+)", line)
        if m:
            if current:
                builds.append(current)
            current = {"build": int(m.group(1)), "lines": [], "result": "unknown",
                       "dead_ends": [], "blockers": []}
            continue
        if current is None:
            continue
        current["lines"].append(line)
        low = line.lower()
        if any(w in low for w in ("pass", "working", "visible", "fixed")):
            current["result"] = "pass"
        if any(w in low for w in ("fail", "broken", "regression", "black screen")):
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
    print(json.dumps(builds, indent=2))
