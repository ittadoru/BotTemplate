from aiogram import Router, types
from aiogram.types import CallbackQuery
from datetime import datetime
from db.base import get_session
from db.subscribers import get_subscriber_expiry


router = Router()

@router.callback_query(lambda c: c.data == "myprofile")
async def show_profile(callback: CallbackQuery):
    """Обработка введённого ID или username, поиск истории ссылок пользователя."""
    user_id = callback.from_user.id

    # Если пользователь не найден
    if user_id is None:
        await callback.message.answer("❌ Пользователь не найден.")
        return

    # Получение информации о пользователе
    async with get_session() as session:
        expire_at = await get_subscriber_expiry(session, user_id)
    if expire_at:
        if expire_at > datetime.now(expire_at.tzinfo):
            subscription_status = f"✅ Подписка активна до <b>{expire_at.strftime('%d.%m.%Y %H:%M')}</b>"
        else:
            subscription_status = "❌ Подписка истекла"
    else:
        subscription_status = "❌ Подписка не активна"

    name = callback.from_user.first_name or "Без имени"
    username = callback.from_user.username or ""

    user_info = "<b>👤 Пользователь:</b>\n\n"
    user_info += f"ID: <code>{user_id}</code>\n"
    user_info += f"Имя: {name}\n"
    user_info += f"{subscription_status}\n"
    user_info += f"Username: @{username}\n"

    full_text = user_info

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💳 Купить подписку", callback_data="subscribe")],
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]
    ])
    await callback.message.edit_text(full_text, parse_mode="HTML", reply_markup=keyboard)
