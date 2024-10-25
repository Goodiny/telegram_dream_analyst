import logging

from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


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


def get_reminder_menu_keyboard(set_reminder: bool = True):
    if set_reminder:
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
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏰ Установить напоминание", callback_data="set_reminder"),
            ],
            [
                InlineKeyboardButton("← Назад", callback_data="back_to_menu")
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


def get_request_keyboard(contex: str):
    if contex.lower() not in {"contact", "location", "weather"}:
        raise ValueError("Данного контекста в данной функции не предусмотренно, "
                         "введите правильный контекст")

    return_button = KeyboardButton("← Вернуться")
    if contex.lower() == "contact":
        contact_button = KeyboardButton(
            text="Отправить номер телефона",
            request_contact=True
        )
        reply_markup = ReplyKeyboardMarkup(
            [[return_button, contact_button]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    elif contex.lower() == "location":
        location_button = KeyboardButton(
            text="Отправить местоположение",
            request_location=True
        )
        reply_markup = ReplyKeyboardMarkup(
            [[return_button, location_button]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    elif contex.lower() == "weather":
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("← Назад", callback_data="back_to_menu"),
             InlineKeyboardButton("Получить совет по сну", callback_data="sleep_tips")]
        ])
    else:
        reply_markup = ReplyKeyboardMarkup([[KeyboardButton("🔙 Назад")]],
                            resize_keyboard=True,
                            one_time_keyboard=True)

    return reply_markup


if __name__ == "__main__":
    pass
