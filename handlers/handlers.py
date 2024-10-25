import csv
import io
import logging
import os
import random

import re
import sqlite3
from datetime import datetime
from uuid import uuid4

from matplotlib import pyplot as plt
from pyrogram import Client, filters
from pyrogram.types import Message, User, ForceReply, CallbackQuery, InputTextMessageContent, InlineQueryResultArticle, \
    ReplyKeyboardRemove

from handlers.keyboards import get_initial_keyboard, get_back_keyboard, get_reminder_menu_keyboard, \
    data_management_keyboard, main_menu_keyboard, character_keyboard, get_request_keyboard
from utils.location_detect import get_city_from_coordinates
from db.modify_tables import save_user_city, get_user_stats, save_phone_number, \
    save_mood_db, save_wake_time_user_db, delete_all_data_user_db, save_reminder_time_db, save_sleep_quality_db, \
    save_sleep_goal_db, get_reminder_time_db, get_has_provided_location, add_user_to_db, get_city_name, \
    get_all_sleep_records, get_user_wake_time, delete_reminder_db, get_sleep_records_per_week, \
    save_wake_time_records_db, save_sleep_time_db, get_wake_time_null
from configs.states import UserStates, user_states
from utils.utils import is_valid_user
from utils.wether_tips import get_sleep_advice_based_on_weather, get_weather

logger = logging.getLogger(__name__)


async def user_state_navigate(state: UserStates, client: Client, message: Message, user: User = None):
    if user is None:
        return  # Игнорируем сообщения без информации о пользователе
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

    user_id = user.id

    if state == UserStates.STATE_WAITING_REMINDER_TIME:
        await save_reminder_time(client, message, user)
    elif state == UserStates.STATE_WAITING_SLEEP_QUALITY:
        await save_sleep_quality(client, message, user)
    elif state == UserStates.STATE_WAITING_SLEEP_GOAL:
        await save_sleep_goal(client, message, user)
    elif state == UserStates.STATE_WAITING_WAKE_TIME:
        await save_wake_time(client, message, user)
    elif state == UserStates.STATE_WAITING_SAVE_MOOD:
        await save_mood(client, message, user)
    elif state == UserStates.STATE_WAITING_CONFIRM_DELETE:
        await confirm_delete(client, message, user)
    else:
        await message.reply_text("Произошла ошибка. Пожалуйста, начните заново.",
                                 reply_markup=get_back_keyboard())
        user_states[user_id] = UserStates.STATE_NONE
    await message.delete()


def add_new_user(user: User):
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

    try:
        # Вставляем или обновляем информацию о пользователе в таблицу users
        add_user_to_db(user_id, username, first_name, last_name, has_provided_location=0)
        logger.info(f"Пользователь {user_id} добавлен или обновлен в таблице users")
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя {user_id} в базу данных: {e}")


