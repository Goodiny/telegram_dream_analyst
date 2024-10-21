from __future__ import annotations

import csv
import json
# import logging
import logging.config
import os
import random
import re
from enum import Enum, auto
from uuid import uuid4

from pyrogram import Client, filters
from pyrogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, User, CallbackQuery, ReplyKeyboardRemove
from pyrogram.types import ForceReply
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import sqlite3
from datetime import datetime, time, timedelta

from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN
from location_detect import get_city_from_coordinates
from modify_tables import execute_query, database_initialize, create_trigers_db, save_user_city

import matplotlib.pyplot as plt
import io

from wether_tips import get_sleep_advice_based_on_weather, get_weather

# Настройка логирования
# logging.basicConfig(
#     level=logging.INFO,  # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("bot.log"),  # Запись логов в файл bot.log
#         logging.StreamHandler()  # Вывод логов в консоль
#     ]
# )

with open('logging.json', 'r') as f:
    config = json.load(f)
    logging.config.dictConfig(config)

logger = logging.getLogger('bot')

# Инициализация переменных окружения
# API_ID = int(os.environ.get("API_ID"))
# API_HASH = os.environ.get("API_HASH")
# BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Создание экземпляра клиента бота
app = Client("sleep_tracker_bot",
             api_id=TELEGRAM_API_ID,
             api_hash=TELEGRAM_API_HASH,
             bot_token=TELEGRAM_BOT_TOKEN)

# Инициализация базы данных
try:
    database_initialize()
    logger.info("База данных инициализирована")
except sqlite3.OperationalError as e:
    logger.error(f"Ошибка при создании баззы данных: {e}")

# Создание триггера update_existing_sleep_time
try:
    create_trigers_db()
    logger.info("Триггер update_existing_sleep_time создан")
except sqlite3.OperationalError as e:
    logger.error(f"Ошибка при создании триггера: {e}")

# Словарь для хранения состояний пользователей
user_states: dict[int, "UserStates"] = {}


# Определение состояний
class UserStates(Enum):
    STATE_NONE = auto()
    STATE_WAITING_REMINDER_TIME = auto()
    STATE_WAITING_SLEEP_QUALITY = auto()
    STATE_WAITING_SLEEP_GOAL = auto()
    STATE_WAITING_WAKE_TIME = auto()
    STATE_WAITING_SAVE_MOOD = auto()
    STATE_WAITING_CONFIRM_DELETE = auto()
    STATE_WAITING_LOCATION = auto()


async def user_state_navigate(state: UserStates, client: Client, message: Message, user: User = None):
    if user is None:
        return  # Игнорируем сообщения без информации о пользователе
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id

    if state == UserStates.STATE_WAITING_REMINDER_TIME:
        await save_reminder_time(client, message, user)
    elif state == UserStates.STATE_WAITING_SLEEP_QUALITY:
        await save_sleep_quality(client, message, user)
    elif state == UserStates.STATE_WAITING_SLEEP_GOAL:
        logger.info(__name__ + str(state))
        await save_sleep_goal(client, message, user)
    elif state == UserStates.STATE_WAITING_SAVE_MOOD:
        await save_mood(client, message, user)
    elif state == UserStates.STATE_WAITING_CONFIRM_DELETE:
        await confirm_delete(client, message, user)
    else:
        await message.reply_text("Произошла ошибка. Пожалуйста, начните заново.",
                           reply_markup=get_back_keyboard())
        user_states[user_id] = UserStates.STATE_NONE
    await message.delete()


