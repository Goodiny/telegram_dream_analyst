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
DATABASE_URL = os.getenv('DATABASE_UL')