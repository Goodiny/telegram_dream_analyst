import json
import sqlite3

import psycopg2

import logging.config
from datetime import datetime

from psycopg2.extras import RealDictCursor

from configs.config import DATABASEPG_URL, DATABASESL_URL
from utils.utils import is_valid_user

logger = logging.getLogger(__name__)


def execute_query_sl(query, params=None, row_factory=True):
    with sqlite3.connect(f'../{DATABASESL_URL}', check_same_thread=False) as conn:
        if row_factory:
            conn.row_factory = sqlite3.Row  # Для доступа к столбцам по имени
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor
        except sqlite3.OperationalError:
            return None


def execute_query(query, params=None, row_factory=True):
    with psycopg2.connect(DATABASEPG_URL, cursor_factory=RealDictCursor) as conn:
        # if row_factory:
        #     conn.row_factory = sqlite3.Row  # Для доступа к столбцам по имени
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor
        except psycopg2.OperationalError:
            return None


def migration_sqlite_to_pg():
    try:
        tables = execute_query_sl('SELECT name FROM sqlite_master WHERE type="table";').fetchall()

        # logger.debug(f'Tables: {[table["name"] for table in tables]}')

        if tables:
            # Перенос данных
            for table in tables:
                table_name = table['name']
                rows = execute_query_sl(f"SELECT * FROM {table_name}").fetchall()

                # Получение информации о столбцах
                columns = [" ".join([str({1: 'NOT NULL', 0: ''}[v[1]]).strip() if v[0] == 2 else
                                     str({1: 'PRIMARY KEY', 0: ''}[v[1]]).strip() if v[0] == 4 else
                                     ('DEFAULT('+str(v[1]).strip()+')'.strip() if v[1] != None else "")
                                     if v[0] == 3 else str(v[1]) for v in enumerate(col[1:])]).strip() for col in execute_query_sl(f"PRAGMA table_info({table_name})", row_factory=False).fetchall()]
                columns_str = ", ".join(columns)


                try:
                    # Создание таблицы в PostgreSQL
                    execute_query(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str});")
                except psycopg2.DatabaseError as e:
                    logger.warning(f"В базе данных уже существует таблица {table_name} c полями {columns_str}: {e}")

                # Вставка данных
                for row in rows:

                    values_str = ", ".join(
                        f"{str(val)}" if str(val).isdigit() else f"'{str(val)}'" if str(val) != 'None' else 'NULL'
                        for i, val in enumerate(row))
                    try:
                        execute_query(f"INSERT INTO {table_name} ({', '.join(row.keys())}) VALUES ({values_str})")
                    except psycopg2.DatabaseError as e:
                        logging.warning(f"В таблице {table_name} уже есть данные {values_str}: {e}")

                logger.info(f"Данные в таблицу {table_name} перенесены успешно")
            logger.info(f"Миграция базы данных прошла успешно")
        else:
            logger.warning(f"Миграция не прошла так как данные не были прочитаны")
    except Exception as e:
        logger.error(f"Ошибка при миграции базы данных: {e}")


def save_user_city(user_id, city_name):
    # Здесь реализуется логика сохранения данных в базе данных
    execute_query(f"UPDATE public.users SET city_name = {city_name}, has_provided_location = 1 WHERE id = {user_id}")


def add_user_to_db(user_id: int, username: str = "", first_name: str = "", last_name: str = "",
                   phone_number: str = "", city_name: str = "", sleep_goal: float = 8.0,
                   wake_time: str = "", has_provided_location: int = 0):
    execute_query(f'''
            INSERT INTO public.users (id, username, first_name, last_name, 
            phone_number, cityt_name, sleep_goal, wake_time, has_provided_location
            )
            VALUES (
                {id}, {username}, {first_name}, {last_name}, 
                {phone_number}, {city_name}, {sleep_goal}, 
                {wake_time}, {has_provided_location}
            )
            ON CONFLICT(id) DO UPDATE SET
                username = {username},
                first_name = {first_name},
                last_name = {last_name},
                phone_number = {phone_number},
                city_name = {city_name},
                sleep_goal = {sleep_goal},
                wake_time = {wake_time},
                has_provided_location = {has_provided_location}
        ''')


