import logging
from datetime import datetime

from aiogram import Bot, F, Router, types
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import subscribers as db_subscribers
from db import users as db_users
from db.base import get_session
from states.history import HistoryStates

router = Router()


class UserCallback(CallbackData, prefix="user_admin"):
    """Фабрика колбэков для действий с пользователем в админ-панели."""
    action: str
    user_id: int


@router.callback_query(F.data == "user_history_start")
async def show_user_history_prompt(callback: types.CallbackQuery, state: FSMContext):
    """
    Запрашивает у администратора ID или username, изменяя текущее сообщение
    и сохраняя его ID для последующего редактирования.
    """
    await state.set_state(HistoryStates.waiting_for_id_or_username)
    await state.update_data(message_to_edit=callback.message.message_id)

    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="manage_users")

    await callback.message.edit_text(
        "⚠️ Введите ID или username пользователя:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.message(HistoryStates.waiting_for_id_or_username)
async def process_user_lookup(message: types.Message, state: FSMContext, bot: Bot):
    """
    Обрабатывает введенный ID/username, находит пользователя,
    удаляет сообщение администратора и изменяет исходное сообщение,
    превращая его в информационную карточку.
    """
    data = await state.get_data()
    message_id_to_edit = data.get("message_to_edit")
    await state.clear()

    user_identifier = message.text.strip()
    user = None

    # Удаляем сообщение администратора с ID/username
    await message.delete()

    async with get_session() as session:
        if user_identifier.isdigit():
            user = await db_users.get_user_by_id(session, int(user_identifier))
        else:
            username = user_identifier.lstrip("@").lower()
            user = await db_users.get_user_by_username(session, username)

        if not user:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id_to_edit,
                text="❌ Пользователь не найден."
            )
            return

        # Получение информации о подписке
        is_active = await db_subscribers.is_subscriber(session, user.id)
        if is_active:
            expiry_date = await db_subscribers.get_subscriber_expiry(session, user.id)
            subscription_status = f"✅ Активна до {expiry_date.strftime('%d.%m.%Y %H:%M')}"
        else:
            subscription_status = "❌ Не активна"

        # Формирование текста сообщения
        user_info_parts = [
            f"<b>👤 Информация о пользователе</b>\n",
            f"<b>ID:</b> <code>{user.id}</code>",
            f"<b>Имя:</b> {user.first_name or 'не указано'}"
        ]
        if user.username:
            user_info_parts.append(f"<b>Username:</b> @{user.username}")
        if user.created_at:
            user_info_parts.append(f"<b>Зарегистрирован:</b> {user.created_at.strftime('%d.%m.%Y %H:%M')}")
        
        user_info_parts.append(f"<b>Подписка:</b> {subscription_status}")
        user_info_text = "\n".join(user_info_parts)

    # Создание клавиатуры
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🗑️ Удалить пользователя",
        callback_data=UserCallback(action="delete", user_id=user.id).pack()
    )
    builder.button(text="⬅️ Назад", callback_data="manage_users")
    builder.adjust(1)

    logging.info(f"Админ {message.from_user.id} просмотрел информацию о пользователе {user.id}")
    await bot.edit_message_text(
        text=user_info_text,
        chat_id=message.chat.id,
        message_id=message_id_to_edit,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(UserCallback.filter(F.action == "delete"))
async def delete_user_handler(callback: types.CallbackQuery, callback_data: UserCallback):
    """
    Обрабатывает нажатие кнопки 'Удалить пользователя'.
    Изменяет сообщение, возвращая меню управления пользователями и уведомляя о результате.
    """
    user_id_to_delete = callback_data.user_id
    admin_id = callback.from_user.id

    async with get_session() as session:
        success = await db_users.delete_user_by_id(session, user_id_to_delete)

    # Создаем клавиатуру меню управления пользователями
    manage_users_keyboard = InlineKeyboardBuilder()
    manage_users_keyboard.button(text="👥 Все пользователи", callback_data="all_users")
    manage_users_keyboard.button(text="🔍 Данные пользователя", callback_data="user_history_start")
    manage_users_keyboard.button(text="🗑️ Удалить всех пользователей", callback_data="delete_all_users")
    manage_users_keyboard.button(text="⬅️ Назад", callback_data="admin_menu")
    manage_users_keyboard.adjust(1)

    if success:
        logging.info(f"Админ {admin_id} удалил пользователя {user_id_to_delete}")
        text = f"✅ Пользователь <code>{user_id_to_delete}</code> успешно удалён.\n\nВыберите действие:"
    else:
        logging.warning(f"Админ {admin_id} не смог удалить несуществующего пользователя {user_id_to_delete}")
        text = f"❌ Не удалось найти и удалить пользователя <code>{user_id_to_delete}</code>.\n\nВыберите действие:"

    await callback.message.edit_text(
        text=text,
        reply_markup=manage_users_keyboard.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

