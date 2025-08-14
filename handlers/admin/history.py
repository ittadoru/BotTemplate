from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from states.history import HistoryStates
from datetime import datetime
from utils import logger as log
from db.base import get_session
from db.users import get_all_user_ids
from db.subscribers import Subscriber
from db.users import User


router = Router()


@router.callback_query(lambda c: c.data == "user_history_start")
async def show_user_history(callback: types.CallbackQuery, state: FSMContext):
    """Запрос ID или username для просмотра истории пользователя (только для админов)."""
    await state.set_state(HistoryStates.waiting_for_id_or_username)

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="manage_users")]
        ]
    )

    await callback.message.edit_text(
        "⚠️ Введите ID или username пользователя:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.message(HistoryStates.waiting_for_id_or_username)
async def process_id_or_username(message: types.Message, state: FSMContext):
    """Обработка введённого ID или username, поиск истории ссылок пользователя."""
    arg = message.text.strip()
    user_id = None

    async with get_session() as session:
        if arg.isdigit():
            user_id = int(arg)
        else:
            # Поиск по username (без @, в нижнем регистре)
            username = arg.lstrip("@").lower()
            user_ids = await get_all_user_ids(session)
            for uid in user_ids:
                user = await session.get(User, int(uid))
                if user and user.username and user.username.lower() == username:
                    user_id = int(uid)
                    break

    # Если пользователь не найден
    if user_id is None:
        await message.answer("❌ Пользователь не найден.")
        await state.clear()
        return


    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("❌ Пользователь не найден.")
            await state.clear()
            return

        # Получение информации о подписке
        subscriber = await session.get(Subscriber, user_id)
        if subscriber and subscriber.expires_at:
            expiry_date = subscriber.expires_at
            if expiry_date > datetime.now():
                subscription_status = f"✅ Подписка активна до <b>{expiry_date.strftime('%d.%m.%Y %H:%M')}</b>"
            else:
                subscription_status = "❌ Подписка истекла"
        else:
            subscription_status = "❌ Подписка не активна"

        name = user.first_name or ""
        username = user.username or ""

    user_info = "<b>👤 Пользователь:</b>\n\n"
    user_info += f"ID: <code>{user_id}</code>\n"
    user_info += f"Имя: {name}\n"
    user_info += f"{subscription_status}\n"
    if username:
        user_info += f"Username: @{username}\n"

    # Клавиатура: удалить пользователя и назад
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=f"🗑️ Удалить пользователя", callback_data=f"delete_user:{user_id}")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="manage_users")]
        ]
    )
    log.log_message(f"Админ просмотрел историю пользователя {user_id}", emoji="📜")
    await message.answer(user_info, parse_mode="HTML", reply_markup=keyboard)
    await state.clear()


async def delete_user_callback(callback: types.CallbackQuery):
    uid = int(callback.data.split(":")[1])

    async with get_session() as session:
        user = await session.get(User, uid)
        if user:
            await session.delete(user)
        subscriber = await session.get(Subscriber, uid)
        if subscriber:
            await session.delete(subscriber)
        await session.commit()

    await callback.message.answer(f"Пользователь {uid} удалён", show_alert=True)
    log.log_message(f"Админ удалил пользователя {uid}", emoji="🗑️")