# Инициализация базы данных
def database_initialize():
    # Таблица users
    execute_query('''
        CREATE TABLE IF NOT EXISTS public.users(
            id bigint NOT NULL,
            username text COLLATE pg_catalog."default",
            first_name text COLLATE pg_catalog."default",
            last_name text COLLATE pg_catalog."default",
            phone_number text COLLATE pg_catalog."default",
            city_name text COLLATE pg_catalog."default",
            sleep_goal real DEFAULT 8.0,
            wake_time text COLLATE pg_catalog."default",
            has_provided_location integer DEFAULT 0,
            CONSTRAINT users_pkey PRIMARY KEY (id)
        )
        
        TABLESPACE pg_default;
        
        ALTER TABLE IF EXISTS public.users
            OWNER to postgres;
    ''')

    # Таблица sleep_records
    execute_query('''      
        CREATE TABLE IF NOT EXISTS public.sleep_records(
            id integer NOT NULL,
            user_id bigint NOT NULL,
            sleep_time timestamp without time zone NOT NULL,
            wake_time timestamp without time zone,
            sleep_quality integer,
            mood integer,
            CONSTRAINT sleep_records_pkey PRIMARY KEY (id),
            CONSTRAINT sleep_records_user_id_fkey FOREIGN KEY (user_id)
                REFERENCES public.users (id) MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE CASCADE
        )
        
        TABLESPACE pg_default;
        
        ALTER TABLE IF EXISTS public.sleep_records
            OWNER to postgres;
    ''')

    # Таблица reminders
    execute_query('''
        CREATE TABLE IF NOT EXISTS public.sleep_records(
            id integer NOT NULL,
            user_id bigint NOT NULL,
            sleep_time timestamp without time zone NOT NULL,
            wake_time timestamp without time zone,
            sleep_quality integer,
            mood integer,
            CONSTRAINT sleep_records_pkey PRIMARY KEY (id),
            CONSTRAINT sleep_records_user_id_fkey FOREIGN KEY (user_id)
                REFERENCES public.users (id) MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE CASCADE
        )
        
        TABLESPACE pg_default;
        
        ALTER TABLE IF EXISTS public.sleep_records
            OWNER to postgres;
     ''')


def create_triggers_db():
    execute_query('''
        CREATE TRIGGER IF NOT EXISTS update_existing_sleep_time
        BEFORE INSERT ON public.sleep_records
        FOR EACH ROW
        WHEN (SELECT COUNT(*) FROM public.sleep_records WHERE user_id = NEW.user_id AND wake_time IS NULL) > 0
        BEGIN
            UPDATE public.sleep_records
            SET sleep_time = NEW.sleep_time
            WHERE user_id = NEW.user_id AND wake_time IS NULL;
            SELECT RAISE(IGNORE);
        END;
    ''')

    execute_query('''
        CREATE TRIGGER after_sleep_records_insert_new_user 
        AFTER INSERT ON public.sleep_records
        FOR EACH ROW
        WHEN (SELECT COUNT(id) FROM public.users WHERE id=NEW.user_id) = 0
        BEGIN
          INSERT INTO public.users (id)
          VALUES (NEW.user_id);
        END
    ''')


# GET

def get_all_sleep_records(user_id: int):
    return execute_query(f'SELECT * FROM public.sleep_records WHERE user_id = {user_id}').fetchall()


def get_city_name(user_id: int):
    return execute_query(f'SELECT city_name FROM public.users WHERE id = {user_id}').fetchone()


def get_has_provided_location(user_id: int):
    return execute_query(f'SELECT id, has_provided_location FROM public.users WHERE id = {user_id}').fetchone()


def get_reminder_db(user_id: int):
    return execute_query(f'SELECT * FROM public.reminders WHERE user_id = {user_id}').fetchone()


def get_reminder_time_db(user_id: int):
    return execute_query(
        f'SELECT reminder_time FROM public.reminders WHERE user_id = {user_id}').fetchone()


