from __future__ import annotations

import io
import logging
import random
from datetime import datetime
from uuid import uuid4

from matplotlib import pyplot as plt
from pyrogram import Client, filters
from pyrogram.types import Message, User, CallbackQuery, \
    InputTextMessageContent, InlineQueryResultArticle, \
    ReplyKeyboardRemove, InlineQuery
from pytz import timezone

from db import (
    get_has_provided_location, get_sleep_records_per_week,
    save_wake_time_records_db, save_sleep_time_records_db, get_wake_time_null
)
from db.db import get_user_time_zone_db
from handlers.data_management import delete_my_data, export_data, show_user_data_management_menu
from handlers.keyboards import (
    get_initial_keyboard, get_back_keyboard, main_menu_keyboard, get_request_keyboard
)
from handlers.reminders import set_reminder, remove_reminder, show_reminders_menu
from handlers.requests import save_contact, request_location, save_location, request_contact
from handlers.sleep_character.sleep_character import show_sleep_characteristics_menu
from handlers.sleep_character.sleep_mood import log_mood
from handlers.sleep_character.sleep_quality import rate_sleep
from handlers.sleep_character.user_sleep_goal import set_sleep_goal
from handlers.sleep_character.user_wake_time import set_wake_time
from handlers.states import UserStates, user_states
from handlers.user_valid import add_new_user, get_user_stats, is_valid_user, user_state_navigate, user_valid, \
    get_local_time, get_user_time_zone, process_user
from handlers.weather_advice import get_weather_advice

logger = logging.getLogger(__name__)


