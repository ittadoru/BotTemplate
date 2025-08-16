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
from db.users import get_user_ids_without_subscription

# Инициализация логгера
logger = logging.getLogger(__name__)


# --- Состояния и CallbackData ---

class AdBroadcastStates(StatesGroup):
    """Состояния для конструктора рекламной рассылки."""
    waiting_text = State()
    waiting_button_text = State()
    waiting_button_url = State()


class AdBroadcastCallback(CallbackData, prefix="ad_broadcast"):
    """
    Фабрика колбэков для управления конструктором рассылки.
    `action`: 'set_text', 'set_button', 'preview', 'send', 'cancel'
    """
    action: str


router = Router()


# --- Вспомогательные функции для UI ---

async def get_constructor_text(state: FSMContext) -> str:
    """
    Генерирует текст для сообщения-конструктора.
    """
    return (
        "📢 **Конструктор рекламной рассылки**\n\n"
        "Используйте кнопки ниже для настройки, предпросмотра и отправки."
    )


def get_constructor_keyboard() -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру для управления конструктором рассылки.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📝 Изменить текст",
                callback_data=AdBroadcastCallback(action="set_text").pack()
            ),
            InlineKeyboardButton(
                text="🔗 Изменить кнопку",
                callback_data=AdBroadcastCallback(action="set_button").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="👀 Предпросмотр",
                callback_data=AdBroadcastCallback(action="preview").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="🚀 Отправить",
                callback_data=AdBroadcastCallback(action="send").pack()
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=AdBroadcastCallback(action="cancel").pack()
            )
        ]
    ])


async def update_constructor_message(message: Message, state: FSMContext):
    """
    Обновляет сообщение-конструктор актуальными данными из FSM.
    """
    text = await get_constructor_text(state)
    keyboard = get_constructor_keyboard()
    with suppress(TelegramAPIError):
        await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")


# --- Основные хендлеры ---

@router.callback_query(F.data == "ad_broadcast_start")
async def ad_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """
    Запускает конструктор рекламной рассылки, сбрасывая предыдущее состояние.
    """
    await state.clear()
    # Сохраняем ID сообщения для его последующего редактирования
    await state.update_data(constructor_message_id=callback.message.message_id)
    await update_constructor_message(callback.message, state)
    await callback.answer()


