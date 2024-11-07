import re
import psycopg2

import logging.config

from psycopg2.extras import RealDictCursor

from configs import DATABASEPG_URL, POSTGRES_USERNAME, POSTGRES_DATABASE, POSTGRES_PASSWORD, \
    POSTGRES_HOST, POSTGRES_PORT

logger = logging.getLogger(__name__)


if POSTGRES_USERNAME is None:
    USERNAME, PASSWORD, HOST, PORT, DATABASE = re.findall(r"/(\w+):(\w+)@(\w+):(\d+)/(\w+)", DATABASEPG_URL)[0]
else:
    USERNAME = POSTGRES_USERNAME
    PASSWORD = POSTGRES_PASSWORD
    HOST = POSTGRES_HOST
    PORT = POSTGRES_PORT
    DATABASE = POSTGRES_DATABASE


def execute_query_pg(query, params=None, row_factory=True):
    """
    Execute a query on a PostgreSQL database.
    :param query: The query to execute.
    :param params: The parameters to use in the query.
    :param row_factory: If True, the query will return a list of dictionaries.
    :return: A list of dictionaries if row_factory is True, or None if row_factory is False.
    """
    with psycopg2.connect(database=DATABASE,
                          user=USERNAME,
                          password=PASSWORD,
                          host=HOST, port=PORT, 
                          cursor_factory=RealDictCursor) as conn:
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