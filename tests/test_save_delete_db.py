import re

import pytest
from unittest.mock import patch
from db.db import (
    save_user_to_db,
    save_user_city,
    save_user_time_zone_db,
    save_phone_number,
    save_sleep_goal_db,
    save_wake_time_user_db,
    save_sleep_time_records_db,
    save_wake_time_records_db,
    save_sleep_quality_db,
    save_mood_db,
    save_reminder_time_db,
    delete_reminder_db,
    delete_sleep_records_db,
    delete_user_db,
    delete_all_data_user_db
)

# Test for save_user_to_db
@patch("db.db.execute_query_pg")
def test_save_user_to_db(mock_execute_query_pg):
    save_user_to_db(1, username="test_user", city_name="TestCity")

    expected_query = '''
        INSERT INTO public.users (id, username, city_name)
        VALUES (
            %(user_id)s, %(username)s, %(city_name)s
        )
        ON CONFLICT(id) DO UPDATE SET
            username = %(username)s, city_name = %(city_name)s
    '''

    # mock_execute_query_pg.assert_called_once_with(
    #     expected_query.strip(),
    #     {'user_id': 1, 'username': "test_user", 'city_name': "TestCity"}
    # )

    actual_query, actual_params = mock_execute_query_pg.call_args[0]
    assert re.sub(r'\s+', ' ', expected_query.strip()) == re.sub(r'\s+', ' ', actual_query.strip())
    assert actual_params == {'user_id': 1, 'username': "test_user", 'city_name': "TestCity"}

# Test for save_user_city
@patch("db.db.execute_query_pg")
def test_save_user_city(mock_execute_query_pg):
    save_user_city(1, "TestCity")

    mock_execute_query_pg.assert_called_once_with('''
        UPDATE public.users SET 
        city_name = %(city_name)s, 
        has_provided_location = 1 
        WHERE id = %(user_id)s
    ''', {'city_name': "TestCity", 'user_id': 1}
    )

# Test for save_user_time_zone_db
@patch("db.db.execute_query_pg")
def test_save_user_time_zone_db(mock_execute_query_pg):
    save_user_time_zone_db(1, "UTC")

    mock_execute_query_pg.assert_called_once_with('''
        UPDATE public.users
        SET time_zone = %(timezone)s
        WHERE id = %(user_id)s
    ''', {'user_id': 1, 'timezone': "UTC"}
    )

# Test for save_phone_number
@patch("db.db.execute_query_pg")
def test_save_phone_number(mock_execute_query_pg):
    save_phone_number(1, "123456789")

    mock_execute_query_pg.assert_called_once_with('''
        UPDATE public.users
        SET phone_number = %(phone_number)s
        WHERE id = %(user_id)s
    ''', {'user_id': 1, 'phone_number': "123456789"}
    )

# Test for save_sleep_goal_db
@patch("db.db.execute_query_pg")
def test_save_sleep_goal_db(mock_execute_query_pg):
    save_sleep_goal_db(1, 8.0)

    mock_execute_query_pg.assert_called_once_with('''
        UPDATE public.users
        SET sleep_goal = %(goal)s
        WHERE id = %(user_id)s
    ''', {'user_id': 1, 'goal': 8.0})

# Test for save_wake_time_user_db
@patch("db.db.execute_query_pg")
def test_save_wake_time_user_db(mock_execute_query_pg):
    save_wake_time_user_db(1, "07:00:00")

    mock_execute_query_pg.assert_called_once_with('''
       UPDATE public.users 
       SET wake_time = %(wake_time)s
       WHERE id = %(user_id)s
   ''', {'user_id': 1, 'wake_time': "07:00:00"}
    )

# Test for save_sleep_time_records_db
@patch("db.db.execute_query_pg")
def test_save_sleep_time_records_db(mock_execute_query_pg):
    save_sleep_time_records_db(1, "2024-12-01T23:00:00")

    mock_execute_query_pg.assert_called_once_with('''
        INSERT INTO public.sleep_records (user_id, sleep_time)
        VALUES (%(user_id)s, %(sleep_time)s)
    ''', {'user_id': 1, 'sleep_time': "2024-12-01T23:00:00"}
    )

