import logging

from aiogram import Router, F
from aiogram.types import Message

from bot.keyboards.main_menu import MAIN_MENU_BUTTONS
from mrkt.client import MrktClient, MrktApiError
from utils.color_analysis import classify_monochrome
from utils.formatting import format_gift_list

logger = logging.getLogger("bot.monochrome")
router = Router(name="monochrome")

SCAN_PAGES = 10
DISCLAIMER = (
    "⚠️ MRKT API не надає колірні дані (RGB/HEX), лише текстові назви "
    "backdrop/symbol/model. Категорія визначена евристично за ключовими "
    "словами кольору в назвах — це наближення, а не аналіз зображення.\n\n"
)


@router.message(F.text == MAIN_MENU_BUTTONS[2])
async def show_mono(message: Message, mrkt_client: MrktClient) -> None:
    await _show(message, mrkt_client, "mono", "🖤 Монохромні (евристика)")


@router.message(F.text == MAIN_MENU_BUTTONS[3])
async def show_semi_mono(message: Message, mrkt_client: MrktClient) -> None:
    await _show(message, mrkt_client, "semi_mono", "⚫ Напівмонохромні (евристика)")


async def _show(message: Message, mrkt_client: MrktClient, category: str, title: str) -> None:
    try:
        gifts = await mrkt_client.fetch_gifts_all(max_pages=SCAN_PAGES)
    except MrktApiError as exc:
        await message.answer(f"Не вдалося отримати дані з MRKT: {exc}")
        return

    matched = []
    extras = {}
    for g in gifts:
        cat, explanation = classify_monochrome(g.backdrop, g.symbol, g.model)
        if cat == category:
            matched.append(g)
            extras[g.gift_id] = explanation

    await message.answer(DISCLAIMER + format_gift_list(title, matched, extras))
