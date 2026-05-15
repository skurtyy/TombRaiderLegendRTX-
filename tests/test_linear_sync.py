import pytest
from unittest.mock import patch
import sys
import os

# Set dummy API key before importing
os.environ["LINEAR_API_KEY"] = "dummy"

# Add root to sys.path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from linear.sync import issue_exists

@patch('linear.sync.gql')
def test_issue_exists_true(mock_gql):
    mock_gql.return_value = {"issues": {"nodes": [{"id": "issue-123"}]}}

    result = issue_exists("team-abc", "Build 7 ")

    assert result is True
    mock_gql.assert_called_once()
    args, kwargs = mock_gql.call_args
    assert "query($f: IssueFilter!)" in args[0]
    assert args[1] == {
        "f": {
            "team": {"id": {"eq": "team-abc"}},
            "title": {"startsWith": "Build 7 "},
        }
    }

@patch('linear.sync.gql')
def test_issue_exists_false_no_nodes(mock_gql):
    mock_gql.return_value = {"issues": {"nodes": []}}

    result = issue_exists("team-abc", "Build 7 ")

    assert result is False

@patch('linear.sync.gql')
def test_issue_exists_false_no_issues(mock_gql):
    mock_gql.return_value = {}

    result = issue_exists("team-abc", "Build 7 ")

    assert result is False
