import logging.config

from pyrogram import Client
from pyrogram.types import Message

from db.db import save_user_city
from handlers.keyboards import get_initial_keyboard, get_request_keyboard
from handlers.weather_advice.location_detect import get_city_from_coordinates

logger = logging.getLogger(__name__)


async def save_location(clientL: Client, message: Message):
    latitude = message.location.latitude
    longitude = message.location.longitude

    city_name = get_city_from_coordinates(latitude, longitude)
    logger.debug(city_name)
    if city_name:
        user_id = message.from_user.id
        save_user_city(user_id, city_name)
        await message.reply_text(f"Ваш город: {city_name}. Спасибо!", reply_markup=get_initial_keyboard())
    else:
        await message.reply_text("Извините, не удалось определить ваш город. Попробуйте еще раз.",
                                    reply_markup=request_location())
    await message.delete()


async def request_location(client: Client, message: Message):
    await message.reply_text("Пожалуйста, поделитесь своим местоположением, чтобы я мог определить ваш город.",
                             reply_markup=get_request_keyboard("location"))
