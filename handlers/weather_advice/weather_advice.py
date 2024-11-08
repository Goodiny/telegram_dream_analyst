import logging.config

from pyrogram import Client
from pyrogram.types import Message, User

from db.db import get_city_name
from handlers.keyboards import get_request_keyboard

from handlers.weather_advice.weather_tips import get_sleep_advice_based_on_weather, get_weather
from handlers.user_valid import is_valid_user, requires_location


logger = logging.getLogger(__name__)


@requires_location
async def get_weather_advice(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

    user_id = user.id

    try:
        user_city_name_record = get_city_name(user_id)
        if user_city_name_record and user_city_name_record['city_name']:
            user_city = user_city_name_record["city_name"]
        else:
            user_city = "Moscow"  # Здесь можно использовать город пользователя или запросить его

        weather = get_weather(user_city)

        if weather:
            advice = get_sleep_advice_based_on_weather(weather)
            response = (
                f"Погода в {weather['city']}:\n"
                f"Температура: {weather['temperature']}°C (ощущается как {weather['feels_like']}°C)\n"
                f"Влажность: {weather['humidity']}%\n"
                f"Погодные условия: {weather['weather_description']}\n"
                f"Скорость ветра: {weather['wind_speed']} м/с\n\n"
                f"Советы по улучшению сна:\n{advice}"
            )
            keyboard = get_request_keyboard("weather")
        else:
            response = "Извините, не удалось получить данные о погоде. Попробуйте позже."
            keyboard = get_request_keyboard()

        await message.reply_text(response, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка при запросе имени города пользователя {user_id}: {e}")
        await message.reply_text("Произошла ошибка при запросе данных о городе, попробуйте ещё раз",
                                 reply_markup=get_request_keyboard("location")
                                 )