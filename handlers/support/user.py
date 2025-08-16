import logging
from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import SUPPORT_GROUP_ID
from db.base import get_session
from db.support import SupportTicket, close_ticket, create_ticket, get_open_ticket
from states.support import Support

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "help")
async def start_support_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начинает диалог с поддержкой.
    Проверяет, нет ли уже открытого тикета, и просит пользователя описать проблему.
    """
    user_id = callback.from_user.id
    async with get_session() as session:
        open_ticket: Optional[SupportTicket] = await get_open_ticket(session, user_id)
        if open_ticket:
            await callback.answer(
                "У вас уже есть активный диалог с поддержкой.", show_alert=True
            )
            return

    await state.set_state(Support.waiting_for_question)
    await callback.message.answer(
        "Опишите вашу проблему или вопрос одним сообщением. "
        "Я передам его в поддержку. Вы можете отправить текст, фото, видео или документ."
    )
    await callback.answer()


@router.message(Support.waiting_for_question)
async def create_ticket_handler(message: Message, state: FSMContext) -> None:
    """
    Создает тикет после получения первого сообщения от пользователя.
    Пересылает вопрос в группу поддержки и уведомляет пользователя.
    """
    await state.clear()
    user = message.from_user
    user_info = (
        f"👤 <b>Пользователь:</b> {user.full_name}\n"
        f"<b>ID:</b> <code>{user.id}</code>\n"
        f"<b>Username:</b> {f'@{user.username}' if user.username else 'не указан'}"
    )

    try:
        # Создаем тему в группе поддержки
        topic = await message.bot.create_forum_topic(
            chat_id=SUPPORT_GROUP_ID, name=f"Тикет от {user.id} ({user.full_name})"
        )
        # Отправляем информацию о пользователе
        await message.bot.send_message(
            SUPPORT_GROUP_ID, user_info, message_thread_id=topic.message_thread_id
        )
        # Копируем сообщение пользователя
        await message.copy_to(
            chat_id=SUPPORT_GROUP_ID, message_thread_id=topic.message_thread_id
        )

        async with get_session() as session:
            await create_ticket(
                session,
                user_id=user.id,
                username=user.username,
                topic_id=topic.message_thread_id,
            )

        await message.answer(
            "✅ Ваш вопрос передан в поддержку. Ожидайте ответа.\n\n"
            "Чтобы завершить диалог, отправьте команду /stop."
        )
        await state.set_state(Support.in_dialog)
        logger.info(
            "Пользователь %d создал новый тикет в теме %d",
            user.id,
            topic.message_thread_id,
        )

    except Exception as e:
        logger.error(
            "Не удалось создать тикет для пользователя %d: %s", user.id, e
        )
        await message.answer(
            "❗️ Произошла ошибка при создании обращения. Пожалуйста, попробуйте позже."
        )


@router.message(Support.in_dialog, F.text.lower().in_(["/stop", "стоп", "закрыть"]))
async def close_ticket_by_user_handler(message: Message, state: FSMContext) -> None:
    """
    Закрывает тикет по команде от пользователя.
    """
    user_id = message.from_user.id
    async with get_session() as session:
        ticket: Optional[SupportTicket] = await get_open_ticket(session, user_id)
        if not ticket:
            await message.answer("У вас нет активного диалога с поддержкой.")
            await state.clear()
            return

        await close_ticket(session, user_id)
        await state.clear()

        await message.answer("Диалог с поддержкой завершён. Вы снова можете пользоваться ботом.")
        try:
            await message.bot.send_message(
                SUPPORT_GROUP_ID,
                "❌ Пользователь завершил диалог.",
                message_thread_id=ticket.topic_id,
            )
        except Exception as e:
            logger.error(
                "Не удалось уведомить группу поддержки о закрытии тикета %d: %s",
                ticket.topic_id,
                e,
            )
        logger.info("Пользователь %d закрыл свой тикет.", user_id)


@router.message(Support.in_dialog)
async def forward_to_support_handler(message: Message) -> None:
    """
    Пересылает последующие сообщения пользователя в соответствующую тему поддержки.
    """
    user_id = message.from_user.id
    async with get_session() as session:
        ticket: Optional[SupportTicket] = await get_open_ticket(session, user_id)
        if not ticket:
            await message.answer("Ваш диалог с поддержкой уже закрыт. Чтобы начать новый, нажмите /help.")
            return

        try:
            await message.copy_to(
                chat_id=SUPPORT_GROUP_ID, message_thread_id=ticket.topic_id
            )
            logger.info(
                "Пользователь %d отправил сообщение в тикет %d",
                user_id,
                ticket.topic_id,
            )
        except Exception as e:
            logger.error(
                "Не удалось переслать сообщение от пользователя %d в тикет %d: %s",
                user_id,
                ticket.topic_id,
                e,
            )
            await message.answer("❗️ Не удалось доставить ваше сообщение. Попробуйте позже.")
