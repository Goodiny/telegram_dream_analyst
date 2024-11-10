from __future__ import annotations

import io
import logging
import random

from datetime import datetime
from uuid import uuid4

from matplotlib import pyplot as plt
from pyrogram import Client, filters
from pyrogram.types import Message, User, ForceReply, CallbackQuery, \
    InputTextMessageContent, InlineQueryResultArticle, \
    ReplyKeyboardRemove


from handlers.requests import save_contact, request_location, save_location, request_contact
from handlers.sleep_character.sleep_character import show_sleep_characteristics_menu
from handlers.sleep_character.sleep_quality import rate_sleep
from handlers.sleep_character.user_sleep_goal import set_sleep_goal
from handlers.sleep_character.user_wake_time import set_wake_time
from handlers.weather_advice import get_weather_advice
from handlers.data_management import delete_my_data, export_data, show_user_data_management_menu
from handlers.keyboards import (
    get_initial_keyboard, get_back_keyboard, main_menu_keyboard, get_request_keyboard
)

from handlers.reminders import set_reminder, remove_reminder, show_reminders_menu

from handlers.sleep_character.sleep_mood import log_mood
from handlers.states import UserStates, user_states
from handlers.user_valid import add_new_user, get_user_stats, is_valid_user, user_state_navigate

from db import (
    get_has_provided_location, get_sleep_records_per_week,
    save_wake_time_records_db, save_sleep_time_records_db, get_wake_time_null
)


logger = logging.getLogger(__name__)


def setup_handlers(app: Client):
    """

    :param app: Client
    :return:
    """
    message_ids: list[int] = []

    @app.on_message(filters.command("start"))
    async def start(client: Client, message: Message):
        user = message.from_user
        result = None
        try:
            add_new_user(user)
            # Отправка приветственного сообщения с пользовательской клавиатурой
            result = get_has_provided_location(user.id)
        except Exception as e:
            logger.error(f"Ошибка при инициализации пользователя {user.id}: {e}")
        finally:
            if result is None or not result['has_provided_location']:
                await message.reply_text(
                    "Пожалуйста, отправьте ваше местоположение, чтобы начать пользоваться ботом.",
                    reply_markup=get_request_keyboard('location_only'))
            else:
                await message.reply_text(
                    "Вы уже предоставили свою локацию.\n\n👋 Привет! Я бот для отслеживания сна.\n\n"
                    "Выберите действие из меню ниже:",
                    reply_markup=get_initial_keyboard()
                )

    # Обработка нажатий кнопок
    @app.on_message(filters.text & ~filters.regex(r'^/'))
    async def handle_button_presses(client: Client, message: Message):
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
            if message_ids:
                await client.delete_messages(message.chat.id, message_ids)
            await remove_main_menu(client, message.chat.id)
            await message.reply_text(
                "Вы вернулись назад. Выберите действие:",
                reply_markup=main_menu_keyboard()
            )
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

                    await user_state_navigate(state, client, message, user)
            else:
                if user.id in user_states and user_states[user.id] != UserStates.STATE_NONE:

                    state = user_states[user_id]

                    await user_state_navigate(state, client, message, user)

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

        await message.delete()

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
            message_ids.append(await show_reminders_menu(client, message, user))
        elif data == "set_reminder":
            message_ids.append(await set_reminder(client, message, user))
        elif data == "reset_reminder":
            message_ids.append(await remove_reminder(client, message, user))
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
            await get_weather_advice(client, message, user)
        elif data == "rate_sleep":
            await rate_sleep(client, message, user)
        elif data == "delete_data":
            await delete_my_data(client, message, user)
        elif data == "save_data":
            await export_data(client, message, user)
        elif data == "back_to_menu":
            if message_ids:
                await client.delete_messages(message.chat.id, message_ids)

            await message.reply("Вы вернулись.", reply_markup=main_menu_keyboard())

            # await send_main_menu(client, message.chat.id)
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
    async def rate_sleep_handler(client: Client, message: Message, user: User = None):
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
    async def get_phone_handler(client: Client, message: Message):
        await request_contact(client, message)

    # Обработка контакта
    @app.on_message(filters.contact)
    async def save_contact_handler(client: Client, message: Message, user: User = None):
        await save_contact(client, message, user)

    # Функция для запроса локации у пользователя
    @app.on_message(filters.command("send_location"))
    async def send_location_handler(client: Client, message: Message, user: User = None):
        await request_location(client, message)

    @app.on_message(filters.location)
    async def handle_location(client: Client, message: Message):
        await save_location(client, message)

    @app.on_message(filters.command("weather_advice"))
    async def weather_advice_handler(client: Client, message: Message, user: User = None):
        await get_weather_advice(client, message, user)

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
                reply_markup=get_back_keyboard()
            )
            logger.warning(
                f"Пользователь {user_id} попытался повторно отметить запись сна без записи пробуждения.")
            return

        save_sleep_time_records_db(user_id, sleep_time_dt.isoformat(sep=' '))
        await message.reply_text(
            f"🌙 Время отхода ко сну отмечено: {sleep_time_dt.strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=get_back_keyboard()
        )
        logger.info(f"Пользователь {user_id} отметил время сна: {sleep_time_dt}")
    except Exception as e:
        logger.error(f"Ошибка при записи времени сна для пользователя {user_id}: {e}")
        await message.reply_text(
            "Произошла ошибка при сохранении времени сна.",
            reply_markup=get_back_keyboard()
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

        if save_wake_time_records_db(user_id, wake_time.isoformat(sep=' ')).rowcount == 0:
            await message.reply_text(
                "❗️ Нет записи о времени сна или уже отмечено пробуждение. "
                "Используйте /sleep, чтобы начать новую запись.",
                reply_markup=get_back_keyboard()
            )
            logger.warning(f"Пользователь {user_id} попытался отметить пробуждение без активной записи сна.")
            return
        await message.reply_text(
            f"☀️ Время пробуждения отмечено: {wake_time.strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=get_back_keyboard()
        )
        logger.info(f"Пользователь {user_id} отметил время пробуждения: {wake_time}")
    except Exception as e:
        logger.error(f"Ошибка при записи времени пробуждения для пользователя {user_id}: {e}")
        await message.reply_text(
            "Произошла ошибка при сохранении времени пробуждения.",
            reply_markup=get_back_keyboard()
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
                reply_markup=get_back_keyboard()
            )
        else:
            await message.reply_text(
                "У вас пока нет записей о сне.",
                reply_markup=get_back_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка при вызове функции get_user_stats: {e}")
        await message.reply_text(
            "Произошла ошибка при получении статистики сна.",
            reply_markup=get_back_keyboard()
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
                                        reply_markup=get_back_keyboard())
                plt.close()
                logger.info(f"Пользователь {user_id} запросил график сна")
            else:
                await message.reply_text(
                    "У вас недостаточно записей для построения графика.",
                    reply_markup=get_back_keyboard()
                )
                logger.info(f"Пользователь {user_id} запросил график сна, но записей недостаточно")
        except Exception as e:
            logger.error(f"Ошибка при создании графика для пользователя {user_id}: {e}")
            await message.reply_text(
                "Произошла ошибка при создании графика.",
                reply_markup=get_back_keyboard()
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