def setup_handlers(app: Client):
    """

    :param app: Client
    :return:
    """
    message_ids: list[int] = []

    @app.on_message(filters.command("start"))
    async def start(client: Client, message: Message):
        message_id = await start_handler(client, message)
        if message_id:
            message_ids.append(message_id)

    # Обработка нажатий кнопок
    @app.on_message(filters.text & ~filters.regex(r'^/'))
    async def handle_button_presses(client: Client, message: Message):
        message_id = await button_process_handler(client, message, message_ids)
        if message_id:
            message_ids.append(message_id)

    # Обработка нажатий кнопок
    @app.on_callback_query()
    async def handle_callback_query(client: Client, callback_query: CallbackQuery):
        message_id = await callback_query_handler(client, callback_query, message_ids)
        if message_id:
            [message_ids.append(msg_id) for msg_id in message_id] if isinstance(message_id, tuple) \
                else message_ids.append(message_id)

    @app.on_inline_query()
    async def answer_inline_query(client: Client, inline_query: InlineQuery):
        await answer_inline_query_handler(client, inline_query)

    # Общий обработчик ответов на ForceReply
    @app.on_message(filters.reply & filters.text)
    async def handle_force_reply(client, message: Message):
        message_id = await force_reply_handler(client, message)
        if message_id:
            message_ids.append(message_id)

    # Команда /sleep
    @app.on_message(filters.command("sleep"))
    async def sleep_handler(client: Client, message: Message, user: User = None):
        message_id = await sleep_time(client, message, user)
        if message_id:
            message_ids.append(message_id)

    # Команда /wake
    @app.on_message(filters.command("wake"))
    async def wake_time_handler(client: Client, message: Message, user: User = None):
        message_id = await wake_time(client, message, user)
        if message_id:
            message_ids.append(message_id)

    @app.on_message(filters.command("get_timezone"))
    async def get_time_handler(client: Client, message: Message, user: User = None):
        message_id = await get_timezone(client, message, user)
        if message_id:
            message_ids.append(message_id)

    # Команда /stats
    @app.on_message(filters.command("stats"))
    async def sleep_stats_handle(client: Client, message: Message, user: User = None):
        message_id = await sleep_stats(client, message, user)
        if message_id:
            message_ids.append(message_id)

    # Команда /remove_reminder
    @app.on_message(filters.command("remove_reminder"))
    async def remove_reminder_handler(client: Client, message: Message, user: User = None):
        message_id = await remove_reminder(client, message, user)
        if message_id:
            message_ids.append(message_id)

    # Команда /log_mood
    @app.on_message(filters.command("log_mood"))
    async def log_mood_handler(client: Client, message: Message, user: User = None):
        message_id = await log_mood(client, message, user)
        if message_id:
            message_ids.append(message_id)

    # Команда /set_sleep_goal
    @app.on_message(filters.command("set_sleep_goal"))
    async def set_sleep_goal_handler(client: Client, message: Message, user: User = None):
        message_id = await set_sleep_goal(client, message, user)
        if message_id:
            message_ids.append(message_id)

    # Команда /rate_sleep
    @app.on_message(filters.command("rate_sleep"))
    async def rate_sleep_handler(client: Client, message: Message, user: User = None):
        message_id = await rate_sleep(client, message, user)
        if message_id:
            message_ids.append(message_id)

    @app.on_message(filters.command("set_wake_time"))
    async def set_wake_time_handler(client: Client, message: Message, user: User = None):
        message_id = await set_wake_time(client, message, user)
        if message_id:
            message_ids.append(message_id)

    # Команда /set_reminder
    @app.on_message(filters.command("set_reminder"))
    async def set_reminder_handler(client: Client, message: Message, user: User = None):
        message_id = await set_reminder(client, message, user)
        if message_id:
            message_ids.append(message_id)

    # Команда /get_phone
    @app.on_message(filters.command("get_phone"))
    async def get_phone_handler(client: Client, message: Message):
        message_id = await request_contact(client, message)
        if message_id:
            message_ids.append(message_id)

    # Обработка контакта
    @app.on_message(filters.contact)
    async def save_contact_handler(client: Client, message: Message, user: User = None):
        message_id = await save_contact(client, message, user)
        if message_id:
            message_ids.append(message_id)

    # Функция для запроса локации у пользователя
    @app.on_message(filters.command("send_location"))
    async def send_location_handler(client: Client, message: Message):
        message_id = await request_location(client, message)
        if message_id:
            message_ids.append(message_id)

    @app.on_message(filters.location)
    async def handle_location(client: Client, message: Message):
        message_id = await save_location(client, message)
        if message_id:
            message_ids.append(message_id)

    @app.on_message(filters.command("weather_advice"))
    async def weather_advice_handler(client: Client, message: Message, user: User = None):
        message_id = await get_weather_advice(client, message, user)
        if message_id:
            message_ids.append(message_id)

    # Команда /sleep_tips
    @app.on_message(filters.command("sleep_tips"))
    async def sleep_tips_handler(client: Client, message: Message, user: User = None):
        message_id = await sleep_tips(client, message, user)
        if message_id:
            message_ids.append(message_id)

    # Команда /export_data
    @app.on_message(filters.command("export_data"))
    async def export_data_handler(client: Client, message: Message, user: User = None):
        message_id = await export_data(client, message, user)
        if message_id:
            message_ids.append(message_id)

    # Команда /delete_my_data
    @app.on_message(filters.command("delete_my_data"))
    async def delete_my_data_handler(client: Client, message: Message, user: User = None):
        message_id = await delete_my_data(client, message, user)
        if message_id:
            message_ids.append(message_id)

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


