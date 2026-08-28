# -*- coding: utf-8 -*-
"""
P2P Гарант угод з NFT-подарунками
aiogram 2.25.1 | SQLite | FSM | Admin Panel
"""

import os
import re
import csv
import io
import logging
import asyncio
import random
import string
from datetime import datetime
from typing import Optional, Dict, Any

from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from aiogram.utils import executor
import aiosqlite

# ==================== НАЛАШТУВАННЯ ====================
API_TOKEN = '8698578814:AAEavw5BZ7nj6czWH5Dq6g22r4WGfvzRHHo'
LOG_CHAT_ID = -1004451013532
PROFIT_CHAT_ID = -1004451013532
LOG_THREAD_ID = 2986
PROFIT_THREAD_ID = 159
ADMIN_IDS = [8323946313]
DB_PATH = "funpay.db"
BOT_USERNAME = "IoIzDeaIs_bot"

COMMISSION_PERCENT = 30

CURRENCIES = ["TON", "RUB", "USD", "UAH", "Stars", "USDT", "KGS", "UZS", "BYN", "KZT"]

LANGUAGES = {
    "en": "English",
    "ru": "Русский",
    "uk": "Українська",
    "zh": "中文",
    "kk": "Қазақша",
    "ko": "한국어",
    "ja": "日本語",
    "de": "Deutsch",
    "ar": "العربية"
}

# ==================== ІНІЦІАЛІЗАЦІЯ ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# ==================== FSM ====================
class CreateDeal(StatesGroup):
    role = State()
    currency = State()
    amount = State()
    description = State()


class AdminStates(StatesGroup):
    confirm_payment = State()
    confirm_transfer = State()
    topup_user = State()
    topup_amount = State()
    topup_currency = State()
    broadcast = State()
    set_requisites = State()


