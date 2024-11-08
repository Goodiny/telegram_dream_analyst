import logging.config

from pyrogram import Client
from pyrogram.types import Message, User, ForceReply

from db.db import save_mood_db
from handlers.keyboards import get_initial_keyboard
from handlers.states import UserStates, user_states
from handlers.user_valid import is_valid_user


logger = logging.getLogger(__name__)


async def log_mood(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

    user_id = user.id
    user_states[user_id] = UserStates.STATE_WAITING_SAVE_MOOD
    await message.reply_text(
        "Пожалуйста, оцените ваше настроение по шкале от 1 (плохое) до 5 (отличное).",
        reply_markup=ForceReply()
    )


# Обработка ответа с настроением
async def save_mood(client: Client, message: Message, user: User = None):
    if message.reply_to_message or message.text:
        if user is None:
            user = message.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
            return

        user_id = user.id
        mood = int(message.text.strip())

        try:
            if 1 <= mood <= 5:
                save_mood_db(user_id, mood)
                user_states[user_id] = UserStates.STATE_NONE
                await message.reply_text(
                    "Спасибо! Ваше настроение сохранено.",
                    reply_markup=get_initial_keyboard()
                )
                logger.info(f"Пользователь {user_id} записал настроение: {mood}")
            else:
                await message.reply_text(
                    "Пожалуйста, введите число от 1 до 5.",
                    reply_markup=ForceReply()
                )
        except ValueError:
            await message.reply_text(
                "Пожалуйста, введите корректное число от 1 до 5.",
                reply_markup=ForceReply()
            )
            logger.error(f"Произошла ошибка при записи настроения: {e}")
        except Exception as e:
            await message.reply_text(
                "Произошла ошибка при записи настроения. Пожалуйста, повторите попытку",
                reply_markup=ForceReply()
            )
            logger.critical(f"Произошла ошибка при записи настроения: {e}")