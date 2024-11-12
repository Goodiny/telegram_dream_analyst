from __future__ import annotations

from datetime import datetime
import logging.config
import re

from pyrogram import Client
from pyrogram.types import User, Message, ForceReply

from db.db import get_has_provided_location, get_sleep_record_last_db, get_user_db, save_user_to_db
from handlers.keyboards import get_back_keyboard, get_request_keyboard
from handlers.states import UserStates, user_states


logger = logging.getLogger(__name__)


def is_valid_user(user: User):
    if not isinstance(user, User):
        raise TypeError
    if (
            user.is_bot or user.is_fake or
            user.is_deleted or user.is_contact or
            user.is_restricted or user.is_scam
        ):
        raise ValueError
    return True


def get_user_stats(user_id: int):
    try:
        record = get_sleep_record_last_db(user_id)
        if record:
            # sleep_time = record['sleep_time']
            sleep_time = datetime.fromisoformat(record['sleep_time'])
            wake_time = record['wake_time']
            if wake_time:
                wake_time = datetime.fromisoformat(wake_time)
                duration = wake_time - sleep_time
                response = (f"🛌 Ваша последняя запись сна:\nС {sleep_time.strftime('%Y-%m-%d %H:%M')} до "
                            f"{wake_time.strftime('%Y-%m-%d %H:%M')} — {duration}")
            else:
                response = f"🛌 Ваша текущая запись сна:\nС {sleep_time.strftime('%Y-%m-%d %H:%M')} — Ещё не проснулись"
            logger.info(f"Пользователь {user_id} запросил статистику сна")
            return response
        else:
            logger.info(f"Пользователь {user_id} запросил статистику сна, но нет записей")
            return
    except Exception as e:
        logger.error(f"Ошибка при получении статистики сна для пользователя {user_id}: {e}")
        return


def add_new_user(user: User):
    if user is None:
        return  # Игнорируем сообщения без информации о пользователе
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

    user_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name

    try:
        user_db = get_user_db(user_id)
        if user_db is not None:
            return  # Пользователь уже есть в базе данных
    except Exception as e:
        logger.warning(f"Ошибка при получении информации о пользователе {user_id}: {e}")

    try:
        # Вставляем или обновляем информацию о пользователе в таблицу users
        save_user_to_db(user_id, username, first_name, last_name)
        logger.info(f"Пользователь {user_id} добавлен или обновлен в таблице users")
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя {user_id} в базу данных: {e}")


async def user_valid(
        message: Message | None,
        user: User,
        text: str = "Вы не являетесь валидным пользователем, "
                    "пожалуйста отправьте сообщение с валидного аккаунта"):
    """
    Проверка валидности пользователя
    :param message: Message
    :param user: User
    :param text: str
    :return:
    """
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        msg = await message.reply_text(
            text,
            reply_markup=get_back_keyboard())
        return 'False', msg.id

    return 'True', user.id


def requires_location(func):
    async def wrapper(client: Client, message: Message, user: User = None):
        is_user, valid_id = await user_valid(message, user)
        if is_user == 'False':
            return valid_id

        user_id = valid_id
        try:
            result = get_has_provided_location(user_id)
        except Exception as e:
            logger.error(f"Ошибка при вызове функции get_has_provided_location пользователя {user_id}: {e}")
            msg = await message.reply_text(
                "Данные о раскрытии местоположения не были получены, отправьте снова или попробуйте позже",
                reply_markup=get_request_keyboard('location')
            )
            return msg.id

        if result is None:
            try:
                add_new_user(user)
            except Exception as e:
                msg = await message.reply_text(
                    "Данный аккаунт не является валидным попробуйте снова с другим аккаунтом",
                    reply_markup=get_request_keyboard('back')
                )
                return msg.id
            result = {'has_provided_location': 0}

        has_provided_location = result['has_provided_location']
        if not has_provided_location:
            try:
                msg = await message.reply_text("Пожалуйста, отправьте ваше местоположение, прежде чем продолжить.",
                                               reply_markup=get_request_keyboard('location'))
                return msg.id
            except Exception as e:
                logger.warning(f"Ошибка при вызове метода message_reply пользователя {user_id}: {e}")
                msg = await message.reply("Пожалуйста, отправьте ваше местоположение, прежде чем продолжить.",
                                          reply_markup=get_request_keyboard('location'))
                return msg.id
        return await func(client, message, user)
    return wrapper


async def valid_time_format(message: Message, user: User):
    """

    :param message: Message
    :param user: User
    :return:
    """
    is_user, valid_id = await user_valid(message, user)
    if is_user == 'False':
        return False, valid_id

    add_new_user(user)
    user_id = valid_id
    _time_str = message.text.strip()
    # Валидация формата времени
    if not re.match(r'^\d{1,2}:\d{2}$', _time_str):
        msg = await message.reply_text(
            "❌ Неверный формат времени. Пожалуйста, введите время в формате HH:MM.",
            reply_markup=ForceReply()
        )
        logger.warning(f"Пользователь {user_id} ввел неверный формат времени: {_time_str}")
        return False, msg.id
    return True, (_time_str, user_id)


async def user_state_navigate(state: UserStates, client: Client, message: Message, user: User = None):
    """

    :param state: UserStates
    :param client: Client
    :param message: Message
    :param user: user
    :return:
    """
    from handlers.data_management import confirm_delete
    from handlers.reminders import save_reminder_time
    from handlers.sleep_character.sleep_mood import save_mood
    from handlers.sleep_character.sleep_quality import save_sleep_quality
    from handlers.sleep_character.user_sleep_goal import save_sleep_goal
    from handlers.sleep_character.user_wake_time import save_wake_time
    
    if user is None:
        return  # Игнорируем сообщения без информации о пользователе
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

    user_id = user.id

    if state == UserStates.STATE_WAITING_REMINDER_TIME:
        message_id = await save_reminder_time(client, message, user)
    elif state == UserStates.STATE_WAITING_SLEEP_QUALITY:
        message_id = await save_sleep_quality(client, message, user)
    elif state == UserStates.STATE_WAITING_SLEEP_GOAL:
        message_id = await save_sleep_goal(client, message, user)
    elif state == UserStates.STATE_WAITING_USER_WAKE_TIME:
        message_id = await save_wake_time(client, message, user)
    elif state == UserStates.STATE_WAITING_SAVE_MOOD:
        message_id = await save_mood(client, message, user)
    elif state == UserStates.STATE_WAITING_CONFIRM_DELETE:
        message_id = await confirm_delete(client, message, user)
    else:
        message_id = await message.reply_text(
            text="Произошла ошибка. Пожалуйста, начните заново.",
            reply_markup=get_back_keyboard())
        user_states[user_id] = UserStates.STATE_NONE
    await message.delete()

    return message_id


if __name__ == "__main__":
    pass
