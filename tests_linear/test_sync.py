import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Mock the environment variable before importing to avoid SystemExit
with patch.dict(os.environ, {"LINEAR_API_KEY": "test_key"}):
    from linear.sync import issue_exists


def test_issue_exists_true():
    expected_team_id = "test_team"
    expected_prefix = "Build 7 "

    with patch("linear.sync.gql") as mock_gql:
        mock_gql.return_value = {"issues": {"nodes": [{"id": "issue_1"}]}}

        result = issue_exists(expected_team_id, expected_prefix)

        assert result is True
        mock_gql.assert_called_once()
        args, kwargs = mock_gql.call_args
        query, variables = args
        assert "query($f: IssueFilter!)" in query
        assert variables == {
            "f": {
                "team": {"id": {"eq": "test_team"}},
                "title": {"startsWith": "Build 7 "},
            }
        }


def test_issue_exists_false_empty_nodes():
    with patch("linear.sync.gql") as mock_gql:
        mock_gql.return_value = {"issues": {"nodes": []}}
        result = issue_exists("test_team", "Build 7 ")
        assert result is False


def test_issue_exists_false_missing_keys():
    with patch("linear.sync.gql") as mock_gql:
        mock_gql.return_value = {}
        result = issue_exists("test_team", "Build 7 ")
        assert result is False


def test_issue_exists_false_none_nodes():
    with patch("linear.sync.gql") as mock_gql:
        mock_gql.return_value = {"issues": {}}
        result = issue_exists("test_team", "Build 7 ")
        assert result is False