# ==================== БАЗА ДАНИХ ====================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                language TEXT DEFAULT 'ru',
                verified INTEGER DEFAULT 0,
                balance_ton REAL DEFAULT 0,
                balance_rub REAL DEFAULT 0,
                balance_usd REAL DEFAULT 0,
                balance_uah REAL DEFAULT 0,
                balance_stars REAL DEFAULT 0,
                balance_usdt REAL DEFAULT 0,
                balance_kgs REAL DEFAULT 0,
                balance_uzs REAL DEFAULT 0,
                balance_byn REAL DEFAULT 0,
                balance_kzt REAL DEFAULT 0,
                requisites TEXT DEFAULT '',
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                deal_id TEXT PRIMARY KEY,
                creator_id INTEGER,
                creator_role TEXT,
                participant_id INTEGER,
                participant_role TEXT,
                amount REAL,
                currency TEXT,
                description TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                completed_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_type TEXT,
                user_id INTEGER,
                username TEXT,
                deal_id TEXT,
                action TEXT,
                details TEXT,
                created_at TEXT
            )
        """)
        await db.commit()


async def get_user(user_id: int, username: str = None) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if row:
            return dict(row)
        now = datetime.utcnow().isoformat()
        try:
            await db.execute(
                "INSERT INTO users (user_id, username, created_at) VALUES (?, ?, ?)",
                (user_id, username or "", now)
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Не вдалося створити користувача {user_id}: {e}")
            return {
                "user_id": user_id, "username": username or "", "language": "ru",
                "verified": 0, "balance_ton": 0, "balance_rub": 0, "balance_usd": 0,
                "balance_uah": 0, "balance_stars": 0, "balance_usdt": 0,
                "balance_kgs": 0, "balance_uzs": 0, "balance_byn": 0, "balance_kzt": 0,
                "requisites": "", "created_at": now
            }
        return {
            "user_id": user_id, "username": username or "", "language": "ru",
            "verified": 0, "balance_ton": 0, "balance_rub": 0, "balance_usd": 0,
            "balance_uah": 0, "balance_stars": 0, "balance_usdt": 0,
            "balance_kgs": 0, "balance_uzs": 0, "balance_byn": 0, "balance_kzt": 0,
            "requisites": "", "created_at": now
        }


async def update_user(user_id: int, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
        await db.commit()


async def get_balance_field(currency: str) -> str:
    return f"balance_{currency.lower()}"


async def add_balance(user_id: int, currency: str, amount: float):
    field = await get_balance_field(currency)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {field} = {field} + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()


async def create_deal(deal_id: str, creator_id: int, role: str, amount: float,
                      currency: str, description: str):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO deals (deal_id, creator_id, creator_role, amount, currency,
                               description, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (deal_id, creator_id, role, amount, currency, description, now))
        await db.commit()


async def get_deal(deal_id: str) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_deal(deal_id: str, **kwargs):
    if not kwargs:
        return
    deal = await get_deal(deal_id)
    if not deal:
        logger.warning(f"Спроба оновити неіснуючу угоду {deal_id}")
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [deal_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE deals SET {fields} WHERE deal_id = ?", values)
        await db.commit()


async def generate_deal_id() -> str:
    chars = string.ascii_uppercase + string.digits
    while True:
        suffix = "".join(random.choices(chars, k=6))
        deal_id = f"#716MZK{suffix}"
        if await get_deal(deal_id) is None:
            return deal_id


async def get_user_deals(user_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM deals
            WHERE creator_id = ? OR participant_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, user_id, limit)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_all_deals(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM deals ORDER BY created_at DESC LIMIT ?", (limit,)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM deals") as cur:
            deals = (await cur.fetchone())[0]
        turnover = {}
        for cur_name in CURRENCIES:
            async with db.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM deals WHERE currency = ? AND status = 'completed'",
                (cur_name,)
            ) as cur:
                turnover[cur_name] = (await cur.fetchone())[0]
        return users, deals, turnover


async def get_recent_users(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT ?", (limit,)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def log_action(log_type: str, user_id: int = None, username: str = None,
                     deal_id: str = None, action: str = "", details: str = ""):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO logs (log_type, user_id, username, deal_id, action, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (log_type, user_id, username, deal_id, action, details, now))
        await db.commit()

    text = f"📝 <b>{log_type}</b>\n"
    if user_id:
        text += f"👤 {username or '—'} (<code>{user_id}</code>)\n"
    if deal_id:
        text += f"🆔 Deal: <code>{deal_id}</code>\n"
    text += f"⚡ {action}\n"
    if details:
        text += f"📄 {details}"
    try:
        kwargs = {"chat_id": LOG_CHAT_ID, "text": text, "parse_mode": ParseMode.HTML}
        if LOG_THREAD_ID:
            kwargs["message_thread_id"] = LOG_THREAD_ID
        await bot.send_message(**kwargs)
    except Exception as e:
        logger.error(f"Log send error: {e}")


async def send_profit(deal: Dict, seller_id: int, seller_amount: float, commission: float):
    text = (
        f"💎 <b>НОВЫЙ ПРОФИТ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📎 СДЕЛКА: <code>{deal['deal_id']}</code>\n"
        f"💰 СУММА: <b>{deal['amount']} {deal['currency']}</b>\n"
        f"📊 КОМИССИЯ (30%): <b>{commission:.4f} {deal['currency']}</b>\n"
        f"👤 ПРОДАВЕЦ ПОЛУЧАЕТ: <b>{seller_amount:.4f} {deal['currency']}</b>\n"
        f"🆔 SELLER ID: <code>{seller_id}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✅ Статус: ПЕРЕДАНО"
    )
    try:
        kwargs = {"chat_id": PROFIT_CHAT_ID, "text": text, "parse_mode": ParseMode.HTML}
        if PROFIT_THREAD_ID:
            kwargs["message_thread_id"] = PROFIT_THREAD_ID
        await bot.send_message(**kwargs)
    except Exception as e:
        logger.error(f"Profit send error: {e}")


# ==================== КЛАВІАТУРИ ====================
def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🆕 Создать сделку", callback_data="create_deal"),
        InlineKeyboardButton("💰 Баланс", callback_data="balance"),
        InlineKeyboardButton("📋 Мои сделки", callback_data="my_deals"),
        InlineKeyboardButton("✅ Верификация", callback_data="verification"),
        InlineKeyboardButton("💳 Реквизиты", callback_data="requisites"),
        InlineKeyboardButton("🌐 Язык", callback_data="language"),
        InlineKeyboardButton("🛡 Безопасно ли это?", callback_data="safety"),
        InlineKeyboardButton("🆘 Поддержка", callback_data="support"),
    )
    return kb


def role_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🛒 Покупатель", callback_data="role_buyer"),
        InlineKeyboardButton("🏷 Продавец", callback_data="role_seller"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_main"),
    )
    return kb


def currency_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for cur in CURRENCIES:
        kb.add(InlineKeyboardButton(f"💱 {cur}", callback_data=f"cur_{cur}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_role"))
    return kb


def balance_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("➕ Пополнить баланс", callback_data="topup_info"),
        InlineKeyboardButton("➖ Вывести баланс", callback_data="withdraw_info"),
        InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_main"),
    )
    return kb


def language_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for code, name in LANGUAGES.items():
        kb.add(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
    return kb


def admin_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📋 Все сделки", callback_data="adm_deals"),
        InlineKeyboardButton("📊 Статистика", callback_data="adm_stats"),
        InlineKeyboardButton("✅ Подтвердить оплату", callback_data="adm_confirm_pay"),
        InlineKeyboardButton("✅ Подтвердить передачу", callback_data="adm_confirm_transfer"),
        InlineKeyboardButton("💳 Пополнить баланс", callback_data="adm_topup"),
        InlineKeyboardButton("📩 Рассылка", callback_data="adm_broadcast"),
        InlineKeyboardButton("👥 Пользователи", callback_data="adm_users"),
        InlineKeyboardButton("📤 Экспорт", callback_data="adm_export"),
        InlineKeyboardButton("🔙 В главное меню", callback_data="back_main"),
    )
    return kb


def back_main_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔙 В меню", callback_data="back_main"))
    return kb


# ==================== ХЕЛПЕРИ ====================
def deal_card(deal: Dict, for_user: int = None) -> str:
    status_emoji = {
        "pending": "⏳",
        "active": "🟢",
        "paid": "💵",
        "completed": "✅",
        "cancelled": "❌"
    }
    st = status_emoji.get(deal["status"], "❓")
    text = (
        f"📄 <b>Сделка {deal['deal_id']}</b>\n\n"
        f"👤 Роль создателя: <b>{deal['creator_role']}</b>\n"
        f"💰 Сумма: <b>{deal['amount']} {deal['currency']}</b>\n"
        f"📝 Описание: {deal['description']}\n"
        f"📊 Статус: {st} <b>{deal['status']}</b>\n"
        f"📅 Создана: {deal['created_at'][:19]}\n"
    )
    if deal.get("participant_id"):
        text += f"👥 Участник: <code>{deal['participant_id']}</code>\n"
    if deal.get("completed_at"):
        text += f"✅ Завершена: {deal['completed_at'][:19]}\n"
    return text


# ==================== ХЕНДЛЕРИ ====================
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    user = await get_user(message.from_user.id, message.from_user.username)
    args = message.get_args()
    
    logger.info(f"🔍 Получен /start от {message.from_user.id} с параметром: {args}")

    if args and args.startswith("deal_"):
        deal_code = args[5:].strip()
        logger.info(f"🔍 Шукаємо угоду з кодом: {deal_code}")
        
        if not deal_code:
            await message.answer("❌ Неверная ссылка.", reply_markup=main_menu_kb())
            return
        
        full_deal_id = f"#716MZK{deal_code}"
        logger.info(f"🔍 Повний ID: {full_deal_id}")
        
        deal = await get_deal(full_deal_id)
        
        if not deal:
            logger.warning(f"❌ Угода {full_deal_id} не знайдена")
            await message.answer(
                "❌ Сделка не найдена.\n\n"
                "Возможно, ссылка устарела или была введена неверно.",
                reply_markup=main_menu_kb()
            )
            return
        
        logger.info(f"✅ Знайдено угоду: {deal['deal_id']}")
        
        if deal["status"] != "pending":
            await message.answer(
                f"❌ Сделка уже {'занята' if deal['status'] == 'active' else 'завершена'}.",
                reply_markup=main_menu_kb()
            )
            return
        
        if deal["creator_id"] == message.from_user.id:
            await message.answer(
                "❌ Вы не можете присоединиться к своей сделке.\n\n"
                "Вы создали эту сделку. Ожидайте подключения второй стороны.",
                reply_markup=main_menu_kb()
            )
            return
        
        if deal.get("participant_id"):
            await message.answer(
                "❌ К сделке уже присоединился участник.",
                reply_markup=main_menu_kb()
            )
            return

        opposite = "seller" if deal["creator_role"] == "buyer" else "buyer"
        await update_deal(
            deal["deal_id"],
            participant_id=message.from_user.id,
            participant_role=opposite,
            status="active"
        )
        
        deal = await get_deal(deal["deal_id"])
        await log_action("DEAL", message.from_user.id, message.from_user.username,
                         deal["deal_id"], "JOIN", f"Роль: {opposite}")

        try:
            await bot.send_message(
                deal["creator_id"],
                f"🎉 К вашей сделке <code>{deal['deal_id']}</code> присоединился участник!\n\n"
                + deal_card(deal),
                reply_markup=main_menu_kb()
            )
        except Exception as e:
            logger.error(f"Не вдалося повідомити творця: {e}")

        role_text = "Продавец" if opposite == "seller" else "Покупатель"
        await message.answer(
            f"✅ Вы успешно присоединились к сделке!\n\n"
            f"📄 <b>Сделка {deal['deal_id']}</b>\n"
            f"👤 Ваша роль: <b>{role_text}</b>\n"
            f"💰 Сумма: <b>{deal['amount']} {deal['currency']}</b>\n"
            f"📝 Описание: {deal['description']}\n\n"
            f"⏳ Ожидайте подтверждения от второй стороны.",
            reply_markup=main_menu_kb()
        )
        return

    await log_action("USER", message.from_user.id, message.from_user.username,
                     action="START", details="Запуск бота")
    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        "🔒 Я — безопасный P2P-гарант сделок с NFT-подарками.\n"
        "Выберите действие:",
        reply_markup=main_menu_kb()
    )


@dp.callback_query_handler(lambda c: c.data == "back_main", state="*")
async def back_main(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.edit_text(
        "🏠 <b>Главное меню</b>\nВыберите действие:",
        reply_markup=main_menu_kb()
    )
    await call.answer()


# ---------- СТВОРЕННЯ УГОДИ ----------
@dp.callback_query_handler(lambda c: c.data == "create_deal")
async def create_deal_start(call: types.CallbackQuery, state: FSMContext):
    await CreateDeal.role.set()
    await call.message.edit_text(
        "🆕 <b>Создание сделки</b>\n\nВыберите вашу роль:",
        reply_markup=role_kb()
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("role_"), state=CreateDeal.role)
async def process_role(call: types.CallbackQuery, state: FSMContext):
    role = "buyer" if call.data == "role_buyer" else "seller"
    await state.update_data(role=role)
    await CreateDeal.currency.set()
    await call.message.edit_text(
        "💱 Выберите валюту сделки:",
        reply_markup=currency_kb()
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data == "back_role", state=CreateDeal.currency)
async def back_role(call: types.CallbackQuery, state: FSMContext):
    await CreateDeal.role.set()
    await call.message.edit_text(
        "🆕 <b>Создание сделки</b>\n\nВыберите вашу роль:",
        reply_markup=role_kb()
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("cur_"), state=CreateDeal.currency)
async def process_currency(call: types.CallbackQuery, state: FSMContext):
    currency = call.data[4:]
    await state.update_data(currency=currency)
    await CreateDeal.amount.set()
    await call.message.edit_text(
        f"💰 Введите сумму сделки в <b>{currency}</b>:\n"
        "(только число, например: 150.5)",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 Назад", callback_data="back_currency")
        )
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data == "back_currency", state=CreateDeal.amount)
async def back_currency(call: types.CallbackQuery, state: FSMContext):
    await CreateDeal.currency.set()
    await call.message.edit_text(
        "💱 Выберите валюту сделки:",
        reply_markup=currency_kb()
    )
    await call.answer()


@dp.message_handler(state=CreateDeal.amount)
async def process_amount(message: types.Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    text = message.text.replace(",", ".").strip()
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное положительное число.")
        return
    await state.update_data(amount=amount)
    await CreateDeal.description.set()
    await message.answer(
        "📝 Введите описание / ссылку на NFT-подарок:\n"
        "(можно просто текст или ссылку)",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 Назад", callback_data="back_amount")
        )
    )


@dp.callback_query_handler(lambda c: c.data == "back_amount", state=CreateDeal.description)
async def back_amount(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await CreateDeal.amount.set()
    await call.message.edit_text(
        f"💰 Введите сумму сделки в <b>{data.get('currency', '')}</b>:",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 Назад", callback_data="back_currency")
        )
    )
    await call.answer()


@dp.message_handler(state=CreateDeal.description)
async def process_description(message: types.Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    description = message.text.strip()[:500]
    data = await state.get_data()
    
    if not data.get("role") or not data.get("currency") or not data.get("amount"):
        await state.finish()
        await message.answer("❌ Данные потеряны. Начните создание сделки заново.", reply_markup=main_menu_kb())
        return
    
    deal_id = await generate_deal_id()
    short_code = deal_id[-6:]

    await create_deal(
        deal_id=deal_id,
        creator_id=message.from_user.id,
        role=data["role"],
        amount=data["amount"],
        currency=data["currency"],
        description=description
    )
    await log_action(
        "DEAL", message.from_user.id, message.from_user.username,
        deal_id, "CREATE",
        f"{data['role']} | {data['amount']} {data['currency']}"
    )

    link = f"https://t.me/{BOT_USERNAME}?start=deal_{short_code}"
    role_text = "Покупатель" if data["role"] == "buyer" else "Продавец"

    text = (
        f"✅ <b>Сделка создана!</b>\n\n"
        f"🆔 ID: <code>{deal_id}</code>\n"
        f"👤 Ваша роль: <b>{role_text}</b>\n"
        f"💰 Сумма: <b>{data['amount']} {data['currency']}</b>\n"
        f"📝 Описание: {description}\n\n"
        f"🔗 Ссылка для второй стороны:\n<code>{link}</code>\n\n"
        f"Отправьте эту ссылку контрагенту."
    )
    await state.finish()
    await message.answer(text, reply_markup=main_menu_kb())


# ---------- БАЛАНС ----------
@dp.callback_query_handler(lambda c: c.data == "balance")
async def show_balance(call: types.CallbackQuery):
    user = await get_user(call.from_user.id)
    text = "💰 <b>Ваш баланс</b>\n\n"
    for cur in CURRENCIES:
        field = f"balance_{cur.lower()}"
        val = user.get(field, 0) or 0
        text += f"• {cur}: <b>{val:.4f}</b>\n"
    await call.message.edit_text(text, reply_markup=balance_kb())
    await call.answer()


@dp.callback_query_handler(lambda c: c.data in ("topup_info", "withdraw_info"))
async def balance_info(call: types.CallbackQuery):
    if call.data == "topup_info":
        text = (
            "➕ <b>Пополнение баланса</b>\n\n"
            "Для пополнения обратитесь в поддержку или используйте админ-панель.\n"
            "После пополнения средства появятся на балансе."
        )
    else:
        text = (
            "➖ <b>Вывод средств</b>\n\n"
            "Для вывода укажите реквизиты в разделе «Реквизиты»\n"
            "и напишите в поддержку сумму и валюту."
        )
    await call.message.edit_text(text, reply_markup=back_main_kb())
    await call.answer()


# ---------- МОИ СДЕЛКИ ----------
@dp.callback_query_handler(lambda c: c.data == "my_deals")
async def my_deals(call: types.CallbackQuery):
    deals = await get_user_deals(call.from_user.id, 10)
    if not deals:
        text = "📋 У вас пока нет сделок."
    else:
        text = "📋 <b>Ваши последние сделки</b>\n\n"
        for d in deals:
            st = {"pending": "⏳", "active": "🟢", "paid": "💵",
                  "completed": "✅", "cancelled": "❌"}.get(d["status"], "❓")
            text += (
                f"{st} <code>{d['deal_id']}</code> — "
                f"{d['amount']} {d['currency']} ({d['status']})\n"
            )
    await call.message.edit_text(text, reply_markup=back_main_kb())
    await call.answer()


# ---------- ВЕРИФИКАЦИЯ ----------
@dp.callback_query_handler(lambda c: c.data == "verification")
async def verification(call: types.CallbackQuery):
    user = await get_user(call.from_user.id)
    status = "✅ Верифицирован" if user["verified"] else "❌ Не верифицирован"
    text = (
        f"✅ <b>Верификация</b>\n\n"
        f"Статус: <b>{status}</b>\n\n"
        "Для прохождения верификации обратитесь в поддержку."
    )
    await call.message.edit_text(text, reply_markup=back_main_kb())
    await call.answer()


# ---------- РЕКВИЗИТЫ ----------
@dp.callback_query_handler(lambda c: c.data == "requisites")
async def requisites_menu(call: types.CallbackQuery, state: FSMContext):
    user = await get_user(call.from_user.id)
    current = user.get("requisites") or "не указаны"
    text = (
        f"💳 <b>Реквизиты</b>\n\n"
        f"Текущие: <code>{current}</code>\n\n"
        "Отправьте новые реквизиты одним сообщением:"
    )
    await AdminStates.set_requisites.set()
    await call.message.edit_text(text, reply_markup=back_main_kb())
    await call.answer()


@dp.message_handler(state=AdminStates.set_requisites)
async def save_requisites(message: types.Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    req = message.text.strip()[:500]
    await update_user(message.from_user.id, requisites=req)
    await log_action("USER", message.from_user.id, message.from_user.username,
                     action="REQUISITES", details=req[:100])
    await state.finish()
    await message.answer("✅ Реквизиты сохранены.", reply_markup=main_menu_kb())


# ---------- ЯЗЫК ----------
@dp.callback_query_handler(lambda c: c.data == "language")
async def language_menu(call: types.CallbackQuery):
    await call.message.edit_text(
        "🌐 <b>Выберите язык</b>",
        reply_markup=language_kb()
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def set_language(call: types.CallbackQuery):
    code = call.data[5:]
    if code in LANGUAGES:
        await update_user(call.from_user.id, language=code)
        await call.message.edit_text(
            f"✅ Язык изменён на <b>{LANGUAGES[code]}</b>",
            reply_markup=main_menu_kb()
        )
    await call.answer()


# ---------- БЕЗОПАСНОСТЬ ----------
@dp.callback_query_handler(lambda c: c.data == "safety")
async def safety(call: types.CallbackQuery):
    text = (
        "🛡 <b>Безопасно ли это?</b>\n\n"
        "1. 🔒 Все сделки проходят через гаранта.\n"
        "2. 💰 Средства удерживаются до подтверждения передачи.\n"
        "3. ✅ Администраторы проверяют каждую сделку.\n"
        "4. 📝 Ведётся полный лог действий.\n"
        "5. 🚫 Запрещены сделки вне бота.\n"
        "6. 👤 Рекомендуется верификация.\n"
        "7. 🆘 При споре обращайтесь в поддержку.\n\n"
        "Мы защищаем обе стороны сделки."
    )
    await call.message.edit_text(text, reply_markup=back_main_kb())
    await call.answer()


# ---------- ПОДДЕРЖКА ----------
@dp.callback_query_handler(lambda c: c.data == "support")
async def support(call: types.CallbackQuery):
    text = (
        "🆘 <b>Поддержка</b>\n\n"
        "По всем вопросам пишите:\n"
        "• @FunPaySupport\n"
        "• или в группу поддержки\n\n"
        "Время ответа: обычно до 1 часа."
    )
    await call.message.edit_text(text, reply_markup=back_main_kb())
    await call.answer()