async def start_handler(client: Client, message: Message):
    user = message.from_user
    user_id = user.id
    result = None
    user_timezone = None
    user_time = None
    try:
        add_new_user(user)
        # Отправка приветственного сообщения с пользовательской клавиатурой
        result = get_has_provided_location(user_id)
        user_timezone_str = get_user_time_zone_db(user_id)['time_zone']
        if user_timezone_str is None:
            logger.debug(f"Пользователь {user_id} не предоставил локальное время.")
            user_timezone_str = get_user_time_zone(user_id)
            if user_timezone_str is not None:
                user_timezone = timezone(user_timezone_str)
                user_time = get_local_time(datetime.now(), user_id)

        else:
            user_timezone = timezone(user_timezone_str)
            user_time = get_local_time(datetime.now(), user_id)

    except Exception as e:
        logger.error(f"Ошибка при инициализации пользователя {user.id}: {e}")
    finally:
        if result is None or not result['has_provided_location'] or user_timezone is None:
            msg = await message.reply_text(
                "Пожалуйста, отправьте ваше местоположение, чтобы начать пользоваться ботом.",
                reply_markup=get_request_keyboard('location_only'))
        else:
            await message.reply_text(
                f"Привет, {user.first_name}!\nВы находитесь в "
                f"{user_timezone} локальное время "
                f"{user_time.strftime('%Y-%m-%d %H:%M:%S')}."
            )
            msg = await message.reply_text(
                "Вы уже предоставили свою локацию.\n\n👋 Привет! Я бот для отслеживания сна.\n\n"
                "Выберите действие из меню ниже:",
                reply_markup=get_initial_keyboard()
            )
            user_states[user_id] = UserStates.STATE_NONE
        return msg.id


async def button_process_handler(client: Client, message: Message, message_ids: list[int]):
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
        await remove_main_menu(client, message.chat.id)
        if message_ids:
            await client.delete_messages(message.chat.id, message_ids)
            message_ids.clear()
        msg = await message.reply_text(
            "Вы вернулись назад. Выберите действие:",
            reply_markup=main_menu_keyboard()
        )
        return msg.id
    else:
        # Если сообщение является ответом на ForceReply, обрабатываем его соответствующим образом
        if message.reply_to_message:

            logger.debug("ForceReply on button presses")

            if user_id not in user_states or user_states[user.id] == UserStates.STATE_NONE:

                await send_main_menu(client, user_id)
                # await message.reply_text("Пожалуйста, используйте соответствующую команду для начала.",
                #                          reply_markup=main_menu_keyboard())
                await message.delete()

            # Обработка ответов на запросы, например, set_reminder, save_reminder_time и т.д.
            elif user_id in user_states and user_states[user.id] != UserStates.STATE_NONE:
                state = user_states[user_id]

                message_id = await user_state_navigate(state, client, message, user)
                return message_id
        else:
            if user.id in user_states and user_states[user.id] != UserStates.STATE_NONE:

                state = user_states[user_id]

                message_id = await user_state_navigate(state, client, message, user)
                return message_ids.append(message_id)

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


async def callback_query_handler(client: Client, callback_query: CallbackQuery, message_ids: list[int]):
    user = callback_query.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

    message = callback_query.message
    data = callback_query.data

    if data == "sleep":
        message_id = await sleep_time(client, message, user)
        return message_id
    elif data == "wake":
        message_id = await wake_time(client, message, user)
        return message_id
    elif data == "stats":
        message_id = await sleep_stats(client, message, user)
        return message_id
    elif data == "sleep_chart":
        message_id = await sleep_chart(client, message, user)
        return message_id
    elif data == "reminders":
        message_id = await show_reminders_menu(client, message, user)
        return message_id
    elif data == "set_reminder":
        message_id = await set_reminder(client, message, user)
        return message_id
    elif data == "reset_reminder":
        message_id = await remove_reminder(client, message, user)
        return message_id
    elif data == "request_contact":
        return await request_contact(client, message)
    elif data == "sleep_goals":
        message_id = await set_sleep_goal(client, message, user)
        return message_id
    elif data == "sleep_characteristics":
        message_id = await show_sleep_characteristics_menu(client, user.id)
        return message_id
    elif data == "sleep_tips":
        message_id = await sleep_tips(client, message, user)
        return message_id
    elif data == "user_data_management":
        message_id = await show_user_data_management_menu(client, user.id)
        return message_id
    elif data == "rate_mood":
        message_id = await log_mood(client, message, user)
        return message_id
    elif data == "set_wake_time":
        message_id = await set_wake_time(client, message, user)
        return message_id
    elif data == "weather":
        message_id = await get_weather_advice(client, message, user)
        return message_id
    elif data == "rate_sleep":
        message_id = await rate_sleep(client, message, user)
        return message_id
    elif data == "delete_data":
        message_id = await delete_my_data(client, message, user)
        return message_id
    elif data == "save_data":
        message_id = await export_data(client, message, user)
        return message_id
    elif data == "back_to_menu":
        if message_ids:
            await client.delete_messages(message.chat.id, message_ids)

        await message.reply("Вы вернулись.", reply_markup=main_menu_keyboard())

        # await send_main_menu(client, message.chat.id)
    # Уведомляем Telegram, что колбэк обработан
    await message.edit_reply_markup(reply_markup=None)
    await message.delete()
    await callback_query.answer()


