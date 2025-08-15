import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import register_handlers
from utils.logger import setup_logger

# Инициализация бота с HTML-парсингом по умолчанию
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Диспетчер с использованием памяти для хранения состояний FSM
dp = Dispatcher(storage=MemoryStorage())


async def main():
    """
    Основная функция для настройки, регистрации обработчиков и запуска polling.
    """
    # Настраиваем логирование, передавая объект бота
    setup_logger(bot)

    logging.info("Регистрация обработчиков...")
    register_handlers(dp)

    logging.info("Запуск бота...")
    # Удаляем все накопленные обновления перед запуском
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
    except Exception as e:
        # Логируем критическую ошибку перед падением
        logging.critical(f"Критическая ошибка при запуске: {e}", exc_info=True)
