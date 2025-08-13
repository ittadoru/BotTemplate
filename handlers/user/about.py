from aiogram import types, Router
from .menu import keyboard

router = Router()

@router.callback_query(lambda c: c.data == "more_info")
async def about_handler(callback: types.CallbackQuery):
    """
    Отвечает пользователю информацией о функционале бота.
    """
    about_text = (
        "👋 Привет! Я — твой помощник"
    )


    await callback.message.edit_text(about_text, reply_markup=keyboard, parse_mode="HTML")
