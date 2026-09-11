import logging
import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.keyboards.main_menu import price_range_submenu, MAIN_MENU_BUTTONS
from bot.states.settings_states import BrowseStates
from mrkt.client import MrktClient, MrktApiError
from utils.formatting import format_gift_list

logger = logging.getLogger("bot.price_range")
router = Router(name="price_range")

RANGE_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)\s*$")


@router.message(F.text == MAIN_MENU_BUTTONS[1])
async def show_price_range_menu(message: Message) -> None:
    await message.answer("💰 За радіусом цін\n\nОбери діапазон:", reply_markup=price_range_submenu())


@router.callback_query(F.data.startswith("price_range:"))
async def handle_price_range(callback: CallbackQuery, mrkt_client: MrktClient, state: FSMContext) -> None:
    value = callback.data.split(":", 1)[1]

    if value == "custom":
        await callback.message.answer(
            "Напиши власний діапазон у форматі: 120-180 (у TON)."
        )
        await state.set_state(BrowseStates.waiting_custom_price_range)
        await callback.answer()
        return

    min_price, max_price = (float(x) for x in value.split("-"))
    await callback.answer("Шукаю...")
    await _fetch_and_show(callback.message, mrkt_client, min_price, max_price)


@router.message(BrowseStates.waiting_custom_price_range)
async def handle_custom_range_input(message: Message, mrkt_client: MrktClient, state: FSMContext) -> None:
    match = RANGE_PATTERN.match(message.text or "")
    if not match:
        await message.answer("Не розпізнав формат. Приклад правильного вводу: 120-180")
        return

    min_price, max_price = float(match.group(1)), float(match.group(2))
    if min_price > max_price:
        min_price, max_price = max_price, min_price

    await state.clear()
    await _fetch_and_show(message, mrkt_client, min_price, max_price)


async def _fetch_and_show(message: Message, mrkt_client: MrktClient, min_price: float, max_price: float) -> None:
    try:
        gifts, _ = await mrkt_client.fetch_gifts_page(
            min_price=min_price, max_price=max_price, ordering="Price", low_to_high=True, count=20
        )
    except MrktApiError as exc:
        await message.answer(f"Не вдалося отримати дані з MRKT: {exc}")
        return

    title = f"💰 NFT у діапазоні {min_price}–{max_price} TON"
    await message.answer(format_gift_list(title, gifts))
