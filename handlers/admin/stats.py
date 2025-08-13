from aiogram import Router, types
from aiogram.types import CallbackQuery
from redis.exceptions import RedisError
import datetime

from utils import logger as log
from config import ADMIN_ERROR
from redis_db import r

router = Router()


@router.callback_query(lambda c: c.data == "stats")
async def handle_stats(callback: CallbackQuery):
    try:
        total_users = await r.scard("users")
        today_key = f"active_users:{datetime.date.today()}"
        active_users_today = await r.pfcount(today_key)
        total_subscribers = len(await r.smembers("subscribers"))
    except Exception as e:
        log.log_error(f"Ошибка при получении статистики: {e}")
        await callback.message.answer("⚠️ Ошибка при получении статистики.")
        await callback.message.bot.send_message(ADMIN_ERROR, f"Ошибка при получении статистики: {e}")
        return await callback.answer()

    msg = (
        f"📊 <b>Статистика:</b>\n"
        f"👥 Уникальных пользователей: <b>{total_users}</b>\n"
        f"💎 С подпиской: <b>{total_subscribers}</b>\n"
        f"🟢 Активных сегодня: <b>{active_users_today}</b>\n"
    )

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")]
        ]
    )
    log.log_message("Админ запросил статистику", emoji="📊")
    await callback.message.edit_text(msg, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()
