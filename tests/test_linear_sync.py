from unittest.mock import patch
from linear.sync import issue_exists


@patch("linear.sync.gql")
def test_issue_exists_true(mock_gql):
    # Setup mock to return data indicating issue exists
    mock_gql.return_value = {"issues": {"nodes": [{"id": "some-id"}]}}

    # Call function
    result = issue_exists("team-123", "Build 10 ")

    # Assert result is True
    assert result is True

    # Verify gql was called with correct arguments
    mock_gql.assert_called_once()
    args, kwargs = mock_gql.call_args
    assert "query($f: IssueFilter!)" in args[0]
    assert args[1] == {
        "f": {
            "team": {"id": {"eq": "team-123"}},
            "title": {"startsWith": "Build 10 "},
        }
    }


@patch("linear.sync.gql")
def test_issue_exists_false_empty_nodes(mock_gql):
    # Setup mock to return empty nodes list
    mock_gql.return_value = {"issues": {"nodes": []}}

    result = issue_exists("team-123", "Build 10 ")
    assert result is False


@patch("linear.sync.gql")
def test_issue_exists_false_missing_nodes(mock_gql):
    # Setup mock to return issues but missing nodes
    mock_gql.return_value = {"issues": {}}

    result = issue_exists("team-123", "Build 10 ")
    assert result is False


@patch("linear.sync.gql")
def test_issue_exists_false_missing_issues(mock_gql):
    # Setup mock to return missing issues key entirely
    mock_gql.return_value = {}

    result = issue_exists("team-123", "Build 10 ")
    assert result is False
