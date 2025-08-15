import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler
from aiogram import Bot
from config import ADMIN_ERROR

# --- Custom Telegram Handler ---
class TelegramErrorHandler(logging.Handler):
    """
    Кастомный обработчик для отправки критических логов в Telegram.
    """
    def __init__(self, bot: Bot, level=logging.ERROR):
        super().__init__(level=level)
        self.bot = bot
        self.last_sent_time = 0
        self.cooldown = 60  # seconds

    def emit(self, record: logging.LogRecord):
        current_time = time.time()
        if current_time - self.last_sent_time < self.cooldown:
            return  # Не отправляем, если не прошел кулдаун

        log_entry = self.format(record)
        # Экранируем символы, которые могут быть интерпретированы как Markdown/HTML
        log_entry = log_entry.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Обрезаем сообщение, если оно слишком длинное
        if len(log_entry) > 4000:
            log_entry = log_entry[:4000] + "\n... (сообщение обрезано)"

        try:
            import asyncio
            # Проверяем, запущен ли event loop, чтобы избежать ошибки RuntimeError
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    self.bot.send_message(
                        chat_id=ADMIN_ERROR,
                        text=f"🆘 <b>Обнаружена ошибка:</b>\n\n<pre>{log_entry}</pre>",
                        parse_mode="HTML"
                    )
                )
                self.last_sent_time = current_time
            except RuntimeError:
                 # Если event loop не запущен, мы не можем отправить сообщение.
                 # Это может произойти при ошибках на самом старте приложения.
                 logging.getLogger(__name__).warning("Не удалось отправить лог в Telegram: event loop не запущен.")

        except Exception as e:
            # Если отправка не удалась, логируем это стандартным способом
            logging.getLogger(__name__).exception(f"Не удалось отправить лог ошибки в Telegram: {e}")


# --- File Rotation Setup ---
def custom_rotator(source, dest):
    """
    Переименовывает архивные логи в формат bot_YYYY-MM-DD.log
    """
    dirname, basename = os.path.split(dest)
    # dest по умолчанию logs/bot.log.YYYY-MM-DD
    date_part = basename.split('.')[-1]
    new_name = os.path.join(dirname, f"bot_{date_part}.log")
    if os.path.exists(new_name):
        os.remove(new_name)
    os.rename(source, new_name)

# --- Main Setup Function ---
def setup_logger(bot: Bot = None):
    """
    Настраивает корневой логгер для всего приложения.
    - Пишет DEBUG логи в файл с ротацией.
    - Пишет INFO логи в консоль.
    - Отправляет ERROR логи в Telegram, если передан bot.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # --- Форматтеры ---
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )

    # --- Обработчик для файла (с ротацией) ---
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "bot.log"),
        when="midnight",
        interval=1,
        backupCount=14,  # Храним логи за 14 дней
        encoding="utf-8"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)  # В файл пишем всё, начиная с DEBUG
    file_handler.rotator = custom_rotator

    # --- Обработчик для консоли ---
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO) # В консоль выводим только INFO и выше

    # --- Получаем корневой логгер и настраиваем его ---
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG) # Устанавливаем самый низкий уровень на корневом логгере
    
    # Очищаем предыдущие обработчики, чтобы избежать дублирования
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # --- Обработчик для Telegram (если передан бот) ---
    if bot:
        error_formatter = logging.Formatter(
            "%(levelname)s | %(name)s:%(lineno)d\n\n%(message)s"
        )
        telegram_handler = TelegramErrorHandler(bot=bot)
        telegram_handler.setFormatter(error_formatter)
        root_logger.addHandler(telegram_handler)

    # Перенаправляем логи от uvicorn и aiogram в нашу систему
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    
    logging.info("Система логирования успешно настроена.")

def log_message(message: str, level: int = 0, emoji: str = "", log_level: str = "info"):
    """
    Удобная обертка для логирования сообщений в старом стиле.
    level — уровень вложенности для отступа, emoji — добавляет визуальный акцент.
    """
    indent = " " * (level * 3)
    prefix = f"{emoji} " if emoji else ""
    full_message = f"{indent}{prefix}{message}"

    # Получаем тот же логгер, который мы настроили
    logger = logging.getLogger()

    if log_level == "info":
        logger.info(full_message)
    elif log_level == "warning":
        logger.warning(full_message)
    elif log_level == "error":
        logger.error(full_message)
    elif log_level == "debug":
        logger.debug(full_message)
    else:
        logger.info(full_message) # По умолчанию info

def log_error(error: Exception, context: str = ""):
    """
    Логирует исключение с полным трассировкой (traceback).
    """
    logger = logging.getLogger()
    
    # Формируем сообщение с контекстом, если он есть
    error_message = f"Произошла ошибка: {context}" if context else "Произошла ошибка"
    
    # Используем exc_info=True, чтобы автоматически добавить traceback
    logger.error(error_message, exc_info=error)
