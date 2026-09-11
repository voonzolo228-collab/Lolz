"""
Фоновий цикл моніторингу MRKT.

Для контролю навантаження: один цикл робить ОДИН прохід пагінації
по глобальному пулу лістингів (обмежений max_pages), і цей же пул
використовується для аналізу всіх активних користувачів одночасно -
замість того, щоб кожен користувач ініціював окремі важкі запити.
"""
import asyncio
import logging
from typing import Any

from aiogram import Bot

from database.db import Database
from mrkt.client import MrktClient, MrktApiError
from mrkt.models import Gift
from services.analyzer import estimate_market_price, liquidity_proxy
from services.notifications import format_opportunity_message, send_opportunity
from services.scoring import compute_opportunity
from utils.number_beauty import score_number_beauty

logger = logging.getLogger("services.monitor")

SIGNIFICANT_PRICE_CHANGE_RATIO = 0.05  # 5% - поріг для повторного сповіщення
GLOBAL_SCAN_MAX_PAGES = 15  # ~300 лістингів за цикл - контрольоване навантаження


class MonitorService:
    def __init__(self, bot: Bot, db: Database, mrkt_client: MrktClient):
        self._bot = bot
        self._db = db
        self._mrkt = mrkt_client
        self._running = False
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Monitor service запущено.")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._run_cycle()
            except MrktApiError as exc:
                logger.error("Помилка MRKT API під час циклу моніторингу: %s", exc)
            except Exception:
                logger.exception("Неочікувана помилка в циклі моніторингу")

            # Найкоротший запитаний користувачами інтервал визначає частоту циклу,
            # але не частіше ніж раз на 10 секунд навіть якщо хтось так налаштує.
            users = await self._db.all_active_users()
            if not users:
                await asyncio.sleep(30)
                continue
            min_interval = max(min(u["interval_seconds"] for u in users), 10)
            await asyncio.sleep(min_interval)

    async def _run_cycle(self) -> None:
        users = await self._db.all_active_users()
        if not users:
            return

        try:
            universe: list[Gift] = await self._mrkt.fetch_gifts_all(
                max_pages=GLOBAL_SCAN_MAX_PAGES, ordering="Price", low_to_high=True
            )
        except MrktApiError as exc:
            logger.error("Не вдалося отримати глобальний пул лістингів: %s", exc)
            return

        if not universe:
            logger.info("MRKT не повернув активних лістингів у цьому циклі.")
            return

        for user in users:
            await self._process_user(user, universe)

        await self._db.cleanup_old_seen()

    async def _process_user(self, user: dict[str, Any], universe: list[Gift]) -> None:
        chat_id = user["chat_id"]
        min_profit = user["min_profit_ton"] or 0
        min_score = user["min_opportunity_score"] or 0
        max_price = user["max_purchase_price"]
        price_min = user["price_min"]
        price_max = user["price_max"]

        import json

        collections_filter = set(json.loads(user["collections_json"] or "[]"))

        candidates = [g for g in universe if g.price_ton is not None]
        if max_price is not None:
            candidates = [g for g in candidates if g.price_ton <= max_price]
        if price_min is not None:
            candidates = [g for g in candidates if g.price_ton >= price_min]
        if price_max is not None:
            candidates = [g for g in candidates if g.price_ton <= price_max]
        if collections_filter:
            candidates = [g for g in candidates if g.collection in collections_filter]

        for gift in candidates:
            estimate = estimate_market_price(gift, universe)
            if estimate is None:
                continue

            liquidity = liquidity_proxy(gift, universe)
            beauty_score, _ = score_number_beauty(gift.number) if gift.number is not None else (0, [])

            result = compute_opportunity(gift.price_ton, estimate, liquidity, beauty_score)
            if result is None:
                continue
            if result.score < min_score:
                continue
            if result.potential_profit_net < min_profit:
                continue

            await self._maybe_notify(user, gift, estimate, liquidity, result)

    async def _maybe_notify(self, user: dict[str, Any], gift, estimate, liquidity, result) -> None:
        if not user["notifications_enabled"]:
            return
        chat_id = user["chat_id"]
        seen = await self._db.get_seen(chat_id, gift.gift_id)
        if seen:
            last_price = seen["last_price"]
            if last_price and gift.price_ton is not None:
                change_ratio = abs(gift.price_ton - last_price) / last_price
                if change_ratio < SIGNIFICANT_PRICE_CHANGE_RATIO:
                    return  # вже сповіщали, ціна суттєво не змінилась - уникаємо спаму

        text = format_opportunity_message(gift, estimate, liquidity, result)
        await send_opportunity(self._bot, chat_id, text)
        await self._db.mark_seen(chat_id, gift.gift_id, gift.price_ton)
