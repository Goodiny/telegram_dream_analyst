import inspect
import psycopg2

import logging.config
from db.execute_query import execute_query_pg


logger = logging.getLogger(__name__)


def exception_handler(func):
    def wrapper(*args, **kwargs):
        params = ', '.join([f"{a}" for a in args] + [f"{k}={v}" for k, v in kwargs.items()])
        logger.info(f'Вызов функции {func.__name__} с параметрами {params}')
        try:
            return func(*args, **kwargs)
        except psycopg2.OperationalError as e:
            logger.error(f'Ошибка дступа к данным при выполнении функции {func.__name__}: {e}', exc_info=True)
            return
        except psycopg2.DatabaseError as e:
            logger.error(f'Ошибка базы данных при выполнении функции {func.__name__}: {e}', exc_info=True)
            return
        except Exception as e:
            logger.error(f'Ошибка при выполнения функции {func.__name__}: {e}', exc_info=True)
            return
            

    return wrapper


# GET

# REMINDERS

@exception_handler
def get_all_reminders():
    """
    Возвращает список всех напоминаний
    """
    return execute_query_pg('SELECT user_id FROM public.reminders').fetchall()


@exception_handler
def get_reminder_db(user_id: int):
    """
    Возвращает reminder_time для пользователя с id user_id
    """
    return execute_query_pg('SELECT * FROM public.reminders WHERE user_id = %(user_id)s', 
                             {'user_id': user_id}).fetchone()


@exception_handler
def get_reminder_time_db(user_id: int):
    """
    Возвращает reminder_time для пользователя с id user_id
    """
    return execute_query_pg(
        'SELECT reminder_time FROM public.reminders WHERE user_id = %(user_id)s', 
        {'user_id': user_id}).fetchone()


# SLEEP_RECORDS

@exception_handler
def get_all_sleep_records(user_id: int):
    """
    Возвращает список всех записей о снах пользователя с id user_id
    """
    return execute_query_pg('SELECT * FROM public.sleep_records WHERE user_id = %(user_id)s', 
                             {'user_id': user_id}).fetchall()


@exception_handler
def get_sleep_records_per_week(user_id: int):
    """
    Возвращает sleep_time и wake_time для пользователя с id user_id, если wake_time == NULL
    """
    return execute_query_pg('''
        SELECT sleep_time, wake_time FROM public.sleep_records
        WHERE user_id = %(user_id)s AND wake_time IS NOT NULL
        ORDER BY sleep_time DESC LIMIT 7
    ''', {'user_id': user_id}).fetchall()


@exception_handler
def get_sleep_record_last_db(user_id: int):
    """
    Возвращает sleep_time и wake_time для пользователя с id user_id
    """
    return execute_query_pg('''
        SELECT sleep_time, wake_time FROM public.sleep_records
        WHERE user_id = %(user_id)s
        ORDER BY sleep_time DESC
    ''', {'user_id': user_id}).fetchone()


@exception_handler
def get_sleep_time_without_wake_db(user_id: int):
    """
    Возвращает sleep_time для пользователя с id = user_id, если wake_time == NULL
    """
    return execute_query_pg('''
        SELECT sleep_time FROM public.sleep_records 
        WHERE user_id = %(user_id)s AND wake_time IS NULL
    ''', {'user_id': user_id}).fetchone()


@exception_handler
def get_wake_time_null(user_id: int):
    """
    Возвращает wake_time для пользователя с id = user_id, если wake_time == NULL
    """
    return execute_query_pg('''
        SELECT wake_time FROM public.sleep_records
        WHERE user_id = %(user_id)s
        AND wake_time IS NULL
    ''', {'user_id': user_id}).fetchall()

# USERS

@exception_handler
def get_all_users():
    """
    Возвращает список всех пользователей
    """
    return execute_query_pg('SELECT * FROM public.users').fetchall()


@exception_handler
def get_all_users_city_name():
    """
    Возвращает список всех пользователей с их городом
    """
    return execute_query_pg('SELECT id, city_name FROM public.users').fetchall()


@exception_handler
def get_user_db(user_id: int):
    """
    Возвращает пользователя с id user_id
    """
    return execute_query_pg('SELECT * FROM public.users WHERE id = %(user_id)s', 
                             {'user_id': user_id}).fetchone()


