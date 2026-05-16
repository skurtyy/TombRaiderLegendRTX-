import os
import pytest
from unittest.mock import patch, Mock
import requests

# Set API key before import so it doesn't sys.exit
os.environ["LINEAR_API_KEY"] = "testkey"
from linear.sync import gql

def test_gql_success():
    with patch("linear.sync.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"key": "value"}}
        mock_post.return_value = mock_response

        result = gql("query myQuery", {"var": "1"})

        assert result == {"key": "value"}
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"] == {"query": "query myQuery", "variables": {"var": "1"}}
        assert "headers" in kwargs
        assert kwargs["headers"]["Authorization"] == "testkey"

def test_gql_http_error():
    with patch("linear.sync.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Bad response")
        mock_post.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            gql("query myQuery")

def test_gql_graphql_error():
    with patch("linear.sync.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {"errors": [{"message": "GraphQL error"}]}
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            gql("query myQuery")

        assert exc_info.value.args[0] == [{"message": "GraphQL error"}]

def test_gql_no_data():
    with patch("linear.sync.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        result = gql("query myQuery")

        assert result == {}