# Функция для создания основной клавиатуры
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton("😴 Сон"), KeyboardButton("🌅 Пробуждение")],
            [KeyboardButton("📊 Статистика"), KeyboardButton("⏰ Установить напоминание")],
            [KeyboardButton("🔕 Удалить напоминание"), KeyboardButton("📞 Отправить номер телефона")],
            [KeyboardButton("📈 График сна"), KeyboardButton("💡 Совет по сну")],
            [KeyboardButton("⭐️ Оценка сна"), KeyboardButton("🎯 Установка цели сна")],
            [KeyboardButton("🥳 Ваше настроение"), KeyboardButton("🗃 Сохранить данные")],
            [KeyboardButton("⚙️ Меню")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_initial_keyboard():
    keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton("⚙️ Меню"), KeyboardButton("ℹ️ Информация")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_back_keyboard():
    keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔙 Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard


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


def add_user_to_db(user: User):
    if user is None:
        return  # Игнорируем сообщения без информации о пользователе
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name

    query = '''
            INSERT INTO users (id, username, first_name, last_name)
            VALUES (:id, :username, :first_name, :last_name)
            ON CONFLICT(id) DO UPDATE SET
                username = :username,
                first_name = :first_name,
                last_name = :last_name
        '''

    params = {
        'id': user_id,
        'username': username,
        'first_name': first_name,
        'last_name': last_name
    }

    try:
        # Вставляем или обновляем информацию о пользователе в таблицу users
        execute_query(query, params)
        logger.info(f"Пользователь {user_id} добавлен или обновлен в таблице users")
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя {user_id} в базу данных: {e}")


def get_user_stats(user_id: int):
    query = '''
        SELECT sleep_time, wake_time FROM sleep_records
        WHERE user_id = :user_id
        ORDER BY sleep_time DESC
    '''
    params = {"user_id": user_id}

    try:
        record = execute_query(query, params).fetchone()
        if record:
            sleep_time = datetime.fromisoformat(record['sleep_time'])
            wake_time = record['wake_time']
            if wake_time:
                wake_time = datetime.fromisoformat(wake_time)
                duration = wake_time - sleep_time
                response = f"🛌 Ваша последняя запись сна:\nС {sleep_time.strftime('%Y-%m-%d %H:%M')} до {wake_time.strftime('%Y-%m-%d %H:%M')} — {duration}"
            else:
                response = f"🛌 Ваша текущая запись сна:\nС {sleep_time.strftime('%Y-%m-%d %H:%M')} — Ещё не проснулись"
            logger.info(f"Пользователь {user_id} запросил статистику сна")
            return response
        else:
            logger.info(f"Пользователь {user_id} запросил статистику сна, но нет записей")
            return
    except sqlite3.OperationalError as e:
        logger.error(f"Ошибка при получении статистики сна для пользователя {user_id}: {e}")
        return


# Команда /start
@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    user = message.from_user
    try:
        add_user_to_db(user)
    finally:
        # Отправка приветственного сообщения с пользовательской клавиатурой

        # result = execute_query("SELECT has_provided_location FROM users WHERE user_id = ? AND "
        #                        "has_provided_location = 0",
        #                        (user.id,)).fetchone()
        #
        # if result is None or not result[0]:
        #     await request_location(client, message)
        # else:
        #     await message.reply_text("Добро пожаловать! Вы уже предоставили свою локацию.")
        await message.reply_text(
            "👋 Привет! Я бот для отслеживания сна.\n\n"
            "Выберите действие из меню ниже:",
            reply_markup=get_initial_keyboard()
        )


# Команда /set_reminder
@app.on_message(filters.command("set_reminder"))
async def set_reminder(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    user_states[user_id] = UserStates.STATE_WAITING_REMINDER_TIME
    await message.reply_text(
        "Пожалуйста, отправьте время, когда вы хотите получать напоминание "
        "о сне, в формате HH:MM (24-часовой формат).\nНапример: 22:30",
        reply_markup=ForceReply()
    )


# Обработка ответа с временем напоминания
async def save_reminder_time(client: Client, message: Message, user: User = None):
    if message.reply_to_message:
        if user is None:
            user = message.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
        add_user_to_db(user)
        user_id = user.id
        reminder_time_str = message.text.strip()
        # Валидация формата времени
        if not re.match(r'^\d{1,2}:\d{2}$', reminder_time_str):
            await message.reply_text(
                "❌ Неверный формат времени. Пожалуйста, введите время в формате HH:MM.",
                reply_markup=ForceReply()
            )
            logger.warning(f"Пользователь {user_id} ввел неверный формат времени: {reminder_time_str}")
            return

        query = '''
                INSERT OR REPLACE INTO reminders (user_id, reminder_time)
                VALUES (:user_id, :reminder_time)
            '''
        params = {'user_id': user_id, 'reminder_time': reminder_time_str}

        try:
            reminder_time = datetime.strptime(reminder_time_str, "%H:%M").time()
            # Сохранение времени напоминания в базе данных
            execute_query(query, params)
            user_states[user_id] = UserStates.STATE_NONE
            await message.reply_text(
                f"⏰ Напоминание установлено на {reminder_time_str}.",
                reply_markup=get_initial_keyboard()
            )
            logger.info(f"Пользователь {user_id} установил напоминание на {reminder_time_str}")
        except ValueError:
            await message.reply_text(
                "❌ Неверное время. Пожалуйста, убедитесь, что время корректно.",
                reply_markup=ForceReply()
            )
            logger.warning(f"Пользователь {user_id} ввел некорректное время: {reminder_time_str}")
        except Exception as e:
            await message.reply_text(
                "Произошла ошибка при вводе времени. Пожалуйста, повторите попытку",
                reply_markup=ForceReply()
            )
            logger.critical(f"Произошла ошибка при вводе времени: {e}")


# Команда /rate_sleep
@app.on_message(filters.command("rate_sleep"))
async def rate_sleep(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
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
        user_id = user.id
        quality = int(message.text.strip())
        query = '''
            UPDATE sleep_records
            SET sleep_quality = :quality
            WHERE sleep_time IN (
                SELECT sleep_time FROM sleep_records 
                WHERE user_id = :user_id AND wake_time IS NOT NULL
                ORDER BY sleep_time DESC 
                LIMIT 1
            );
        '''
        params = {'quality': quality, 'user_id': user_id}
        try:
            if 1 <= quality <= 5:
                execute_query(query, params)
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


# Команда /set_sleep_goal
@app.on_message(filters.command("set_sleep_goal"))
async def set_sleep_goal(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    user_states[user_id] = UserStates.STATE_WAITING_SLEEP_GOAL
    await message.reply_text(
        "Пожалуйста, введите вашу цель по продолжительности сна в часах (например, 7.5).",
        reply_markup=ForceReply()
    )


# Обработка ответа с целью сна
async def save_sleep_goal(client: Client, message: Message, user: User = None):
    if message.reply_to_message or message.text:
        if user is None:
            user = message.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
        add_user_to_db(user)
        user_id = user.id
        goal = float(message.text.strip())
        query = '''
            UPDATE users
            SET sleep_goal = :goal
            WHERE id = :user_id
        '''
        params = {'goal': goal, 'user_id': user_id}
        try:
            if 0 < goal <= 24:
                execute_query(query, params)
                user_states[user_id] = UserStates.STATE_NONE
                await message.reply_text(
                    f"Ваша цель по продолжительности сна установлена на {goal} часов.",
                    reply_markup=get_initial_keyboard()
                )
                logger.info(f"Пользователь {user_id} установил цель сна: {goal} часов")
            else:
                await message.reply_text(
                    "Пожалуйста, введите число от 0 до 24.",
                    reply_markup=ForceReply()
                )
        except ValueError:
            await message.reply_text(
                "Пожалуйста, введите корректное число.",
                reply_markup=ForceReply()
            )
        except Exception as e:
            await message.reply_text(
                "Произошла ошибка при установки цели сна. Пожалуйста, повторите попытку",
                reply_markup=ForceReply()
            )
            logger.critical(f"Произошла ошибка при установке цели сна: {e}")


@app.on_message(filters.command("set_wake_time"))
async def set_wake_time(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    user_states[user_id] = UserStates.STATE_WAITING_WAKE_TIME
    await message.reply_text(
        "Пожалуйста, введите время в котором вы хотели бы проснутся "
        "в формате HH:MM (24 часовой формат). \nНапример: 7:45",
        reply_markup=ForceReply()
    )


async def save_wake_time(client: Client, message: Message, user: User = None):
    if message.reply_to_message or message.text:
        if user is None:
            user = message.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
        add_user_to_db(user)
        user_id = user.id
        wake_time_str = message.text.strip()
        # Валидация формата времени
        if not re.match(r'^\d{1,2}:\d{2}$', wake_time_str):
            await message.reply_text(
                "❌ Неверный формат времени. Пожалуйста, введите время в формате HH:MM.",
                reply_markup=ForceReply()
            )
            logger.warning(f"Пользователь {user_id} ввел неверный формат времени: {wake_time_str}")
            return
        query = '''
           UPDATE users 
           SET wake_time = :wake_time
           WHERE id = :user_id
       '''
        params = {'user_id': user_id, 'wake_time': wake_time_str}

        try:
            wake_time = datetime.strptime(wake_time_str, "%H:%M").time()
            # Сохранение времени напоминания в базе данных
            execute_query(query, params)
            user_states[user_id] = UserStates.STATE_NONE
            await message.reply_text(
                f"⏰ Время подъема установлено на {wake_time_str}.",
                reply_markup=get_initial_keyboard()
            )
            logger.info(f"Пользователь {user_id} установил время подъема на {wake_time_str}")
        except ValueError:
            await message.reply_text(
                "❌ Неверное время. Пожалуйста, убедитесь, что время корректно.",
                reply_markup=ForceReply()
            )
            logger.warning(f"Пользователь {user_id} ввел некорректное время: {wake_time_str}")
        except Exception as e:
            await message.reply_text(
                "Произошла ошибка при вводе времени. Пожалуйста, повторите попытку",
                reply_markup=ForceReply()
            )
            logger.critical(f"Произошла ошибка при вводе времени подъема: {e}")



# Команда /log_mood
@app.on_message(filters.command("log_mood"))
async def log_mood(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
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
        user_id = user.id
        mood = int(message.text.strip())
        query = '''
            UPDATE sleep_records
            SET mood = :mood
            WHERE sleep_time IN (
                SELECT sleep_time FROM sleep_records 
                WHERE user_id = :user_id AND wake_time IS NOT NULL
                ORDER BY sleep_time DESC 
                LIMIT 1
            );
        '''
        params = {'mood': mood, 'user_id': user_id}
        try:
            if 1 <= mood <= 5:
                execute_query(query, params)
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
        except Exception as e:
            await message.reply_text(
                "Произошла ошибка при записи настроения. Пожалуйста, повторите попытку",
                reply_markup=ForceReply()
            )
            logger.critical(f"Произошла ошибка при записи настроения: {e}")


# Команда /delete_my_data
@app.on_message(filters.command("delete_my_data"))
async def delete_my_data(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    user_states[user_id] = UserStates.STATE_WAITING_CONFIRM_DELETE
    await message.reply_text(
        "Вы уверены, что хотите удалить все свои данные? Это действие необратимо. Напишите 'Да' для подтверждения.",
        reply_markup=ForceReply()
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
        user_id = user.id
        queries = [
            'DELETE FROM sleep_records WHERE user_id = :user_id',
            'DELETE FROM reminders WHERE user_id = :user_id',
            'DELETE FROM users WHERE id = :user_id'
        ]
        params = {'user_id': user_id}
        if message.text.strip().lower() == 'да':
            try:
                for query in queries:
                    execute_query(query, params)
                user_states[user_id] = UserStates.STATE_NONE
                await message.reply_text(
                    "Все ваши данные были удалены.",
                    reply_markup=get_initial_keyboard()
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
                reply_markup=get_initial_keyboard()
            )


# Команда /sleep
@app.on_message(filters.command("sleep"))
async def sleep_time(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    add_user_to_db(user)
    user_id = user.id
    sleep_time = datetime.now()
    query = '''
        INSERT INTO sleep_records (user_id, sleep_time)
        VALUES (:user_id, :sleep_time)
    '''
    params = {'user_id': user_id, 'sleep_time': sleep_time.isoformat()}
    try:

        select_query = execute_query('''
            SELECT user_id FROM sleep_records
            WHERE user_id = :user_id
            AND wake_time IS NULL
        ''', {'user_id': user_id})

        if len(select_query.fetchall()) > 0:
            await message.reply_text(
                "❗️ Запись о времени сна уже отмечена. "
                "Используйте /wake, для пробуждения.",
                reply_markup=get_initial_keyboard()
            )
            logger.warning(f"Пользователь {user_id} попытался повторно отметить запись сна без записи пробуждения.")
            return

        execute_query(query, params)
        await message.reply_text(
            f"🌙 Время отхода ко сну отмечено: {sleep_time.strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=get_initial_keyboard()
        )
        logger.info(f"Пользователь {user_id} отметил время сна: {sleep_time}")
    except Exception as e:
        logger.error(f"Ошибка при записи времени сна для пользователя {user_id}: {e}")
        await message.reply_text(
            "Произошла ошибка при сохранении времени сна.",
            reply_markup=get_initial_keyboard()
        )


# Команда /wake
@app.on_message(filters.command("wake"))
async def wake_time(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    wake_time = datetime.now()
    query = '''
        UPDATE sleep_records
        SET wake_time = :wake_time
        WHERE user_id = :user_id AND wake_time IS NULL
    '''
    params = {'wake_time': wake_time.isoformat(), 'user_id': user_id}
    try:

        if execute_query(query, params).rowcount == 0:
            await message.reply_text(
                "❗️ Нет записи о времени сна или уже отмечено пробуждение. "
                "Используйте /sleep, чтобы начать новую запись.",
                reply_markup=get_initial_keyboard()
            )
            logger.warning(f"Пользователь {user_id} попытался отметить пробуждение без активной записи сна.")
            return
        await message.reply_text(
            f"☀️ Время пробуждения отмечено: {wake_time.strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=get_initial_keyboard()
        )
        logger.info(f"Пользователь {user_id} отметил время пробуждения: {wake_time}")
    except Exception as e:
        logger.error(f"Ошибка при записи времени пробуждения для пользователя {user_id}: {e}")
        await message.reply_text(
            "Произошла ошибка при сохранении времени пробуждения.",
            reply_markup=get_initial_keyboard()
        )


# Команда /stats
@app.on_message(filters.command("stats"))
async def sleep_stats(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    try:
        response = get_user_stats(user_id)
        if response:
            await message.reply_text(
                response,
                reply_markup=get_initial_keyboard()
            )
        else:
            await message.reply_text(
                "У вас пока нет записей о сне.",
                reply_markup=get_initial_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка при вызове функции get_user_stats: {e}")
        await message.reply_text(
            "Произошла ошибка при получении статистики сна.",
            reply_markup=get_initial_keyboard()
        )


# Команда /remove_reminder
@app.on_message(filters.command("remove_reminder"))
async def remove_reminder(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    query = 'DELETE FROM reminders WHERE user_id = :user_id'
    params = {'user_id': user_id}
    try:
        execute_query(query, params)
        await message.reply_text(
            "🔕 Напоминание удалено.",
            reply_markup=get_initial_keyboard()
        )
        logger.info(f"Пользователь {user_id} удалил напоминание")
    except Exception as e:
        logger.error(f"Ошибка при удалении напоминания для пользователя {user_id}: {e}")
        await message.reply_text(
            "Произошла ошибка при удалении напоминания.",
            reply_markup=get_initial_keyboard()
        )


# Команда /get_phone
@app.on_message(filters.command("get_phone"))
async def request_contact(client: Client, message: Message):
    contact_button = KeyboardButton(
        text="Отправить номер телефона",
        request_contact=True
    )
    return_button = KeyboardButton("← Вернуться")
    reply_markup = ReplyKeyboardMarkup(
        [[return_button, contact_button]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.reply_text(
        "Пожалуйста, поделитесь своим номером телефона, нажав на кнопку ниже.",
        reply_markup=reply_markup
    )


# Обработка контакта
@app.on_message(filters.contact)
async def save_contact(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    add_user_to_db(user)
    user_id = user.id
    contact = message.contact
    phone_number = contact.phone_number
    contact_user_id = contact.user_id  # ID пользователя, который отправил контакт

    query = '''
        UPDATE users
        SET phone_number = :phone_number
        WHERE id = :id
    '''
    params = {'phone_number': phone_number, 'id': user_id}

    if contact_user_id == user_id:
        # Сохранение номера телефона в базе данных
        try:
            execute_query(query, params)
            await message.reply_text(
                "📞 Спасибо! Ваш номер телефона сохранен.",
                reply_markup=get_initial_keyboard()
            )
            logger.info(f"Пользователь {user_id} поделился номером телефона: {phone_number}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении номера телефона для пользователя {user_id}: {e}")
            await message.reply_text(
                "Произошла ошибка при сохранении вашего номера телефона.",
                reply_markup=get_initial_keyboard()
            )
    else:
        await message.reply_text(
            "Пожалуйста, отправьте свой собственный контакт.",
            reply_markup=get_initial_keyboard()
        )
        logger.warning(f"Пользователь {user_id} попытался отправить чужой контакт.")


# Функция для запроса локации у пользователя
@app.on_message(filters.command("send_location"))
async def request_location(client: Client, message: Message):
    location_button = KeyboardButton("Отправить местоположение", request_location=True)
    reply_markup = ReplyKeyboardMarkup([[KeyboardButton('← Вернуться'), location_button]],
                                       resize_keyboard=True, one_time_keyboard=True)
    await message.reply_text("Пожалуйста, поделитесь своим местоположением, чтобы я мог определить ваш город.",
                             reply_markup=reply_markup)


@app.on_message(filters.location)
async def handle_location(client: Client, message: Message):
    latitude = message.location.latitude
    longitude = message.location.longitude

    city_name = get_city_from_coordinates(latitude, longitude)
    if city_name:
        user_id = message.from_user.id
        save_user_city(user_id, city_name)
        await message.reply_text(f"Ваш город: {city_name}. Спасибо!", reply_markup=get_initial_keyboard())
    else:
        await message.reply_text("Извините, не удалось определить ваш город. Попробуйте еще раз.",
                                 reply_markup=request_location())
    await message.delete()


@app.on_message(filters.command("weather_advice"))
async def weather_advice(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    add_user_to_db(user)
    user_id = user.id

    try:
        user_city_name_record = execute_query('SELECT city_name FROM users WHERE id = :user_id',
                                              {"user_id": user_id}).fetchone()
        if user_city_name_record:
            user_city = user_city_name_record["city_name"]
        else:
            user_city = "Moscow" # Здесь можно использовать город пользователя или запросить его

        weather = get_weather(user_city)

        if weather:
            advice = get_sleep_advice_based_on_weather(weather)
            response = (
                f"Погода в {weather['city']}:\n"
                f"Температура: {weather['temperature']}°C (ощущается как {weather['feels_like']}°C)\n"
                f"Влажность: {weather['humidity']}%\n"
                f"Погодные условия: {weather['weather_description']}\n"
                f"Скорость ветра: {weather['wind_speed']} м/с\n\n"
                f"Советы по улучшению сна:\n{advice}"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Получить совет по сну", callback_data="sleep_tips")]
            ])
        else:
            response = "Извините, не удалось получить данные о погоде. Попробуйте позже."
            keyboard = ReplyKeyboardMarkup([[KeyboardButton("🔙 Назад")]])

        await message.reply_text(response, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка при запросе имени города пользователя {user_id}: {e}")
        await message.reply_text("Произошла ошибка при запросе данных о городе, попробуйте ещё раз",
                                 reply_markup=request_location(client, message))


# Команда /sleep_chart
@app.on_message(filters.command("sleep_chart"))
async def sleep_chart(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    query = '''
        SELECT sleep_time, wake_time FROM sleep_records
        WHERE user_id = :user_id AND wake_time IS NOT NULL
        ORDER BY sleep_time DESC LIMIT 7
    '''
    params = {'user_id': user_id}
    try:
        records = execute_query(query, params).fetchall()
        if records:
            durations = []
            dates = []
            for record in records:
                sleep_time = datetime.fromisoformat(record['sleep_time'])
                wake_time = datetime.fromisoformat(record['wake_time'])
                duration = (wake_time - sleep_time).total_seconds() / 3600  # В часах
                durations.append(duration)
                dates.append(sleep_time.date())
            # Построение графика
            plt.figure(figsize=(10, 5))
            plt.plot(dates, durations, marker='o')
            plt.xlabel('Дата')
            plt.ylabel('Продолжительность сна (часы)')
            plt.title('Ваш сон за последние 7 дней')
            plt.grid(True)
            # Сохранение графика в буфер
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            # Отправка графика пользователю
            await client.send_photo(chat_id=user_id, photo=buf, caption='Ваш график сна за последние 7 дней.',
                                    reply_markup=get_initial_keyboard())
            plt.close()
            logger.info(f"Пользователь {user_id} запросил график сна")
        else:
            await message.reply_text(
                "У вас недостаточно записей для построения графика.",
                reply_markup=get_initial_keyboard()
            )
            logger.info(f"Пользователь {user_id} запросил график сна, но записей недостаточно")
    except Exception as e:
        logger.error(f"Ошибка при создании графика для пользователя {user_id}: {e}")
        await message.reply_text(
            "Произошла ошибка при создании графика.",
            reply_markup=get_initial_keyboard()
        )


# Команда /sleep_tips
@app.on_message(filters.command("sleep_tips"))
async def sleep_tips(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    sleep_tips = []
    with open("sleep_tips.txt", 'r') as st:
        while line := st.readline():
            sleep_tips.append(line)

    tip = random.choice(sleep_tips)
    await message.reply_text(
        f"💡 Совет для улучшения сна:\n\n{tip}",
        reply_markup=get_initial_keyboard()
    )
    logger.info(f"Пользователь {user_id} запросил совет по сну")


# Команда /export_data
@app.on_message(filters.command("export_data"))
async def export_data(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    query = '''
        SELECT * FROM sleep_records
        WHERE user_id = :user_id
    '''
    params = {'user_id': user_id}
    try:
        records = execute_query(query, params).fetchall()
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
                reply_markup=get_initial_keyboard()
            )
            logger.info(f"Пользователь {user_id} экспортировал свои данные")
        else:
            await message.reply_text(
                "У вас нет данных для экспорта.",
                reply_markup=get_initial_keyboard()
            )
    except sqlite3.OperationalError as e:
        logger.error(f"Ошибка при обращение к базе данных для пользователя {user_id}: {e}")
        await message.reply_text(
            "Произошла ошибка при обращении к базе данных.",
            reply_markup=get_initial_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при экспорте данных для пользователя {user_id}: {e}")
        await message.reply_text(
            "Произошла ошибка при экспорте данных.",
            reply_markup=get_initial_keyboard()
        )


# Команда /menu
@app.on_message(filters.command("menu"))
async def send_main_menu(client: Client, chat_id: int):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("😴 Сон", callback_data="sleep"),
            InlineKeyboardButton("🌅 Пробуждение", callback_data="wake")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats"),
            InlineKeyboardButton("📈 График сна", callback_data="sleep_chart")
        ],
        [
            InlineKeyboardButton("🎯 Цели сна", callback_data="sleep_goals"),
            InlineKeyboardButton("💤 Характеристика сна", callback_data="sleep_characteristics")
        ],
        [
            InlineKeyboardButton("⏰ Напоминания", callback_data="reminders"),
            InlineKeyboardButton("💡 Советы по сну", callback_data="sleep_tips")
        ],
        [
            InlineKeyboardButton("👤 Управление данными", callback_data="user_data_management"),
            InlineKeyboardButton("📱 Отправка номера", callback_data="request_contact")
        ]
    ])
    await client.send_message(
        chat_id=chat_id,
        text='Главное меню.',
        reply_markup=ReplyKeyboardRemove()
    )
    await client.send_message(
        chat_id=chat_id,
        text="Выберите действие:",
        reply_markup=keyboard
    )


async def show_reminders_menu(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id

    try:
        reminders_record = execute_query("SELECT reminder_time FROM reminders WHERE user_id = :user_id",
                                         {'user_id': user_id}).fetchone()
        if reminders_record:
            reminder_time = reminders_record['reminder_time']
            text = f"У вас уже есть установленное напоминания: {reminder_time}."
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("⏰ Установить напоминание", callback_data="set_reminder"),
                    InlineKeyboardButton("🔕 Удалить напоминание", callback_data="reset_reminder")
                ],
                [
                    InlineKeyboardButton("← Назад", callback_data="back_to_menu")
                ]
            ])
        else:
            text = "У вас нет установленного напоминания."
            keyboard = InlineKeyboardMarkup([ 
                [
                    InlineKeyboardButton("⏰ Установить напоминание", callback_data="set_reminder"),
                ],
                [
                    InlineKeyboardButton("← Назад", callback_data="back_to_menu")
                ]
            ])
        await message.reply_text(text, reply_markup=ReplyKeyboardRemove())
        await client.send_message(
            chat_id=user_id,
            text="Что вы хотите сделать?",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f'При получении данных от пользователя {user_id} произошла ошибка: {e}')
        await message.reply_text("Произошла ошибка при получении данных, попробуйте ещё раз или вернитесь назад")


async def show_sleep_characteristics_menu(client: Client, user_id: int):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("😊 Ваше настроение", callback_data="rate_mood")],
            [InlineKeyboardButton("🛌 Оценка сна", callback_data="rate_sleep")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
        ]
    )
    await client.send_message(
        chat_id=user_id,
        text="Выберите характеристику сна:",
        reply_markup=keyboard
    )


async def show_user_data_management_menu(client: Client, user_id: int):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💾 Сохранение данных", callback_data="save_data")],
            [InlineKeyboardButton("🗑 Удаление данных", callback_data="delete_data")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
        ]
    )
    await client.send_message(
        chat_id=user_id,
        text="Управление данными пользователя:",
        reply_markup=keyboard
    )


# Обработка нажатий кнопок
@app.on_callback_query()
async def handle_callback_query(client: Client, callback_query: CallbackQuery):
    user = callback_query.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    data = callback_query.data
    if data == "sleep":
        # Вызываем функцию sleep_time
        await sleep_time(client, callback_query.message, user)
    elif data == "wake":
        # Вызываем функцию wake_time
        await wake_time(client, callback_query.message, user)
    elif data == "stats":
        # Вызываем функцию sleep_stats
        await sleep_stats(client, callback_query.message, user)
    elif data == "reminders":
        await show_reminders_menu(client, callback_query.message, user)
    elif data == "set_reminder":
        await set_reminder(client, callback_query.message, user)
    elif data == "reset_reminder":
        await remove_reminder(client, callback_query.message, user)
    elif data == "request_contact":
        await request_contact(client, callback_query.message)
    elif data == "sleep_chart":
        await sleep_chart(client, callback_query.message, user)
    elif data == "sleep_goals":
        await set_sleep_goal(client, callback_query.message, user)
    elif data == "sleep_characteristics":
        await show_sleep_characteristics_menu(client, user.id)
    elif data == "sleep_tips":
        await sleep_tips(client, callback_query.message, user)
    elif data == "user_data_management":
        await show_user_data_management_menu(client, user.id)
        # Обработка подпунктов меню
    elif data == "rate_mood":
        await log_mood(client, callback_query.message, user)
    elif data == "rate_sleep":
        await rate_sleep(client, callback_query.message, user)
    elif data == "delete_data":
        await delete_my_data(client, callback_query.message, user)
    elif data == "save_data":
        await export_data(client, callback_query.message, user)
    elif data == "back_to_menu":
        await callback_query.message.reply_text("Вы вернулись.",
                                                reply_markup=get_initial_keyboard())
        await send_main_menu(client, callback_query.message.chat.id)
    # Уведомляем Telegram, что колбэк обработан
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.answer()


@app.on_inline_query()
async def answer_inline_query(client, inline_query):
    user = inline_query.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    query = inline_query.query.strip()
    if query == "stats":
        # Получение статистики пользователя из базы данных
        stats = get_user_stats(user_id)
        if stats:
            result = [
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title="Моя статистика сна",
                    input_message_content=InputTextMessageContent(stats),
                    description="Моя статистика сна за последний сон"
                )
            ]
            inline_query.answer(result)
        else:
            inline_query.answer([])
    else:
        inline_query.answer([])

    logger.info(f"Пользователь {user_id} отправил Inline-query запрос: {query}")


# Обработка нажатий кнопок
@app.on_message(filters.text & ~filters.regex(r'^/'))
async def handle_button_presses(client, message: Message):
    user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    text = message.text.strip()
    if text == "⚙️ Меню":
        await send_main_menu(client, message.chat.id)
    # elif text == "😴 Сон":
    #     sleep_time(client, message, user)
    # elif text == "🌅 Пробуждение":
    #     wake_time(client, message, user)
    # elif text == "📊 Статистика":
    #     sleep_stats(client, message, user)
    # elif text == "⏰ Установить напоминание":
    #     set_reminder(client, message)
    # elif text == "🔕 Удалить напоминание":
    #     remove_reminder(client, message, user)
    # elif text == "📞 Отправить номер телефона":
    #     request_contact(client, message)
    # elif text == "📈 График сна":
    #     sleep_chart(client, message, user)
    # elif text == "💡 Совет по сну":
    #     sleep_tips(client, message, user)
    # elif text == "⭐️ Оценка сна":
    #     rate_sleep(client, message)
    # elif text == "🎯 Установка цели сна":
    #     set_sleep_goal(client, message)
    # elif text == "🥳 Ваше настроение":
    #     log_mood(client, message)
    # elif text == "🗃 Сохранить данные":
    #     export_data(client, message, user)
    elif text == "ℹ️ Информация":
        await message.reply_text("Это информация о боте.")
    elif text in {"← Вернуться", "🔙 Назад", "← Назад"}:
        await message.reply_text(
            "Вы вернулись назад. Выберите действие:",
            reply_markup=get_initial_keyboard()
        )
    else:
        # Если сообщение является ответом на ForceReply, обрабатываем его соответствующим образом
        if message.reply_to_message:

            if user_id not in user_states:
                await message.reply_text("Пожалуйста, используйте соответствующую команду для начала.",
                                         reply_markup=get_back_keyboard())
                await send_main_menu(client, user_id)
                return

            # Обработка ответов на запросы, например, set_reminder, save_reminder_time и т.д.
            if user_id in user_states and user_states[user.id] != UserStates.STATE_NONE:
                await message.reply_text("Пожалуйста, ответьте на предыдущий вопрос.", reply_markup=ForceReply())

                state = user_states[user_id]

                await user_state_navigate(state, client, message, user)
        else:
            if user.id in user_states and user_states[user.id] != UserStates.STATE_NONE:

                state = user_states[user_id]

                await user_state_navigate(state, client, message, user)

                # message.reply_text("Пожалуйста, ответьте на предыдущий вопрос.", reply_markup=ForceReply())
            # Неизвестная команда
            else:
                await message.reply_text(
                    "Пожалуйста, выберите действие из меню.",
                    reply_markup=get_initial_keyboard()
                )
    if text in {"😴 Сон", "🌅 Пробуждение", "📊 Статистика",
                "⏰ Установить напоминание", "🔕 Удалить напоминание",
                "📞 Отправить номер телефона", "📈 График сна", "💡 Совет по сну",
                "⭐️ Оценка сна", "🎯 Установка цели сна", "🥳 Ваше настроение",
                "🗃 Сохранить данные", "❌ Удалить мои данные", "⚙️ Меню", "← Вернуться", "🔙 Назад"}:
        await message.delete()

# Общий обработчик ответов на ForceReply
@app.on_message(filters.reply & filters.text)
async def handle_force_reply(client, message: Message):
    user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    if user_id not in user_states:
        await message.reply_text("Пожалуйста, используйте соответствующую команду для начала.",
                                 reply_markup=get_back_keyboard())
        await send_main_menu(client, user_id)
        return

    state = user_states[user_id]

    await user_state_navigate(state, client, message, user)


@app.on_message(filters.regex(r'^/'), group=1)
async def handle_command_text(client: Client, message: Message):
    await message.delete()


async def daily_weather_reminder():
    try:
        # Получаем всех пользователей и их города из базы данных
        users = execute_query("SELECT id, city_name FROM users").fetchall()

        for user in users:
            user_id, city = user
            weather = get_weather(city)
            if weather:
                advice = get_sleep_advice_based_on_weather(weather)
                response = (
                    f"Погода в {weather['city']}:\n"
                    f"Температура: {weather['temperature']}°C (ощущается как {weather['feels_like']}°C)\n"
                    f"Влажность: {weather['humidity']}%\n"
                    f"Погодные условия: {weather['weather_description']}\n"
                    f"Скорость ветра: {weather['wind_speed']} м/с\n\n"
                    f"Советы по улучшению сна:\n{advice}"
                )
                try:
                    await app.send_message(chat_id=user_id, text=response)
                except Exception as e:
                    logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка в функции daily_weather_reminder: {e}")

# Функция для расчета времени отхода ко сну
def calculate_bedtime(user_id):
    user = execute_query(
        'SELECT sleep_goal FROM users WHERE id = :user_id',
        {'user_id': user_id}).fetchone()
    reminder = execute_query(
        'SELECT reminder_time FROM reminders WHERE user_id = :user_id',
        {'user_id': user_id}).fetchone()
    if user and user['sleep_goal'] and reminder and reminder['reminder_time']:
        sleep_goal = user['sleep_goal']
        reminder_time = datetime.strptime(reminder['reminder_time'], "%H:%M").time()
        # Предположим, что пользователь хочет вставать в reminder_time
        wake_up_time = datetime.combine(datetime.now(), reminder_time)
        bedtime = wake_up_time - timedelta(hours=sleep_goal)
        return bedtime.time()
    else:
        return None


# Обновление функции отправки напоминаний
async def send_sleep_reminder():
    try:
        users = execute_query('SELECT user_id FROM reminders').fetchall()
        now = datetime.now()
        current_time = now.time()
        for user in users:
            user_id = user['user_id']
            sleep_record_count = execute_query('''
                        SELECT sleep_time FROM sleep_records 
                        WHERE user_id = :user_id AND sleep_time IS NOT NULL AND wake_time IS NULL
                    ''', {'user_id': user_id}).rowcount
            bedtime = calculate_bedtime(user_id)
            if (bedtime and current_time.hour == bedtime.hour
                    and current_time.minute == bedtime.minute
                    and not sleep_record_count):
                try:
                    await app.send_message(chat_id=user_id,
                                           text="🌙 Пора ложиться спать, чтобы достичь вашей цели "
                                                "по продолжительности сна на основе времени пробуждения!")
                    logger.info(f"Отправлено напоминание пользователю {user_id} на основе цели сна")
                except Exception as e:
                    logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка в функции send_sleep_reminder: {e}")


def calculate_wake_up_time(user_id):
    user = execute_query('SELECT sleep_goal FROM users WHERE id = :user_id',
                         {'user_id': user_id}).fetchone()
    sleep_record = execute_query('''
        SELECT sleep_time FROM sleep_records 
        WHERE user_id = :user_id AND wake_time IS NULL
        ''', {'user_id': user_id}).fetchone()
    if user and user['sleep_goal'] and sleep_record and sleep_record['sleep_time']:
        sleep_goal = user['sleep_goal']
        sleep_time_str = sleep_record['sleep_time']
        sleep_time = datetime.strptime(sleep_time_str[:-10], "%Y-%m-%dT%H:%M")
        # Преобразовываем в datetime и плюсуем желаемую цель сна
        sleep_datetime = datetime.combine(sleep_time, sleep_time.time())
        wake_up_time = sleep_datetime + timedelta(hours=sleep_goal)
        return wake_up_time.time()
    else:
        return None


async def send_wake_up_reminder():
    try:
        users = execute_query('SELECT user_id FROM reminders').fetchall()
        now = datetime.now()
        current_time = now.time()
        for user in users:
            user_id = user['user_id']
            wake_up_time = calculate_wake_up_time(user_id)
            if (wake_up_time and current_time.hour == wake_up_time.hour
                    and current_time.minute == wake_up_time.minute):
                try:
                    await app.send_message(chat_id=user_id,
                                           text="☀️ Пора вставать, чтобы достичь назначенных целей!")
                    logger.info(f"Отправлено напоминание пользователю {user_id} на основе цели сна")
                except Exception as e:
                    logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка в функции send_wake_up_reminder: {e}")


# Обработка необработанных сообщений
@app.on_message()
def handle_messages(client, message: Message):
    logger.info(f"Получено сообщение от пользователя {message.from_user.id}: {message.text}")


# Запуск бота
if __name__ == '__main__':
    # Инициализация и запуск планировщика напоминаний
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_sleep_reminder, CronTrigger(minute='*'))
    scheduler.add_job(send_wake_up_reminder,  CronTrigger(minute='*'))
    scheduler.add_job(daily_weather_reminder,  CronTrigger(hour=14, minute=4))
    scheduler.start()
    logger.info("Планировщик запущен")
    try:
        logger.info("Бот запускается...")
        app.run()
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}")
