import pytest
from unittest.mock import patch, MagicMock
from db.db import (
    get_all_sleep_records,
    get_sleep_records_per_week,
    get_sleep_record_last_db,
    get_sleep_time_without_wake_db,
    get_wake_time_null
)

@pytest.fixture
def mock_execute_query_pg():
    with patch("db.db.execute_query_pg") as mock:
        yield mock

# Test for get_all_sleep_records
@patch("db.db.execute_query_pg")
def test_get_all_sleep_records(mock_execute_query_pg):
    mock_execute_query_pg.return_value.fetchall.return_value = [
        {"user_id": 1, "sleep_time": "2024-12-01T23:00:00", "wake_time": "2024-12-02T07:00:00"},
        {"user_id": 1, "sleep_time": "2024-11-30T23:30:00", "wake_time": "2024-12-01T06:30:00"}
    ]

    result = get_all_sleep_records(1)

    mock_execute_query_pg.assert_called_once_with(
        'SELECT * FROM public.sleep_records WHERE user_id = %(user_id)s',
        {'user_id': 1}
    )
    assert result == [
        {"user_id": 1, "sleep_time": "2024-12-01T23:00:00", "wake_time": "2024-12-02T07:00:00"},
        {"user_id": 1, "sleep_time": "2024-11-30T23:30:00", "wake_time": "2024-12-01T06:30:00"}
    ]

# Test for get_sleep_records_per_week
@patch("db.db.execute_query_pg")
def test_get_sleep_records_per_week(mock_execute_query_pg):
    mock_execute_query_pg.return_value.fetchall.return_value = [
        {"sleep_time": "2024-12-01T23:00:00", "wake_time": "2024-12-02T07:00:00"},
        {"sleep_time": "2024-11-30T23:30:00", "wake_time": "2024-12-01T06:30:00"}
    ]

    result = get_sleep_records_per_week(1)

    mock_execute_query_pg.assert_called_once_with('''
        SELECT sleep_time, wake_time FROM public.sleep_records
        WHERE user_id = %(user_id)s AND wake_time IS NOT NULL
        ORDER BY sleep_time DESC LIMIT 7
    ''', {'user_id': 1}
    )
    assert result == [
        {"sleep_time": "2024-12-01T23:00:00", "wake_time": "2024-12-02T07:00:00"},
        {"sleep_time": "2024-11-30T23:30:00", "wake_time": "2024-12-01T06:30:00"}
    ]

# Test for get_sleep_record_last_db
@patch("db.db.execute_query_pg")
def test_get_sleep_record_last_db(mock_execute_query_pg):
    mock_execute_query_pg.return_value.fetchone.return_value = {
        "sleep_time": "2024-12-01T23:00:00", "wake_time": "2024-12-02T07:00:00"
    }

    result = get_sleep_record_last_db(1)

    mock_execute_query_pg.assert_called_once_with('''
        SELECT sleep_time, wake_time FROM public.sleep_records
        WHERE user_id = %(user_id)s
        ORDER BY sleep_time DESC
    ''',{'user_id': 1}
    )
    assert result == {
        "sleep_time": "2024-12-01T23:00:00", "wake_time": "2024-12-02T07:00:00"
    }

# Test for get_sleep_time_without_wake_db
@patch("db.db.execute_query_pg")
def test_get_sleep_time_without_wake_db(mock_execute_query_pg):
    mock_execute_query_pg.return_value.fetchone.return_value = {
        "sleep_time": "2024-12-01T23:00:00"
    }

    result = get_sleep_time_without_wake_db(1)

    mock_execute_query_pg.assert_called_once_with('''
        SELECT sleep_time FROM public.sleep_records 
        WHERE user_id = %(user_id)s AND wake_time IS NULL
    ''', {'user_id': 1}
    )
    assert result == {
        "sleep_time": "2024-12-01T23:00:00"
    }

# Test for get_wake_time_null
@patch("db.db.execute_query_pg")
def test_get_wake_time_null(mock_execute_query_pg):
    mock_execute_query_pg.return_value.fetchall.return_value = [
        {"wake_time": None}
    ]

    result = get_wake_time_null(1)

    mock_execute_query_pg.assert_called_once_with('''
        SELECT wake_time FROM public.sleep_records
        WHERE user_id = %(user_id)s
        AND wake_time IS NULL
    ''', {'user_id': 1}
    )
    assert result == [
        {"wake_time": None}
    ]
