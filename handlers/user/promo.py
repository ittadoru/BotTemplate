import logging

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from db.base import get_session
from db.promocodes import activate_promocode
from states.promo import PromoStates

router = Router()


@router.callback_query(F.data == "promo")
async def promo_start(callback: types.CallbackQuery, state: FSMContext):
    """
    Запускает процесс активации промокода пользователем.
    """
    bot_message = await callback.message.answer("Пожалуйста, введите промокод для активации:")
    await state.update_data(last_bot_message_id=bot_message.message_id)
    await state.set_state(PromoStates.user)
    await callback.answer()


@router.message(PromoStates.user)
async def process_user_promocode(message: types.Message, state: FSMContext):
    """
    Обрабатывает введенный пользователем промокод, активирует его и сообщает результат.
    """
    if not message.text:
        await state.clear()
        return

    code = message.text.strip().upper()
    user = message.from_user

    async with get_session() as session:
        # Функция возвращает длительность подписки в днях или None в случае неудачи.
        duration = await activate_promocode(session, user.id, code)

    # Пытаемся удалить сообщение с просьбой ввести код, чтобы не засорять чат
    try:
        data = await state.get_data()
        if "last_bot_message_id" in data:
            await message.bot.delete_message(message.chat.id, data["last_bot_message_id"])
    except Exception as e:
        logging.error(f"Не удалось удалить сообщение с запросом промокода: {e}")

    if duration:
        logging.info(
            f"Пользователь {user.full_name} ({user.id}) "
            f"успешно активировал промокод '{code}' на {duration} дней."
        )
        await message.answer(
            f"🎉 <b>Промокод успешно активирован!</b>\n"
            f"Ваша подписка продлена на <b>{duration}</b> дн.",
            parse_mode="HTML"
        )
    else:
        logging.warning(
            f"Пользователь {user.full_name} ({user.id}) "
            f"не смог активировать промокод '{code}'."
        )
        await message.answer(
            "⚠️ <b>Промокод не найден или уже был использован.</b>\n"
            "Проверьте правильность ввода и попробуйте снова.",
            parse_mode="HTML"
        )

    await state.clear()
