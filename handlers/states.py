# Словарь для хранения состояний пользователей
import logging
from enum import Enum, auto

logger = logging.getLogger(__name__)

user_states: dict[int, "UserStates"] = {}


# Определение состояний
class UserStates(Enum):
    STATE_NONE = auto()
    STATE_WAITING_REMINDER_TIME = auto()
    STATE_WAITING_SLEEP_QUALITY = auto()
    STATE_WAITING_SLEEP_GOAL = auto()
    STATE_WAITING_USER_WAKE_TIME = auto()
    STATE_WAITING_SAVE_MOOD = auto()
    STATE_WAITING_CONFIRM_DELETE = auto()
    STATE_WAITING_PROVIDED_LOCATION = auto()
