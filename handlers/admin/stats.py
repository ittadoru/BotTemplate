from aiogram import Router, types
from aiogram.types import CallbackQuery
import datetime

from utils import logger as log
from config import ADMIN_ERROR
from db.base import get_session
from db.users import get_total_users, get_active_users_today
from db.subscribers import get_total_subscribers


router = Router()

@router.callback_query(lambda c: c.data == "stats")
async def handle_stats(callback: CallbackQuery):

    try:
        async with get_session() as session:
            total_users = await get_total_users(session)
            total_subscribers = await get_total_subscribers(session)
            active_users_today = await get_active_users_today(session)
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
