from aiogram import types, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils import logger as log
from db.base import get_session
from db.users import get_all_user_ids, User, delete_user_by_id, get_users_by_ids
from db.subscribers import get_all_subscribers, delete_subscriber_by_id


router = Router()

@router.callback_query(lambda c: c.data == "all_users")
async def list_users(callback: types.CallbackQuery):
    """
    Показывает список всех пользователей с отметкой о подписке.
    Отображает первую страницу с пагинацией.
    """
    async with get_session() as session:
        user_ids = await get_all_user_ids(session)
        if not user_ids:
            await callback.message.answer("❌ Пользователей пока нет.")
            return

        user_ids.sort()
        page = 1
        per_page = 20
        total_pages = (len(user_ids) + per_page - 1) // per_page

        users_page = user_ids[(page - 1) * per_page : page * per_page]
        subs = await get_all_subscribers(session)
        subs_ids = set(str(s.user_id) for s in subs)
        users = await get_users_by_ids(session, [int(uid) for uid in users_page])
        users_dict = {str(u.id): u for u in users}

        text = "👥 <b>Пользователи:</b>\n\n"
        for uid in users_page:
            user = users_dict.get(str(uid))
            username = user.username if user and user.username else ""
            name = user.first_name if user and user.first_name else ""
            is_sub = "💎" if str(uid) in subs_ids else "❌"
            text += f"{is_sub} {uid} — {name}"
            if username:
                text += f" (@{username})"
            text += "\n"

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_users_keyboard(page, total_pages),
        )
        log.log_message("Админ запросил список пользователей", emoji="👥")
        await callback.answer()


def get_users_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру с кнопками для навигации по страницам и кнопкой назад.
    """
    buttons = [
        InlineKeyboardButton(
            text="◀️", callback_data=f"users_page:{page - 1}" if page > 1 else "noop"
        ),
        InlineKeyboardButton(text=f"{page} / {total_pages}", callback_data="noop"),
        InlineKeyboardButton(
            text="▶️", callback_data=f"users_page:{page + 1}" if page < total_pages else "noop"
        ),
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            buttons,
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="manage_users")]
        ]
    )

# Удаление всех пользователей
@router.callback_query(lambda c: c.data == "delete_all_users")
async def delete_all_users_callback(callback: types.CallbackQuery):
    async with get_session() as session:
        user_ids = await get_all_user_ids(session)
        for uid in user_ids:
            await delete_user_by_id(session, int(uid))
            await delete_subscriber_by_id(session, int(uid))
        await session.commit()

    log.log_message("Админ удалил всех пользователей", emoji="🗑️")
    await callback.message.answer(f"Все пользователи удалены", show_alert=True)

@router.callback_query(lambda c: c.data.startswith("users_page:"))
async def paginate_users(callback: types.CallbackQuery):
    """
    Обрабатывает переключение страниц списка пользователей.
    """
    page = int(callback.data.split(":")[1])

    async with get_session() as session:
        user_ids = await get_all_user_ids(session)
        user_ids.sort()

        per_page = 20
        total_pages = (len(user_ids) + per_page - 1) // per_page

        if page < 1 or page > total_pages:
            await callback.answer("Нет такой страницы", show_alert=True)
            return

        users_page = user_ids[(page - 1) * per_page : page * per_page]
        subs = await get_all_subscribers(session)
        subs_ids = set(str(s.user_id) for s in subs)
        users = await get_users_by_ids(session, [int(uid) for uid in users_page])
        users_dict = {str(u.id): u for u in users}

        text = "👥 <b>Пользователи:</b>\n\n"
        for uid in users_page:
            user = users_dict.get(str(uid))
            username = user.username if user and user.username else ""
            name = user.first_name if user and user.first_name else ""
            is_sub = "💎" if str(uid) in subs_ids else "❌"
            text += f"{is_sub} {uid} — {name}"
            if username:
                text += f" (@{username})"
            text += "\n"

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_users_keyboard(page, total_pages),
        )
        await callback.answer()
