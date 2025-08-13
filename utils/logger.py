import logging
import traceback
import colorlog
import os
from logging.handlers import TimedRotatingFileHandler

# Создаем папку logs, если ее нет
os.makedirs("logs", exist_ok=True)

# === Цветной логгер для консоли ===
console_handler = colorlog.StreamHandler()
console_formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    },
)
console_handler.setFormatter(console_formatter)


# === Ротация файла раз в сутки ===
# Текущий день всегда пишет в logs/bot.log, при ротации файл переименовывается в logs/bot_YYYY-MM-DD.log
file_handler = TimedRotatingFileHandler(
    filename="logs/bot.log",
    when="midnight",
    interval=1,
    backupCount=30,           # Сколько логов хранить
    encoding="utf-8",
    utc=False
)

# Формат логов для файлов
file_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(file_formatter)

# === Кастомный постфикс для архивных файлов ===
def custom_rotator(source, dest):
    # dest по умолчанию logs/bot.log.YYYY-MM-DD
    dirname, basename = os.path.split(dest)
    date_part = basename.replace("bot.log.", "")
    new_name = os.path.join(dirname, f"bot_{date_part}.log")
    os.rename(source, new_name)

file_handler.rotator = custom_rotator

# === Общий логгер ===
logger = colorlog.getLogger("SaveBotLogger")
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)
logger.propagate = False


def log_message(message: str, level: int = 0, emoji: str = "", log_level: str = "info"):
    """
    Основная функция логирования с поддержкой отступов и эмодзи.
    level — уровень вложенности для отступа, emoji — добавляет визуальный акцент.
    """
    indent = " " * (level * 3)
    prefix = f"{emoji} " if emoji else ""
    full_message = f"{indent}{prefix}{message}"

    if log_level == "info":
        logger.info(full_message)
    elif log_level == "warning":
        logger.warning(full_message)
    elif log_level == "error":
        logger.error(full_message)
    else:
        logger.debug(full_message)

def log_error(error: Exception, username: str = "", context: str = ""):
    """
    Логирует исключение с полным трассировкой (traceback).
    Позволяет указать контекст ошибки и пользователя, при котором она произошла.
    """
    log_message(f"[ERROR] Произошла ошибка (@{username if username else "Без юзернейм"})", emoji="❌", log_level="error")
    if context:
        log_message(f"Контекст: {context}", level=1, log_level="error")
    if isinstance(error, BaseException):
        tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    else:
        tb = str(error)

    log_message(tb, level=1, log_level="error")
