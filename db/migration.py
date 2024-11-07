import psycopg2
import logging.config
from db.execute_query import execute_query_sl, execute_query_pg
from configs.config import logger

logger = logging.getLogger(__name__)

def migration_sqlite_to_pg():
    '''
    Миграция базы данных SQLite на PostgreSQL
    '''
    try:
        tables = execute_query_sl('SELECT name FROM sqlite_master WHERE type="table";').fetchall()


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
                    execute_query_pg(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str});")
                except psycopg2.DatabaseError as e:
                    logger.warning(f"В базе данных уже существует таблица {table_name} c полями {columns_str}: {e}")

                # Вставка данных
                for row in rows:

                    values_str = ", ".join(
                        f"{str(val)}" if str(val).isdigit() else f"'{str(val)}'" if str(val) != 'None' else 'NULL'
                        for i, val in enumerate(row))
                    try:
                        execute_query_pg(f"INSERT INTO {table_name} ({', '.join(row.keys())}) VALUES ({values_str})")
                    except psycopg2.DatabaseError as e:
                        logging.warning(f"В таблице {table_name} уже есть данные {values_str}: {e}")

                logger.info(f"Данные в таблицу {table_name} перенесены успешно")
            logger.info(f"Миграция базы данных прошла успешно")
        else:
            logger.warning(f"Миграция не прошла так как данные не были прочитаны")
    except Exception as e:
        logger.error(f"Ошибка при миграции базы данных: {e}")