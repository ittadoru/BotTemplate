"""Общая рассылка: конструктор сообщения (с кнопкой при необходимости) и асинхронная отправка всем пользователям."""

import asyncio
import logging
from contextlib import suppress

from aiogram import F, Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

from db.base import get_session
from db.users import get_all_user_ids

# Инициализация логгера
logger = logging.getLogger(__name__)


# --- Состояния и CallbackData ---

class BroadcastStates(StatesGroup):
    """Состояния для конструктора общей рассылки."""
    waiting_text = State()
    waiting_button_text = State()
    waiting_button_url = State()


class BroadcastCallback(CallbackData, prefix="broadcast"):
    """
    Фабрика колбэков для управления конструктором рассылки.
    `action`: 'set_text', 'set_button', 'preview', 'send', 'cancel'
    """
    action: str


router = Router()


# --- Вспомогательные функции для UI ---

async def get_constructor_text(state: FSMContext) -> str:
    """Генерирует текст для сообщения-конструктора."""
    return (
        "📢 **Конструктор общей рассылки**\n\n"
        "Используйте кнопки ниже для настройки, предпросмотра и отправки."
    )


def get_constructor_keyboard() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для управления конструктором рассылки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📝 Изменить текст",
                callback_data=BroadcastCallback(action="set_text").pack()
            ),
            InlineKeyboardButton(
                text="🔗 Изменить кнопку",
                callback_data=BroadcastCallback(action="set_button").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="👀 Предпросмотр",
                callback_data=BroadcastCallback(action="preview").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="🚀 Отправить всем",
                callback_data=BroadcastCallback(action="send").pack()
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=BroadcastCallback(action="cancel").pack()
            )
        ]
    ])


async def update_constructor_message(message: Message, state: FSMContext):
    """Обновляет сообщение-конструктор актуальными данными из FSM."""
    text = await get_constructor_text(state)
    keyboard = get_constructor_keyboard()
    with suppress(TelegramAPIError):
        await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")


# --- Основные хендлеры ---

