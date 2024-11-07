import psycopg2

import logging.config
from db.execute_query import execute_query_pg


logger = logging.getLogger(__name__)


def save_user_city(user_id, city_name):
    # Здесь реализуется логика сохранения данных в базе данных
    execute_query_pg("UPDATE public.users SET city_name = %(city_name)s, has_provided_location = 1 WHERE id = %(user_id)s",
                  {'city_name': city_name, 'user_id': user_id})


def save_user_to_db(user_id: int, username: str = "NULL", first_name: str = "NULL", last_name: str = "NULL",
                    phone_number: str = "NULL", city_name: str = "NULL", sleep_goal: float = 8.0,
                    wake_time: str = "NULL", has_provided_location: int = 0):
    execute_query_pg('''
            INSERT INTO public.users (id, username, first_name, last_name, 
            phone_number, city_name, sleep_goal, wake_time, has_provided_location)
            VALUES (
                %(user_id)s, %(username)s, %(first_name)s, %(last_name)s, 
                %(phone_number)s, %(city_name)s, %(sleep_goal)s,                                      
                %(wake_time)s, %(has_provided_location)s
            )
            ON CONFLICT(id) DO UPDATE SET
                username = %(username)s,
                first_name = %(first_name)s,
                last_name = %(last_name)s,
                phone_number = %(phone_number)s,
                city_name = %(city_name)s,
                sleep_goal = %(sleep_goal)s,
                wake_time = %(wake_time)s,
                has_provided_location = %(has_provided_location)s
        ''', {'user_id': user_id, 'username': username, 'first_name': first_name,
              'last_name':last_name, 'phone_number': phone_number, 'city_name': city_name,
              'sleep_goal': sleep_goal, 'wake_time': wake_time, 'has_provided_location': has_provided_location})


# GET

def get_all_sleep_records(user_id: int):
    return execute_query_pg('SELECT * FROM public.sleep_records WHERE user_id = %(user_id)s', 
                         {'user_id': user_id}).fetchall()


def get_city_name(user_id: int):
    return execute_query_pg('SELECT city_name FROM public.users WHERE id = %(user_id)s', 
                         {'user_id': user_id}).fetchone()


def get_has_provided_location(user_id: int):
    return execute_query_pg('SELECT id, has_provided_location FROM public.users WHERE id = %(user_id)s', 
                         {'user_id': user_id}).fetchone()


def get_reminder_db(user_id: int):
    return execute_query_pg('SELECT * FROM public.reminders WHERE user_id = %(user_id)s', 
                         {'user_id': user_id}).fetchone()


def get_reminder_time_db(user_id: int):
    return execute_query_pg(
        'SELECT reminder_time FROM public.reminders WHERE user_id = %(user_id)s', 
                         {'user_id': user_id}).fetchone()


def get_all_reminders():
    return execute_query_pg('SELECT user_id FROM public.reminders').fetchall()


def get_all_users():
    return execute_query_pg('SELECT * FROM public.users').fetchall()


def get_all_users_city_name():
    return execute_query_pg('SELECT id, city_name FROM public.users').fetchall()


def get_user_wake_time(user_id: int):
    return execute_query_pg('SELECT id, wake_time FROM public.users WHERE id = %(user_id)s', 
                         {'user_id': user_id}).fetchone()


def get_sleep_goal_user(user_id: int):
    return execute_query_pg('SELECT sleep_goal FROM public.users WHERE id = %(user_id)s', 
                         {'user_id': user_id}).fetchone()


def get_sleep_records_per_week(user_id: int):
    return execute_query_pg('''
            SELECT sleep_time, wake_time FROM public.sleep_records
            WHERE user_id = %(user_id)s AND wake_time IS NOT NULL
            ORDER BY sleep_time DESC LIMIT 7
        ''', {'user_id': user_id}).fetchall()


def get_sleep_record_last_db(user_id: int):
    return execute_query_pg('''
        SELECT sleep_time, wake_time FROM public.sleep_records
        WHERE user_id = %(user_id)s
        ORDER BY sleep_time DESC
    ''', {'user_id': user_id}).fetchone()