# Test for save_wake_time_records_db
@patch("db.db.execute_query_pg")
def test_save_wake_time_records_db(mock_execute_query_pg):
    save_wake_time_records_db(1, "2024-12-02T07:00:00")

    mock_execute_query_pg.assert_called_once_with('''
        UPDATE public.sleep_records
        SET wake_time = %(wake_time)s   
        WHERE user_id = %(user_id)s AND wake_time IS NULL
    ''', {'user_id': 1, 'wake_time': "2024-12-02T07:00:00"}
    )

# Test for save_sleep_quality_db
@patch("db.db.execute_query_pg")
def test_save_sleep_quality_db(mock_execute_query_pg):
    save_sleep_quality_db(1, 4)

    mock_execute_query_pg.assert_called_once_with(
        '''
            UPDATE public.sleep_records
            SET sleep_quality = %(quality)s
            WHERE sleep_time IN (
                SELECT sleep_time FROM public.sleep_records 
                WHERE user_id = %(user_id)s AND wake_time IS NOT NULL
                ORDER BY sleep_time DESC 
                LIMIT 1
            );
        ''',
        {'user_id': 1, 'quality': 4}
    )

# Test for save_mood_db
@patch("db.db.execute_query_pg")
def test_save_mood_db(mock_execute_query_pg):
    save_mood_db(1, 3)

    mock_execute_query_pg.assert_called_once_with(
        '''
            UPDATE public.sleep_records
            SET mood = %(mood)s
            WHERE sleep_time IN (
                SELECT sleep_time FROM public.sleep_records 
                WHERE user_id = %(user_id)s AND wake_time IS NOT NULL
                ORDER BY sleep_time DESC 
                LIMIT 1
            );
        ''',
        {'user_id': 1, 'mood': 3}
    )

# Test for save_reminder_time_db
@patch("db.db.execute_query_pg")
def test_save_reminder_time_db(mock_execute_query_pg):
    save_reminder_time_db(1, "08:00")

    mock_execute_query_pg.assert_called_once_with('''
        INSERT INTO public.reminders (user_id, reminder_time)
        VALUES (%(user_id)s, %(reminder_time)s)
        ON CONFLICT(user_id) DO UPDATE SET
            reminder_time = %(reminder_time)s
    ''', {'user_id': 1, 'reminder_time': "08:00"}
    )

# Test for delete_reminder_db
@patch("db.db.execute_query_pg")
def test_delete_reminder_db(mock_execute_query_pg):
    delete_reminder_db(1)

    mock_execute_query_pg.assert_called_once_with(
        'DELETE FROM public.reminders WHERE user_id = %(user_id)s',
        {'user_id': 1}
    )

# Test for delete_sleep_records_db
@patch("db.db.execute_query_pg")
def test_delete_sleep_records_db(mock_execute_query_pg):
    delete_sleep_records_db(1)

    mock_execute_query_pg.assert_called_once_with(
        'DELETE FROM public.sleep_records WHERE user_id = %(user_id)s',
        {'user_id': 1}
    )

# Test for delete_user_db
@patch("db.db.execute_query_pg")
def test_delete_user_db(mock_execute_query_pg):
    delete_user_db(1)

    mock_execute_query_pg.assert_called_once_with(
        'DELETE FROM public.users WHERE id = %(user_id)s',
        {'user_id': 1}
    )

# Test for delete_all_data_user_db
@patch("db.db.delete_sleep_records_db")
@patch("db.db.delete_reminder_db")
@patch("db.db.delete_user_db")
def test_delete_all_data_user_db(mock_delete_user, mock_delete_reminder, mock_delete_sleep_records):
    delete_all_data_user_db(1)

    mock_delete_sleep_records.assert_called_once_with(1)
    mock_delete_reminder.assert_called_once_with(1)
    mock_delete_user.assert_called_once_with(1)
