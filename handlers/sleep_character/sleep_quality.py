import logging.config

from pyrogram import Client
from pyrogram.types import Message, User, ForceReply

from db.db import save_sleep_quality_db
from handlers.keyboards import get_initial_keyboard
from handlers.states import UserStates, user_states
from handlers.user_valid import is_valid_user


logger = logging.getLogger(__name__)


async def rate_sleep(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

    user_id = user.id
    user_states[user_id] = UserStates.STATE_WAITING_SLEEP_QUALITY
    await message.reply_text(
        "Пожалуйста, оцените качество вашего сна по шкале от 1 до 5.",
        reply_markup=ForceReply()
    )


# Обработка ответа с оценкой сна
async def save_sleep_quality(client: Client, message: Message, user: User = None):
    if message.reply_to_message or message.text:
        if user is None:
            user = message.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
            return

        user_id = user.id
        quality = int(message.text.strip())

        try:
            if 1 <= quality <= 5:
                save_sleep_quality_db(user_id, quality)
                user_states[user_id] = UserStates.STATE_NONE
                await message.reply_text(
                    "Спасибо! Ваша оценка сохранена.",
                    reply_markup=get_initial_keyboard()
                )
                logger.info(f"Пользователь {user_id} оценил сон на {quality}")
            else:
                await message.reply_text(
                    "Пожалуйста, введите число от 1 до 5.",
                    reply_markup=ForceReply()
                )
                logger.warning(f"Пользоователь {user_id} ввел число не соответсвующее диапазону. Повторите попытку")
        except ValueError:
            await message.reply_text(
                "Пожалуйста, введите корректное число от 1 до 5.",
                reply_markup=ForceReply()
            )
            logger.error(f"Пользоователь {user_id} ввел неверно число. Повторите попытку")
        except Exception as e:
            await message.reply_text(
                "Произошла ошибка при оценке сна. Пожалуйста, повторите попытку",
                reply_markup=ForceReply()
            )
            logger.critical(f"Произошла ошибка при оценке сна: {e}")
