from aiogram import Router, F, types
from aiogram.types import Message
from config import SUPPORT_GROUP_ID
from db.base import get_session
from db.support import get_ticket, close_ticket, SupportTicket
from sqlalchemy.future import select
from utils import logger as log

router = Router()


@router.message(F.chat.id == SUPPORT_GROUP_ID, F.is_topic_message)
async def admin_reply(message: Message):
    """
    Обрабатывает ответы админов в теме поддержки.
    Пересылает текстовые и фото сообщения пользователю, если тикет открыт.
    """
    topic_id = message.message_thread_id
    # user_id = await get_user_id_by_topic(session, topic_id)
    # Новый способ: user_id = название темы
    user_id = None
    async with get_session() as session:
        ticket = await session.execute(
            select(SupportTicket).where(SupportTicket.topic_id == topic_id, SupportTicket.is_closed == 0)
        )
        ticket = ticket.scalars().first()
        if not ticket:
            await message.reply("Тикет уже закрыт.")
            return
        user_id = ticket.user_id
        if message.text:
            await message.bot.send_message(
                user_id,
                f"💬 Ответ поддержки:\n{message.text}"
            )
        if message.photo:
            await message.bot.send_photo(
                user_id,
                message.photo[-1].file_id,
                caption=f"💬 Ответ поддержки:\n{message.caption or ''}"
            )
        log.log_message(
            f"👨‍💻 Админ ответил пользователю id={user_id} в тикете topic_id={topic_id}: "
            f"{message.text or '[не текстовое сообщение]'}",
            emoji="🛠️"
        )

    # TODO: Добавить обработку других типов сообщений (документы, аудио и т.п.) по необходимости


@router.message(F.chat.id == SUPPORT_GROUP_ID, F.is_topic_message, F.text == "/stop")
async def admin_close_ticket(message: Message):
    """
    Закрывает тикет по команде /stop от админа.
    Отправляет пользователю уведомление о закрытии диалога.
    """
    topic_id = message.message_thread_id
    async with get_session() as session:
        ticket = await session.execute(
            select(SupportTicket).where(SupportTicket.topic_id == topic_id, SupportTicket.is_closed == 0)
        )
        ticket = ticket.scalars().first()
        if not ticket:
            return
        user_id = ticket.user_id
        await close_ticket(session, user_id)
        await message.bot.send_message(
            user_id,
            "❌ Администратор завершил диалог. Бот снова доступен для скачивания видео."
        )
        await message.reply("Диалог с пользователем закрыт.")
