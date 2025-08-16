FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y gcc python3-dev postgresql-client && \
    apt-get clean

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["bash", "-c", "alembic upgrade head && python bot.py"]