from __future__ import annotations

import logging.config

from pyrogram import Client
import sqlite3
from configs.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN
from handlers.handlers import setup_handlers

from db.modify_tables import database_initialize, create_triggers_db
from handlers.scheduler import setup_scheduler

# Настройка логирования
logger = logging.getLogger(__name__)

# Создание экземпляра клиента бота
app = Client("sleep_tracker_bot",
             api_id=TELEGRAM_API_ID,
             api_hash=TELEGRAM_API_HASH,
             bot_token=TELEGRAM_BOT_TOKEN)

# Инициализация базы данных
try:
    database_initialize()
    logger.info("База данных инициализирована")
except sqlite3.OperationalError as e:
    logger.error(f"Ошибка при создании баззы данных: {e}")

# Создание триггера update_existing_sleep_time
try:
    create_triggers_db()
    logger.info("Триггер update_existing_sleep_time создан")
except sqlite3.OperationalError as e:
    logger.error(f"Ошибка при создании триггера: {e}")


# Настройка всех обработчиков
setup_handlers(app)

# Запуск бота
if __name__ == '__main__':
    # Инициализация и запуск планировщика напоминаний
    setup_scheduler(app)
    logger.info("Планировщик запущен")
    try:
        logger.info("Бот запускается...")
        app.run()
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}")
