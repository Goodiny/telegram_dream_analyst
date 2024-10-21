import sqlite3

from config import DATABASE_URL


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


def create_trigers_db():
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


def modify_table():
    with sqlite3.connect('sleep_data.db', check_same_thread=False) as conn:
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