@exception_handler
def get_city_name(user_id: int):
    """
    Возвращает city_name для пользователя с id user_id
    """
    return execute_query_pg('SELECT city_name FROM public.users WHERE id = %(user_id)s', 
                             {'user_id': user_id}).fetchone()


@exception_handler
def get_sleep_goal_user(user_id: int):
    """
    Возвращает sleep_goal для пользователя с id user_id
    """
    return execute_query_pg('SELECT sleep_goal FROM public.users WHERE id = %(user_id)s', 
                             {'user_id': user_id}).fetchone()


@exception_handler
def get_user_wake_time(user_id: int):
    """
    Возвращает id и wake_time для пользователя с id user_id
    """
    return execute_query_pg('SELECT id, wake_time FROM public.users WHERE id = %(user_id)s', 
                             {'user_id': user_id}).fetchone()


@exception_handler
def get_has_provided_location(user_id: int):
    """
    Возвращает has_provided_location для пользователя с id user_id
    """
    return execute_query_pg('SELECT id, has_provided_location FROM public.users WHERE id = %(user_id)s', 
                             {'user_id': user_id}).fetchone()


# SAVE

@exception_handler
def save_user_to_db(user_id: int, 
                    username: str = None, 
                    first_name: str = None, 
                    last_name: str = None,
                    phone_number: str = None,
                    city_name: str = None, 
                    sleep_goal: float = None,
                    wake_time: str = None, 
                    has_provided_location: int = None):
    """
    Сохраняет в базе данных пользователя с id = user_id, username, first_name, last_name, phone_number, city_name,
    sleep_goal, wake_time, has_provided_location
    """
    
    frame = inspect.currentframe()

    args, _, _, values = inspect.getargvalues(frame)

    params = {}
    for arg in args:
        if arg not in {'user_id', 'username', 'first_name', 
                    'last_name', 'phone_number', 
                    'city_name','sleep_goal', 
                    'wake_time', 'has_provided_location'}:
            raise ValueError('Неизвестные параметры при сохранении пользователя')
        if arg == 'sleep_goal' and not (isinstance(values[arg], float) or values[arg] is None):
            raise ValueError('Неверный тип параметра sleep_goal')
        if arg == 'has_provided_location' and not (isinstance(values[arg], int) or values[arg] is None):
            raise ValueError('Неверный тип параметра has_provided_location')
        if arg != 'user_id' and not (isinstance(values[arg], str) or values[arg] is None):
            raise ValueError('Неверный тип параметра ' + arg)
        if arg != 'user_id' and values[arg] is not None:
            params[arg] = values[arg]

    insert_keys_str = ', '.join([f"{key}" for key in params.keys()])
    insert_values_str = ', '.join([f"%({key})s" for key in params.keys()])
    update_keys_str = ', '.join([f"{key} = %({key})s" for key in params.keys()])
    query_str = f'''
        INSERT INTO public.users ({'id, ' + insert_keys_str if insert_keys_str != '' else 'id'})
        VALUES (
            {'%(user_id)s, ' + insert_values_str if insert_values_str != '' else '%(user_id)s'}
        )
        ON CONFLICT(id) DO UPDATE SET
            {update_keys_str}
    ''' if update_keys_str != '' else f'''
        INSERT INTO public.users ({'id, ' + insert_keys_str if insert_keys_str != '' else 'id'})
        VALUES (
            {'%(user_id)s, ' + insert_values_str if insert_values_str != '' else '%(user_id)s'}
        )
    '''
    params['user_id'] = user_id

    execute_query_pg(query_str, params)
    logger.info(f'Пользователь  с id {user_id} сохранен в базе данных')
    

@exception_handler
def save_user_city(user_id, city_name):
    """
    Сохраняет в базе данных пользователя с id = user_id и названием города city_name
    """
    # Здесь реализуется логика сохранения данных в базе данных
    execute_query_pg('''
        UPDATE public.users SET 
            city_name = %(city_name)s, 
            has_provided_location = 1 
            WHERE id = %(user_id)s
    ''', {'city_name': city_name, 'user_id': user_id})
    logger.info(f'Город {city_name} для пользователя с id {user_id} сохранены в базе данных')


@exception_handler
def save_phone_number(user_id: int, phone_number: str):
    """
    Сохраняет в базе данных пользователя с id = user_id и номером телефона phone_number
    """
    execute_query_pg('''
        UPDATE public.users
        SET phone_number = %(phone_number)s
        WHERE id = %(user_id)s
    ''', {'user_id': user_id, 'phone_number': phone_number})


