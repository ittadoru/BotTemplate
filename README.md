# BotTemplatePostgreDB

Шаблон Telegram-бота с:

* Админ-панелью
* Панелью пользователя
* PostgreSQL
* Миграциями Alembic
* Docker + docker-compose для быстрого запуска

## 📦 Запуск проекта

### 1. Клонировать репозиторий

```bash
git clone https://github.com/ittadoru/BotTemplatePostgreDB.git
cd BotTemplatePostgreDB
```

### 2. Создать файл `.env`

Скопируйте пример и заполните своими значениями:

```bash
cp .env.example .env
```

### 3. Запустить проект

```bash
docker compose up --build
```

Это:

* поднимет контейнер с PostgreSQL
* применит миграции
* запустит API (Uvicorn) на порту **8000**
* запустит бота

### 4. Проверить работу

* API будет доступен по адресу:
  [http://127.0.0.1:8000](http://127.0.0.1:8000)
* Бот будет онлайн, можно писать в Telegram.

---

## 🔄 Миграции

### Создать новую миграцию

```bash
docker compose exec app alembic revision --autogenerate -m "описание_изменений"
```

### Применить миграции вручную

(обычно не нужно — они применяются автоматически при старте)

```bash
docker compose exec app alembic upgrade head
```

---

## 📂 Структура проекта

```
.
├── alembic/            # Конфигурация миграций Alembic
│   ├── versions/       # Файлы миграций
│   ├── env.py
│   └── script.py.mako
├── bot.py              # Запуск Telegram-бота
├── server.py           # Запуск API (FastAPI/Uvicorn)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## 🛠 Требования

* Docker
* docker-compose
* Telegram Bot API токен


docker compose build --no-cache
docker compose up -d
docker compose exec app alembic revision --autogenerate -m "init"
docker compose exec app alembic upgrade head
docker compose logs -f app