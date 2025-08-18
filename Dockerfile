FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Устанавливаем PYTHONPATH, чтобы Python видел папку db как модуль
ENV PYTHONPATH=/app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc curl postgresql-client && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Отдельный слой для зависимостей (кэшируется пока не меняется requirements.txt)
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Основной код
COPY . .

EXPOSE 8000

CMD ["bash", "-c", "alembic upgrade head && python bot.py"]