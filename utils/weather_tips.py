import json
import logging.config

import requests

from configs.config import WEATHER_API_KEY, WEATHER_BASE_URL

logger = logging.getLogger(__name__)


def get_weather(city_name: str):
    try:
        params = {
            "q": city_name,
            "appid": WEATHER_API_KEY,
            "units": "metric",
            "lang": "ru"
        }
        response = requests.get(WEATHER_BASE_URL, params)
        data = response.json()

        if response.status_code == 200:
            weather = {
                "city": data["name"],
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "weather_description": data["weather"][0]["description"],
                "wind_speed": data["wind"]["speed"]
            }
            return weather
        else:
            logger.error(f"Ошибка: {data['message']}")
            return

    except Exception as e:
        logger.error(f"Ошибка при получении данных о погоде: {e}")
        return


def get_sleep_advice_based_on_weather(weather):
    advice = []

    # Совет по температуре
    if weather["temperature"] > 25:
        advice.append(
            "Температура на улице высокая. Убедитесь, что ваша комната проветривается или используйте кондиционер."
        )
    elif weather["temperature"] < 10:
        advice.append(
            "Температура на улице низкая. Убедитесь, что в вашей комнате достаточно тепло, используйте теплое одеяло."
        )
    else:
        advice.append("Температура в норме. Убедитесь, что в комнате комфортная температура для сна.")

    # Совет по влажности
    if weather["humidity"] > 70:
        advice.append(
            "Влажность высокая, что может затруднять дыхание. Проветривайте комнату или используйте осушитель воздуха."
        )
    elif weather["humidity"] < 30:
        advice.append("Влажность низкая, что может вызвать сухость в горле. Используйте увлажнитель воздуха.")

    # Совет по осадкам и облачности
    if "дождь" in weather["weather_description"]:
        advice.append("Сегодня возможен дождь. Проверьте, закрыты ли окна, чтобы избежать попадания влаги в комнату.")
    elif "гроза" in weather["weather_description"]:
        advice.append("На улице гроза. Лучше закрыть окна и избежать шума снаружи.")
    elif "снег" in weather["weather_description"]:
        advice.append("Ожидается снег. Проверьте, достаточно ли тепло в комнате и используйте дополнительные одеяла.")

    return "\n".join(advice)


if __name__ == "__main__":
    print(get_sleep_advice_based_on_weather(get_weather("Кобулети")))
