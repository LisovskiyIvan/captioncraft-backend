# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libavcodec-extra \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY . .

# Создаем директории для загрузки файлов и моделей
RUN mkdir -p uploads/videos uploads/subtitles models

# Скачиваем модель Vosk (если используется)
RUN python -c "from vosk import Model; Model(model_name='vosk-model-small-en-us-0.15')"
# Добавляем скрипт для ожидания готовности базы данных

# Открываем порт
EXPOSE 8000


# Запускаем приложение
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# Запускаем приложение с ожиданием базы данных
# CMD ["/wait-for-it.sh", "db:5432", "--", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
