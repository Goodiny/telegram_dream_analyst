import pytest
from unittest.mock import AsyncMock, patch
from handlers.handlers import button_process_handler
from pyrogram.types import Message, User
from handlers.user_valid import is_valid_user
from handlers.handlers import send_main_menu, remove_main_menu, main_menu_keyboard

@pytest.mark.asyncio
@patch("handlers.handlers.send_main_menu")
@patch("handlers.handlers.remove_main_menu")
@patch("handlers.user_valid.is_valid_user")
async def test_button_process_handler_menu(mock_is_valid_user, mock_remove_main_menu, mock_send_main_menu):
    mock_client = AsyncMock()
    mock_message = AsyncMock()
    mock_message.from_user = User(id=12345, first_name="TestUser", is_bot=False)
    mock_message.text = "\u2699\ufe0f \u041c\u0435\u043d\u044e"
    mock_message.chat.id = 12345

    # Mock user validation
    mock_is_valid_user.return_value = True

    await button_process_handler(mock_client, mock_message, [])

    # Проверяем вызов send_main_menu
    mock_send_main_menu.assert_awaited_once_with(mock_client, 12345)


@pytest.mark.asyncio
@patch("handlers.handlers.main_menu_keyboard")
@patch("handlers.handlers.remove_main_menu")
@patch("handlers.user_valid.is_valid_user")
async def test_button_process_handler_back(mock_is_valid_user, mock_remove_main_menu, mock_main_menu_keyboard):
    mock_client = AsyncMock()
    mock_message = AsyncMock()
    mock_message.from_user = User(id=12345, first_name="TestUser", is_bot=False)
    mock_message.text = "\u2190 \u0412\u0435\u0440\u043d\u0443\u0442\u044c\u0441\u044f"
    mock_message.chat.id = 12345

    # Mock user validation
    mock_is_valid_user.return_value = True

    # Mock main menu keyboard
    mock_main_menu_keyboard.return_value = "MockKeyboard"

    message_ids = [1, 2, 3]

    await button_process_handler(mock_client, mock_message, message_ids)

    # Проверяем вызов remove_main_menu
    mock_remove_main_menu.assert_awaited_once_with(mock_client, 12345)

    # Проверяем удаление сообщений
    # Проверка вызова delete_messages
    try:
        mock_client.delete_messages.assert_awaited_once_with(12345, [1, 2, 3])
    except AssertionError as e:
        print(f"message_ids на момент вызова delete_messages: {message_ids}")
        raise e

    # Проверка, что message_ids был очищен
    assert message_ids == []

    # Проверяем отправку сообщения с меню
    mock_message.reply_text.assert_awaited_once_with(
        "Вы вернулись назад. Выберите действие:", reply_markup="MockKeyboard"
    )


@pytest.mark.asyncio
@patch("handlers.handlers.get_initial_keyboard")
@patch("handlers.user_valid.is_valid_user")
async def test_button_process_handler_unknown_command(mock_is_valid_user, mock_get_initial_keyboard):
    mock_client = AsyncMock()
    mock_message = AsyncMock()
    mock_message.from_user = User(id=12345, first_name="TestUser", is_bot=False)
    mock_message.text = "Неизвестная команда"
    mock_message.chat.id = 12345
    mock_message.reply_to_message = None  # Убедимся, что это не ForceReply

    # Mock user validation
    mock_is_valid_user.return_value = True

    # Mock initial keyboard
    mock_get_initial_keyboard.return_value = "MockKeyboard"

    mock_message.reply_text = AsyncMock()

    await button_process_handler(mock_client, mock_message, [])

    # Проверяем, что reply_text был вызван
    try:
        mock_message.reply_text.assert_awaited_once_with(
            "Пожалуйста, выберите действие из меню.",
            reply_markup="MockKeyboard"
        )
    except AssertionError as e:
        print(f"mock_message.reply_text.await_args_list: {mock_message.reply_text.await_args_list}")
        raise e


@pytest.mark.asyncio
@patch("handlers.user_valid.is_valid_user", side_effect=Exception("Invalid user"))
async def test_button_process_handler_invalid_user(mock_is_valid_user):
    mock_client = AsyncMock()
    mock_message = AsyncMock()
    mock_message.from_user = User(id=12345, first_name="TestUser", is_bot=False)
    mock_message.text = "\u041d\u0435\u0432\u0430\u043b\u0438\u0434\u043d\u044b\u0439 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c"

    await button_process_handler(mock_client, mock_message, [])

    # Проверяем, что сообщение отправлено не было
    mock_message.reply_text.assert_not_awaited()
    mock_client.delete_messages.assert_not_awaited()