async def answer_inline_query_handler(client: Client, inline_query: InlineQuery):
    is_user, valid_id = await user_valid(None, inline_query.from_user)
    if is_user == 'False':
        return valid_id

    user_id = valid_id
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
            await inline_query.answer(result)
        else:
            await inline_query.answer([])
    else:
        await inline_query.answer([])

    logger.info(f"Пользователь {user_id} отправил Inline-query запрос: {query}")


async def force_reply_handler(client: Client, message: Message):
    user = message.from_user
    try:
        is_valid_user(user)
    except Exception as e:
        logger.error(f"Пользователь {user} не является валидным: {e}")
        return

    user_id = user.id
    if user_id not in user_states:
        await message.reply_text("Пожалуйста, используйте соответствующую команду для начала.",
                                 reply_markup=get_back_keyboard())
        await send_main_menu(client, user_id)
        return

    logger.debug("user_id in user_states")
    state = user_states[user_id]

    message_id = await user_state_navigate(state, client, message, user)
    return message_id


async def sleep_time(client: Client, message: Message, user: User = None):
    valid_id, user_timezone, sleep_time_dt = await process_user(message, user)
    if user_timezone is None:
        return valid_id

    user_id = valid_id

    try:

        if len(get_wake_time_null(user_id)) > 0:
            msg = await message.reply_text(
                "❗️ Запись о времени сна уже отмечена. "
                "Используйте /wake, для пробуждения.",
                reply_markup=get_back_keyboard()
            )
            logger.warning(
                f"Пользователь {user_id} попытался повторно отметить запись сна без записи пробуждения.")
            return msg.id

        save_sleep_time_records_db(user_id, sleep_time_dt)
        await message.reply_text(
            f"🌙 Время отхода ко сну отмечено: {sleep_time_dt.strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=get_back_keyboard()
        )
        logger.info(f"Пользователь {user_id} отметил время сна: {sleep_time_dt}")
    except Exception as e:
        logger.error(f"Ошибка при записи времени сна для пользователя {user_id}: {e}")
        msg = await message.reply_text(
            "Произошла ошибка при сохранении времени сна.",
            reply_markup=get_back_keyboard()
        )

        return msg.id


async def wake_time(client: Client, message: Message, user: User = None):
    valid_id, user_timezone, wake_time_dt = await process_user(message, user)
    if user_timezone is None:
        return valid_id

    user_id = valid_id

    try:
        if save_wake_time_records_db(user_id, wake_time_dt).rowcount == 0:
            msg = await message.reply_text(
                "❗️ Нет записи о времени сна или уже отмечено пробуждение. "
                "Используйте /sleep, чтобы начать новую запись.",
                reply_markup=get_back_keyboard()
            )
            logger.warning(f"Пользователь {user_id} попытался отметить пробуждение без активной записи сна.")
            return msg.id

        await message.reply_text(
            f"☀️ Время пробуждения отмечено: {wake_time_dt.strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=get_back_keyboard()
        )
        logger.info(f"Пользователь {user_id} отметил время пробуждения: {wake_time_dt}")
    except Exception as e:
        logger.error(f"Ошибка при записи времени пробуждения для пользователя {user_id}: {e}")
        msg = await message.reply_text(
            "Произошла ошибка при сохранении времени пробуждения.",
            reply_markup=get_back_keyboard()
        )

        return msg.id


