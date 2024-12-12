import pytest
from unittest.mock import patch, MagicMock
import psycopg2
from db.db import exception_handler

# Пример функции для тестирования декоратора
@exception_handler
def test_function(param1, param2=None):
    if param1 == "raise_operational_error":
        raise psycopg2.OperationalError("Test Operational Error")
    elif param1 == "raise_database_error":
        raise psycopg2.DatabaseError("Test Database Error")
    elif param1 == "raise_general_error":
        raise ValueError("Test General Error")
    return f"Success: {param1}, {param2}"

@patch("db.db.logger")
def test_exception_handler_no_error(mock_logger):
    """Test that the decorator logs the function call and returns the correct result when no error occurs."""
    result = test_function("test_value", param2="test_param")
    assert result == "Success: test_value, test_param"
    mock_logger.debug.assert_called_once_with(
        "Вызов функции test_function с параметрами test_value, param2=test_param"
    )

@patch("db.db.logger")
def test_exception_handler_operational_error(mock_logger):
    """Test that the decorator catches and logs OperationalError."""
    result = test_function("raise_operational_error")
    assert result is None
    mock_logger.error.assert_called_once_with(
        "Ошибка дступа к данным при выполнении функции test_function: Test Operational Error",
        exc_info=True
    )

@patch("db.db.logger")
def test_exception_handler_database_error(mock_logger):
    """Test that the decorator catches and logs DatabaseError."""
    result = test_function("raise_database_error")
    assert result is None
    mock_logger.error.assert_called_once_with(
        "Ошибка базы данных при выполнении функции test_function: Test Database Error",
        exc_info=True
    )

@patch("db.db.logger")
def test_exception_handler_general_error(mock_logger):
    """Test that the decorator catches and logs general exceptions."""
    result = test_function("raise_general_error")
    assert result is None
    mock_logger.error.assert_called_once_with(
        "Ошибка при выполнения функции test_function: Test General Error",
        exc_info=True
    )