from aiogram import Router, types, Bot
from aiogram.filters import Command
from db.base import get_session
from db.subscribers import add_promocode
from db.users import add_user, is_user_exists
import random

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, bot: Bot):
    """
    Обрабатывает команду /start.
    Проверяет, новый ли пользователь, и добавляет его в базу данных.
    Если пользователь новый, генерирует уникальный промокод на 7 дней подписки.
    """
    async with get_session() as session:
        is_new = not await is_user_exists(session, message.from_user.id)
        await add_user(session, message.from_user.id, first_name=message.from_user.first_name, username=message.from_user.username)
    username = message.from_user.username or message.from_user.full_name or "пользователь"

    if is_new:
        # Генерируем уникальный промокод для нового пользователя
        promo_code = f"WELCOME-{random.randint(100000, 999999)}"
        await add_promocode(promo_code, duration_days=7)
        promo_text = (
            f"В подарок тебе промокод на 7 дней подписки: <pre>{promo_code}</pre>\n"
            "Активируй его через меню профиля, нажми на команду /profile.\n\n"
        )
    else:
        promo_text = ""

    await message.answer(
        f"👋 Привет, {username}!\n\n"
        f"{promo_text}"
        "Твой <b>профиль</b> со статистикой и лимитами всегда доступен через меню по команду /profile.",
        parse_mode="HTML"
    )
