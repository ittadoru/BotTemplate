import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from aiogram import Bot

from db.subscribers import add_subscriber_with_duration
from db.tariff import get_tariff_by_id
from utils import logger as log
from config import BOT_TOKEN, SUPPORT_GROUP_ID, SUBSCRIBE_TOPIC_ID, ADMIN_ERROR
 
app = FastAPI()

class BotLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        log.log_message(msg)  # или log.log_error(msg) для ошибок

# Перехват стандартных логов FastAPI/Uvicorn
logging.getLogger("uvicorn.access").handlers = [BotLogHandler()]
logging.getLogger("uvicorn.error").handlers = [BotLogHandler()]
logging.getLogger("fastapi").handlers = [BotLogHandler()]

@app.post("/yookassa")
async def yookassa_webhook(request: Request):
    """
    Обрабатывает вебхуки от YooKassa.
    При успешной оплате начисляет дни подписки пользователю.
    """
    bot: Bot = app.state.bot
    r = app.state.redis

    try:
        data = await request.json()
    except Exception as e:
        log.log_message(f"Ошибка парсинга JSON: {e}", log_level="error", emoji="⚠️")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Корректная обработка webhook: начисляем дни по тарифу, а не по сумме оплаты
    try:
        payment_status = data["object"]["status"]
        user_id_str = data["object"]["metadata"]["user_id"]
        tariff_id_str = data["object"]["metadata"]["tariff_id"]

        user_id = int(user_id_str)
        tariff_id = int(tariff_id_str)
    except (KeyError, ValueError) as e:
        await bot.send_message(ADMIN_ERROR, f"Ошибка получения данных webhook: {e}")
        log.log_message(f"Ошибка данных webhook: {e}", log_level="error", emoji="❌")
        raise HTTPException(status_code=400, detail="Invalid data")

    if payment_status == "succeeded":
        try:
            tariff = await get_tariff_by_id(tariff_id)
            days = tariff.duration_days
        except Exception as e:
            await bot.send_message(ADMIN_ERROR, f"Ошибка получения тарифа: {e}")
            log.log_message(f"Ошибка получения тарифа: {e}", log_level="error", emoji="❌")
            raise HTTPException(status_code=400, detail="Tariff error")

        await add_subscriber_with_duration(user_id, days)
        log.log_message(f"Подписка продлена для user_id={user_id} на {days} дней", emoji="✅")

        try:
            # Получаем данные пользователя
            user = await bot.get_chat(user_id)
            username = f"@{user.username}" if user.username else "—"
            full_name = user.full_name or user.first_name or "—"
            # Дата окончания подписки
            from datetime import datetime, timedelta
            expire_date = datetime.now() + timedelta(days=days)
            expire_str = expire_date.strftime('%d.%m.%Y')

            # Сообщение пользователю
            await bot.send_message(
                user_id,
                f"✅ Ваша подписка успешно оформлена и продлена на <b>{days} дней</b>!\n\n"
                f"🏷️ Тариф: <b>{tariff.name}</b>\n"
                f"📅 Действует до: <b>{expire_str}</b>"
                , parse_mode="HTML"
            )
            log.log_message(
                f"Уведомление об успешной оплате отправлено пользователю {user_id}.",
                emoji="📩", log_level="info"
            )
            # Красивое уведомление в группу
            await bot.send_message(
                SUPPORT_GROUP_ID,
                f"<b>💳 Новая оплата подписки!</b>\n\n"
                f"👤 <b>Пользователь:</b> {full_name} ({username})\n"
                f"🆔 <b>ID:</b> <code>{user_id}</code>\n\n"
                f"🏷️ <b>Тариф:</b> <b>{tariff.name}</b>\n"
                f"⏳ <b>Дней:</b> <b>{days}</b>\n"
                f"📅 <b>Действует до:</b> <b>{expire_str}</b>\n",
                parse_mode="HTML",
                message_thread_id=SUBSCRIBE_TOPIC_ID
            )
        except Exception as e:
            log.log_message(f"Ошибка отправки сообщения пользователю: {e}", log_level="error", emoji="⚠️")

    return JSONResponse(content={"status": "ok"})

@app.on_event("startup")
async def on_startup():
    """
    Инициализация бота и Redis при запуске FastAPI-приложения.
    """
    log.log_message("Запуск FastAPI приложения", emoji="🚀")
    app.state.bot = Bot(token=BOT_TOKEN)
