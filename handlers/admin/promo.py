from aiogram import Router, types
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from db.base import get_session
from db.subscribers import get_all_promocodes, remove_promocode, add_promocode, remove_all_promocodes
from utils import logger as log
from config import ADMINS
from states.promo import PromoStates

router = Router()

# Обработка нажатия кнопки "Добавить промокод"
@router.callback_query(lambda c: c.data == "add_promocode")
async def add_promocode_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите промокод и срок действия (дней) через пробел.\nПример: CODE123 30"
    )
    await state.set_state(PromoStates.add)
    await callback.answer()


# Обработка ввода промокода
@router.message(PromoStates.add)
async def process_add_promocode(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return

    data = await state.get_data()
    attempts = data.get("add_attempts", 0)

    if message.text:
        parts = message.text.strip().split()
        if len(parts) == 2 and parts[1].isdigit():
            code, days = parts[0], int(parts[1])
            async with get_session() as session:
                await add_promocode(session, code, days)

            log.log_message(f"Добавлен промокод: {code} на {days} дней админом ", emoji="🎟")
            log.log_message(f"{message.from_user.username} ({message.from_user.id})", level=1)

            await message.answer(f"Промокод {code} на {days} дней добавлен.")
            await state.clear()
        else:
            attempts += 1
            if attempts < 2:
                await state.update_data(add_attempts=attempts)
                await message.answer("Неверный формат. Пример: CODE123 30\nПопробуйте ещё раз.")
            else:
                await message.answer("Вы дважды ошиблись с форматом. Операция отменена.")
                await state.clear()


# Обработка нажатия кнопки "Удалить промокод"
@router.callback_query(lambda c: c.data == "remove_promocode")
async def remove_promocode_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите промокод для удаления:")
    await state.set_state(PromoStates.remove)
    await callback.answer()

# Обработка удаления промокода
@router.message(PromoStates.remove)
async def process_remove_promocode(message: types.Message, state: FSMContext):
    code = message.text.strip()
    async with get_session() as session:
        promocodes = await get_all_promocodes(session)
        if code in [p.code for p in promocodes]:
            await remove_promocode(session, code)
            log.log_message(f"Удалён промокод: {code} админом ", emoji="🗑")
            log.log_message(f"{message.from_user.username} ({message.from_user.id})", level=1)
            text = f"Промокод {code} удалён."
        else:
            text = f"Промокод {code} не найден."

    await message.answer(text)
    await state.clear()

# Обработка нажатия кнопки "Все промокоды"
@router.callback_query(lambda c: c.data == "all_promocodes")
async def show_all_promocodes(callback: CallbackQuery):
    from db.base import get_session
    async with get_session() as session:
        promocodes = await get_all_promocodes(session)

        if promocodes:
            text = "<b>🎟 Все промокоды:</b>\n" + "\n".join(
                [f"{p.code}: \t{p.duration_days} дней" for p in promocodes]
            )
        else:
            text = "❌ Нет активных промокодов."

    await callback.message.edit_text(text, parse_mode="HTML", 
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                         [InlineKeyboardButton(text="⬅️ Назад", callback_data="promocode_menu")]
                                     ]))
    await callback.answer()

@router.callback_query(lambda c: c.data == "remove_all_promocodes")
async def remove_all_promocodes_handler(callback: CallbackQuery):
    async with get_session() as session:
        await remove_all_promocodes(session)
        log.log_message("Удалены все промокоды админом", emoji="🗑")
        await callback.message.answer("❌ Все промокоды удалены.")
        await callback.answer()