

import io
import csv
from db.base import get_session, Base
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import Router

router = Router()


# --- Экспорт таблиц ---
def get_all_models():
    # Получить все модели, наследующиеся от Base
    return [mapper.class_ for mapper in Base.registry.mappers]

def get_table_keyboard():
    models = get_all_models()
    keyboard = []
    for model in models:
        table_name = model.__tablename__
        btn = InlineKeyboardButton(text=table_name, callback_data=f"export_table_{table_name}")
        keyboard.append([btn])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.callback_query(lambda c: c.data == "export_table_menu")
async def export_table_menu(callback: CallbackQuery):
    await callback.message.edit_text("Выберите таблицу для экспорта:", reply_markup=get_table_keyboard())
    await callback.answer()


# Универсальный обработчик экспорта любой таблицы
@router.callback_query(lambda c: c.data.startswith("export_table_") and c.data != "export_table_menu")
async def export_table(callback: CallbackQuery):
    table_name = callback.data.replace("export_table_", "")
    # Найти модель по имени таблицы
    model = next((m for m in get_all_models() if m.__tablename__ == table_name), None)
    if not model:
        await callback.answer("Таблица не найдена", show_alert=True)
        return
    async with get_session() as session:
        result = await session.execute(model.__table__.select())
        rows = result.fetchall()
        headers = result.keys()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([str(col) if col is not None else "" for col in row])
    output.seek(0)
    file = FSInputFile(io.BytesIO(output.getvalue().encode()), f"{table_name}.csv")
    await callback.message.answer_document(file, caption=f"Экспорт: {table_name}.csv")
    await callback.answer()