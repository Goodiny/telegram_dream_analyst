import json
import logging.config
import os
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENCAGE_API_KEY = os.getenv('OPENCAGE_API_KEY')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
WEATHER_BASE_URL = os.getenv('WEATHER_BASE_URL')
DATABASESL_URL = os.getenv('DATABASESL_URL')
DATABASEPG_URL = os.getenv('DATABASEPG_URL')

path = "configs/logging.json" if os.path.basename(os.path.abspath('./')) == "telegram_dream_analyst" \
    else "../configs/logging.json"

# Настройка логирования
with open(path, 'r') as f:
    config = json.load(f)
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)