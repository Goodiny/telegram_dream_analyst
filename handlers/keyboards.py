import logging

from pyrogram import Client
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, \
    ReplyKeyboardRemove, User, Message

from db.modify_tables import execute_query, get_reminder_time_db
from utils.utils import is_valid_user


logger = logging.getLogger(__name__)


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


def main_menu_keyboard():
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
            InlineKeyboardButton("🌦 Прогноз погоды", callback_data="weather"),
            InlineKeyboardButton("📝 Установить время пробуждения", callback_data="set_wake_time")
        ],
        [
            InlineKeyboardButton("👤 Управление данными", callback_data="user_data_management"),
            InlineKeyboardButton("📱 Отправка номера", callback_data="request_contact")
        ]
    ])
    return keyboard


def character_keyboard():
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("😊 Ваше настроение", callback_data="rate_mood")],
            [InlineKeyboardButton("🛌 Оценка сна", callback_data="rate_sleep")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
        ]
    )
    return keyboard


def data_management_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💾 Сохранение данных", callback_data="save_data")],
            [InlineKeyboardButton("🗑 Удаление данных", callback_data="delete_data")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
        ]
    )


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
    user_id = user.id

    try:
        reminders_record = get_reminder_time_db(user_id)
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


async def request_location(client: Client, message: Message):
    location_button = KeyboardButton("Отправить местоположение", request_location=True)
    reply_markup = ReplyKeyboardMarkup([[KeyboardButton('← Вернуться'), location_button]],
                                       resize_keyboard=True, one_time_keyboard=True)
    await message.reply_text("Пожалуйста, поделитесь своим местоположением, чтобы я мог определить ваш город.",
                             reply_markup=reply_markup)


if __name__ == "__main__":
    pass
