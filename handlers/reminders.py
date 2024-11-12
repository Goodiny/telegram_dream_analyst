from datetime import datetime
import logging.config
import re

from db import delete_reminder_db
from db.db import get_reminder_time_db, save_reminder_time_db
from handlers.keyboards import get_reminder_menu_keyboard, get_back_keyboard
from handlers.states import UserStates, user_states
from handlers.user_valid import user_valid, valid_time_format
from pyrogram import Client
from pyrogram.types import Message, User, ForceReply, ReplyKeyboardRemove


logger = logging.getLogger(__name__)


async def set_reminder(client: Client, message: Message, user: User = None):
    is_user, valid_id = await user_valid(message, user)
    if is_user == 'False':
        return valid_id

    user_id = valid_id
    user_states[user_id] = UserStates.STATE_WAITING_REMINDER_TIME
    msg = await message.reply(
        "Пожалуйста, отправьте время, когда вы хотите получать напоминание "
        "о сне, в формате HH:MM (24-часовой формат).\nНапример: 22:30",
        reply_markup=ForceReply()
    )

    return msg.id


# Обработка ответа с временем напоминания
async def save_reminder_time(client: Client, message: Message, user: User = None):
    """
    Установка времени напоминания
    :param client: Client
    :param message: Message
    :param user: User | None
    :return:
    """
    if message.reply_to_message or message.text:
        valid_format, format_result = await valid_time_format(message, user)
        if not valid_format:
            return format_result

        reminder_time_str, user_id = format_result
        try:
            reminder_time = datetime.strptime(reminder_time_str, "%H:%M").time()
            # Сохранение времени напоминания в базе данных
            save_reminder_time_db(user_id, reminder_time_str)
            user_states[user_id] = UserStates.STATE_NONE
            await message.reply_text(
                f"⏰ Напоминание установлено на {reminder_time_str}.",
                reply_markup=get_back_keyboard()
            )
            logger.info(f"Пользователь {user_id} установил напоминание на {reminder_time_str}")
        except ValueError:
            msg = await message.reply_text(
                "❌ Неверное время. Пожалуйста, убедитесь, что время корректно.",
                reply_markup=ForceReply()
            )
            logger.warning(f"Пользователь {user_id} ввел некорректное время: {reminder_time_str}")
            return msg.id
        except Exception as e:
            msg = await message.reply_text(
                "Произошла ошибка при вводе времени. Пожалуйста, повторите попытку",
                reply_markup=ForceReply()
            )
            logger.critical(f"Произошла ошибка при вводе времени: {e}")
            return msg.id


async def remove_reminder(client: Client, message: Message, user: User = None):
    """
    Удаление напоминания
    :param client: Client
    :param message: Message
    :param user: User
    :return:
    """
    is_user, valid_id = await user_valid(message, user)
    if is_user == 'False':
        return valid_id

    user_id = valid_id

    try:
        delete_reminder_db(user_id)
        await message.reply_text(
            "🔕 Напоминание удалено.",
            reply_markup=get_back_keyboard()
        )
        logger.info(f"Пользователь {user_id} удалил напоминание")
    except Exception as e:
        logger.error(f"Ошибка при удалении напоминания для пользователя {user_id}: {e}")
        await message.reply_text(
            "Произошла ошибка при удалении напоминания.",
            reply_markup=get_back_keyboard()
        )


async def show_reminders_menu(client: Client, message: Message, user: User = None):
    """
    Отправка меню с напоминаниями
    :param client: Client
    :param message: Message
    :param user: User | None
    :return:
    """
    is_user, valid_id = await user_valid(message, user)
    if is_user == 'False':
        return valid_id

    user_id = valid_id

    try:
        reminders_record = get_reminder_time_db(user_id)
        if reminders_record:
            reminder_time = reminders_record['reminder_time']
            text = f"У вас уже есть установленное напоминания: {reminder_time}."
            keyboard = get_reminder_menu_keyboard(True)
        else:
            text = "У вас нет установленного напоминания."
            keyboard = get_reminder_menu_keyboard(False)
        msg = await message.reply_text(text, reply_markup=ReplyKeyboardRemove())
        await client.send_message(
            chat_id=user_id,
            text="Что вы хотите сделать?",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f'При получении данных от пользователя {user_id} произошла ошибка: {e}')
        msg = await message.reply_text(
            "Произошла ошибка при получении данных, попробуйте ещё раз или вернитесь назад",
            reply_markup=ForceReply()
        )

    return msg.id
