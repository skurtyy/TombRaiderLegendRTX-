"""Sync CHANGELOG + WHITEBOARD to Linear for TombRaiderLegendRTX."""
import json
import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path when invoked as `python linear/sync.py`
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from linear.parse_changelog import parse_changelog  # noqa: E402

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

API_KEY = os.environ.get("LINEAR_API_KEY", "")
if not API_KEY:
    sys.exit("Set LINEAR_API_KEY environment variable")

HEADERS = {"Authorization": API_KEY, "Content-Type": "application/json"}
GQL = "https://api.linear.app/graphql"


def gql(query: str, variables: dict | None = None) -> dict:
    r = requests.post(GQL, json={"query": query, "variables": variables or {}},
                      headers=HEADERS, timeout=30)
    r.raise_for_status()
    payload = r.json()
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload.get("data", {})


def create_issue(team_id: str, title: str, description: str, label_ids: list[str]) -> str:
    q = """
    mutation($input: IssueCreateInput!) {
      issueCreate(input: $input) { issue { id identifier } }
    }"""
    v = {"input": {"teamId": team_id, "title": title,
                   "description": description, "labelIds": label_ids}}
    data = gql(q, v)
    return data["issueCreate"]["issue"]["identifier"]


def main() -> None:
    config_path = Path("linear/config.json")
    if not config_path.exists():
        sys.exit("Run linear/setup_linear.py first")
    config = json.loads(config_path.read_text())
    team_id = config["team_id"]
    last_synced = config.get("last_synced_build", -1)

    builds = parse_changelog()
    last_build = builds[-1] if builds else None

    if last_build and last_build["build"] > last_synced:
        title = f"Build {last_build['build']} — {last_build['result'].upper()}"
        body = "\n".join(last_build["lines"][:30])
        issue_id = create_issue(team_id, title, body, [])
        print(f"Created: {issue_id}")
        config["last_synced_build"] = last_build["build"]
        config_path.write_text(json.dumps(config, indent=2))
    elif last_build:
        print(f"Build {last_build['build']} already synced, skipping.")
    else:
        print("No builds found in changelog.")

    print("Sync complete.")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "sync"
    if mode in ("--status", "status"):
        config = json.loads(Path("linear/config.json").read_text())
        print("Team:", config["team_id"])
        print("Last synced build:", config.get("last_synced_build", "none"))
    elif mode == "research":
        print("Research mode: invoke the research-scanner Claude agent for research tasks.")
    else:
        main()
