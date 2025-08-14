FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y gcc python3-dev && \
    apt-get clean

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

EXPOSE 8000

CMD alembic upgrade head && bash -c "uvicorn server:app --host 0.0.0.0 --port 8000 & python bot.py"