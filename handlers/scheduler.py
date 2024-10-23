import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pyrogram import Client

from db.modify_tables import execute_query, get_all_reminders
from utils.wether_tips import get_weather, get_sleep_advice_based_on_weather

logger = logging.getLogger()


def setup_scheduler(app: Client):
    async def send_sleep_reminder():
        try:
            users = get_all_reminders()
            now = datetime.now()
            current_time = now.time()
            for user in users:
                user_id = user['user_id']
                sleep_record_count = execute_query('''
                            SELECT sleep_time FROM sleep_records 
                            WHERE user_id = :user_id AND sleep_time IS NOT NULL AND wake_time IS NULL
                        ''', {'user_id': user_id}).rowcount
                bedtime = calculate_bedtime(user_id)
                if (bedtime and current_time.hour == bedtime.hour
                        and current_time.minute == bedtime.minute
                        and not sleep_record_count):
                    try:
                        await app.send_message(chat_id=user_id,
                                               text="🌙 Пора ложиться спать, чтобы достичь вашей цели "
                                                    "по продолжительности сна на основе времени пробуждения!")
                        logger.info(f"Отправлено напоминание пользователю {user_id} на основе цели сна")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
        except Exception as e:
            logger.error(f"Ошибка в функции send_sleep_reminder: {e}")

    async def send_wake_up_reminder():
        try:
            users = execute_query('SELECT user_id FROM reminders').fetchall()
            now = datetime.now()
            current_time = now.time()
            for user in users:
                user_id = user['user_id']
                wake_up_time = calculate_wake_up_time(user_id)
                if (wake_up_time and current_time.hour == wake_up_time.hour
                        and current_time.minute == wake_up_time.minute):
                    try:
                        await app.send_message(chat_id=user_id,
                                               text="☀️ Пора вставать, чтобы достичь назначенных целей!")
                        logger.info(f"Отправлено напоминание пользователю {user_id} на основе цели сна")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
        except Exception as e:
            logger.error(f"Ошибка в функции send_wake_up_reminder: {e}")

    async def daily_weather_reminder():
        try:
            # Получаем всех пользователей и их города из базы данных
            users = execute_query("SELECT id, city_name FROM users").fetchall()

            for user in users:
                user_id, city = user
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
                    try:
                        await app.send_message(chat_id=user_id, text=response)
                    except Exception as e:
                        logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
        except Exception as e:
            logger.error(f"Ошибка в функции daily_weather_reminder: {e}")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_sleep_reminder, CronTrigger(minute='*'))
    scheduler.add_job(send_wake_up_reminder, CronTrigger(minute='*'))
    scheduler.add_job(daily_weather_reminder, CronTrigger(hour=14, minute=4))
    scheduler.start()


# Функция для расчета времени отхода ко сну
def calculate_bedtime(user_id):
    user = execute_query(
        'SELECT sleep_goal FROM users WHERE id = :user_id',
        {'user_id': user_id}).fetchone()
    reminder = execute_query(
        'SELECT reminder_time FROM reminders WHERE user_id = :user_id',
        {'user_id': user_id}).fetchone()
    if user and user['sleep_goal'] and reminder and reminder['reminder_time']:
        sleep_goal = user['sleep_goal']
        reminder_time = datetime.strptime(reminder['reminder_time'], "%H:%M").time()
        # Предположим, что пользователь хочет вставать в reminder_time
        wake_up_time = datetime.combine(datetime.now(), reminder_time)
        bedtime = wake_up_time - timedelta(hours=sleep_goal)
        return bedtime.time()
    else:
        return None


def calculate_wake_up_time(user_id):
    user = execute_query('SELECT sleep_goal FROM users WHERE id = :user_id',
                         {'user_id': user_id}).fetchone()
    sleep_record = execute_query('''
        SELECT sleep_time FROM sleep_records 
        WHERE user_id = :user_id AND wake_time IS NULL
        ''', {'user_id': user_id}).fetchone()
    if user and user['sleep_goal'] and sleep_record and sleep_record['sleep_time']:
        sleep_goal = user['sleep_goal']
        sleep_time_str = sleep_record['sleep_time']
        sleep_time = datetime.strptime(sleep_time_str[:-10], "%Y-%m-%dT%H:%M")
        # Преобразовываем в datetime и плюсуем желаемую цель сна
        sleep_datetime = datetime.combine(sleep_time, sleep_time.time())
        wake_up_time = sleep_datetime + timedelta(hours=sleep_goal)
        return wake_up_time.time()
    else:
        return None


if __name__ == "__main__":
    pass
