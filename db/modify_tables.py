import json
import sqlite3
import logging.config
from datetime import datetime

from pyrogram.types import User

from configs.config import DATABASE_URL
from utils.utils import is_valid_user

logger = logging.getLogger(__name__)


def execute_query(query, params=None, row_factory=True):
    with sqlite3.connect(DATABASE_URL, check_same_thread=False) as conn:
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


def save_user_city(user_id, city_name):
    # Здесь реализуется логика сохранения данных в базе данных
    execute_query("UPDATE users SET city_name = ?, has_provided_location = 1 WHERE id = ?",
                  (city_name, user_id))


def get_user_stats(user_id: int):
    query = '''
        SELECT sleep_time, wake_time FROM sleep_records
        WHERE user_id = :user_id
        ORDER BY sleep_time DESC
    '''
    params = {"user_id": user_id}

    try:
        record = execute_query(query, params).fetchone()
        if record:
            sleep_time = datetime.fromisoformat(record['sleep_time'])
            wake_time = record['wake_time']
            if wake_time:
                wake_time = datetime.fromisoformat(wake_time)
                duration = wake_time - sleep_time
                response = f"🛌 Ваша последняя запись сна:\nС {sleep_time.strftime('%Y-%m-%d %H:%M')} до {wake_time.strftime('%Y-%m-%d %H:%M')} — {duration}"
            else:
                response = f"🛌 Ваша текущая запись сна:\nС {sleep_time.strftime('%Y-%m-%d %H:%M')} — Ещё не проснулись"
            logger.info(f"Пользователь {user_id} запросил статистику сна")
            return response
        else:
            logger.info(f"Пользователь {user_id} запросил статистику сна, но нет записей")
            return
    except sqlite3.OperationalError as e:
        logger.error(f"Ошибка при получении статистики сна для пользователя {user_id}: {e}")
        return


def add_user_to_db(user: User):
    if user is None:
        return  # Игнорируем сообщения без информации о пользователе
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name

    query = '''
            INSERT INTO users (id, username, first_name, last_name)
            VALUES (:id, :username, :first_name, :last_name)
            ON CONFLICT(id) DO UPDATE SET
                username = :username,
                first_name = :first_name,
                last_name = :last_name
        '''

    params = {
        'id': user_id,
        'username': username,
        'first_name': first_name,
        'last_name': last_name
    }

    try:
        # Вставляем или обновляем информацию о пользователе в таблицу users
        execute_query(query, params)
        logger.info(f"Пользователь {user_id} добавлен или обновлен в таблице users")
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя {user_id} в базу данных: {e}")


