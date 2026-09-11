"""
Точка входу бота.

Перший запуск:
1. Pyrogram запросить твій номер телефону (уже в .env, підставиться сам),
   потім КОД ПІДТВЕРДЖЕННЯ прямо в консолі (не в Telegram-чат з ботом) -
   введи його в термінал, де запущено `python main.py`. Якщо в акаунті
   увімкнена 2FA, Pyrogram так само запросить пароль у консолі.
2. Після цього створюється файл сесії (PYROGRAM_SESSION_NAME.session) -
   наступні запуски вже не питатимуть код повторно, поки сесія жива.
3. Бот отримує MRKT auth token автоматично через Mini App init_data.
4. Стартує aiogram-бот і фоновий цикл моніторингу.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from pyrogram import Client as PyrogramClient

from config import settings
from utils.logger import setup_logging
from database.db import Database
from mrkt.auth import MrktAuth
from mrkt.client import MrktClient
from services.monitor import MonitorService

from bot.handlers import menu, turnover, price_range, monochrome, rare_numbers, best_deals, settings as settings_handlers

logger = logging.getLogger("main")


async def main() -> None:
    setup_logging(settings.log_level)
    logger.info("Запуск MRKT monitoring bot...")

    db = Database(settings.db_path)
    await db.connect()

    pyrogram_client = PyrogramClient(
        settings.pyrogram_session_name,
        api_id=settings.api_id,
        api_hash=settings.api_hash,
    )
    await pyrogram_client.start()
    logger.info("Pyrogram user client авторизовано.")

    mrkt_auth = MrktAuth(pyrogram_client, settings.mrkt_api_base, settings.mrkt_bot_username)
    await mrkt_auth.refresh_token()
    logger.info("MRKT auth token отримано.")

    mrkt_client = MrktClient(settings.mrkt_api_base, mrkt_auth)

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=None))
    dp = Dispatcher()

    dp.include_router(menu.router)
    dp.include_router(turnover.router)
    dp.include_router(price_range.router)
    dp.include_router(monochrome.router)
    dp.include_router(rare_numbers.router)
    dp.include_router(best_deals.router)
    dp.include_router(settings_handlers.router)

    monitor = MonitorService(bot, db, mrkt_client)
    monitor.start()

    try:
        await dp.start_polling(bot, mrkt_client=mrkt_client, db=db)
    finally:
        await monitor.stop()
        await pyrogram_client.stop()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
