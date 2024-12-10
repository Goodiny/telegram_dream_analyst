from __future__ import annotations

import logging.config

from pyrogram import Client

from configs import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN
from db import database_initialize
from handlers import setup_handlers, setup_scheduler

# Настройка логирования
logger = logging.getLogger(__name__)

# Создание экземпляра клиента бота
app = Client("sleep_tracker_bot",
             api_id=TELEGRAM_API_ID,
             api_hash=TELEGRAM_API_HASH,
             bot_token=TELEGRAM_BOT_TOKEN)

# Инициализация базы данных
database_initialize()

# Инициализация триггеров для базы данных
#create_triggers_db()

# Настройка обработчиков
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
