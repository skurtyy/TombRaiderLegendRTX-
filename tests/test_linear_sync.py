import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linear.sync import issue_exists


@patch("linear.sync.gql")
def test_issue_exists_true(mock_gql):
    mock_gql.return_value = {"issues": {"nodes": [{"id": "123"}]}}

    result = issue_exists("team-123", "Build 10 ")

    assert result is True
    mock_gql.assert_called_once()
    args, kwargs = mock_gql.call_args

    expected_vars = {
        "f": {
            "team": {"id": {"eq": "team-123"}},
            "title": {"startsWith": "Build 10 "},
        }
    }
    assert args[1] == expected_vars


@patch("linear.sync.gql")
def test_issue_exists_false_empty_nodes(mock_gql):
    mock_gql.return_value = {"issues": {"nodes": []}}

    result = issue_exists("team-123", "Build 10 ")

    assert result is False


@patch("linear.sync.gql")
def test_issue_exists_false_no_issues(mock_gql):
    mock_gql.return_value = {}

    result = issue_exists("team-123", "Build 10 ")

    assert result is False
