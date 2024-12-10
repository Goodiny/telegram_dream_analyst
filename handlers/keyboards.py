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


def get_reminder_menu_keyboard(has_reminder: bool = True):
    """
    :param has_reminder: bool
    :return: ReplyKeyboardMarkup | InlineKeyboardMarkup
    """
    if has_reminder:
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


def get_request_keyboard(context: str = None):
    """

    :param context: str
    :return: ReplyKeyboardMarkup | InlineKeyboardMarkup
    """
    if context is not None:
        context = context.lower()
        return_button = KeyboardButton("← Вернуться")
        return_inline_button = InlineKeyboardButton("← Вернуться", callback_data="back_to_menu")
        if context == "contact":
            contact_button = KeyboardButton(
                text="Отправить номер телефона",
                request_contact=True
            )
            reply_markup = ReplyKeyboardMarkup(
                [[return_button, contact_button]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        elif context == "location":
            location_button = KeyboardButton(
                text="Отправить местоположение",
                request_location=True
            )
            reply_markup = ReplyKeyboardMarkup(
                [[return_button, location_button]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        elif context == 'location_only':
            location_button = KeyboardButton(
                text="Отправить местоположение",
                request_location=True
            )
            reply_markup = ReplyKeyboardMarkup(
                [[location_button]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        elif context.lower() == "weather":
            reply_markup = InlineKeyboardMarkup([
                [return_inline_button,
                 InlineKeyboardButton("Получить совет по сну", callback_data="sleep_tips")]
            ])
        elif context == "get_weather":
            reply_markup = InlineKeyboardMarkup([
                [return_inline_button,
                 InlineKeyboardButton('🌤 Прогноз погоды', callback_data='weather')]

            ])
        elif context == "back":
            reply_markup = InlineKeyboardMarkup(
                [[return_inline_button]]
            )
        else:
            raise ValueError("Данного контекста в данной функции не предусмотренно, "
                             "введите правильный контекст")
    else:
        reply_markup = ReplyKeyboardMarkup(
            [[KeyboardButton("🔙 Назад")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

    return reply_markup


if __name__ == "__main__":
    pass
