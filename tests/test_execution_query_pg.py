import pytest
from unittest.mock import patch, MagicMock
from db.execute_query.execute_pg import execute_query_pg
import psycopg2
from psycopg2.extras import RealDictCursor

@patch("psycopg2.connect")
def test_execute_query_pg_success(mock_connect):
    # Mock the connection and cursor
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    # Define the test query and parameters
    query = "SELECT * FROM public.users WHERE id = %(user_id)s"
    params = {"user_id": 1}

    # Call the function
    result = execute_query_pg(query, params)

    # Assert that the connection and cursor were used as expected
    mock_connect.assert_called_once_with(
        database="sleep_bot_database", user="postgres", password="root",
        host="localhost", port="5432", cursor_factory=RealDictCursor
    )
    mock_cursor.execute.assert_called_once_with(query, params)
    mock_connection.commit.assert_called_once()

    # Assert the result is the mocked cursor
    assert result == mock_cursor

@patch("psycopg2.connect")
def test_execute_query_pg_no_params(mock_connect):
    # Mock the connection and cursor
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    # Define the test query
    query = "SELECT * FROM public.users"

    # Call the function without parameters
    result = execute_query_pg(query)

    # Assert that the connection and cursor were used as expected
    mock_connect.assert_called_once_with(
        database="sleep_bot_database", user="postgres", password="root",
        host="localhost", port="5432", cursor_factory=RealDictCursor
    )
    mock_cursor.execute.assert_called_once_with(query)
    mock_connection.commit.assert_called_once()

    # Assert the result is the mocked cursor
    assert result == mock_cursor

@patch("psycopg2.connect")
def test_execute_query_pg_operational_error(mock_connect):
    # Mock the connection to raise an OperationalError
    mock_connect.side_effect = psycopg2.OperationalError("Connection failed")

    # Call the function
    result = execute_query_pg("SELECT 1")

    # Assert that the result is None
    assert result is None

    # Assert that the connection was attempted
    mock_connect.assert_called_once_with(
        database="sleep_bot_database", user="postgres", password="root",
        host="localhost", port="5432", cursor_factory=RealDictCursor
    )

@patch("psycopg2.connect")
def test_execute_query_pg_general_exception(mock_connect):
    # Mock the connection and cursor
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_connection
    mock_connection.cursor.return_value = mock_cursor

    # Mock the cursor to raise an exception on execute
    mock_cursor.execute.side_effect = Exception("Query failed")

    # Call the function
    result = execute_query_pg("SELECT 1")

    # Assert that the result is None
    assert result is None

    # Assert that the connection and cursor were used as expected
    mock_connect.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_called_once_with("SELECT 1")