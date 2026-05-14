"""TRL Daily Review Agent.

Runs against the repo state, produces a blind-spot analysis + priority queue,
and writes to daily-reviews/YYYY-MM-DD.md.

Flags HAS_BLOCKERS=true via $GITHUB_ENV if any critical blockers detected.
"""
from __future__ import annotations

import os
import sys
import datetime as dt
from pathlib import Path

import anthropic

REPO_ROOT = Path(__file__).resolve().parent.parent
REVIEW_DIR = REPO_ROOT / "daily-reviews"
REVIEW_DIR.mkdir(exist_ok=True)

CONTEXT_FILES = [
    "CLAUDE.md",
    "WHITEBOARD.md",
    "CHANGELOG.md",
    "README.md",
    "proxy.ini",
    "rtx.conf",
]


def read_context() -> str:
    """Concatenate all canonical context files with headers."""
    parts: list[str] = []
    for fname in CONTEXT_FILES:
        path = REPO_ROOT / fname
        if path.exists():
            parts.append(f"\n## ===== {fname} =====\n")
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
    # Most recent 5 build summaries
    build_dirs = sorted(
        [p for p in REPO_ROOT.rglob("build-*/SUMMARY.md")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:5]
    for build_summary in build_dirs:
        parts.append(f"\n## ===== {build_summary.relative_to(REPO_ROOT)} =====\n")
        parts.append(build_summary.read_text(encoding="utf-8", errors="replace"))
    return "".join(parts)


SYSTEM = """You are a senior reverse-engineering and graphics-pipeline analyst conducting a daily review of the TombRaiderLegendRTX project.

Your output target: another LLM that will execute on these findings tomorrow.

Mandatory output structure:
1. **Project state snapshot** (current build, active blockers)
2. **Blind-spot analysis** — assumptions in WHITEBOARD.md that lack reproducible test evidence
3. **Contradictions** — claims that conflict with the latest build evidence
4. **Priority queue** — ranked list of next experiments by effort-to-impact ratio
5. **Critical blockers** — anything requiring human input (mark "CRITICAL:" at line start)

Hard rules:
- Never mark a claim "Believed Resolved" — only "Verified (build-NNN)" with explicit evidence
- Never propose an experiment in the CHANGELOG.md dead-ends table
- Be exhaustive and technical; this is an LLM-to-LLM handoff, not a user-facing summary
"""

USER_TEMPLATE = """Review the following project state and produce today's daily review.

Today's date: {date}

{context}

Begin review.
"""


def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1

    client = anthropic.Anthropic(api_key=api_key)
    context = read_context()
    today = dt.date.today().isoformat()

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=8000,
        thinking={"type": "enabled", "budget_tokens": 4000},
        system=SYSTEM,
        messages=[
            {
                "role": "user",
                "content": USER_TEMPLATE.format(date=today, context=context[:180000]),
            }
        ],
    )

    # Extract text blocks (skip thinking blocks)
    review_text = "\n".join(
        block.text for block in response.content if block.type == "text"
    )

    out_path = REVIEW_DIR / f"{today}.md"
    out_path.write_text(review_text, encoding="utf-8")
    (REVIEW_DIR / "latest.md").write_text(review_text, encoding="utf-8")

    # Detect blockers
    has_blockers = "CRITICAL:" in review_text
    if has_blockers:
        blocker_lines = [
            line for line in review_text.splitlines() if "CRITICAL:" in line
        ]
        (REVIEW_DIR / "latest-blockers.md").write_text(
            "\n".join(blocker_lines), encoding="utf-8"
        )
        gh_env = os.environ.get("GITHUB_ENV")
        if gh_env:
            with open(gh_env, "a", encoding="utf-8") as fh:
                fh.write("HAS_BLOCKERS=true\n")

    print(f"Daily review written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