def setup_handlers(app: Client):
    @app.on_message(filters.command("start"))
    async def start(client: Client, message: Message):
        user = message.from_user
        try:
            add_new_user(user)
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

    # Обработка нажатий кнопок
    @app.on_message(filters.text & ~filters.regex(r'^/'))
    async def handle_button_presses(client, message: Message):
        user = message.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
            return

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

                if user_id not in user_states or user_states[user.id] == UserStates.STATE_NONE:
                    logger.debug("Message_Reply without UserStates")
                    await message.reply_text("Пожалуйста, используйте соответствующую команду для начала.",
                                             reply_markup=get_back_keyboard())
                    await message.delete()
                    await send_main_menu(client, user_id)
                    return

                # Обработка ответов на запросы, например, set_reminder, save_reminder_time и т.д.
                elif user_id in user_states and user_states[user.id] != UserStates.STATE_NONE:
                    logger.debug("Message_Reply on UserStates")
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

    # Обработка нажатий кнопок
    @app.on_callback_query()
    async def handle_callback_query(client: Client, callback_query: CallbackQuery):
        user = callback_query.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
            return

        message = callback_query.message
        data = callback_query.data
        if data == "sleep":
            # Вызываем функцию sleep_time
            await sleep_time(client, message, user)
        elif data == "wake":
            # Вызываем функцию wake_time
            await wake_time(client, message, user)
        elif data == "stats":
            # Вызываем функцию sleep_stats
            await sleep_stats(client, message, user)
        elif data == "reminders":
            await show_reminders_menu(client, message, user)
        elif data == "set_reminder":
            await set_reminder(client, message, user)
        elif data == "reset_reminder":
            await remove_reminder(client, message, user)
        elif data == "request_contact":
            await request_contact(client, message)
        elif data == "sleep_chart":
            await sleep_chart(client, message, user)
        elif data == "sleep_goals":
            await set_sleep_goal(client, message, user)
        elif data == "sleep_characteristics":
            await show_sleep_characteristics_menu(client, user.id)
        elif data == "sleep_tips":
            await sleep_tips(client, message, user)
        elif data == "user_data_management":
            await show_user_data_management_menu(client, user.id)
        elif data == "rate_mood":
            await log_mood(client, message, user)
        elif data == "set_wake_time":
            await set_wake_time(client, message, user)
        elif data == "weather":
            await weather_advice(client, message, user)
        elif data == "rate_sleep":
            await rate_sleep(client, message, user)
        elif data == "delete_data":
            await delete_my_data(client, message, user)
        elif data == "save_data":
            await export_data(client, message, user)
        elif data == "back_to_menu":
            await callback_query.message.reply_text("Вы вернулись.",
                                                    reply_markup=get_initial_keyboard())
            await send_main_menu(client, message.chat.id)
        # Уведомляем Telegram, что колбэк обработан
        await message.edit_reply_markup(reply_markup=None)
        await callback_query.answer()

    @app.on_inline_query()
    async def answer_inline_query(client, inline_query):
        user = inline_query.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
            return

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

    # Общий обработчик ответов на ForceReply
    @app.on_message(filters.reply & filters.text)
    async def handle_force_reply(client, message: Message):
        user = message.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
            return

        logger.debug("Handle_Force_Reply")
        user_id = user.id
        if user_id not in user_states:
            await message.reply_text("Пожалуйста, используйте соответствующую команду для начала.",
                                     reply_markup=get_back_keyboard())
            await send_main_menu(client, user_id)
            return

        logger.debug("user_id in user_states")
        state = user_states[user_id]

        await user_state_navigate(state, client, message, user)

    # Команда /sleep
    @app.on_message(filters.command("sleep"))
    async def sleep_handler(client: Client, message: Message, user: User = None):
        await sleep_time(client, message, user)

    # Команда /wake
    @app.on_message(filters.command("wake"))
    async def wake_time_handler(client: Client, message: Message, user: User = None):
        await wake_time(client, message, user)

    # Команда /stats
    @app.on_message(filters.command("stats"))
    async def sleep_stats_handle(client: Client, message: Message, user: User = None):
        await sleep_stats(client, message, user)

    # Команда /remove_reminder
    @app.on_message(filters.command("remove_reminder"))
    async def remove_reminder_handler(client: Client, message: Message, user: User = None):
        await remove_reminder(client, message, user)

    # Команда /log_mood
    @app.on_message(filters.command("log_mood"))
    async def log_mood_handler(client: Client, message: Message, user: User = None):
        await log_mood(client, message, user)

    # Команда /set_sleep_goal
    @app.on_message(filters.command("set_sleep_goal"))
    async def set_sleep_goal_handler(client: Client, message: Message, user: User = None):
        await set_sleep_goal(client, message, user)

    # Команда /rate_sleep
    @app.on_message(filters.command("rate_sleep"))
    async def rate_sleep_hanlder(client: Client, message: Message, user: User = None):
        await rate_sleep(client, message, user)

    @app.on_message(filters.command("set_wake_time"))
    async def set_wake_time_handler(client: Client, message: Message, user: User = None):
        await set_wake_time(client, message, user)

    # Команда /set_reminder
    @app.on_message(filters.command("set_reminder"))
    async def set_reminder_handler(client: Client, message: Message, user: User = None):
        await set_reminder(client, message, user)

    # Команда /get_phone
    @app.on_message(filters.command("get_phone"))
    async def get_phone_handler(client: Client, messsage: Message):
        await request_contact(client, messsage)

    # Обработка контакта
    @app.on_message(filters.contact)
    async def save_contact(client: Client, message: Message, user: User = None):
        if user is None:
            user = message.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
            return

        add_new_user(user)
        user_id = user.id
        contact = message.contact
        phone_number = contact.phone_number
        contact_user_id = contact.user_id  # ID пользователя, который отправил контакт

        if contact_user_id == user_id:
            # Сохранение номера телефона в базе данных
            try:
                save_phone_number(user_id, phone_number)
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
    async def send_location_handler(client: Client, message: Message):
        await request_location(client, message)

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
    async def weather_advice_handler(client: Client, message: Message, user: User = None):
        await weather_advice(client, message, user)

    # Команда /sleep_chart
    @app.on_message(filters.command("sleep_chart"))
    async def sleep_chart_handler(client: Client, message: Message, user: User = None):
        await sleep_chart()

    # Команда /sleep_tips
    @app.on_message(filters.command("sleep_tips"))
    async def sleep_tips_handler(client: Client, message: Message, user: User = None):
        await sleep_tips(client, message, user)

    # Команда /export_data
    @app.on_message(filters.command("export_data"))
    async def export_data_handler(client: Client, message: Message, user: User = None):
        await export_data(client, message, user)

    # Команда /delete_my_data
    @app.on_message(filters.command("delete_my_data"))
    async def delete_my_data_handler(client: Client, message: Message, user: User = None):
        await delete_my_data(client, message, user)

    # Команда /menu
    @app.on_message(filters.command("menu"))
    async def send_main_menu_handler(client: Client, chat_id: int):
        await send_main_menu(client, chat_id)

    # Удаление всех команд
    @app.on_message(filters.regex(r'^/'), group=1)
    async def handle_command_text(client: Client, message: Message):
        await message.delete()

    # Обработка необработанных сообщений
    @app.on_message()
    def handle_messages(client, message: Message):
        logger.info(f"Получено сообщение от пользователя {message.from_user.id}: {message.text}")


