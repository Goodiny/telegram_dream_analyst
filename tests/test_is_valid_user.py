import pytest
from unittest.mock import Mock
from handlers.user_valid import is_valid_user
from pyrogram.types import User


def test_is_valid_user_valid_user():
    # Мокаем валидного пользователя
    valid_user = Mock(spec=User)
    valid_user.is_bot = False
    valid_user.is_fake = False
    valid_user.is_deleted = False
    valid_user.is_contact = False
    valid_user.is_restricted = False
    valid_user.is_scam = False

    # Убеждаемся, что функция возвращает True
    assert is_valid_user(valid_user) is True


def test_is_valid_user_invalid_type():
    # Передаем объект некорректного типа
    with pytest.raises(TypeError):
        is_valid_user("invalid_type")


@pytest.mark.parametrize("field, value", [
    ("is_bot", True),
    ("is_fake", True),
    ("is_deleted", True),
    ("is_contact", True),
    ("is_restricted", True),
    ("is_scam", True),
])
def test_is_valid_user_invalid_fields(field, value):
    # Создаем мока пользователя
    invalid_user = Mock(spec=User)
    invalid_user.is_bot = False
    invalid_user.is_fake = False
    invalid_user.is_deleted = False
    invalid_user.is_contact = False
    invalid_user.is_restricted = False
    invalid_user.is_scam = False

    # Устанавливаем конкретное поле в значение True
    setattr(invalid_user, field, value)

    # Убеждаемся, что вызывается ValueError
    with pytest.raises(ValueError):
        is_valid_user(invalid_user)