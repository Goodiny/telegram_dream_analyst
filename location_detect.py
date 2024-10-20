import logging

import requests

OPENCAGE_API_KEY = "47f19b58763542309908925d4357927b"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),  # Запись логов в файл bot.log
        logging.StreamHandler()  # Вывод логов в консоль
    ]
)

logger = logging.getLogger(__name__)

def get_city_from_coordinates(latitude, longitude):
    url = "https://api.opencagedata.com/geocode/v1/json"
    params = {
        "q": f"{latitude},{longitude}",
        "key": OPENCAGE_API_KEY,
        "language": "ru",
        "pretty": 1
    }
    response = requests.get(url, params)
    data = response.json()

    if response.status_code == 200 and data["results"]:
        for component in data["results"][0]["components"]:
            if "city" in data["results"][0]["components"]:
                return data["results"][0]["components"]["city"]
            elif "town" in data["results"][0]["components"]:
                return data["results"][0]["components"]["town"]
            elif "village" in data["results"][0]["components"]:
                return data["results"][0]["components"]["village"]
    else:
        logger.error("Ошибка при запросе геолокации:", data.get("error", "Неизвестная ошибка"))
        return


if __name__ == "__main__":
    get_city_from_coordinates()
