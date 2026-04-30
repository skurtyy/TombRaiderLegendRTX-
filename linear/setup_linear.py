"""One-time setup: creates Linear team, projects, labels, milestones for TombRaiderLegendRTX."""
import json
import os
import sys
from pathlib import Path

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
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


MILESTONES = [
    "Infrastructure",
    "Geometry Visible",
    "Hash Stability",
    "Visual Quality",
    "Stable Release",
]

LABELS = [
    ("proxy-code", "#6366f1"),
    ("config", "#8b5cf6"),
    ("static-analysis", "#06b6d4"),
    ("hash-stability", "#f59e0b"),
    ("culling", "#ef4444"),
    ("sky-water", "#3b82f6"),
    ("upstream", "#10b981"),
    ("auto-idea", "#a78bfa"),
    ("dead-end", "#6b7280"),
    ("blocker", "#dc2626"),
]


def main() -> None:
    me = gql("{ viewer { id name } }")
    print(f"Authenticated as: {me['viewer']['name']}")

    teams = gql("{ teams { nodes { id name } } }")
    team = next(
        (t for t in teams["teams"]["nodes"]
         if "legend" in t["name"].lower() or "trl" in t["name"].lower()),
        None,
    )
    if not team:
        print("Available teams:", [t["name"] for t in teams["teams"]["nodes"]])
        sys.exit("No TRL team found. Create it in Linear first.")

    team_id = team["id"]
    print(f"Team: {team['name']} ({team_id})")

    config = {"team_id": team_id, "milestones": {}, "labels": {}}
    Path("linear/config.json").write_text(json.dumps(config, indent=2))
    print("linear/config.json written. Run linear/sync.py to push first sync.")


if __name__ == "__main__":
    main()
