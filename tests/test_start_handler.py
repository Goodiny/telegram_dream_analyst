from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from handlers.handlers import start_handler
from handlers.keyboards import get_request_keyboard, get_initial_keyboard


@pytest.mark.asyncio
async def test_start_handler_user_without_location():
    mock_client = AsyncMock()
    mock_message = AsyncMock()
    mock_message.from_user.id = 12345
    mock_message.from_user.first_name = "Женя"

    # Настраиваем mock для reply_text
    mock_message.reply_text.return_value = AsyncMock(id=42)  # Устанавливаем id как число

    # Замокируем зависимости
    with patch("handlers.handlers.add_new_user") as mock_add_new_user, \
         patch("handlers.handlers.get_has_provided_location", return_value=None) as mock_get_has_location, \
         patch("handlers.handlers.get_user_time_zone_db", return_value={"time_zone": None}) as mock_get_time_zone_db, \
         patch("handlers.handlers.get_user_time_zone", return_value="UTC") as mock_get_user_time_zone, \
         patch("handlers.handlers.get_local_time", return_value=datetime(2024, 11, 10, 10, 0, 0)) as mock_get_local_time, \
         patch("handlers.handlers.logger") as mock_logger:

        # Вызов функции
        msg_id = await start_handler(mock_client, mock_message)

        # Проверяем вызовы функций
        mock_add_new_user.assert_called_once_with(mock_message.from_user)
        mock_get_has_location.assert_called_once_with(12345)
        mock_get_time_zone_db.assert_called_once_with(12345)
        mock_get_user_time_zone.assert_called_once_with(12345)
        mock_get_local_time.assert_called_once()

        # Проверяем отправку сообщения с запросом локации
        mock_message.reply_text.assert_any_call(
            "Пожалуйста, отправьте ваше местоположение, чтобы начать пользоваться ботом.",
            reply_markup=get_request_keyboard('location_only')
        )

        # Убедимся, что msg_id корректно возвращается
        assert isinstance(msg_id, int)
        assert msg_id == 42

@pytest.mark.asyncio
async def test_start_handler_user_with_location():
    mock_client = AsyncMock()
    mock_message = AsyncMock()
    mock_message.from_user.id = 12345
    mock_message.from_user.first_name = "Женя"

    # Настраиваем mock для reply_text
    mock_message.reply_text.return_value = AsyncMock(id=42)  # Устанавливаем id как число

    # Замокируем зависимости
    with patch("handlers.handlers.add_new_user") as mock_add_new_user, \
         patch("handlers.handlers.get_has_provided_location", return_value={"has_provided_location": True}) as mock_get_has_location, \
         patch("handlers.handlers.get_user_time_zone_db", return_value={"time_zone": "UTC"}) as mock_get_time_zone_db, \
         patch("handlers.handlers.get_local_time", return_value=datetime(2024, 11, 10, 10, 0, 0)) as mock_get_local_time, \
         patch("handlers.handlers.logger") as mock_logger:

        # Вызов функции
        msg_id = await start_handler(mock_client, mock_message)

        # Проверяем вызовы функций
        mock_add_new_user.assert_called_once_with(mock_message.from_user)
        mock_get_has_location.assert_called_once_with(12345)
        mock_get_time_zone_db.assert_called_once_with(12345)
        mock_get_local_time.assert_called_once()

        # Проверяем отправку приветственного сообщения
        mock_message.reply_text.assert_any_call(
            "Привет, Женя!\nВы находитесь в UTC локальное время 2024-11-10 10:00:00."
        )

        # Проверяем отправку сообщения с выбором действия
        mock_message.reply_text.assert_any_call(
            "Вы уже предоставили свою локацию.\n\n👋 Привет! Я бот для отслеживания сна.\n\n"
            "Выберите действие из меню ниже:",
            reply_markup=get_initial_keyboard()
        )

        # Убедимся, что msg_id корректно возвращается
        assert isinstance(msg_id, int)
        assert msg_id == 42