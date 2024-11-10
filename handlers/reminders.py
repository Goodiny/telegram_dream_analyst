from datetime import datetime
import logging.config
import re

from db import delete_reminder_db
from db.db import get_reminder_time_db, save_reminder_time_db
from handlers.keyboards import get_reminder_menu_keyboard, get_back_keyboard
from handlers.states import UserStates, user_states
from handlers.user_valid import add_new_user, is_valid_user, user_valid
from pyrogram import Client
from pyrogram.types import Message, User, ForceReply, ReplyKeyboardRemove


logger = logging.getLogger(__name__)


async def set_reminder(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

    user_id = user.id
    user_states[user_id] = UserStates.STATE_WAITING_REMINDER_TIME
    logger.debug(f"user_states: {user_states[user_id]}" )
    reminder = await message.reply(
        "Пожалуйста, отправьте время, когда вы хотите получать напоминание "
        "о сне, в формате HH:MM (24-часовой формат).\nНапример: 22:30",
        reply_markup=ForceReply()
    )

    return reminder.id


# Обработка ответа с временем напоминания
async def save_reminder_time(client: Client, message: Message, user: User = None):
    if message.reply_to_message or message.text:
        user_is_valid, valid_id = user_valid(message, user)
        if user_is_valid == 'False':
            return valid_id

        add_new_user(user)
        user_id = valid_id
        reminder_time_str = message.text.strip()
        # Валидация формата времени
        if not re.match(r'^\d{1,2}:\d{2}$', reminder_time_str):
            reminder = await message.reply_text(
                "❌ Неверный формат времени. Пожалуйста, введите время в формате HH:MM.",
                reply_markup=ForceReply()
            )
            logger.warning(f"Пользователь {user_id} ввел неверный формат времени: {reminder_time_str}")
            return reminder.id

        try:
            reminder_time = datetime.strptime(reminder_time_str, "%H:%M").time()
            # Сохранение времени напоминания в базе данных
            save_reminder_time_db(user_id, reminder_time_str)
            user_states[user_id] = UserStates.STATE_NONE
            reminder = await message.reply_text(
                f"⏰ Напоминание установлено на {reminder_time_str}.",
                reply_markup=get_back_keyboard()
            )
            logger.info(f"Пользователь {user_id} установил напоминание на {reminder_time_str}")
        except ValueError:
            reminder = await message.reply_text(
                "❌ Неверное время. Пожалуйста, убедитесь, что время корректно.",
                reply_markup=ForceReply()
            )
            logger.warning(f"Пользователь {user_id} ввел некорректное время: {reminder_time_str}")
        except Exception as e:
            reminder = await message.reply_text(
                "Произошла ошибка при вводе времени. Пожалуйста, повторите попытку",
                reply_markup=ForceReply()
            )
            logger.critical(f"Произошла ошибка при вводе времени: {e}")

        return reminder.id


async def remove_reminder(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

    user_id = user.id

    try:
        delete_reminder_db(user_id)
        reminder = await message.reply_text(
            "🔕 Напоминание удалено.",
            reply_markup=get_back_keyboard()
        )
        logger.info(f"Пользователь {user_id} удалил напоминание")
    except Exception as e:
        logger.error(f"Ошибка при удалении напоминания для пользователя {user_id}: {e}")
        reminder = await message.reply_text(
            "Произошла ошибка при удалении напоминания.",
            reply_markup=get_back_keyboard()
        )

    return reminder.id


async def show_reminders_menu(client: Client, message: Message, user: User = None):
    """
    Отправка меню с напоминаниями
    :param client: Client
    :param message: Message
    :param user: User | None
    :return:
    """
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

    user_id = user.id

    try:
        reminders_record = get_reminder_time_db(user_id)
        if reminders_record:
            reminder_time = reminders_record['reminder_time']
            text = f"У вас уже есть установленное напоминания: {reminder_time}."
            keyboard = get_reminder_menu_keyboard(True)
        else:
            text = "У вас нет установленного напоминания."
            keyboard = get_reminder_menu_keyboard(False)
        reminder = await message.reply_text(text, reply_markup=ReplyKeyboardRemove())
        await client.send_message(
            chat_id=user_id,
            text="Что вы хотите сделать?",
            reply_markup=keyboard
        )

        return reminder.id

    except Exception as e:
        logger.error(f'При получении данных от пользователя {user_id} произошла ошибка: {e}')
        await message.reply_text(
            "Произошла ошибка при получении данных, попробуйте ещё раз или вернитесь назад",
            reply_markup=ForceReply()
        )