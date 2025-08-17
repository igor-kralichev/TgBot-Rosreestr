# Используем официальный образ Python 3.11.3 на базе slim
FROM python:3.11.3-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем зависимости для Playwright и Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Playwright и его зависимости
RUN pip install --no-cache-dir playwright
RUN playwright install --with-deps

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1

# Открываем порт для FastAPI
EXPOSE 8000

# Запускаем приложение
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]