async def sleep_time(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
        add_new_user(user)
    except ValueError as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

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
        return

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
        return

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
            return

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
        return

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
        return

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
        return

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
        return

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
        return

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
        return

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
        return

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
        return

    user_id = user.id
    user_states[user_id] = UserStates.STATE_WAITING_CONFIRM_DELETE
    await message.reply_text(
        "Вы уверены, что хотите удалить все свои данные? Это действие необратимо. Напишите 'Да' для подтверждения.",
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


async def send_main_menu(client: Client, chat_id: int):
    await client.send_message(
        chat_id=chat_id,
        text='Главное меню.',
        reply_markup=ReplyKeyboardRemove()
    )
    await client.send_message(
        chat_id=chat_id,
        text="Выберите действие:",
        reply_markup=main_menu_keyboard()
    )


async def show_sleep_characteristics_menu(client: Client, user_id: int):
    await client.send_message(
        chat_id=user_id,
        text="Выберите характеристику сна:",
        reply_markup=character_keyboard()
    )


async def show_user_data_management_menu(client: Client, user_id: int):
    await client.send_message(
        chat_id=user_id,
        text="Управление данными пользователя:",
        reply_markup=data_management_keyboard()
    )


async def show_reminders_menu(client: Client, message: Message, user: User = None):
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
        await message.reply_text(text, reply_markup=ReplyKeyboardRemove())
        await client.send_message(
            chat_id=user_id,
            text="Что вы хотите сделать?",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f'При получении данных от пользователя {user_id} произошла ошибка: {e}')
        await message.reply_text("Произошла ошибка при получении данных, попробуйте ещё раз или вернитесь назад")


async def request_contact(client: Client, message: Message):
    await message.reply_text(
        "Пожалуйста, поделитесь своим номером телефона, нажав на кнопку ниже.",
        reply_markup=get_request_keyboard("contact")
    )


async def request_location(client: Client, message: Message):
    await message.reply_text("Пожалуйста, поделитесь своим местоположением, чтобы я мог определить ваш город.",
                             reply_markup=get_request_keyboard("location"))


def requires_location(func):
    async def wrapper(client: Client, message: Message, user: User = None):
        if user is None:
            user = message.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
            return

        user_id = user.id
        try:
            result = get_has_provided_location(user_id)
        except Exception as e:
            logger.error(f"Ошибка при вызове функции get_has_provided_location пользователя {user_id}: {e}")
            return

        if result is None:
            try:
                add_new_user(user)
            except Exception as e:
                logger.error(f"Ошибка при вызове функции add_new_user пользователя {user_id}: {e}")
                return
            result = {'has_provided_location': 0}

        has_provided_location = result['has_provided_location']
        if not has_provided_location:
            try:
                await message.reply_text("Пожалуйста, отправьте ваше местоположение, прежде чем продолжить.",
                                         reply_markup=get_request_keyboard('location'))
                return
            except Exception as e:
                logger.warning(f"Ошибка при вызове метода message_reply пользователя {user_id}: {e}")
                await message.reply("Пожалуйста, отправьте ваше местоположение, прежде чем продолжить.",
                                    reply_markup=get_request_keyboard('location'))
                return
        return await func(client, message, user)
    return wrapper


@requires_location
async def weather_advice(client: Client, message: Message, user: User = None):
    if user is None:
        user = message.from_user
    try:
        is_valid_user(user)
        add_new_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

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
            keyboard = get_request_keyboard("weather")
        else:
            response = "Извините, не удалось получить данные о погоде. Попробуйте позже."
            keyboard = get_request_keyboard()

        await message.reply_text(response, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка при запросе имени города пользователя {user_id}: {e}")
        await message.reply_text("Произошла ошибка при запросе данных о городе, попробуйте ещё раз",
                                 reply_markup=get_request_keyboard("location")
                                 )


async def save_wake_time(client: Client, message: Message, user: User = None):
    if message.reply_to_message or message.text:
        if user is None:
            user = message.from_user
        try:
            is_valid_user(user)
            add_new_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
            return

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

        try:
            wake_time = datetime.strptime(wake_time_str, "%H:%M").time()
            # Сохранение времени напоминания в базе данных
            save_wake_time_user_db(user_id, wake_time_str)
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


# Обработка ответа с целью сна
async def save_sleep_goal(client: Client, message: Message, user: User = None):
    if message.reply_to_message or message.text:
        if user is None:
            user = message.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
            return

        add_new_user(user)
        user_id = user.id
        goal = float(message.text.strip())

        try:
            if 0 < goal <= 24:
                save_sleep_goal_db(user_id, goal)
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


# Обработка ответа с временем напоминания
async def save_reminder_time(client: Client, message: Message, user: User = None):
    if message.reply_to_message:
        if user is None:
            user = message.from_user
        try:
            is_valid_user(user)
        except Exception as e:
            logger.error(f"Пользователь {user} не является валидным: {e}")
            return

        add_new_user(user)
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

        try:
            reminder_time = datetime.strptime(reminder_time_str, "%H:%M").time()
            # Сохранение времени напоминания в базе данных
            save_reminder_time_db(user_id, reminder_time_str)
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

if __name__ == "__main__":
    pass
