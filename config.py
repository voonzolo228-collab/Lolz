"""
Централізована конфігурація. Всі секрети беруться виключно з .env.
Ніколи не хардкодь тут реальні значення.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Змінна оточення {name} не задана. Заповни її у файлі .env "
            f"(скопіюй .env.example -> .env і впиши значення)."
        )
    return value


def _optional_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    # Telegram bot
    bot_token: str

    # Telegram user client (потрібен для отримання MRKT init_data через Mini App)
    api_id: int
    api_hash: str
    pyrogram_session_name: str

    # Кому бот дозволено писати / хто власник (сповіщення йдуть саме сюди)
    owner_chat_id: int

    # MRKT
    mrkt_bot_username: str
    mrkt_api_base: str

    # DB
    db_path: str

    # Логування
    log_level: str


def load_settings() -> Settings:
    return Settings(
        bot_token=_require("BOT_TOKEN"),
        api_id=int(_require("API_ID")),
        api_hash=_require("API_HASH"),
        pyrogram_session_name=os.getenv("PYROGRAM_SESSION_NAME", "mrkt_user_session"),
        owner_chat_id=int(_require("OWNER_CHAT_ID")),
        mrkt_bot_username=os.getenv("MRKT_BOT_USERNAME", "mrkt"),
        mrkt_api_base=os.getenv("MRKT_API_BASE", "https://api.tgmrkt.io/api/v1"),
        db_path=os.getenv("DB_PATH", "mrkt_bot.sqlite3"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


settings = load_settings()
