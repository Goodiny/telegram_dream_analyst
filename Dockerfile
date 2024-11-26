# Используем официальный Python-образ с версией 3.12
FROM python:3.12-slim

# Установка системных зависимостей для сборки cryptography и TgCrypto
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Копируем только необходимые папки
COPY configs ./configs
COPY db ./db
COPY handlers ./handlers
COPY logs ./logs
COPY bot.py ./bot.py

# Определяем команду для запуска бота
CMD ["python", "bot.py"]