@router.callback_query(AdBroadcastCallback.filter(F.action == "cancel"))
async def cancel_ad_broadcast(callback: CallbackQuery, state: FSMContext):
    """
    Отменяет конструктор рассылки и возвращает в главное меню.
    """
    from .menu import get_admin_menu_keyboard
    await state.clear()
    await callback.message.edit_text(
        "🔐 Админ-панель", reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


# --- Хендлеры для изменения параметров рассылки ---

@router.callback_query(AdBroadcastCallback.filter(F.action == "set_text"))
async def set_broadcast_text_prompt(callback: CallbackQuery, state: FSMContext):
    """
    Запрашивает у администратора текст для рассылки.
    """
    await state.set_state(AdBroadcastStates.waiting_text)
    prompt = await callback.message.answer("Введите текст для рекламной рассылки:")
    # Сохраняем ID сообщения с приглашением, чтобы потом его удалить
    await state.update_data(prompt_message_id=prompt.message_id)
    await callback.answer()


@router.message(AdBroadcastStates.waiting_text)
async def process_broadcast_text(message: Message, state: FSMContext, bot: Bot):
    """
    Сохраняет текст рассылки и обновляет сообщение-конструктор.
    """
    await state.update_data(text=message.text)
    await state.set_state(None)  # Выходим из состояния ожидания

    data = await state.get_data()
    constructor_msg_id = data.get("constructor_message_id")
    prompt_msg_id = data.get("prompt_message_id")

    # Удаляем сообщение с приглашением и ответ пользователя
    with suppress(TelegramAPIError):
        if prompt_msg_id:
            await bot.delete_message(message.chat.id, prompt_msg_id)
        await message.delete()

    if constructor_msg_id:
        # Редактируем исходное сообщение-конструктор
        # Создаем "прокси" объект Message для редактирования
        constructor_message = Message(
            message_id=constructor_msg_id, chat=message.chat, bot=bot
        )
        await update_constructor_message(constructor_message, state)
        
@router.callback_query(AdBroadcastCallback.filter(F.action == "set_button"))
async def set_button_text_prompt(callback: CallbackQuery, state: FSMContext):
    """
    Запрашивает текст для кнопки.
    """
    await state.set_state(AdBroadcastStates.waiting_button_text)
    prompt = await callback.message.answer("Введите текст для кнопки:")
    await state.update_data(prompt_message_id=prompt.message_id)
    await callback.answer()


@router.message(AdBroadcastStates.waiting_button_text)
async def process_button_text(message: Message, state: FSMContext, bot: Bot):
    """
    Сохраняет текст кнопки и запрашивает URL.
    """
    await state.update_data(button_text=message.text)
    await state.set_state(AdBroadcastStates.waiting_button_url)
    
    data = await state.get_data()
    prompt_msg_id = data.get("prompt_message_id")

    # Удаляем старое приглашение и ответ
    with suppress(TelegramAPIError):
        if prompt_msg_id:
            await bot.delete_message(message.chat.id, prompt_msg_id)
        await message.delete()

    # Отправляем новое приглашение
    prompt = await message.answer(
        "Отлично! Теперь введите URL-адрес для кнопки "
        "(начиная с http:// или https://):"
    )
    await state.update_data(prompt_message_id=prompt.message_id)


@router.message(AdBroadcastStates.waiting_button_url)
async def process_button_url(message: Message, state: FSMContext, bot: Bot):
    """
    Сохраняет URL кнопки и обновляет конструктор.
    """
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer(
            "Неверный формат ссылки. Пожалуйста, введите URL, "
            "начинающийся с http:// или https://."
        )
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

@router.callback_query(AdBroadcastCallback.filter(F.action == "preview"))
async def preview_ad_broadcast(callback: CallbackQuery, state: FSMContext):
    """
    Показывает администратору, как будет выглядеть сообщение для пользователя.
    """
    data = await state.get_data()
    text = data.get("text")

    if not text:
        await callback.answer(
            "❗️ Сначала нужно задать текст сообщения.", show_alert=True
        )
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


@router.callback_query(AdBroadcastCallback.filter(F.action == "send"))
async def confirm_and_send_broadcast(
    callback: CallbackQuery, state: FSMContext, bot: Bot
):
    """
    Запускает процесс рассылки в фоновом режиме после подтверждения.
    """
    data = await state.get_data()
    text = data.get("text")

    if not text:
        await callback.answer(
            "❗️ Нельзя отправить пустое сообщение. Задайте текст.",
            show_alert=True
        )
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")]
    ])

    await callback.message.edit_text(
        "⏳ Рассылка начинается... Вы получите отчет по завершении.",
        reply_markup=keyboard
    )

    # Запускаем тяжелую задачу в фоне
    asyncio.create_task(start_broadcast_task(bot, callback.from_user.id, data))

    await state.clear()
    await callback.answer()


async def start_broadcast_task(bot: Bot, admin_id: int, data: dict):
    """
    Выполняет фактическую рассылку сообщений пользователям как фоновую задачу.
    """
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
        user_ids = await get_user_ids_without_subscription(session)

    total_users = len(user_ids)
    logger.info(
        f"Начинается рекламная рассылка для {total_users} пользователей."
    )

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, text, reply_markup=markup)
            sent_count += 1
        except TelegramAPIError as e:
            logger.warning(
                f"Не удалось отправить сообщение пользователю {user_id}: {e}"
            )
            failed_count += 1
        # Небольшая задержка для избежания флуда и блокировки
        await asyncio.sleep(0.1)

    logger.info(
        f"Рассылка завершена. Отправлено: {sent_count}, "
        f"Ошибок: {failed_count}"
    )

    summary_text = (
        f"✅ **Рекламная рассылка завершена!**\n\n"
        f"👥 Всего пользователей для рассылки: {total_users}\n"
        f"👍 Успешно отправлено: {sent_count}\n"
        f"👎 Не удалось доставить: {failed_count}"
    )
    # Отправляем отчет администратору
    with suppress(TelegramAPIError):
        await bot.send_message(admin_id, summary_text, parse_mode="Markdown")
