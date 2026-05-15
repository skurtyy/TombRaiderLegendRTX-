from unittest.mock import patch, MagicMock
import pytest
from requests.exceptions import HTTPError

from linear.sync import gql

@patch("linear.sync.requests.post")
def test_gql_success(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"issues": {"nodes": []}}}
    mock_post.return_value = mock_response

    result = gql("query { test }", {"var1": "val1"})

    mock_post.assert_called_once()
    # Check that post was called with correct arguments
    _, kwargs = mock_post.call_args
    assert kwargs["json"] == {"query": "query { test }", "variables": {"var1": "val1"}}
    assert result == {"issues": {"nodes": []}}

@patch("linear.sync.requests.post")
def test_gql_errors_in_payload(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"errors": [{"message": "Invalid query"}]}
    mock_post.return_value = mock_response

    with pytest.raises(RuntimeError) as exc_info:
        gql("query { test }")

    mock_post.assert_called_once()
    assert exc_info.value.args[0] == [{"message": "Invalid query"}]

@patch("linear.sync.requests.post")
def test_gql_http_error(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
    mock_post.return_value = mock_response

    with pytest.raises(HTTPError) as exc_info:
        gql("query { test }")

    mock_post.assert_called_once()
    assert str(exc_info.value) == "404 Not Found"
