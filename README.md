# BotTemplate (Telegram Bot + FastAPI + PostgreSQL + YooKassa)

Проект — практичный шаблон: Telegram‑бот (aiogram 3) + FastAPI веб‑сервер (webhook/payment endpoint) + PostgreSQL (SQLAlchemy 2 async + Alembic) + YooKassa платежи. Цель: быстро стартовать продукт с подписками и админ‑панелью, сохранив читаемость и расширяемость кода.

Важно: файл `.env` не коммитится — используйте пример `.env.example` и не публикуйте реальные токены / ключи.

Основные возможности:
* Пользовательское меню, подписка, промокоды
* Админ‑раздел: рассылки, статистика, экспорт логов и таблиц, управление тарифами
* Платежи через YooKassa (создание платежа + обработка webhook `/yookassa`)
* Миграции БД Alembic (async URL → sync для мигратора)
* Полностью контейнеризовано (Docker Compose)
* Минимизированный `requirements.txt` только с прямыми зависимостями

---

## 🚀 Быстрый запуск
```bash
git clone https://github.com/ittadoru/BotTemplate.git
cd BotTemplate
cp .env.example .env  # заполнить значения
docker compose up --build -d
docker compose logs -f app
```
Бот: открыть в Telegram (по токену). Webhook платежей: `https://DOMAIN/yookassa` (DOMAIN в `.env`).

---

## 📋 Полная пошаговая инструкция
1. Клонировать репозиторий.
2. Создать `.env` из примера (`cp .env.example .env`).
3. Заполнить обязательные переменные (см. таблицу ниже).
4. (Опционально) Изменить/добавить модели и создать миграцию до первого запуска prod.
5. Запустить контейнеры: `docker compose up --build -d`.
6. Проверить логи: `docker compose logs -f app` (убедиться что миграции применились).
7. При необходимости вручную: `docker compose exec app alembic upgrade head`.
8. Настроить webhook в кабинете YooKassa → URL: `https://DOMAIN/yookassa`.
9. Протестировать тестовый платеж (YooKassa sandbox) → увидеть продление подписки.
10. Готово.

---

## 🔐 Переменные окружения
Полный список в `.env.example`.
| Имя | Обязат. | Пример | Назначение |
|-----|---------|--------|-----------|
| BOT_TOKEN | Да | 123456:ABC | Токен Telegram бота |
| ADMINS | Нет | 111,222 | Список ID админов |
| ADMIN | Да | 111 | Главный админ (уведомления ошибок) |
| DATABASE_URL | Да | postgresql+asyncpg://user:pass@postgres:5432/appdb | Async URL БД |
| POSTGRES_USER | Да | appuser | Пользователь Postgres контейнера (должен совпадать с частью DATABASE_URL) |
| POSTGRES_PASSWORD | Да | strongpass | Пароль Postgres контейнера (совпадает с DATABASE_URL) |
| POSTGRES_DB | Да | appdb | Имя БД (совпадает с DATABASE_URL) |
| SHOP_ID | Да | 123456 | YooKassa shop id |
| API_KEY | Да | test_xxx | YooKassa secret key |
| DOMAIN | Да | https://mydomain.ru | Базовый публичный домен для webhook |
| SUPPORT_GROUP_ID | Нет | -100123456789 | Группа поддержки |
| SUBSCRIBE_TOPIC_ID | Нет | 12 | ID топика (форум) |

---

## 🗄 Миграции Alembic
`alembic/env.py` конвертирует async URL (asyncpg) → sync (psycopg2) для работы мигратора.
Создать ревизию:
```bash
docker compose exec app alembic revision --autogenerate -m "add_feature"
```
Применить:
```bash
docker compose exec app alembic upgrade head
```
Откатить:
```bash
docker compose exec app alembic downgrade -1
```
Советы:
* Проверяйте diff перед коммитом.
* Избегайте редактирования старых миграций — добавляйте новые.

---

## 🧩 Архитектура
| Компонент | Роль |
|-----------|------|
| `bot.py` | Aiogram бот (polling) |
| `server.py` | FastAPI сервер (webhook) |
| `utils/payment.py` | Создание платежей YooKassa |
| `utils/webhook.py` | Логика обработки успешного платежа |
| `db/` | Модели и CRUD |
| `handlers/` | Роутеры (user/admin/support) |
| `services/` | Бизнес‑логика/сценарии (ядро поведения; сюда выносить обработку, расчёты, рассылки) |
| `alembic/` | Миграции |

Поток платежа: выбор тарифа → платёж с метаданными → webhook → продление подписки.

Папка `services/` — место для прикладной логики (оригинал шаблона подразумевает вынос «умных» операций из хендлеров). Хендлеры остаются тонкими: достают данные из апдейта, вызывают функции из `services/`, отправляют ответы.

---

## 💳 Платежи / Webhook
* Endpoint: `POST /yookassa`
* Idempotency: persistent (таблица `processed_payments` + уникальный `payment_id`)

Как работает idempotency:
1. Webhook приходит с `object.id` платежа
2. Перед обработкой выполняется `SELECT` по `processed_payments`
3. Если запись есть → webhook игнорируется (дубликат)
4. Если нет → транзакционно продлевается подписка и фиксируется `payment_id`
5. Уникальный индекс предотвращает гонку при нескольких одновременных запросах

Тест:
1. Создать тестовый тариф
2. Сгенерировать платёж
3. Смоделировать повтор: отправить один и тот же webhook 2 раза — продление произойдёт один раз

---

## 🛠 Типовые операции
Добавить тариф → изменить модель / данные → `revision --autogenerate` → `upgrade`.
Обновить зависимости → редактировать `requirements.txt` → `docker compose build`.
Сбросить БД (осторожно): `docker compose down -v`.

---

## 🧪 Development vs Production
Dev запуск:
```bash
docker compose up --build
```
Логи: `docker compose logs -f app`.

Production рекомендации:
* Без `watchfiles`
* Reverse proxy + TLS → корректный DOMAIN
* Persistent idempotency таблица
* Ротация логов

Пример override:
```yaml
services:
	app:
		volumes:
			- ./:/app
		command: bash -c "alembic upgrade head && watchfiles --filter python 'python bot.py'"
```

---

## ⚠️ Подводные камни
* Пока нет проверки суммы → нужна сверка amount vs тариф (добавьте в webhook)
* Нет проверки события типа (можно валидировать notification.event == "payment.succeeded")
* UTC срок действия; локальное отображение может отличаться
* DOMAIN обязателен для внешнего webhook
* Удалённый тариф → продление упадёт (следите за целостностью)

---

## 🩺 Troubleshooting
| Проблема | Причина | Решение |
|----------|---------|---------|
| 400 /yookassa | Неверный webhook URL | Проверьте DOMAIN и YooKassa настройку |
| Нет продления | Тариф не найден | Проверьте таблицу тарифов / миграции |
| Дубли продлений | Повторный webhook | Реализуйте persistent idempotency |
| Нет подключения к БД | Неверный URL / postgres не поднят | Логи postgres контейнера |
| Бот не отвечает | Неверный BOT_TOKEN | Пересоздать токен у BotFather |


## Связь с разработчиком

Если нужны доработки / вопросы / баги:

* Telegram: @ittadoru

PR приветствуются — небольшой diff, понятное описание миграций и обновлений.
