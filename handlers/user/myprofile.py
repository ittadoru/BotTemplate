"""Профиль пользователя: показ статуса подписки и базовой информации."""

from datetime import datetime
from aiogram import Router, types
from aiogram.types import CallbackQuery
from db.base import get_session
from db.subscribers import get_subscriber_expiry
from handlers.user.referral import get_referral_stats


router = Router()

def _build_profile_keyboard() -> types.InlineKeyboardMarkup:
    """Возвращает клавиатуру профиля."""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="💳 Купить подписку", callback_data="subscribe")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")],
        ]
    )

def _format_subscription_status(expire_at: datetime | None) -> str:
    """Возвращает человекочитаемый статус подписки."""
    if not expire_at:
        return "❌ Подписка не активна"
    now = datetime.now(expire_at.tzinfo)
    if expire_at > now:
        if expire_at.year > 2124:
            return "✅ Подписка: <b>бессрочная</b>"
        return f"✅ Подписка активна до <b>{expire_at.strftime('%d.%m.%Y %H:%M')}</b>"
    return "❌ Подписка истекла"


def _build_profile_text(user_id: int, name: str, username: str, status: str) -> str:
    username_part = f"@{username}" if username else "—"
    stats = (
        f"<b>👤 Пользователь:</b>\n\n"
        f"ID: <code>{user_id}</code>\n"
        f"Имя: {name}\n"
        f"{status}\n"
        f"Username: {username_part}\n\n"
    )

    return stats

def _build_referral_text(ref_count: int, level: int, to_next: str, progress_bar: str = "") -> str:
    level_names = {
        1: "1 (базовый)",
        2: "2 (1 реферал)",
        3: "3 (3 реферала)",
        4: "4 (10 рефералов)",
        5: "5 (30 рефералов)"
    }
    return (
        f"\n\n<b>Реферальная программа:</b>\n"
        f"\n<b>Твой уровень:</b> {level_names.get(level, '—')}"
        f"\n<b>Рефералов:</b> {ref_count}"
        f"\n{progress_bar}"
        f"\n{to_next}\n"
    )

@router.callback_query(lambda c: c.data == "myprofile")
async def show_profile(callback: CallbackQuery) -> None:
    """Показывает профиль пользователя (кнопка myprofile)."""
    user_id = callback.from_user.id
    name = callback.from_user.first_name or "Без имени"
    username = callback.from_user.username or ""

    async with get_session() as session:
        expire_at = await get_subscriber_expiry(session, user_id)

        ref_count, level, _ = await get_referral_stats(session, user_id)
        # Новая логика перехода между уровнями
        next_level_map = {1: 2, 2: 3, 3: 4, 4: 5, 5: None}
        next_level_reqs = {2: 1, 3: 3, 4: 10, 5: 30}
        prev_level_min = {1: 0, 2: 1, 3: 3, 4: 10, 5: 30}[level]
        next_level = next_level_map.get(level)
        if next_level:
            need = next_level_reqs[next_level] - prev_level_min
            have = max(0, ref_count - prev_level_min)
            to_next = f"До следующего уровня: {next_level_reqs[next_level] - ref_count} рефералов"
            # Прогресс-бар
            bar_len = 8
            filled = min(bar_len, int(bar_len * have / need)) if need > 0 else bar_len
            empty = bar_len - filled
            progress_bar = f"Прогресс: {'🟩'*filled}{'⬜️'*empty} ({have}/{need})"
        else:
            to_next = "Максимальный уровень!"
            progress_bar = ""

    status = _format_subscription_status(expire_at)
    text = _build_profile_text(user_id, name, username, status)
    text += _build_referral_text(ref_count, level, to_next, progress_bar)

    current = (callback.message.text or "").strip()
    if current == text.strip():
        await callback.answer()
        return

    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=_build_profile_keyboard()
    )
    await callback.answer()