def get_sleep_time_without_wake_db(user_id: int):
    return execute_query_pg('''
        SELECT sleep_time FROM public.sleep_records 
        WHERE user_id = %(user_id)s AND wake_time IS NULL
        ''', {'user_id': user_id}).fetchone()


def get_wake_time_null(user_id: int):
    return execute_query_pg('''
            SELECT user_id FROM public.sleep_records
            WHERE user_id = %(user_id)s
            AND wake_time IS NULL
        ''', {'user_id': user_id}).fetchall()


# SAVE

def save_phone_number(user_id: int, phone_number: str):
    execute_query_pg('''
            UPDATE public.users
            SET phone_number = %(phone_number)s
            WHERE id = %(user_id)s
        ''', {'user_id': user_id})


def save_wake_time_user_db(user_id: int, wake_time: str):
    execute_query_pg('''
           UPDATE public.users 
           SET wake_time = %(wake_time)s
           WHERE id = %(user_id)s
       ''', {'user_id': user_id, 'wake_time': wake_time})


def save_sleep_time_records_db(user_id: int, sleep_time: str):
    execute_query_pg('''
        INSERT INTO public.sleep_records (user_id, sleep_time)
        VALUES (%(user_id)s, %(sleep_time)s)
    ''', {'user_id': user_id, 'sleep_time': sleep_time})


def save_wake_time_records_db(user_id: int, wake_time: str):
    return execute_query_pg('''
        UPDATE public.sleep_records
        SET wake_time = %(wake_time)s   
        WHERE user_id = %(user_id)s AND wake_time IS NULL
    ''', {'user_id': user_id, 'wake_time': wake_time})


def save_mood_db(user_id, mood: int):
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


def save_reminder_time_db(user_id: int, reminder_time: str):
    execute_query_pg('''
                INSERT INTO public.reminders (user_id, reminder_time)
                VALUES (%(user_id)s, %(reminder_time)s)
                ON CONFLICT(user_id) DO UPDATE SET
                  reminder_time = %(reminder_time)s
            ''', {'user_id': user_id, 'reminder_time': reminder_time})


def save_sleep_quality_db(user_id: int, quality: int):
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


def save_sleep_goal_db(user_id: int, goal: float):
    execute_query_pg('''
            UPDATE public.users
            SET sleep_goal = %(goal)s
            WHERE id = %(user_id)s
        ''', {'user_id': user_id, 'goal': goal})


# DELETE

def delete_sleep_records_db(user_id: int):
    execute_query_pg('DELETE FROM public.sleep_records WHERE user_id = %(user_id)s', 
                  {'user_id': user_id})


def delete_reminder_db(user_id: int):
    execute_query_pg('DELETE FROM public.reminders WHERE user_id = %(user_id)s', 
                  {'user_id': user_id})


def delete_user_db(user_id: int):
    execute_query_pg('DELETE FROM public.users WHERE id = %(user_id)s', 
                  {'user_id': user_id})


def delete_all_data_user_db(user_id: int):
    delete_sleep_records_db(user_id)
    delete_reminder_db(user_id)
    delete_user_db(user_id)


