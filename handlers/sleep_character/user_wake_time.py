import logging.config
from datetime import datetime

from pyrogram import Client
from pyrogram.types import Message, User, ForceReply

from db.db import get_user_wake_time, save_wake_time_user_db
from handlers.keyboards import get_back_keyboard
from handlers.states import UserStates, user_states
from handlers.user_valid import user_valid, valid_time_format

logger = logging.getLogger(__name__)


async def set_wake_time(client: Client, message: Message, user: User = None):
    is_user, valid_id = await user_valid(message, user)
    if is_user == 'False':
        return valid_id

    user_id = valid_id
    user_states[user_id] = UserStates.STATE_WAITING_USER_WAKE_TIME
    try:
        wake_time_str = get_user_wake_time(user_id)
        if wake_time_str and wake_time_str['wake_time']:
            wake_time_dt = datetime.strptime(wake_time_str['wake_time'], "%H:%M")
            response = (
                f"Время пробуждения установлено на {wake_time_str['wake_time']}.\n\n"
                f"Пожалуйста, введите время в котором вы хотели бы проснутся "
                f"в формате HH:MM (24 часовой формат). \nНапример: 7:45"
            )
        else:
            response = (
                "Время пробуждения не установлено.\n\n"
                "Пожалуйста, введите время в котором вы хотели бы проснутся "
                "в формате HH:MM (24 часовой формат). \nНапример: 7:45"
            )

        msg = await message.reply_text(
            response,
            reply_markup=ForceReply()
        )
        return msg.id
    except Exception as e:
        logger.error(f"Произошла ошибка при попытке пользователя {user_id} "
                     f"установить отложенное время пробуждения: {e}")
        

async def save_wake_time(client: Client, message: Message, user: User = None):
    if message.reply_to_message or message.text:
        valid_format, format_result = await valid_time_format(message, user)
        if not valid_format:
            return format_result

        wake_time_str, user_id = format_result

        try:
            wake_time = datetime.strptime(wake_time_str, "%H:%M").time()
            # Сохранение времени напоминания в базе данных
            save_wake_time_user_db(user_id, wake_time_str)
            user_states[user_id] = UserStates.STATE_NONE
            await message.reply_text(
                f"⏰ Время подъема установлено на {wake_time_str}.",
                reply_markup=get_back_keyboard()
            )
            logger.info(f"Пользователь {user_id} установил время подъема на {wake_time_str}")
        except ValueError:
            msg = await message.reply_text(
                "❌ Неверное время. Пожалуйста, убедитесь, что время корректно.",
                reply_markup=ForceReply()
            )
            logger.warning(f"Пользователь {user_id} ввел некорректное время: {wake_time_str}")
            return msg.id
        except Exception as e:
            msg = await message.reply_text(
                "Произошла ошибка при вводе времени. Пожалуйста, повторите попытку",
                reply_markup=ForceReply()
            )
            logger.critical(f"Произошла ошибка при вводе времени подъема: {e}")
            return msg.id
