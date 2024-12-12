from unittest.mock import patch, MagicMock

from db import get_all_reminders, get_reminder_db, get_reminder_time_db


@patch("db.db.execute_query_pg")
def test_get_all_reminders(mock_execute_query_pg):
    # Create MockMagic object
    mock_execute_query_pg.return_value.fetchall.return_value = [
        {'user_id': 1},
        {'user_id': 2},
    ]

    query = 'SELECT user_id FROM public.reminders'

    # Call the function
    result = get_all_reminders()

    # Assert the query was executed
    mock_execute_query_pg.assert_called_once_with(query)

    # Assert the result is as expected
    assert result == [{'user_id': 1}, {'user_id': 2}]

@patch("db.db.execute_query_pg")
def test_get_reminder_db(mock_execute_query_pg):
    # Mock response from execute_query_pg
    mock_execute_query_pg.return_value.fetchone.return_value = {
        'user_id': 1,
        'reminder_time': '10:00'
    }

    # Call the function
    user_id = 1
    result = get_reminder_db(user_id)

    # Assert the query was executed with the correct parameters
    mock_execute_query_pg.assert_called_once_with(
        'SELECT * FROM public.reminders WHERE user_id = %(user_id)s',
        {'user_id': user_id}
    )

    # Assert the result is as expected
    assert result == {'user_id': 1, 'reminder_time': '10:00'}

@patch("db.db.execute_query_pg")
def test_get_reminder_time_db(mock_execute_query_pg):
    # Mock response from execute_query_pg
    mock_execute_query_pg.return_value.fetchone.return_value = {
        'reminder_time': '10:00'
    }

    # Call the function
    user_id = 1
    result = get_reminder_time_db(user_id)

    # Assert the query was executed with the correct parameters
    mock_execute_query_pg.assert_called_once_with(
        'SELECT reminder_time FROM public.reminders WHERE user_id = %(user_id)s',
        {'user_id': user_id}
    )

    # Assert the result is as expected
    assert result == {'reminder_time': '10:00'}

@patch("db.db.execute_query_pg")
def test_get_all_reminders_exception(mock_execute_query_pg):
    # Mock exception
    mock_execute_query_pg.side_effect = Exception("Database error")

    # Call the function and assert it handles the exception
    result = get_all_reminders()

    # Assert the result is None
    assert result is None

@patch("db.db.execute_query_pg")
def test_get_reminder_db_exception(mock_execute_query_pg):
    # Mock exception
    mock_execute_query_pg.side_effect = Exception("Database error")

    # Call the function and assert it handles the exception
    result = get_reminder_db(1)

    # Assert the result is None
    assert result is None

@patch("db.db.execute_query_pg")
def test_get_reminder_time_db_exception(mock_execute_query_pg):
    # Mock exception
    mock_execute_query_pg.side_effect = Exception("Database error")

    # Call the function and assert it handles the exception
    result = get_reminder_time_db(1)

    # Assert the result is None
    assert result is None
