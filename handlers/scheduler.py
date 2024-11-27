import logging
from datetime import datetime, timedelta, time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pyrogram import Client
from pytz import timezone

from db.db import get_all_reminders, get_all_users_city_name, get_sleep_goal_user, get_reminder_time_db, \
    get_sleep_time_without_wake_db, get_user_wake_time, get_user_time_zone_db
from handlers.keyboards import get_initial_keyboard
from handlers.weather_advice import get_weather, get_sleep_advice_based_on_weather

logger = logging.getLogger()


def setup_scheduler(app: Client):
    """
    :param app: pyrogram Client
    """

    async def send_sleep_reminder():
        """
        :return:
        """
        try:
            users = get_all_reminders()
            now = datetime.now()
            for user in users:
                user_id = user['user_id']
                if user_id:
                    user_timezone = get_user_time_zone_db(user_id)['time_zone']
                    if user_timezone is None:
                        user_timezone = 'UTC'
                    now = now.astimezone(timezone(user_timezone))
                current_time = now.time()
                sleep_record = get_sleep_time_without_wake_db(user_id)
                bedtime = calculate_bedtime(user_id)
                if (bedtime and current_time.hour == bedtime.hour
                        and current_time.minute == bedtime.minute
                        and not sleep_record):
                    try:
                        await app.send_message(chat_id=user_id,
                                               text="🌙 Пора ложиться спать, чтобы достичь вашей цели "
                                                    "по продолжительности сна на основе времени пробуждения!",
                                               reply_markup=get_initial_keyboard())
                        logger.info(f"Отправлено напоминание пользователю {user_id} на основе цели сна")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
        except Exception as e:
            logger.error(f"Ошибка в функции send_sleep_reminder: {e}")

    async def send_wake_up_reminder():
        """
        :return:
        """
        try:
            users = get_all_reminders()
            now = datetime.now()
            for user in users:
                user_id = user['user_id']
                if user_id:
                    user_timezone = get_user_time_zone_db(user_id)['time_zone']
                    if user_timezone is None:
                        user_timezone = 'UTC'
                    now = now.astimezone(timezone(user_timezone))
                current_time = now.time()
                wake_up_time = calculate_wake_up_time(user_id)
                if (wake_up_time and current_time.hour == wake_up_time.hour
                        and current_time.minute == wake_up_time.minute):
                    try:
                        await app.send_message(chat_id=user_id,
                                               text="☀️ Пора вставать, чтобы достичь назначенных целей!",
                                               reply_markup=get_initial_keyboard())
                        logger.info(f"Отправлено напоминание пользователю {user_id} на основе цели сна")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
        except Exception as e:
            logger.error(f"Ошибка в функции send_wake_up_reminder: {e}")

    async def daily_weather_reminder():
        """
        :return:
        """
        try:
            # Получаем всех пользователей и их города из базы данных
            users = get_all_users_city_name()
            now = datetime.now()
            for user in users:
                user_id, city, user_timezone = [user['id'], user['city_name'], user['time_zone']]
                if user_timezone is None:
                    user_timezone = 'UTC'
                now.astimezone(timezone(user_timezone))
                current_time = now.time()
                weather = get_weather(city)
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
                    weather_time = calculate_weather_reminder(user_id)
                    if weather_time and current_time.hour == weather_time.hour and \
                            current_time.minute == weather_time.minute:
                        try:
                            await app.send_message(chat_id=user_id, text=response,
                                                   reply_markup=get_initial_keyboard())
                        except Exception as e:
                            logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
        except Exception as e:
            logger.error(f"Ошибка в функции daily_weather_reminder: {e}")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_sleep_reminder, CronTrigger(minute='*'))
    scheduler.add_job(send_wake_up_reminder, CronTrigger(minute='*'))
    scheduler.add_job(daily_weather_reminder, CronTrigger(minute='*'))
    scheduler.start()


def calculate_weather_reminder(user_id: int):
    reminder = get_reminder_time_db(user_id)
    if reminder and reminder["reminder_time"]:
        reminder_time = datetime.strptime(reminder["reminder_time"], "%H:%M").time()
        return reminder_time
    else:
        return datetime.combine(datetime.now(), time(20, 00))


# Функция для расчета времени отхода ко сну
def calculate_bedtime(user_id: int):
    """
    :param user_id: id пользователя
    """
    user = get_sleep_goal_user(user_id)
    sleep_record = get_user_wake_time(user_id)
    if user and user['sleep_goal'] and sleep_record and \
            sleep_record['wake_time'] and sleep_record['wake_time'] is None:
        sleep_goal = user['sleep_goal']
        # wake_time_dt = datetime.strptime(wake_time['wake_time'], "%H:%M").time()
        wake_time_dt = sleep_record['wake_time'].time()
        # Предположим, что пользователь хочет вставать в wake_time и он определен
        wake_up_time = datetime.combine(datetime.now(), wake_time_dt)
        bedtime = wake_up_time - timedelta(hours=sleep_goal)
        return bedtime.time()
    else:
        return None


def calculate_wake_up_time(user_id: int):
    """
    :param user_id: id пользователя
    """
    user = get_sleep_goal_user(user_id)
    sleep_record = get_sleep_time_without_wake_db(user_id)
    if user and user['sleep_goal'] and sleep_record and sleep_record['sleep_time']:
        sleep_goal = user['sleep_goal']
        # sleep_time_str = sleep_record['sleep_time']
        # sleep_time = datetime.strptime(sleep_time_str[:-10], "%Y-%m-%d %H:%M")
        sleep_time = sleep_record['sleep_time']
        # Преобразовываем в datetime и плюсуем желаемую цель сна
        sleep_datetime = datetime.combine(sleep_time, sleep_time.time())
        wake_up_time = sleep_time + timedelta(hours=sleep_goal)
        return wake_up_time.time()
    else:
        return None


if __name__ == "__main__":
    pass
