import logging

from aiogram import Router, F
from aiogram.types import Message

from bot.keyboards.main_menu import MAIN_MENU_BUTTONS
from mrkt.client import MrktClient, MrktApiError
from utils.number_beauty import score_number_beauty
from utils.formatting import format_gift_list

logger = logging.getLogger("bot.rare_numbers")
router = Router(name="rare_numbers")

SCAN_PAGES = 10
MIN_BEAUTY_SCORE = 30


@router.message(F.text == MAIN_MENU_BUTTONS[4])
async def show_rare_numbers(message: Message, mrkt_client: MrktClient) -> None:
    try:
        gifts = await mrkt_client.fetch_gifts_all(max_pages=SCAN_PAGES)
    except MrktApiError as exc:
        await message.answer(f"Не вдалося отримати дані з MRKT: {exc}")
        return

    scored = []
    extras = {}
    for g in gifts:
        if g.number is None:
            continue
        score, reasons = score_number_beauty(g.number)
        if score >= MIN_BEAUTY_SCORE:
            scored.append((score, g))
            extras[g.gift_id] = f"beauty {score}/100: {', '.join(reasons)}"

    scored.sort(key=lambda t: t[0], reverse=True)
    gifts_sorted = [g for _, g in scored]

    await message.answer(format_gift_list("🔢 Рідкісні номери", gifts_sorted, extras))
