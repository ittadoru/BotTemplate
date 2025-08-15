import logging
import os
import re
from aiogram import F, Router
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

LOG_DIR = "logs"

class LogCallback(CallbackData, prefix="log"):
    """Фабрика колбэков для выбора логов."""
    filename: str

router = Router()

def get_log_files():
    """Сканирует директорию логов и возвращает отсортированный список архивных файлов."""
    if not os.path.exists(LOG_DIR):
        return []
    
    # Регулярное выражение для поиска файлов формата bot_YYYY-MM-DD.log
    log_pattern = re.compile(r"^bot_(\d{4}-\d{2}-\d{2})\.log$")
    
    files = []
    for filename in os.listdir(LOG_DIR):
        if log_pattern.match(filename):
            files.append(filename)
            
    # Сортируем файлы по дате в обратном порядке (самые новые сверху)
    return sorted(files, reverse=True)

@router.callback_query(F.data == "get_logs")
async def show_log_menu(callback: CallbackQuery):
    """Показывает меню выбора типа логов: текущий или архивный."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📄 Текущий лог", callback_data=LogCallback(filename="bot.log").pack()),
        InlineKeyboardButton(text="🗂️ Архивные логи", callback_data="list_archive_logs")
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu"))

    await callback.message.edit_text(
        "Выберите, какой файл логов вы хотите получить:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "list_archive_logs")
async def list_archive_logs(callback: CallbackQuery):
    """Показывает список доступных архивных логов в виде кнопок."""
    archive_files = get_log_files()
    
    if not archive_files:
        await callback.answer("🗂️ Архивные логи не найдены.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for filename in archive_files:
        # Извлекаем дату из имени файла для текста на кнопке
        date_str = filename.replace("bot_", "").replace(".log", "")
        builder.row(
            InlineKeyboardButton(
                text=f"📄 {date_str}",
                callback_data=LogCallback(filename=filename).pack()
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="get_logs"))
    
    await callback.message.edit_text(
        "Выберите дату для выгрузки архивного лога:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(LogCallback.filter())
async def send_log_file(callback: CallbackQuery, callback_data: LogCallback):
    """Отправляет выбранный файл логов администратору."""
    filename = callback_data.filename
    log_path = os.path.join(LOG_DIR, filename)
    user_id = callback.from_user.id

    if not os.path.exists(log_path):
        logging.warning(f"Админ {user_id} запросил несуществующий лог: {filename}")
        await callback.answer(f"❗️ Файл логов '{filename}' не найден.", show_alert=True)
        return

    if os.path.getsize(log_path) == 0:
        logging.warning(f"Админ {user_id} запросил пустой лог: {filename}")
        await callback.answer(f"⚠️ Файл логов '{filename}' пуст.", show_alert=True)
        return

    logging.info(f"Админ {user_id} запросил лог: {filename}")
    
    file = FSInputFile(log_path)
    await callback.message.answer_document(file, caption=f"📄 Ваш файл логов: `{filename}`")
    await callback.answer()