# Инициализация базы данных
def database_initialize():
    # Таблица users
    execute_query('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            phone_number TEXT,  -- если вы храните номер телефона
            city_name TEXT,
            sleep_goal REAL,     -- если вы храните цель сна
            has_provided_location INT DEFAULT 0
        )
    ''')

    # Таблица sleep_records
    execute_query('''
        CREATE TABLE IF NOT EXISTS sleep_records (
            user_id INTEGER NOT NULL,
            sleep_time TIMESTAMP NOT NULL,
            wake_time TIMESTAMP DEFAULT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE
            ON UPDATE NO ACTION
        )
    ''')

    # Таблица reminders
    execute_query('''
        CREATE TABLE IF NOT EXISTS reminders (
            user_id INTEGER PRIMARY KEY NOT NULL,
            reminder_time TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE
            ON UPDATE NO ACTION
        )
    ''')


def create_triggers_db():
    execute_query('''
        CREATE TRIGGER IF NOT EXISTS update_existing_sleep_time
        BEFORE INSERT ON sleep_records
        FOR EACH ROW
        WHEN (SELECT COUNT(*) FROM sleep_records WHERE user_id = NEW.user_id AND wake_time IS NULL) > 0
        BEGIN
            UPDATE sleep_records
            SET sleep_time = NEW.sleep_time
            WHERE user_id = NEW.user_id AND wake_time IS NULL;
            SELECT RAISE(IGNORE);
        END;
    ''')


# GET

def get_all_sleep_records(user_id: int):
    return execute_query('SELECT * FROM sleep_records WHERE user_id = :user_id', {"user_id": user_id}).fetchall()


def get_city_name(user_id: int):
    return execute_query('SELECT city_name FROM users WHERE id = :user_id', {"user_id": user_id}).fetchone()


def get_has_provided_location(user_id: int):
    return execute_query('SELECT user, has_provided_location FROM users WHERE uaser_id = ?',
                         (user_id,)).fetchone()


def get_reminder(user_id: int):
    return execute_query('SELECT * FROM reminders WHERE user_id = ?', (user_id,)).fetchone()


def get_all_reminders():
    return execute_query('SELECT user_id FROM reminders').fetchall()


def get_sleep_records_per_week(user_id: int):
    return execute_query('''
            SELECT sleep_time, wake_time FROM sleep_records
            WHERE user_id = ? AND wake_time IS NOT NULL
            ORDER BY sleep_time DESC LIMIT 7
        ''', (user_id,)).fetchall()


def get_wake_time_null(user_id: int):
    return execute_query('''
            SELECT user_id FROM sleep_records
            WHERE user_id = :user_id
            AND wake_time IS NULL
        ''', {'user_id': user_id}).fetchall()


# SAVE

def save_phone_number(user_id: int, phone_number: str):
    execute_query('''
            UPDATE users
            SET phone_number = ?
            WHERE id = ?
        ''', (phone_number, user_id))


def save_wake_time_user_db(user_id: int, wake_time: str):
    execute_query('''
           UPDATE users 
           SET wake_time = :wake_time
           WHERE id = :user_id
       ''', (wake_time, user_id))


def save_sleep_time_db(user_id: int, sleep_time: str):
    execute_query('''
        INSERT INTO sleep_records (user_id, sleep_time)
        VALUES (:user_id, :sleep_time)
    ''', {"user_id": user_id, "sleep_time": sleep_time})


def save_wake_time_records_db(user_id: int, wake_time: str):
    return execute_query('''
        UPDATE sleep_records
        SET wake_time = ?
        WHERE user_id = ? AND wake_time IS NULL
    ''', (wake_time, user_id))


def save_mood_db(user_id, mood: int):
    execute_query('''
            UPDATE sleep_records
            SET mood = ?
            WHERE sleep_time IN (
                SELECT sleep_time FROM sleep_records 
                WHERE user_id = ? AND wake_time IS NOT NULL
                ORDER BY sleep_time DESC 
                LIMIT 1
            );
        ''', (mood, user_id))


def save_reminder_time_db(user_id: int, reminder_time: str):
    execute_query('''
                INSERT OR REPLACE INTO reminders (user_id, reminder_time)
                VALUES (?, ?)
            ''', (user_id, reminder_time))


def save_sleep_quality_db(user_id: int, quality: int):
        execute_query('''
            UPDATE sleep_records
            SET sleep_quality = ?
            WHERE sleep_time IN (
                SELECT sleep_time FROM sleep_records 
                WHERE user_id = ? AND wake_time IS NOT NULL
                ORDER BY sleep_time DESC 
                LIMIT 1
            );
        ''', (quality, user_id))


def save_sleep_goal_db(user_id: int, goal: float):
    execute_query('''
            UPDATE users
            SET sleep_goal = ?
            WHERE id = ?
        ''', (goal, user_id))


# DELETE

def delete_sleep_rocords_db(user_id: int):
    execute_query('DELETE FROM sleep_records WHERE user_id = ?', (user_id,))


def delete_reminder_db(user_id: int):
    execute_query('DELETE FROM reminders WHERE user_id = ?',(user_id,))


def delete_user_db(user_id: int):
    execute_query('DELETE FROM users WHERE id = ?', (user_id,))


def delete_all_data_user_db(user_id: int):
    delete_sleep_rocords_db(user_id)
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
        # Переименовываем старую таблицу users
        cursor.execute('ALTER TABLE users RENAME TO users_old;')

        # Создаем новую таблицу users
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone_number TEXT,
                city_name TEXT,
                sleep_goal REAL DEFAULT 8.0
            );
        ''')

        # Переносим данные с преобразованием типа users
        cursor.execute('''
            INSERT INTO users
            SELECT *
            FROM users_old;
        ''')

        # Удаляем старую таблицу users
        cursor.execute('DROP TABLE users_old;')

        # Переименовываем старую таблицу sleep_records
        cursor.execute('ALTER TABLE sleep_records RENAME TO sleep_records_old;')

        # Создаем новую таблицу sleep_records
        cursor.execute('''
            CREATE TABLE sleep_records (
                user_id INTEGER NOT NULL,
                sleep_time TEXT NOT NULL,
                wake_time TEXT DEFAULT NULL,
                sleep_quality TEXT DEFAULT NULL,
                mood TEXT DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE 
                ON UPDATE NO ACTION
            );
        ''')

        # Переносим данные с преобразованием типа sleep_records
        cursor.execute('''
            INSERT INTO sleep_records
            SELECT *
            FROM sleep_records_old;
        ''')

        # Удаляем старую таблицу sleep_recordes
        cursor.execute('DROP TABLE sleep_records_old;')

        # Переименовываем старую таблицу reminders
        cursor.execute('ALTER TABLE reminders RENAME TO reminders_old;')

        # Создаем новую таблицу reminders
        cursor.execute('''
               CREATE TABLE reminders (
                   user_id INTEGER PRIMARY KEY NOT NULL,
                   reminder_time TEXT NOT NULL,
                   FOREIGN KEY (user_id) REFERENCES users(id)
                   ON DELETE CASCADE 
                   ON UPDATE NO ACTION
               );
           ''')

        # Переносим данные с преобразованием типа reminders
        cursor.execute('''
               INSERT INTO reminders 
               SELECT *
               FROM reminders_old;
           ''')

        # Удаляем старую таблицу reminders
        cursor.execute('DROP TABLE reminders_old;')

        # Вставляем уникальные user_id из sleep_records в users
        cursor.execute('''
            INSERT INTO users (id)
            SELECT DISTINCT user_id FROM sleep_records
            WHERE user_id NOT IN (SELECT id FROM users)
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
    modify_table()
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
