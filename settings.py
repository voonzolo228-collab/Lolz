import json
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.keyboards.main_menu import settings_menu, interval_submenu, MAIN_MENU_BUTTONS
from bot.states.settings_states import SettingsStates
from database.db import Database

logger = logging.getLogger("bot.settings")
router = Router(name="settings")


def _format_settings(user: dict) -> str:
    collections = json.loads(user["collections_json"] or "[]")
    return (
        "⚙️ Поточні налаштування:\n\n"
        f"Моніторинг: {'ON' if user['monitoring_enabled'] else 'OFF'}\n"
        f"Інтервал: {user['interval_seconds']} сек\n"
        f"Макс. ціна покупки: {user['max_purchase_price'] or '—'}\n"
        f"Мін. прибуток: {user['min_profit_ton']} TON\n"
        f"Мін. Opportunity Score: {user['min_opportunity_score']}\n"
        f"Діапазон ціни: {user['price_min'] or '—'} – {user['price_max'] or '—'}\n"
        f"Collections: {', '.join(collections) if collections else 'всі'}\n"
        f"Сповіщення: {'ON' if user['notifications_enabled'] else 'OFF'}"
    )


@router.message(F.text == MAIN_MENU_BUTTONS[6])
async def show_settings(message: Message, db: Database) -> None:
    user = await db.get_or_create_user(message.chat.id)
    await message.answer(_format_settings(user), reply_markup=settings_menu())


@router.callback_query(F.data == "settings:toggle_monitoring")
async def toggle_monitoring(callback: CallbackQuery, db: Database) -> None:
    user = await db.get_or_create_user(callback.from_user.id)
    new_value = 0 if user["monitoring_enabled"] else 1
    await db.update_user(callback.from_user.id, monitoring_enabled=new_value)
    await callback.answer(f"Моніторинг {'увімкнено' if new_value else 'вимкнено'}")
    user = await db.get_or_create_user(callback.from_user.id)
    await callback.message.edit_text(_format_settings(user), reply_markup=settings_menu())


@router.callback_query(F.data == "settings:toggle_notifications")
async def toggle_notifications(callback: CallbackQuery, db: Database) -> None:
    user = await db.get_or_create_user(callback.from_user.id)
    new_value = 0 if user["notifications_enabled"] else 1
    await db.update_user(callback.from_user.id, notifications_enabled=new_value)
    await callback.answer(f"Сповіщення {'увімкнено' if new_value else 'вимкнено'}")
    user = await db.get_or_create_user(callback.from_user.id)
    await callback.message.edit_text(_format_settings(user), reply_markup=settings_menu())


@router.callback_query(F.data == "settings:interval")
async def choose_interval(callback: CallbackQuery) -> None:
    await callback.message.answer("Обери інтервал моніторингу:", reply_markup=interval_submenu())
    await callback.answer()


@router.callback_query(F.data.startswith("interval:"))
async def set_interval(callback: CallbackQuery, db: Database) -> None:
    seconds = int(callback.data.split(":")[1])
    await db.update_user(callback.from_user.id, interval_seconds=seconds)
    await callback.answer(f"Інтервал встановлено: {seconds} сек")
    await callback.message.answer(f"✅ Інтервал моніторингу: {seconds} сек")


@router.callback_query(F.data == "settings:max_price")
async def ask_max_price(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("Напиши максимальну ціну покупки в TON (наприклад 500):")
    await state.set_state(SettingsStates.waiting_max_price)
    await callback.answer()


@router.message(SettingsStates.waiting_max_price)
async def set_max_price(message: Message, db: Database, state: FSMContext) -> None:
    try:
        value = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Це не число. Спробуй ще раз, наприклад: 500")
        return
    await db.update_user(message.chat.id, max_purchase_price=value)
    await state.clear()
    await message.answer(f"✅ Максимальна ціна покупки: {value} TON")


@router.callback_query(F.data == "settings:min_profit")
async def ask_min_profit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("Напиши мінімальний потенційний прибуток у TON (наприклад 20):")
    await state.set_state(SettingsStates.waiting_min_profit)
    await callback.answer()


@router.message(SettingsStates.waiting_min_profit)
async def set_min_profit(message: Message, db: Database, state: FSMContext) -> None:
    try:
        value = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Це не число. Спробуй ще раз, наприклад: 20")
        return
    await db.update_user(message.chat.id, min_profit_ton=value)
    await state.clear()
    await message.answer(f"✅ Мінімальний прибуток: {value} TON")


@router.callback_query(F.data == "settings:min_score")
async def ask_min_score(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("Напиши мінімальний Opportunity Score (0-100, наприклад 70):")
    await state.set_state(SettingsStates.waiting_min_score)
    await callback.answer()


@router.message(SettingsStates.waiting_min_score)
async def set_min_score(message: Message, db: Database, state: FSMContext) -> None:
    try:
        value = int(message.text)
        if not (0 <= value <= 100):
            raise ValueError
    except ValueError:
        await message.answer("Введи ціле число від 0 до 100, наприклад: 70")
        return
    await db.update_user(message.chat.id, min_opportunity_score=value)
    await state.clear()
    await message.answer(f"✅ Мінімальний Opportunity Score: {value}")


@router.callback_query(F.data == "settings:price_range")
async def ask_price_range(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("Напиши діапазон ціни у форматі: 100-300")
    await state.set_state(SettingsStates.waiting_price_range)
    await callback.answer()


@router.message(SettingsStates.waiting_price_range)
async def set_price_range(message: Message, db: Database, state: FSMContext) -> None:
    parts = (message.text or "").replace(" ", "").split("-")
    if len(parts) != 2:
        await message.answer("Невірний формат. Приклад: 100-300")
        return
    try:
        low, high = float(parts[0]), float(parts[1])
    except ValueError:
        await message.answer("Невірний формат. Приклад: 100-300")
        return
    if low > high:
        low, high = high, low
    await db.update_user(message.chat.id, price_min=low, price_max=high)
    await state.clear()
    await message.answer(f"✅ Діапазон ціни: {low}–{high} TON")


@router.callback_query(F.data == "settings:collections")
async def ask_collections(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "Напиши назви колекцій через кому (наприклад: Ice Cream, Lunar Snake), "
        "або напиши 'всі', щоб зняти фільтр."
    )
    await state.set_state(SettingsStates.waiting_collections)
    await callback.answer()


@router.message(SettingsStates.waiting_collections)
async def set_collections(message: Message, db: Database, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text.lower() in ("всі", "все", "all"):
        collections: list[str] = []
    else:
        collections = [c.strip() for c in text.split(",") if c.strip()]
    await db.update_user(message.chat.id, collections=collections)
    await state.clear()
    await message.answer(
        f"✅ Collections: {', '.join(collections) if collections else 'всі'}"
    )
