import logging.config
import sqlite3

from configs import DATABASESL_URL


logger = logging.getLogger(__name__)


def execute_query_sl(query, params=None, row_factory=True):
    """
    Принимает строку запроса и возвращает курсор, если он не None, иначе None
    """
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