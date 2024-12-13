import pytest
from unittest.mock import patch
from db.db import (
    get_all_users,
    get_all_users_city_name,
    get_user_time_zone_db,
    get_user_db,
    get_city_name,
    get_sleep_goal_user,
    get_user_wake_time,
    get_has_provided_location,
)

# Test for get_all_users
@patch("db.db.execute_query_pg")
def test_get_all_users(mock_execute_query_pg):
    mock_execute_query_pg.return_value.fetchall.return_value = [
        {"id": 1, "name": "User1", "city_name": "City1", "time_zone": "UTC"},
        {"id": 2, "name": "User2", "city_name": "City2", "time_zone": "UTC+1"},
    ]

    result = get_all_users()

    mock_execute_query_pg.assert_called_once_with('SELECT * FROM public.users')
    assert result == [
        {"id": 1, "name": "User1", "city_name": "City1", "time_zone": "UTC"},
        {"id": 2, "name": "User2", "city_name": "City2", "time_zone": "UTC+1"},
    ]

# Test for get_all_users_city_name
@patch("db.db.execute_query_pg")
def test_get_all_users_city_name(mock_execute_query_pg):
    mock_execute_query_pg.return_value.fetchall.return_value = [
        {"id": 1, "city_name": "City1", "time_zone": "UTC"},
        {"id": 2, "city_name": "City2", "time_zone": "UTC+1"},
    ]

    result = get_all_users_city_name()

    mock_execute_query_pg.assert_called_once_with('SELECT id, city_name, time_zone FROM public.users')
    assert result == [
        {"id": 1, "city_name": "City1", "time_zone": "UTC"},
        {"id": 2, "city_name": "City2", "time_zone": "UTC+1"},
    ]

# Test for get_user_time_zone_db
@patch("db.db.execute_query_pg")
def test_get_user_time_zone_db(mock_execute_query_pg):
    mock_execute_query_pg.return_value.fetchone.return_value = {"time_zone": "UTC"}

    result = get_user_time_zone_db(1)

    mock_execute_query_pg.assert_called_once_with(
        'SELECT time_zone FROM public.users WHERE id = %(user_id)s', {'user_id': 1}
    )
    assert result == {"time_zone": "UTC"}

# Test for get_user_db
@patch("db.db.execute_query_pg")
def test_get_user_db(mock_execute_query_pg):
    mock_execute_query_pg.return_value.fetchone.return_value = {"id": 1, "name": "User1"}

    result = get_user_db(1)

    mock_execute_query_pg.assert_called_once_with(
        'SELECT * FROM public.users WHERE id = %(user_id)s', {'user_id': 1}
    )
    assert result == {"id": 1, "name": "User1"}

# Test for get_city_name
@patch("db.db.execute_query_pg")
def test_get_city_name(mock_execute_query_pg):
    mock_execute_query_pg.return_value.fetchone.return_value = {"city_name": "City1"}

    result = get_city_name(1)

    mock_execute_query_pg.assert_called_once_with(
        'SELECT city_name FROM public.users WHERE id = %(user_id)s', {'user_id': 1}
    )
    assert result == {"city_name": "City1"}

# Test for get_sleep_goal_user
@patch("db.db.execute_query_pg")
def test_get_sleep_goal_user(mock_execute_query_pg):
    mock_execute_query_pg.return_value.fetchone.return_value = {"sleep_goal": 8}

    result = get_sleep_goal_user(1)

    mock_execute_query_pg.assert_called_once_with(
        'SELECT sleep_goal FROM public.users WHERE id = %(user_id)s', {'user_id': 1}
    )
    assert result == {"sleep_goal": 8}

# Test for get_user_wake_time
@patch("db.db.execute_query_pg")
def test_get_user_wake_time(mock_execute_query_pg):
    mock_execute_query_pg.return_value.fetchone.return_value = {"id": 1, "wake_time": "07:00:00"}

    result = get_user_wake_time(1)

    mock_execute_query_pg.assert_called_once_with(
        'SELECT id, wake_time FROM public.users WHERE id = %(user_id)s', {'user_id': 1}
    )
    assert result == {"id": 1, "wake_time": "07:00:00"}

# Test for get_has_provided_location
@patch("db.db.execute_query_pg")
def test_get_has_provided_location(mock_execute_query_pg):
    mock_execute_query_pg.return_value.fetchone.return_value = {"id": 1, "has_provided_location": True}

    result = get_has_provided_location(1)

    mock_execute_query_pg.assert_called_once_with(
        'SELECT id, has_provided_location FROM public.users WHERE id = %(user_id)s', {'user_id': 1}
    )
    assert result == {"id": 1, "has_provided_location": True}