async def get_timezone(client: Client, message: Message, user: User = None):
    is_user, valid_id = await user_valid(message, user)
    if is_user == 'False':
        return valid_id

    user_id = valid_id
    user_timezone = 'Europe/Moscow'
    message_time = message.date

    format = '%Y-%m-%d %H:%M:%S'
    local_time = get_local_time(message_time, user_id).strftime(format)
    server_time = datetime.now().strftime(format)
    if local_time:
        msg = await message.reply_text(
            f"🕒 Время вашего сообщения: {local_time}\nВремя чата: {message_time}\nВремя сервера: {server_time}",
            reply_markup=get_back_keyboard()
        )
    else:
        msg = await message.reply_text(
            f"❗️ Время вашего сообщения не найдено. "
            "Попробуйте еще раз.",
            reply_markup=get_back_keyboard()
        )
    return msg.id


async def sleep_stats(client: Client, message: Message, user: User = None):
    is_user, valid_id = await user_valid(message, user)
    if is_user == 'False':
        return valid_id

    user_id = valid_id
    try:
        response = get_user_stats(user_id)
        if response:
            await message.reply_text(
                response,
                reply_markup=get_back_keyboard()
            )
        else:
            msg = await message.reply_text(
                "У вас пока нет записей о сне.",
                reply_markup=get_back_keyboard()
            )
            return msg.id
    except Exception as e:
        logger.error(f"Ошибка при вызове функции get_user_stats: {e}")
        msg = await message.reply_text(
            "Произошла ошибка при получении статистики сна.",
            reply_markup=get_back_keyboard()
        )

        return msg.id


async def sleep_chart(client: Client, message: Message, user: User = None):
    is_user, valid_id = await user_valid(message, user)
    if is_user == 'False':
        return valid_id

    user_id = valid_id

    try:
        records = get_sleep_records_per_week(user_id)
        if records:
            durations = []
            dates = []
            for record in records:
                # sleep_time = datetime.fromisoformat(record['sleep_time'])
                # wake_time = datetime.fromisoformat(record['wake_time'])
                user_timezone_str = get_user_time_zone_db(user_id)['time_zone']
                if user_timezone_str:
                    user_timezone = timezone(user_timezone_str)
                else:
                    user_timezone = timezone('Europe/Moscow')
                sleep_time = record['sleep_time'].astimezone(user_timezone)
                wake_time = record['wake_time'].astimezone(user_timezone)
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
                                    reply_markup=get_back_keyboard())
            plt.close()
            logger.info(f"Пользователь {user_id} запросил график сна")
        else:
            msg = await message.reply_text(
                "У вас недостаточно записей для построения графика.",
                reply_markup=get_back_keyboard()
            )
            logger.info(f"Пользователь {user_id} запросил график сна, но записей недостаточно")
            return msg.id
    except Exception as e:
        logger.error(f"Ошибка при создании графика для пользователя {user_id}: {e}")
        msg = await message.reply_text(
            "Произошла ошибка при создании графика.",
            reply_markup=get_back_keyboard()
        )

        return msg.id


async def sleep_tips(client: Client, message: Message, user: User = None):
    is_user, valid_id = await user_valid(message, user)
    if is_user == 'False':
        return valid_id

    user_id = valid_id

    tips = []
    with open("configs/sleep_tips.txt", 'r') as st:
        while line := st.readline():
            tips.append(line)

    tip = random.choice(tips)
    await message.reply_text(
        f"💡 Совет для улучшения сна:\n\n{tip}",
        reply_markup=get_back_keyboard()
    )
    logger.info(f"Пользователь {user_id} запросил совет по сну")


async def remove_main_menu(client: Client, chat_id: int):
    sent_remove = await client.send_message(
        chat_id=chat_id,
        text="Вы успешно вышли из меню.",
        reply_markup=ReplyKeyboardRemove()
    )
    await sent_remove.delete()
    logger.info(f"Пользователь {chat_id} вышел из меню")


async def send_main_menu(client: Client, chat_id: int):
    await remove_main_menu(client, chat_id)
    await client.send_message(
        chat_id=chat_id,
        text="Выберите действие:",
        reply_markup=main_menu_keyboard()
    )


if __name__ == "__main__":
    pass
