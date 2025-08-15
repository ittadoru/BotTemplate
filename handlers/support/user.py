from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from config import SUPPORT_GROUP_ID
from states.support import Support
from utils import logger as log
from db.base import get_session
from db.support import create_ticket, get_ticket, close_ticket, SupportTicket
from sqlalchemy.future import select


router = Router()


@router.callback_query(lambda c: c.data == "help")
async def start_support(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает команду /help от пользователя.
    Если чат с поддержкой уже открыт, уведомляет об этом.
    Иначе создаёт новый тикет и открывает чат поддержки.
    """
    user_id = callback.from_user.id
    username = callback.from_user.username or ""
    async with get_session() as session:
        ticket = await session.execute(
            select(SupportTicket).where(SupportTicket.user_id == user_id, SupportTicket.is_closed == 0)
        )
        ticket = ticket.scalars().first()
        bot = callback.message.bot
        topic_id = None
        if ticket and getattr(ticket, "topic_id", None):
            topic_id = ticket.topic_id
        else:
            # Создаём новую тему с user_id
            new_topic = await bot.create_forum_topic(chat_id=SUPPORT_GROUP_ID, name=str(user_id))
            topic_id = new_topic.message_thread_id
            # Создаём тикет с topic_id
            ticket = await create_ticket(session, user_id, username, topic_id)
        log.log_message(
            f"Открыт чат поддержки для @{username or 'Без username'} | id={user_id}",
            emoji="💬"
        )
        await callback.message.answer(
            "🆘 Чат с поддержкой открыт!\n"
            "Чтобы завершить диалог, нажмите на /stop.\n"
            "Пока чат открыт, бот не будет реагировать на другие команды."
        )
        if topic_id:
            await bot.send_message(
                SUPPORT_GROUP_ID,
                f"👤 Новый тикет: @{username or 'Без username'} | {user_id}\nДиалог открыт.",
                message_thread_id=topic_id
            )
    await state.set_state(Support.waiting_for_message)


@router.message(Command("stop"), Support.waiting_for_message)
async def stop_support(message: Message, state: FSMContext):
    """
    Обрабатывает команду /stop, закрывает открытый чат поддержки пользователя.
    Оповещает как пользователя, так и группу поддержки.
    """
    user_id = message.from_user.id
    username = message.from_user.username or ""
    async with get_session() as session:
        ticket = await session.execute(
            select(SupportTicket).where(SupportTicket.user_id == user_id, SupportTicket.is_closed == 0)
        )
        ticket = ticket.scalars().first()
        if ticket:
            await close_ticket(session, user_id)
            log.log_message(
                f"Пользователь @{username or 'Без username'} | id={user_id} закрыл чат поддержки",
                emoji="🔒"
            )
            await message.answer("Диалог с поддержкой завершён. Бот снова доступен для скачивания видео.")
            topic_id = getattr(ticket, "topic_id", None)
            if topic_id:
                await message.bot.send_message(
                    SUPPORT_GROUP_ID,
                    "❌ Пользователь завершил диалог.",
                    message_thread_id=topic_id
                )
        else:
            await message.answer("У вас нет открытого диалога с поддержкой.")
        await state.clear()


@router.message(Support.waiting_for_message)
async def forward_to_support(message: Message, state: FSMContext):
    """
    Пересылает сообщения пользователя в группу поддержки, если тикет открыт.
    Поддерживаются текст и фото.
    """
    user_id = message.from_user.id
    username = message.from_user.username or ""
    async with get_session() as session:
        ticket = await session.execute(
            select(SupportTicket).where(SupportTicket.user_id == user_id, SupportTicket.is_closed == 0)
        )
        ticket = ticket.scalars().first()
        if not ticket:
            await message.answer("У вас нет открытого диалога с поддержкой. Напишите /help для начала.")
            await state.clear()
            return
        topic_id = getattr(ticket, "topic_id", None)
        if not topic_id:
            await message.answer("❗️ Не удалось найти тему поддержки. Попробуйте начать чат заново через /help.")
            await state.clear()
            return
        try:
            # Пересылаем текстовое сообщение
            if message.text:
                await message.bot.send_message(
                    SUPPORT_GROUP_ID,
                    f"Сообщение от @{username or 'Без username'} | {user_id}:\n{message.text}",
                    message_thread_id=topic_id
                )
            # Пересылаем фото, если есть
            if message.photo:
                await message.bot.send_photo(
                    SUPPORT_GROUP_ID,
                    message.photo[-1].file_id,
                    caption=f"Фото от @{username or 'Без username'} | {user_id}:\n{message.caption or ''}",
                    message_thread_id=topic_id
                )
            log.log_message(
                f"Пользователь @{username or 'Без username'} | id={user_id} отправил сообщение в поддержку: "
                f"{message.text or '[не текстовое сообщение]'}",
                emoji="📩"
            )
        except Exception as e:
            from aiogram.exceptions import TelegramBadRequest
            if isinstance(e, TelegramBadRequest) and "message thread not found" in str(e):
                await close_ticket(session, user_id)
                await message.answer("❗️ Диалог с поддержкой был удалён или устарел. Пожалуйста, начните чат заново через /help.")
                await state.clear()
                log.log_error(f"Тема поддержки не найдена для user_id={user_id}, topic_id={topic_id}. Тикет закрыт автоматически.")
            else:
                log.log_error(f"Ошибка при отправке сообщения в поддержку: {e}")
                await message.answer("❗️ Не удалось отправить сообщение в поддержку. Попробуйте позже.")
