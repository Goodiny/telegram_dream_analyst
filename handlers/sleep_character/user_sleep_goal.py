import logging.config

from pyrogram import Client
from pyrogram.types import Message, User, ForceReply

from db.db import save_sleep_goal_db
from handlers.keyboards import get_back_keyboard
from handlers.states import UserStates, user_states
from handlers.user_valid import add_new_user, is_valid_user, user_valid

logger = logging.getLogger(__name__)


async def set_sleep_goal(client: Client, message: Message, user: User = None):
    is_user, valid_id = await user_valid(message, user)
    if is_user == 'False':
        return valid_id

    user_id = valid_id
    user_states[user_id] = UserStates.STATE_WAITING_SLEEP_GOAL
    msg = await message.reply_text(
        "Пожалуйста, введите вашу цель по продолжительности сна в часах (например, 7.5).",
        reply_markup=ForceReply()
    )

    return msg.id


# Обработка ответа с целью сна
async def save_sleep_goal(client: Client, message: Message, user: User = None):
    if message.reply_to_message or message.text:
        is_user, valid_id = await user_valid(message, user)
        if is_user == 'False':
            return valid_id

        add_new_user(user)
        user_id = valid_id
        goal = float(message.text.strip())

        try:
            if 0 < goal <= 24:
                save_sleep_goal_db(user_id, goal)
                user_states[user_id] = UserStates.STATE_NONE
                await message.reply_text(
                    f"Ваша цель по продолжительности сна установлена на {goal} часов.",
                    reply_markup=get_back_keyboard()
                )
                logger.info(f"Пользователь {user_id} установил цель сна: {goal} часов")
            else:
                msg = await message.reply_text(
                    "Пожалуйста, введите число от 0 до 24.",
                    reply_markup=ForceReply()
                )
                return msg.id
        except ValueError:
            msg = await message.reply_text(
                "Пожалуйста, введите корректное число.",
                reply_markup=ForceReply()
            )
            return msg.id
        except Exception as e:
            msg = await message.reply_text(
                "Произошла ошибка при установки цели сна. Пожалуйста, повторите попытку",
                reply_markup=ForceReply()
            )
            logger.critical(f"Произошла ошибка при установке цели сна: {e}")

            return msg.id
