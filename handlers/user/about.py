
"""Информация о возможностях и бонусах SaverBot для пользователя."""

from aiogram import F, Router, types
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton


router = Router()

@router.callback_query(F.data == "more_info")
async def about_handler(callback: types.CallbackQuery) -> None:
    """
    Отвечает пользователю информацией о функционале бота.
    """
    about_text = (
        "<b>👋 Привет! Я — BotTemplate</b>\n\n"
        "<b>✨ Возможности:</b>\n"
        "<b>•</b> Подписка для расширенного доступа к функциям.\n"
        "<b>•</b> Промокоды и бонусы.\n\n"
        "<b>💎 Преимущества подписки:</b>\n"
        "<b>•</b> Нет рекламы.\n"
        "<b>•</b> Оформить подписку: /subscribe или через Профиль.\n\n"
        "<b>🤝 Реферальная программа:</b>\n"
        "<b>•</b> Приглашай друзей и получай бонусы!\n"
        "<b>•</b> Подробнее о реферальных уровнях — по кнопке ниже.\n\n"
        "<b>❓ Вопросы?</b>\n"
        "— Пиши в <b>техподдержку</b> через меню или команду /help."
    )

    await callback.message.edit_text(
        about_text, reply_markup=get_about_keyboard(), parse_mode="HTML"
    )
    await callback.answer()


def get_about_keyboard():
    """Клавиатура: Подробнее о рефералах + Назад в профиль."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="ℹ️ О реферальной программе", callback_data="referral_info")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")
    )
    return builder.as_markup()