@router.callback_query(F.data == "broadcast_start")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Запускает конструктор общей рассылки."""
    await state.clear()
    await state.update_data(constructor_message_id=callback.message.message_id)
    await update_constructor_message(callback.message, state)
    await callback.answer()


@router.callback_query(BroadcastCallback.filter(F.action == "cancel"))
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отменяет конструктор рассылки и возвращает в главное меню."""
    from .menu import get_admin_menu_keyboard
    await state.clear()
    await callback.message.edit_text(
        "🔐 Админ-панель", reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


# --- Хендлеры для изменения параметров рассылки ---

@router.callback_query(BroadcastCallback.filter(F.action == "set_text"))
async def set_broadcast_text_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрашивает у администратора текст для рассылки."""
    await state.set_state(BroadcastStates.waiting_text)
    prompt = await callback.message.answer("Введите текст для рассылки:")
    await state.update_data(prompt_message_id=prompt.message_id)
    await callback.answer()


@router.message(BroadcastStates.waiting_text)
async def process_broadcast_text(message: Message, state: FSMContext, bot: Bot):
    """Сохраняет текст рассылки и обновляет конструктор."""
    await state.update_data(text=message.text)
    await state.set_state(None)

    data = await state.get_data()
    constructor_msg_id = data.get("constructor_message_id")
    prompt_msg_id = data.get("prompt_message_id")

    with suppress(TelegramAPIError):
        if prompt_msg_id:
            await bot.delete_message(message.chat.id, prompt_msg_id)
        await message.delete()

    if constructor_msg_id:
        constructor_message = Message(
            message_id=constructor_msg_id, chat=message.chat, bot=bot
        )
        await update_constructor_message(constructor_message, state)


@router.callback_query(BroadcastCallback.filter(F.action == "set_button"))
async def set_button_text_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрашивает текст для кнопки."""
    await state.set_state(BroadcastStates.waiting_button_text)
    prompt = await callback.message.answer("Введите текст для кнопки:")
    await state.update_data(prompt_message_id=prompt.message_id)
    await callback.answer()


@router.message(BroadcastStates.waiting_button_text)
async def process_button_text(message: Message, state: FSMContext, bot: Bot):
    """Сохраняет текст кнопки и запрашивает URL."""
    await state.update_data(button_text=message.text)
    await state.set_state(BroadcastStates.waiting_button_url)
    
    data = await state.get_data()
    prompt_msg_id = data.get("prompt_message_id")

    with suppress(TelegramAPIError):
        if prompt_msg_id:
            await bot.delete_message(message.chat.id, prompt_msg_id)
        await message.delete()

    prompt = await message.answer(
        "Отлично! Теперь введите URL (начиная с http:// или https://):"
    )
    await state.update_data(prompt_message_id=prompt.message_id)


@router.message(BroadcastStates.waiting_button_url)
async def process_button_url(message: Message, state: FSMContext, bot: Bot):
    """Сохраняет URL кнопки и обновляет конструктор."""
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("Неверный формат ссылки. URL должен начинаться с http:// или https://.")
        return

    await state.update_data(button_url=url)
    await state.set_state(None)

    data = await state.get_data()
    constructor_msg_id = data.get("constructor_message_id")
    prompt_msg_id = data.get("prompt_message_id")

    with suppress(TelegramAPIError):
        if prompt_msg_id:
            await bot.delete_message(message.chat.id, prompt_msg_id)
        await message.delete()

    if constructor_msg_id:
        constructor_message = Message(
            message_id=constructor_msg_id, chat=message.chat, bot=bot
        )
        await update_constructor_message(constructor_message, state)


# --- Предпросмотр и отправка ---

@router.callback_query(BroadcastCallback.filter(F.action == "preview"))
async def preview_broadcast(callback: CallbackQuery, state: FSMContext):
    """Показывает администратору предпросмотр сообщения."""
    data = await state.get_data()
    text = data.get("text")

    if not text:
        await callback.answer("❗️ Сначала нужно задать текст сообщения.", show_alert=True)
        return

    button_text = data.get("button_text")
    button_url = data.get("button_url")

    markup = None
    if button_text and button_url:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button_text, url=button_url)]
        ])

    await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(BroadcastCallback.filter(F.action == "send"))
async def confirm_and_send_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Запускает процесс рассылки в фоновом режиме."""
    data = await state.get_data()
    text = data.get("text")

    if not text:
        await callback.answer("❗️ Нельзя отправить пустое сообщение.", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")]
    ])

    await callback.message.edit_text(
        "⏳ Рассылка всем пользователям начинается...",
        reply_markup=keyboard
    )
    asyncio.create_task(start_broadcast_task(bot, callback.from_user.id, data))
    await state.clear()
    await callback.answer()


async def start_broadcast_task(bot: Bot, admin_id: int, data: dict):
    """Выполняет фактическую рассылку сообщений как фоновую задачу."""
    text = data.get("text")
    button_text = data.get("button_text")
    button_url = data.get("button_url")

    markup = None
    if button_text and button_url:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button_text, url=button_url)]
        ])

    sent_count = 0
    failed_count = 0

    async with get_session() as session:
        user_ids = await get_all_user_ids(session)

    total_users = len(user_ids)
    logger.info(f"Начинается общая рассылка для {total_users} пользователей.")

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, text, reply_markup=markup)
            sent_count += 1
        except TelegramAPIError as e:
            logger.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
            failed_count += 1
        await asyncio.sleep(0.1)

    logger.info(f"Рассылка завершена. Отправлено: {sent_count}, Ошибок: {failed_count}")

    summary_text = (
        f"✅ **Общая рассылка завершена!**\n\n"
        f"👥 Всего пользователей для рассылки: {total_users}\n"
        f"👍 Успешно отправлено: {sent_count}\n"
        f"👎 Не удалось доставить: {failed_count}"
    )
    with suppress(TelegramAPIError):
        await bot.send_message(admin_id, summary_text, parse_mode="Markdown")
