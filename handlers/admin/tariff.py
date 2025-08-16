import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMINS
from db.base import get_session
from db.tariff import create_tariff, delete_tariff, get_all_tariffs
from states.tariff import TariffStates

# Инициализация логгера для этого модуля
logger = logging.getLogger(__name__)

# Создание роутера и применение фильтра ко всем хендлерам (только для админов)
router = Router()
router.message.filter(F.from_user.id.in_(ADMINS))
router.callback_query.filter(F.from_user.id.in_(ADMINS))


@router.callback_query(F.data == "tariff_menu")
async def tariff_menu_callback(callback: CallbackQuery) -> None:
    """Обрабатывает нажатие на кнопку 'tariff_menu'."""
    await tariff_menu(message=callback.message, edit=True)
    await callback.answer()


async def tariff_menu(message: Message, edit: bool = False) -> None:
    """Отображает меню управления тарифами."""
    text = "Меню управления тарифами:"
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить тариф", callback_data="add_tariff")
    builder.button(text="✖️ Удалить тариф", callback_data="delete_tariff_menu")
    builder.button(text="⬅️ Назад", callback_data="admin_menu")
    builder.adjust(1)

    if edit:
        await message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "delete_tariff_menu")
async def delete_tariff_menu_callback(callback: CallbackQuery) -> None:
    """Отображает меню для удаления тарифов."""
    async with get_session() as session:
        tariffs = await get_all_tariffs(session)

    builder = InlineKeyboardBuilder()
    if not tariffs:
        builder.button(text="⬅️ Назад", callback_data="tariff_menu")
        await callback.message.edit_text(
            "Список тарифов пуст.", reply_markup=builder.as_markup()
        )
        await callback.answer()
        return

    for t in tariffs:
        builder.button(
            text=f"❌ {t.name} ({t.duration_days} д., {t.price} ₽)",
            callback_data=f"delete_tariff_confirm:{t.id}",
        )
    builder.button(text="⬅️ Назад", callback_data="tariff_menu")
    builder.adjust(1)

    await callback.message.edit_text(
        "Выберите тариф для удаления:", reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "add_tariff")
async def start_add_tariff(callback: CallbackQuery, state: FSMContext) -> None:
    """Начинает процесс добавления нового тарифа."""
    await callback.message.edit_text("Введите название нового тарифа:")
    await state.set_state(TariffStates.waiting_for_name)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_tariff_confirm:"))
async def delete_tariff_handler(callback: CallbackQuery) -> None:
    """Удаляет выбранный тариф и обновляет меню удаления."""
    tariff_id = int(callback.data.split(":")[1])
    async with get_session() as session:
        await delete_tariff(session, tariff_id)

    logger.info(
        "Администратор %d удалил тариф с id %d", callback.from_user.id, tariff_id
    )
    # Просто подтверждаем колбэк, чтобы убрать "часики"
    await callback.answer()

    # Обновляем меню удаления, чтобы показать актуальный список
    await delete_tariff_menu_callback(callback)


@router.message(TariffStates.waiting_for_name)
async def process_tariff_name(message: Message, state: FSMContext) -> None:
    """Обрабатывает название тарифа и запрашивает длительность."""
    if not message.text or len(message.text) > 50:
        await message.answer(
            "Название не должно быть пустым или длиннее 50 символов. "
            "Пожалуйста, введите корректное название:"
        )
        return
    await state.update_data(name=message.text.strip())
    await message.answer("Отлично! Теперь введите длительность тарифа в днях:")
    await state.set_state(TariffStates.waiting_for_days)


@router.message(TariffStates.waiting_for_days)
async def process_tariff_days(message: Message, state: FSMContext) -> None:
    """Обрабатывает длительность тарифа и запрашивает цену."""
    if not message.text.isdigit() or not 0 < int(message.text) < 10000:
        await message.answer(
            "Пожалуйста, введите корректное количество дней (целое число от 1 до 9999):"
        )
        return
    await state.update_data(days=int(message.text))
    await message.answer("Теперь введите цену тарифа в рублях (например, 99.90):")
    await state.set_state(TariffStates.waiting_for_price)


@router.message(TariffStates.waiting_for_price)
async def process_tariff_price(message: Message, state: FSMContext) -> None:
    """Обрабатывает ввод цены и создаёт новый тариф."""
    try:
        price = float(message.text.replace(",", "."))
        if not 0 < price < 1000000:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer(
            "Пожалуйста, введите корректную цену (число, например, 199.50):"
        )
        return

    data = await state.get_data()
    name = data["name"]
    days = data["days"]

    async with get_session() as session:
        await create_tariff(session, name=name, price=price, duration_days=days)

    logger.info(
        "Админ %d создал новый тариф: %s, %d дней, %.2f RUB",
        message.from_user.id,
        name,
        days,
        price,
    )

    await message.answer(
        f"✅ Тариф «{name}» успешно добавлен!\n"
        f"Длительность: {days} дней\n"
        f"Цена: {price:.2f} ₽"
    )
    await state.clear()

    # Отображаем главное меню тарифов
    await tariff_menu(message=message)
