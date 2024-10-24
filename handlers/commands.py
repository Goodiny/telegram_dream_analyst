import csv
import io
import logging
import os
import random
import sqlite3
from datetime import datetime

from matplotlib import pyplot as plt
from pyrogram import Client
from pyrogram.types import User, Message, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, \
    KeyboardButton

from configs.states import UserStates, user_states
from db.modify_tables import execute_query, add_user_to_db, get_user_stats, get_all_sleep_records, get_city_name, \
    delete_reminder_db, get_sleep_records_per_week, save_wake_time_records_db, get_wake_time_null, save_sleep_time_db, \
    get_user_wake_time
from handlers.keyboards import get_initial_keyboard, request_location
from utils.utils import is_valid_user
from utils.wether_tips import get_sleep_advice_based_on_weather, get_weather

logger = logging.getLogger(__name__)


async def sleep_time(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
        add_user_to_db(user)
    except ValueError as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")

    user_id = user.id
    sleep_time_dt = datetime.now()

    try:

        if len(get_wake_time_null(user_id)) > 0:
            await message.reply_text(
                "❗️ Запись о времени сна уже отмечена. "
                "Используйте /wake, для пробуждения.",
                reply_markup=get_initial_keyboard()
            )
            logger.warning(
                f"Пользователь {user_id} попытался повторно отметить запись сна без записи пробуждения.")
            return

        save_sleep_time_db(user_id, sleep_time_dt.isoformat())
        await message.reply_text(
            f"🌙 Время отхода ко сну отмечено: {sleep_time_dt.strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=get_initial_keyboard()
        )
        logger.info(f"Пользователь {user_id} отметил время сна: {sleep_time_dt}")
    except Exception as e:
        logger.error(f"Ошибка при записи времени сна для пользователя {user_id}: {e}")
        await message.reply_text(
            "Произошла ошибка при сохранении времени сна.",
            reply_markup=get_initial_keyboard()
        )


async def wake_time(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")

    user_id = user.id
    wake_time = datetime.now()

    try:

        if save_wake_time_records_db(user_id, wake_time.isoformat()).rowcount == 0:
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


async def sleep_chart(client: Client, message: Message, user: User = None):
        if user is None:
            user = message.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")

        user_id = user.id

        try:
            records = get_sleep_records_per_week(user_id)
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


async def remove_reminder(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")

    user_id = user.id

    try:
        delete_reminder_db(user_id)
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


async def sleep_tips(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id

    tips = []
    with open("configs/sleep_tips.txt", 'r') as st:
        while line := st.readline():
            tips.append(line)

    tip = random.choice(tips)
    await message.reply_text(
        f"💡 Совет для улучшения сна:\n\n{tip}",
        reply_markup=get_initial_keyboard()
    )
    logger.info(f"Пользователь {user_id} запросил совет по сну")


async def set_wake_time(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
    user_id = user.id
    user_states[user_id] = UserStates.STATE_WAITING_WAKE_TIME
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

        await message.reply_text(
        response,
        reply_markup=ForceReply()
        )
    except Exception as e:
        logger.error(f"Произошла ошибка при попытке пользователя {user_id} "
                     f"установить отложенное время пробуждения: {e}")


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
        user_city_name_record = get_city_name(user_id)
        if user_city_name_record:
            user_city = user_city_name_record["city_name"]
        else:
            user_city = "Moscow"  # Здесь можно использовать город пользователя или запросить его

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
                [InlineKeyboardButton("← Назад", callback_data="back_to_menu"), InlineKeyboardButton("Получить совет по сну", callback_data="sleep_tips")]
            ])
        else:
            response = "Извините, не удалось получить данные о погоде. Попробуйте позже."
            keyboard = ReplyKeyboardMarkup([[KeyboardButton("🔙 Назад")]])

        await message.reply_text(response, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка при запросе имени города пользователя {user_id}: {e}")
        await message.reply_text("Произошла ошибка при запросе данных о городе, попробуйте ещё раз",
                                 reply_markup=request_location(client, message)
                                 )


async def export_data(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
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


if __name__ == "__main__":
    pass