@exception_handler
def save_sleep_goal_db(user_id: int, goal: float):
    """
    Сохраняет sleep_goal для пользователя с id = user_id
    """
    execute_query_pg('''
            UPDATE public.users
            SET sleep_goal = %(goal)s
            WHERE id = %(user_id)s
        ''', {'user_id': user_id, 'goal': goal})


@exception_handler
def save_wake_time_user_db(user_id: int, wake_time: str):
    """
    Сохраняет wake_time для пользователя с id = user_id
    """
    execute_query_pg('''
           UPDATE public.users 
           SET wake_time = %(wake_time)s
           WHERE id = %(user_id)s
       ''', {'user_id': user_id, 'wake_time': wake_time})


@exception_handler
def save_sleep_time_records_db(user_id: int, sleep_time: str):
    """
    Сохраняет sleep_time для пользователя с id = user_id
    """
    execute_query_pg('''
        INSERT INTO public.sleep_records (user_id, sleep_time)
        VALUES (%(user_id)s, %(sleep_time)s)
    ''', {'user_id': user_id, 'sleep_time': sleep_time})


@exception_handler
def save_wake_time_records_db(user_id: int, wake_time: str):
    """
    Сохраняет wake_time для пользователя с id = user_id
    """
    return execute_query_pg('''
        UPDATE public.sleep_records
        SET wake_time = %(wake_time)s   
        WHERE user_id = %(user_id)s AND wake_time IS NULL
    ''', {'user_id': user_id, 'wake_time': wake_time})


@exception_handler
def save_sleep_quality_db(user_id: int, quality: int):
        """
        Сохраняет sleep_quality для пользователя с id = user_id
        """
        execute_query_pg('''
            UPDATE public.sleep_records
            SET sleep_quality = %(quality)s
            WHERE sleep_time IN (
                SELECT sleep_time FROM public.sleep_records 
                WHERE user_id = %(user_id)s AND wake_time IS NOT NULL
                ORDER BY sleep_time DESC 
                LIMIT 1
            );
        ''', {'user_id': user_id, 'quality': quality})


@exception_handler
def save_mood_db(user_id, mood: int):
    """
    Сохраняет mood для пользователя с id = user_id
    """
    execute_query_pg('''
            UPDATE public.sleep_records
            SET mood = %(mood)s
            WHERE sleep_time IN (
                SELECT sleep_time FROM public.sleep_records 
                WHERE user_id = %(user_id)s AND wake_time IS NOT NULL
                ORDER BY sleep_time DESC 
                LIMIT 1
            );
        ''', {'user_id': user_id, 'mood': mood})


@exception_handler
def save_reminder_time_db(user_id: int, reminder_time: str):
    """
    Сохраняет reminder_time для пользователя с id = user_id
    """
    execute_query_pg('''
                INSERT INTO public.reminders (user_id, reminder_time)
                VALUES (%(user_id)s, %(reminder_time)s)
                ON CONFLICT(user_id) DO UPDATE SET
                  reminder_time = %(reminder_time)s
            ''', {'user_id': user_id, 'reminder_time': reminder_time})


# DELETE

@exception_handler
def delete_reminder_db(user_id: int):
    """
    Удаляет записи reminders для пользователя с id = user_id
    """
    execute_query_pg('DELETE FROM public.reminders WHERE user_id = %(user_id)s', 
                  {'user_id': user_id})


@exception_handler
def delete_sleep_records_db(user_id: int):
    """
    Удаляет записи sleep_records для пользователя с id = user_id
    """
    execute_query_pg('DELETE FROM public.sleep_records WHERE user_id = %(user_id)s', 
                  {'user_id': user_id})


@exception_handler
def delete_user_db(user_id: int):
    """
    Удаляет записи users для пользователя с id = user_id
    """
    execute_query_pg('DELETE FROM public.users WHERE id = %(user_id)s', 
                  {'user_id': user_id})


# MAIN

def delete_all_data_user_db(user_id: int):
    delete_sleep_records_db(user_id)
    delete_reminder_db(user_id)
    delete_user_db(user_id)


if __name__ == "__main__":
    save_user_to_db(2, 'user2')
