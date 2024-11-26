import logging.config
from datetime import datetime

from pyrogram import Client
from pyrogram.types import Message, User
from pytz import timezone

from db.db import save_phone_number, save_user_city
from handlers.keyboards import get_initial_keyboard, get_request_keyboard
from handlers.user_valid import add_new_user, user_valid, get_user_time_zone
from handlers.weather_advice.location_detect import get_city_from_coordinates

logger = logging.getLogger(__name__)


async def request_location(client: Client, message: Message):
    """
    Получение местоположения пользователя.
    :param client: Client
    :param message: Message
    :return:
    """
    msg = await message.reply_text("Пожалуйста, поделитесь своим местоположением, чтобы я мог определить ваш город.",
                                   reply_markup=get_request_keyboard("location"))
    return msg.id


async def save_location(client: Client, message: Message):
    """
    Получение местоположения пользователя.
    :param client: Client
    :param message: Message
    :return:
    """
    if message.location:
        logger.info("Получено местоположение.")
        latitude = message.location.latitude
        longitude = message.location.longitude
    else:
        logger.warning("Пользователь не указал местоположение.")
        msg = await message.reply_text(
                "Пожалуйста, поделитесь своим местоположением, чтобы я мог определить ваш город.",
                reply_markup=get_request_keyboard('location')
            )
        return msg.id

    user_id = message.from_user.id
    user_timezone = get_user_time_zone(user_id, latitude, longitude)
    if user_timezone:
        # Отправляем текущее время
        user_time = datetime.now(timezone(user_timezone))
        logger.info(f"Часовой пояс {user_id}: {user_timezone}\nТекущее время: "
                    f"{user_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        logger.warning(f"Не удалось определить часовой пояс пользователя {user_id}")

    try:
        city_name = get_city_from_coordinates(latitude, longitude)
        if city_name:
            save_user_city(user_id, city_name)
            await message.reply_text(f"Ваш город: {city_name}. Спасибо!",
                                     reply_markup=get_request_keyboard('get_weather'))
        else:
            msg = await message.reply_text("Извините, не удалось определить ваш город. Попробуйте еще раз.",
                                           reply_markup=get_request_keyboard('location'))
            await message.delete()
            return msg.id
    except Exception as e:
        logger.error(f"Ошибка при определении города пользователя {message.from_user.id}: {e}")


async def request_contact(client: Client, message: Message):
    """
    Получение номера телефона пользователя.
    :param client: Client
    :param message: Message
    :return:
    """
    msg = await message.reply_text(
        "Пожалуйста, поделитесь своим номером телефона, нажав на кнопку ниже.",
        reply_markup=get_request_keyboard("contact")
    )

    return msg.id


async def save_contact(client: Client, message: Message, user: User = None):
    """
    Получение номера телефона пользователя.
    :param client: Client
    :param message: Message
    :param user: User
    :return:
    """
    is_user, valid_id = await user_valid(message, user)
    if is_user == 'False':
        return valid_id

    add_new_user(user)
    user_id = valid_id
    contact = message.contact
    phone_number = contact.phone_number
    contact_user_id = contact.user_id  # ID пользователя, который отправил контакт

    if contact_user_id == user_id:
        # Сохранение номера телефона в базе данных
        try:
            save_phone_number(user_id, phone_number)
            await message.reply_text(
                "📞 Спасибо! Ваш номер телефона сохранен.",
                reply_markup=get_request_keyboard('back')
            )
            logger.info(f"Пользователь {user_id} поделился номером телефона: {phone_number}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении номера телефона для пользователя {user_id}: {e}")
            msg = await message.reply_text(
                "Произошла ошибка при сохранении вашего номера телефона.",
                reply_markup=get_initial_keyboard()
            )
            return msg.id
    else:
        msg = await message.reply_text(
            "Пожалуйста, отправьте свой собственный контакт.",
            reply_markup=get_initial_keyboard()
        )
        logger.warning(f"Пользователь {user_id} попытался отправить чужой контакт.")
        return msg.id
