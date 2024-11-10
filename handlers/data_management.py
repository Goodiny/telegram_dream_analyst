import csv
import logging.config
import os

import psycopg2
from pyrogram import Client
from pyrogram.types import Message, User, ForceReply

from db.db import delete_all_data_user_db, get_all_sleep_records
from handlers.keyboards import data_management_keyboard, get_back_keyboard
from handlers.states import UserStates, user_states
from handlers.user_valid import is_valid_user


logger = logging.getLogger(__name__)


async def export_data(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

    user_id = user.id
    try:
        records = get_all_sleep_records(user_id)
        if records:
            # Создание CSV файла
            fieldnames = records[0].keys()
            with open(f'sleep_data_{user_id}.csv', 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows([dict(record) for record in records])
            # Отправка файла пользователю
            await client.send_document(chat_id=user_id, document=f'sleep_data_{user_id}.csv')
            os.remove(f'sleep_data_{user_id}.csv')  # Удаление файла после отправки
            await message.reply_text(
                "Данные о сне получены.",
                reply_markup=get_back_keyboard()
            )
            logger.info(f"Пользователь {user_id} экспортировал свои данные")
        else:
            await message.reply_text(
                "У вас нет данных для экспорта.",
                reply_markup=get_back_keyboard()
            )
    except psycopg2.OperationalError as e:
        logger.error(f"Ошибка при обращение к базе данных для пользователя {user_id}: {e}")
        await message.reply_text(
            "Произошла ошибка при обращении к базе данных.",
            reply_markup=get_back_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при экспорте данных для пользователя {user_id}: {e}")
        await message.reply_text(
            "Произошла ошибка при экспорте данных.",
            reply_markup=get_back_keyboard()
        )


async def delete_my_data(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

    user_id = user.id
    user_states[user_id] = UserStates.STATE_WAITING_CONFIRM_DELETE
    await message.reply_text(
        "Вы уверены, что хотите удалить все свои данные? Это действие необратимо. Напишите 'Да' для подтверждения.",
        reply_markup=ForceReply()
    )


async def show_user_data_management_menu(client: Client, user_id: int):
    await client.send_message(
        chat_id=user_id,
        text="Управление данными пользователя:",
        reply_markup=data_management_keyboard()
    )


# Обработка подтверждения удаления данных
async def confirm_delete(client: Client, message: Message, user: User = None):
    if message.reply_to_message or message.text:
        if user is None:
            user = message.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
            return

        user_id = user.id

        if message.text.strip().lower() == 'да':
            try:
                delete_all_data_user_db(user_id)
                user_states[user_id] = UserStates.STATE_NONE
                await message.reply_text(
                    "Все ваши данные были удалены.",
                    reply_markup=get_back_keyboard()
                )
                logger.info(f"Пользователь {user_id} удалил все свои данные")
            except Exception as e:
                logger.error(f"Ошибка при удалении данных пользователя {user_id}: {e}")
                await message.reply_text(
                    "Произошла ошибка при удалении ваших данных.",
                    reply_markup=ForceReply()
                )
        else:
            await message.reply_text(
                "Операция отменена.",
                reply_markup=get_back_keyboard()
            )