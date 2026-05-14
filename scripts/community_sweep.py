"""Weekly Remix community sweep.

Uses Claude with web search to identify NEW (this week) findings in the RTX Remix
community relevant to cdcEngine, D3D9 FFP proxy, or hash stability.
"""
from __future__ import annotations

import os
import sys
import datetime as dt
from pathlib import Path

import anthropic

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "community-findings"
OUT_DIR.mkdir(exist_ok=True)

SYSTEM = """You are scanning the RTX Remix community for findings relevant to a Tomb Raider: Legend (2006, cdcEngine) D3D9 FFP proxy DLL project.

Use web_search to look for content from the past 7 days on:
- github.com/NVIDIAGameWorks/rtx-remix issues, PRs, releases
- github.com/NVIDIAGameWorks/dxvk-remix
- xoxor4d/remix-comp-projects
- r/RTXRemix
- RTX Remix Discord public summaries
- ModDB RTX Remix projects
- Any cdcEngine modding work (Tomb Raider Legend/Anniversary/Underworld, Painkiller)

Output a structured weekly digest. Format:
## New this week
### Topic
- **Source**: URL
- **Date**: YYYY-MM-DD
- **Summary**: 1-2 sentences
- **Relevance to TRL**: 1-2 sentences

Skip anything older than 7 days. Skip irrelevant content. Be ruthless about signal-to-noise.
"""


def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1

    client = anthropic.Anthropic(api_key=api_key)
    today = dt.date.today().isoformat()

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4000,
        system=SYSTEM,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 15}],
        messages=[
            {
                "role": "user",
                "content": f"Run the weekly community sweep. Today is {today}. Output the digest.",
            }
        ],
    )

    digest = "\n".join(
        block.text for block in response.content if block.type == "text"
    )

    out_path = OUT_DIR / f"{today}.md"
    out_path.write_text(digest, encoding="utf-8")
    (OUT_DIR / "latest.md").write_text(digest, encoding="utf-8")
    print(f"Community digest written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
