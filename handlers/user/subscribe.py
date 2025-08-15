from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils.payment import create_payment
from db.tariff import get_all_tariffs, get_tariff_by_id
from db.base import get_session


router = Router()

@router.callback_query(lambda c: c.data == "subscribe")
async def subscribe_handler(callback: types.CallbackQuery):
    """
    Обработчик нажатия кнопки "Подписка" в меню профиля.
    """

    text = (
        "<b>💎 Преимущества подписки:</b>\n"
        "• Приоритетная поддержка\n\n"
        "Выберите вариант подписки:"
    )

    async with get_session() as session:
        tariffs = await get_all_tariffs(session)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{tariff.name} — {tariff.price} RUB",
            callback_data=f"buy_tariff:{tariff.id}"
        )] for tariff in tariffs
    ] + [
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()



@router.callback_query(lambda c: c.data and c.data.startswith("buy_tariff:"))
async def payment_callback_handler(callback: types.CallbackQuery):
    """
    Обработка нажатия кнопки "Оплатить" для тарифа.
    Создаёт платёж и отправляет ссылку на оплату.
    """
    user_id = callback.from_user.id
    
    try:
        tariff_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Некорректный тариф.", show_alert=True)
        return


    async with get_session() as session:
        tariff = await get_tariff_by_id(session, tariff_id)
    if not tariff:
        await callback.answer("Тариф не найден.", show_alert=True)
        return

    # Создаём платёж
    payment_url, payment_id = create_payment(
        user_id=user_id,
        amount=tariff.price,
        description=f"Подписка: {tariff.name}",
        bot_username=callback.message.from_user.username,
        metadata={
            "user_id": str(user_id),
            "tariff_id": str(tariff.id)
        }
    )

    await callback.message.edit_text(
        f"💳 Для оплаты тарифа <b>{tariff.name}</b> нажмите на кнопку оплаты",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🪙 Оплатить", url=payment_url)],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="subscribe")]
            ]
        )
    )
    await callback.answer()
