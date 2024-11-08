import sqlite3

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


if __name__ == '__main__':
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