def get_all_reminders():
    return execute_query('SELECT user_id FROM public.reminders').fetchall()


def get_all_users():
    return execute_query('SELECT * FROM public.users').fetchall()


def get_all_users_city_name():
    return execute_query('SELECT id, city_name FROM public.users').fetchall()


def get_user_wake_time(user_id: int):
    return execute_query(f'SELECT id, wake_time FROM public.users WHERE id = {user_id}').fetchone()


def get_sleep_goal_user(user_id: int):
    return execute_query(f'SELECT sleep_goal FROM public.users WHERE id = {user_id}').fetchone()


def get_sleep_records_per_week(user_id: int):
    return execute_query(f'''
            SELECT sleep_time, wake_time FROM public.sleep_records
            WHERE user_id = {user_id} AND wake_time IS NOT NULL
            ORDER BY sleep_time DESC LIMIT 7
        ''').fetchall()


def get_sleep_record_last_db(user_id: int):
    return execute_query(f'''
        SELECT sleep_time, wake_time FROM public.sleep_records
        WHERE user_id = {user_id}
        ORDER BY sleep_time DESC
    ''').fetchone()


def get_sleep_time_without_wake_db(user_id: int):
    return execute_query(f'''
        SELECT sleep_time FROM public.sleep_records 
        WHERE user_id = {user_id} AND wake_time IS NULL
        ''').fetchone()


def get_wake_time_null(user_id: int):
    return execute_query(f'''
            SELECT user_id FROM public.sleep_records
            WHERE user_id = {user_id}
            AND wake_time IS NULL
        ''').fetchall()


# SAVE

def save_phone_number(user_id: int, phone_number: str):
    execute_query(f'''
            UPDATE public.users
            SET phone_number = {phone_number}
            WHERE id = {user_id}
        ''')


def save_wake_time_user_db(user_id: int, wake_time: str):
    execute_query(f'''
           UPDATE public.users 
           SET wake_time = {wake_time}
           WHERE id = {user_id}
       ''')


def save_sleep_time_records_db(user_id: int, sleep_time: str):
    execute_query(f'''
        INSERT INTO public.sleep_records (user_id, sleep_time)
        VALUES ({user_id}, '{sleep_time}')
    ''')


def save_wake_time_records_db(user_id: int, wake_time: str):
    return execute_query(f'''
        UPDATE public.sleep_records
        SET wake_time = '{wake_time}'   
        WHERE user_id = {user_id} AND wake_time IS NULL
    ''')


def save_mood_db(user_id, mood: int):
    execute_query(f'''
            UPDATE public.sleep_records
            SET mood = {mood}
            WHERE sleep_time IN (
                SELECT sleep_time FROM public.sleep_records 
                WHERE user_id = {user_id} AND wake_time IS NOT NULL
                ORDER BY sleep_time DESC 
                LIMIT 1
            );
        ''')


def save_reminder_time_db(user_id: int, reminder_time: str):
    execute_query(f'''
                INSERT OR REPLACE INTO public.reminders (user_id, reminder_time)
                VALUES ({user_id}, {reminder_time})
            ''')


def save_sleep_quality_db(user_id: int, quality: int):
        execute_query(f'''
            UPDATE public.sleep_records
            SET sleep_quality = {quality}
            WHERE sleep_time IN (
                SELECT sleep_time FROM public.sleep_records 
                WHERE user_id = {user_id} AND wake_time IS NOT NULL
                ORDER BY sleep_time DESC 
                LIMIT 1
            );
        ''')


def save_sleep_goal_db(user_id: int, goal: float):
    execute_query(f'''
            UPDATE public.users
            SET sleep_goal = {goal}
            WHERE id = {user_id}
        ''')


# DELETE

def delete_sleep_records_db(user_id: int):
    execute_query(f'DELETE FROM public.sleep_records WHERE user_id = {user_id}')


def delete_reminder_db(user_id: int):
    execute_query(f'DELETE FROM public.reminders WHERE user_id = {user_id}')


def delete_user_db(user_id: int):
    execute_query(f'DELETE FROM public.users WHERE id = {user_id}')


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
