import logging

from aiogram import Router, F
from aiogram.types import Message

from bot.keyboards.main_menu import MAIN_MENU_BUTTONS
from database.db import Database
from mrkt.client import MrktClient, MrktApiError
from services.analyzer import estimate_market_price, liquidity_proxy
from services.scoring import compute_opportunity
from utils.number_beauty import score_number_beauty

logger = logging.getLogger("bot.best_deals")
router = Router(name="best_deals")

SCAN_PAGES = 15
TOP_N = 10


@router.message(F.text == MAIN_MENU_BUTTONS[5])
async def show_best_deals(message: Message, mrkt_client: MrktClient, db: Database) -> None:
    user = await db.get_or_create_user(message.chat.id)
    await message.answer("🔥 Шукаю найвигідніші можливості зараз, це займе кілька секунд...")

    try:
        universe = await mrkt_client.fetch_gifts_all(max_pages=SCAN_PAGES)
    except MrktApiError as exc:
        await message.answer(f"Не вдалося отримати дані з MRKT: {exc}")
        return

    if not universe:
        await message.answer("MRKT не повернув активних лістингів.")
        return

    min_score = user["min_opportunity_score"] or 0
    min_profit = user["min_profit_ton"] or 0
    max_price = user["max_purchase_price"]

    results = []
    for gift in universe:
        if gift.price_ton is None:
            continue
        if max_price is not None and gift.price_ton > max_price:
            continue

        estimate = estimate_market_price(gift, universe)
        if estimate is None:
            continue

        liquidity = liquidity_proxy(gift, universe)
        beauty_score, _ = score_number_beauty(gift.number) if gift.number is not None else (0, [])
        result = compute_opportunity(gift.price_ton, estimate, liquidity, beauty_score)
        if result is None:
            continue
        if result.score < min_score or result.potential_profit_net < min_profit:
            continue

        results.append((result.score, gift, estimate, result))

    results.sort(key=lambda t: t[0], reverse=True)
    top = results[:TOP_N]

    if not top:
        await message.answer(
            "Зараз немає можливостей, що відповідають твоїм критеріям "
            "(див. ⚙️ Налаштування — можливо, поріг min score/profit занадто високий)."
        )
        return

    lines = ["🔥 Найвигідніші можливості зараз:", ""]
    for score, gift, estimate, result in top:
        lines.append(
            f"⭐ {result.score}/100 — {gift.collection} {gift.model or ''} "
            f"#{gift.number if gift.number is not None else '—'}\n"
            f"  Купівля: {gift.price_ton} TON → оцінка перепродажу: "
            f"{result.estimated_resale_price} TON (чистий прибуток {result.potential_profit_net} TON)\n"
            f"  {gift.market_url()}"
        )

    await message.answer("\n\n".join(lines))