def modify_table():
    with sqlite3.connect('../sleep_data.db', check_same_thread=False) as conn:
        cursor = conn.cursor()

    # Отключаем поддержку внешних ключей
    cursor.execute('PRAGMA foreign_keys = OFF;')

    # Начинаем транзакцию
    cursor.execute('BEGIN TRANSACTION;')

    try:
        # Переименовываем старую таблицу public.users
        cursor.execute('ALTER TABLE public.users RENAME TO users_old;')

        # Создаем новую таблицу users
        cursor.execute('''
            CREATE TABLE public.users (
                id INTEGER PRIMARY KEY NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone_number TEXT,
                city_name TEXT,
                sleep_goal REAL DEFAULT 8.0,
                wake_time TEXT,
                has_provided_location INT DEFAULT 0 
            );
        ''')

        # Переносим данные с преобразованием типа users
        cursor.execute('''
            INSERT INTO public.users
            SELECT *
            FROM public.users_old;
        ''')

        # Удаляем старую таблицу users
        cursor.execute('DROP TABLE public.users_old;')

        # Переименовываем старую таблицу sleep_records
        cursor.execute('ALTER TABLE public.sleep_reocrds RENAME TO public.sleep_reocrds_old;')

        # Создаем новую таблицу sleep_records
        cursor.execute('''
            CREATE TABLE public.sleep_reocrds (
                user_id INTEGER NOT NULL,
                sleep_time TEXT NOT NULL,
                wake_time TEXT DEFAULT NULL,
                sleep_quality TEXT DEFAULT NULL,
                mood TEXT DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES public.users(id)
                ON DELETE CASCADE 
                ON UPDATE NO ACTION
            );
        ''')

        # Переносим данные с преобразованием типа sleep_records
        cursor.execute('''
            INSERT INTO public.sleep_reocrds
            SELECT *
            FROM public.sleep_reocrds_old;
        ''')

        # Удаляем старую таблицу sleep_recordes
        cursor.execute('DROP TABLE public.sleep_reocrds_old;')

        # Переименовываем старую таблицу reminders
        cursor.execute('ALTER TABLE public.reminders RENAME TO public.reminders_old;')

        # Создаем новую таблицу reminders
        cursor.execute('''
               CREATE TABLE public.reminders (
                   user_id INTEGER PRIMARY KEY NOT NULL,
                   reminder_time TEXT NOT NULL,
                   FOREIGN KEY (user_id) REFERENCES users(id)
                   ON DELETE CASCADE 
                   ON UPDATE NO ACTION
               );
           ''')

        # Переносим данные с преобразованием типа reminders
        cursor.execute('''
               INSERT INTO public.reminders 
               SELECT *
               FROM public.reminders_old;
           ''')

        # Удаляем старую таблицу reminders
        cursor.execute('DROP TABLE public.reminders_old;')

        # Вставляем уникальные user_id из sleep_records в users
        cursor.execute('''
            INSERT INTO public.users (id)
            SELECT DISTINCT user_id FROM public.sleep_reocrds
            WHERE user_id NOT IN (SELECT id FROM public.users)
        ''')

        # Включаем поддержку внешних ключей
        cursor.execute('PRAGMA foreign_keys = ON;')

        # Завершаем транзакцию
        conn.commit()
        print("Таблица успешно обновлена.")
    except Exception as e:
        # В случае ошибки откатываем транзакцию
        conn.rollback()
        print(f"Ошибка при обновлении таблицы: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    # modify_table()
    migration_sqlite_to_pg()
# # Добавление поля sleep_quality в таблицу sleep_records
# try:
#     execute_query('''
#         ALTER TABLE sleep_records
#         ADD COLUMN sleep_quality INTEGER
#     ''')
#     logger.info("В таблицу sleep_records добавлен столбец sleep_quality")
# except sqlite3.OperationalError as e:
#     logger.info("Столбец sleep_quality уже существует в таблице sleep_records")

# # Добавление поля mood в таблицу sleep_records
# try:
#     execute_query('''
#         ALTER TABLE sleep_records
#         ADD COLUMN mood INTEGER
#     ''')
#     logger.info("В таблицу sleep_records добавлен столбец mood")
# except sqlite3.OperationalError as e:
#     logger.info("Столбец mood уже существует в таблице sleep_records")

# # Добавление поля sleep_goal в таблицу users
# try:
#     execute_query('''
#         ALTER TABLE users
#         ADD COLUMN sleep_goal REAL DEFAULT 8.0
#     ''')
#     logger.info("В таблицу users добавлен столбец sleep_goal")
# except sqlite3.OperationalError as e:
#     logger.info("Столбец sleep_goal уже существует в таблице users")
#     execute_query('''
#         ALTER TABLE users
#         ADD COLUMN city_name TEXT
#     ''')
