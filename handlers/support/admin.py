import logging

from aiogram import F, Router
from aiogram.types import Message

from config import SUPPORT_GROUP_ID
from db.base import get_session
from db.support import close_ticket, get_open_ticket_by_topic_id

router = Router()


@router.message(F.chat.id == SUPPORT_GROUP_ID, F.is_topic_message)
async def admin_reply(message: Message):
    """
    Handles replies from administrators in support topics.
    Forwards text and photo messages to the user if the ticket is open.
    """
    # Ignore messages sent by the bot itself
    if message.from_user.is_bot:
        return

    topic_id = message.message_thread_id
    admin_id = message.from_user.id

    async with get_session() as session:
        ticket = await get_open_ticket_by_topic_id(session, topic_id)

        if not ticket:
            await message.reply("⚠️ Этот тикет уже закрыт. Сообщение не доставлено.")
            return

        user_id = ticket.user_id
        try:
            if message.text:
                await message.bot.send_message(user_id, f"💬 Ответ поддержки:\n{message.text}")
            elif message.photo:
                await message.bot.send_photo(
                    user_id,
                    message.photo[-1].file_id,
                    caption=f"💬 Ответ поддержки:\n{message.caption or ''}"
                )
            else:
                # Optional: handle other content types or notify admin
                await message.reply("ℹ️ Этот тип сообщения не поддерживается для пересылки.")
                return

            logging.info(
                f"Admin {admin_id} replied to user {user_id} in topic {topic_id}"
            )
        except Exception as e:
            logging.error(
                f"Failed to send message from admin {admin_id} to user {user_id}",
                exc_info=e
            )
            await message.reply(f"❗️ Не удалось доставить сообщение пользователю. Ошибка: {e}")


@router.message(F.chat.id == SUPPORT_GROUP_ID, F.is_topic_message, F.text.lower() == "/stop")
async def admin_close_ticket(message: Message):
    """
    Closes a ticket by the /stop command from an administrator.
    Notifies the user that the dialogue is closed.
    """
    topic_id = message.message_thread_id
    admin_id = message.from_user.id

    async with get_session() as session:
        ticket = await get_open_ticket_by_topic_id(session, topic_id)

        if not ticket:
            await message.reply("⚠️ Этот тикет уже закрыт.")
            return

        user_id = ticket.user_id
        await close_ticket(session, user_id)

        await message.bot.send_message(
            user_id,
            "❌ Администратор завершил диалог. Бот снова доступен для скачивания видео."
        )
        await message.reply("✅ Диалог с пользователем закрыт.")
        logging.info(f"Admin {admin_id} closed ticket for user {user_id} (topic {topic_id})")
