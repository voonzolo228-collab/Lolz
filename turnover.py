import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from bot.keyboards.main_menu import turnover_submenu, MAIN_MENU_BUTTONS
from mrkt.client import MrktClient, MrktApiError
from services.analyzer import group_by_identity

logger = logging.getLogger("bot.turnover")
router = Router(name="turnover")

SCAN_PAGES = 15  # ~300 лістингів - розумний обсяг для рейтингу без надмірного навантаження


@router.message(F.text == MAIN_MENU_BUTTONS[0])
async def show_turnover_menu(message: Message) -> None:
    await message.answer(
        "🔄 За обороткою\n\n"
        "Важливо: MRKT API не надає історію продажів/офіційний оборот, "
        "лише поточні активні лістинги. Тому рейтинг тут будується за "
        "кількістю активних лістингів у групі collection+model — це "
        "проксі попиту/ліквідності, а НЕ факт обсягу продажів.\n\n"
        "Обери розмір рейтингу:",
        reply_markup=turnover_submenu(),
    )


@router.callback_query(F.data.startswith("turnover:"))
async def handle_turnover(callback: CallbackQuery, mrkt_client: MrktClient) -> None:
    top_n = int(callback.data.split(":")[1])
    await callback.answer("Збираю дані...")

    try:
        gifts = await mrkt_client.fetch_gifts_all(max_pages=SCAN_PAGES)
    except MrktApiError as exc:
        await callback.message.answer(f"Не вдалося отримати дані з MRKT: {exc}")
        return

    if not gifts:
        await callback.message.answer("MRKT не повернув активних лістингів.")
        return

    groups = group_by_identity(gifts)
    ranked = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)[:top_n]

    lines = [f"🔄 TOP {top_n} за кількістю активних лістингів (проксі ліквідності):", ""]
    for idx, (key, group_gifts) in enumerate(ranked, start=1):
        sample = group_gifts[0]
        prices = [g.price_ton for g in group_gifts if g.price_ton is not None]
        price_info = f"floor {min(prices)} TON" if prices else "ціна невідома"
        lines.append(
            f"{idx}. {sample.collection} — {sample.model or '—'} "
            f"({len(group_gifts)} лістингів, {price_info})"
        )

    await callback.message.answer("\n".join(lines))
