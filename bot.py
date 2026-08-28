# -*- coding: utf-8 -*-
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# ==================== ТЕКСТИ ДЛЯ РІЗНИХ МОВ ====================
TEXTS = {
    "ru": {
        "welcome": "🎉 Добро пожаловать в FunPay!\n\n💎 0% комиссии для всех сделок\n🔐 Безопасные P2P-сделки с NFT\n📱 Нажми кнопки ниже чтобы начать",
        "balance": "💰 Ваш баланс FunPay",
        "my_deals": "📋 Ваши последние сделки",
        "verify": "🔐 Верификация FunPay\n\nВаш статус: не верифицирован",
        "support": "🆘 Поддержка FunPay\n\n👨‍💻 Свяжитесь с нами: @FunPaySupport",
        "safety": "🛡 Безопасность сделок FunPay",
        "language_changed": "✅ Язык изменен на Русский",
        "no_deals": "📭 У вас пока нет сделок.",
        "requisites_empty": "💳 Реквизиты не заполнены",
        "admin_panel": "🔐 Админ-панель FunPay",
        "deal_created": "✅ Сделка успешно создана!",
        "deal_joined": "✅ Вы подключились к сделке!",
        "payment_confirmed": "✅ Оплата подтверждена!",
        "transfer_confirmed": "✅ Передача подтверждена!",
        "create_deal": "🆕 Создать сделку",
        "balance_btn": "💰 Баланс",
        "my_deals_btn": "📋 Мои сделки",
        "requisites_btn": "💳 Реквизиты",
        "language_btn": "🌐 Язык",
        "safety_btn": "🛡 Безопасно ли это?",
        "support_btn": "🆘 Поддержка",
        "back_btn": "🔙 Вернуться в меню",
        "topup_info": "💰 <b>Пополнение баланса</b>\n\nДля пополнения баланса напишите в поддержку:\n• @FunPaySupport\n\n📌 Укажите:\n▫️ Ваш ID (можно посмотреть в профиле)\n▫️ Сумму пополнения\n▫️ Валюту (TON, RUB, USD, UAH, Stars, USDT, KGS, UZS, BYN, KZT)\n\n⏱ Время обработки: до 15 минут",
        "withdraw_info": "💸 <b>Вывод средств</b>\n\nДля вывода средств напишите в поддержку:\n• @FunPaySupport\n\n📌 Укажите:\n▫️ Ваш ID\n▫️ Сумму вывода\n▫️ Валюту\n▫️ Реквизиты для вывода\n\n⏱ Время обработки: до 30 минут",
        "deal_not_found": "❌ Сделка не найдена.\n\nВозможно, ссылка устарела или была введена неверно.",
        "already_joined": "❌ К этой сделке уже присоединился участник.",
        "cant_join_own": "❌ Вы не можете присоединиться к своей сделке.\n\nВы создали эту сделку. Ожидайте подключения второй стороны."
    },
    "uk": {
        "welcome": "🎉 Ласкаво просимо до FunPay!\n\n💎 0% комісії для всіх угод\n🔐 Безпечні P2P-угоди з NFT\n📱 Натисніть кнопки нижче щоб почати",
        "balance": "💰 Ваш баланс FunPay",
        "my_deals": "📋 Ваші останні угоди",
        "verify": "🔐 Верифікація FunPay\n\nВаш статус: не верифіковано",
        "support": "🆘 Підтримка FunPay\n\n👨‍💻 Зв'яжіться з нами: @FunPaySupport",
        "safety": "🛡 Безпека угод FunPay",
        "language_changed": "✅ Мову змінено на Українську",
        "no_deals": "📭 У вас поки немає угод.",
        "requisites_empty": "💳 Реквізити не заповнені",
        "admin_panel": "🔐 Адмін-панель FunPay",
        "deal_created": "✅ Угоду успішно створено!",
        "deal_joined": "✅ Ви підключилися до угоди!",
        "payment_confirmed": "✅ Оплату підтверджено!",
        "transfer_confirmed": "✅ Передачу підтверджено!",
        "create_deal": "🆕 Створити угоду",
        "balance_btn": "💰 Баланс",
        "my_deals_btn": "📋 Мої угоди",
        "requisites_btn": "💳 Реквізити",
        "language_btn": "🌐 Мова",
        "safety_btn": "🛡 Безпечно чи це?",
        "support_btn": "🆘 Підтримка",
        "back_btn": "🔙 Повернутися в меню",
        "topup_info": "💰 <b>Поповнення балансу</b>\n\nДля поповнення балансу напишіть у підтримку:\n• @FunPaySupport\n\n📌 Вкажіть:\n▫️ Ваш ID (можна подивитись у профілі)\n▫️ Суму поповнення\n▫️ Валюту (TON, RUB, USD, UAH, Stars, USDT, KGS, UZS, BYN, KZT)\n\n⏱ Час обробки: до 15 хвилин",
        "withdraw_info": "💸 <b>Виведення коштів</b>\n\nДля виведення коштів напишіть у підтримку:\n• @FunPaySupport\n\n📌 Вкажіть:\n▫️ Ваш ID\n▫️ Суму виведення\n▫️ Валюту\n▫️ Реквізити для виведення\n\n⏱ Час обробки: до 30 хвилин",
        "deal_not_found": "❌ Угоду не знайдено.\n\nМожливо, посилання застаріло або було введено невірно.",
        "already_joined": "❌ До цієї угоди вже приєднався учасник.",
        "cant_join_own": "❌ Ви не можете приєднатися до своєї угоди.\n\nВи створили цю угоду. Очікуйте підключення другої сторони."
    },
    "en": {
        "welcome": "🎉 Welcome to FunPay!\n\n💎 0% commission for all deals\n🔐 Secure P2P NFT deals\n📱 Click buttons below to start",
        "balance": "💰 Your FunPay balance",
        "my_deals": "📋 Your latest deals",
        "verify": "🔐 FunPay Verification\n\nYour status: not verified",
        "support": "🆘 FunPay Support\n\n👨‍💻 Contact us: @FunPaySupport",
        "safety": "🛡 FunPay Deal Security",
        "language_changed": "✅ Language changed to English",
        "no_deals": "📭 You have no deals yet.",
        "requisites_empty": "💳 Requisites not filled",
        "admin_panel": "🔐 FunPay Admin Panel",
        "deal_created": "✅ Deal created successfully!",
        "deal_joined": "✅ You joined the deal!",
        "payment_confirmed": "✅ Payment confirmed!",
        "transfer_confirmed": "✅ Transfer confirmed!",
        "create_deal": "🆕 Create deal",
        "balance_btn": "💰 Balance",
        "my_deals_btn": "📋 My deals",
        "requisites_btn": "💳 Requisites",
        "language_btn": "🌐 Language",
        "safety_btn": "🛡 Is it safe?",
        "support_btn": "🆘 Support",
        "back_btn": "🔙 Back to menu",
        "topup_info": "💰 <b>Balance top-up</b>\n\nTo top up your balance, contact support:\n• @FunPaySupport\n\n📌 Specify:\n▫️ Your ID (can be found in profile)\n▫️ Amount to top up\n▫️ Currency (TON, RUB, USD, UAH, Stars, USDT, KGS, UZS, BYN, KZT)\n\n⏱ Processing time: up to 15 minutes",
        "withdraw_info": "💸 <b>Withdrawal</b>\n\nTo withdraw funds, contact support:\n• @FunPaySupport\n\n📌 Specify:\n▫️ Your ID\n▫️ Amount to withdraw\n▫️ Currency\n▫️ Withdrawal details\n\n⏱ Processing time: up to 30 minutes",
        "deal_not_found": "❌ Deal not found.\n\nThe link may be outdated or entered incorrectly.",
        "already_joined": "❌ A participant has already joined this deal.",
        "cant_join_own": "❌ You cannot join your own deal.\n\nYou created this deal. Wait for the second party to connect."
    }
}


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
                paid_at TEXT,
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


def get_language(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result and result[0] in ["uk", "en"] else "ru"


def get_text(user_id, key):
    lang = get_language(user_id)
    return TEXTS[lang].get(key, TEXTS["ru"][key])


async def get_user(user_id: int, username: str = None) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if row:
            return dict(row)
        now = datetime.utcnow().isoformat()
        try:
            await db.execute("INSERT INTO users (user_id, username, language, created_at) VALUES (?, ?, ?, ?)", (user_id, username or "", "ru", now))
            await db.commit()
        except Exception as e:
            logger.error(f"Не вдалося створити користувача {user_id}: {e}")
            return {"user_id": user_id, "username": username or "", "language": "ru", "verified": 0, "balance_ton": 0, "balance_rub": 0, "balance_usd": 0, "balance_uah": 0, "balance_stars": 0, "balance_usdt": 0, "balance_kgs": 0, "balance_uzs": 0, "balance_byn": 0, "balance_kzt": 0, "requisites": "", "created_at": now}
        return {"user_id": user_id, "username": username or "", "language": "ru", "verified": 0, "balance_ton": 0, "balance_rub": 0, "balance_usd": 0, "balance_uah": 0, "balance_stars": 0, "balance_usdt": 0, "balance_kgs": 0, "balance_uzs": 0, "balance_byn": 0, "balance_kzt": 0, "requisites": "", "created_at": now}


async def update_user(user_id: int, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
        await db.commit()


async def add_balance(user_id: int, currency: str, amount: float):
    field = f"balance_{currency.lower()}"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {field} = {field} + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()


async def create_deal(deal_id: str, creator_id: int, role: str, amount: float, currency: str, description: str):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO deals (deal_id, creator_id, creator_role, amount, currency, description, status, created_at)
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
        async with db.execute("SELECT * FROM deals WHERE creator_id = ? OR participant_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, user_id, limit)) as cur:
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
            async with db.execute("SELECT COALESCE(SUM(amount), 0) FROM deals WHERE currency = ? AND status = 'completed'", (cur_name,)) as cur:
                turnover[cur_name] = (await cur.fetchone())[0]
        return users, deals, turnover


async def get_recent_users(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT ?", (limit,)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def log_action(log_type: str, user_id: int = None, username: str = None, deal_id: str = None, action: str = "", details: str = ""):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO logs (log_type, user_id, username, deal_id, action, details, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (log_type, user_id, username, deal_id, action, details, now))
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


def main_menu_kb(user_id=None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    
    if user_id:
        kb.add(
            InlineKeyboardButton(get_text(user_id, "create_deal"), callback_data="create_deal"),
            InlineKeyboardButton(get_text(user_id, "balance_btn"), callback_data="balance"),
            InlineKeyboardButton(get_text(user_id, "my_deals_btn"), callback_data="my_deals"),
            InlineKeyboardButton(get_text(user_id, "requisites_btn"), callback_data="requisites"),
            InlineKeyboardButton(get_text(user_id, "language_btn"), callback_data="language"),
            InlineKeyboardButton(get_text(user_id, "safety_btn"), callback_data="safety"),
            InlineKeyboardButton(get_text(user_id, "support_btn"), callback_data="support"),
        )
    else:
        kb.add(
            InlineKeyboardButton("🆕 Создать сделку", callback_data="create_deal"),
            InlineKeyboardButton("💰 Баланс", callback_data="balance"),
            InlineKeyboardButton("📋 Мои сделки", callback_data="my_deals"),
            InlineKeyboardButton("💳 Реквизиты", callback_data="requisites"),
            InlineKeyboardButton("🌐 Язык", callback_data="language"),
            InlineKeyboardButton("🛡 Безопасно ли это?", callback_data="safety"),
            InlineKeyboardButton("🆘 Поддержка", callback_data="support"),
        )
    return kb


def role_kb(user_id=None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    if user_id:
        kb.add(
            InlineKeyboardButton("🛒 " + get_text(user_id, "buyer"), callback_data="role_buyer"),
            InlineKeyboardButton("🏷 " + get_text(user_id, "seller"), callback_data="role_seller"),
            InlineKeyboardButton("🔙 " + get_text(user_id, "back_btn"), callback_data="back_main"),
        )
    else:
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


def deal_card(deal: Dict) -> str:
    status_emoji = {"pending": "⏳", "active": "🟢", "paid": "💵", "completed": "✅", "cancelled": "❌"}
    st = status_emoji.get(deal["status"], "❓")
    text = f"📄 <b>Сделка {deal['deal_id']}</b>\n\n"
    text += f"👤 Роль создателя: <b>{deal['creator_role']}</b>\n"
    text += f"💰 Сумма: <b>{deal['amount']} {deal['currency']}</b>\n"
    text += f"📝 Описание: {deal['description']}\n"
    text += f"📊 Статус: {st} <b>{deal['status']}</b>\n"
    text += f"📅 Создана: {deal['created_at'][:19]}\n"
    if deal.get("participant_id"):
        text += f"👥 Участник: <code>{deal['participant_id']}</code>\n"
    if deal.get("paid_at"):
        text += f"💳 Оплачена: {deal['paid_at'][:19]}\n"
    if deal.get("completed_at"):
        text += f"✅ Завершена: {deal['completed_at'][:19]}\n"
    return text


def deal_kb(deal: Dict, user_role: str = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    
    if user_role == "buyer" and deal["status"] == "active":
        kb.add(InlineKeyboardButton("💳 Оплатить", callback_data=f"pay_{deal['deal_id']}"))
    
    kb.add(InlineKeyboardButton("🔄 Обновить статус", callback_data=f"refresh_{deal['deal_id']}"))
    kb.add(InlineKeyboardButton("🔙 В меню", callback_data="back_main"))
    return kb


# ==================== ХЕНДЛЕРИ ====================

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    await get_user(user_id, message.from_user.username)
    args = message.get_args()
    
    logger.info(f"🔍 Получен /start от {user_id} с параметром: {args}")
    
    if args and args.startswith("deal_"):
        deal_code = args[5:].strip()
        logger.info(f"🔍 Шукаємо угоду з кодом: {deal_code}")
        
        if not deal_code:
            await message.answer("❌ Неверная ссылка.", reply_markup=main_menu_kb(user_id))
            return
        
        full_deal_id = f"#716MZK{deal_code}"
        deal = await get_deal(full_deal_id)
        
        if not deal:
            logger.info(f"🔍 Шукаємо LIKE: %{deal_code}%")
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM deals WHERE deal_id LIKE ?", (f"%{deal_code}%",)) as cur:
                    row = await cur.fetchone()
                    if row:
                        deal = dict(row)
                        logger.info(f"✅ Знайдено угоду через LIKE: {deal['deal_id']}")
        
        if not deal:
            logger.warning(f"❌ Угода з кодом {deal_code} не знайдена")
            await message.answer(get_text(user_id, "deal_not_found"), reply_markup=main_menu_kb(user_id))
            return
        
        logger.info(f"✅ Знайдено угоду: {deal['deal_id']}")
        
        if deal["status"] != "pending":
            await message.answer(
                f"❌ Сделка уже {'занята' if deal['status'] == 'active' else 'завершена'}.",
                reply_markup=main_menu_kb(user_id)
            )
            return
        
        if deal["creator_id"] == user_id:
            await message.answer(get_text(user_id, "cant_join_own"), reply_markup=main_menu_kb(user_id))
            return
        
        if deal.get("participant_id"):
            await message.answer(get_text(user_id, "already_joined"), reply_markup=main_menu_kb(user_id))
            return

        opposite = "seller" if deal["creator_role"] == "buyer" else "buyer"
        await update_deal(
            deal["deal_id"],
            participant_id=user_id,
            participant_role=opposite,
            status="active"
        )
        
        deal = await get_deal(deal["deal_id"])
        await log_action("DEAL", user_id, message.from_user.username,
                         deal["deal_id"], "JOIN", f"Роль: {opposite}")

        try:
            await bot.send_message(
                deal["creator_id"],
                f"❗ К вашей сделке <code>{deal['deal_id']}</code> присоединился участник!\n\n"
                + deal_card(deal),
                reply_markup=main_menu_kb(deal["creator_id"])
            )
        except Exception as e:
            logger.error(f"Не вдалося повідомити творця: {e}")

        role_text = "Продавец" if opposite == "seller" else "Покупатель"
        user_role = "buyer" if role_text == "Покупатель" else "seller"
        
        await message.answer(
            f"✅ Вы успешно присоединились к сделке!\n\n"
            + deal_card(deal),
            reply_markup=deal_kb(deal, user_role)
        )
        return

    await message.answer(
        get_text(user_id, "welcome"),
        parse_mode="HTML",
        reply_markup=main_menu_kb(user_id)
    )


@dp.callback_query_handler(lambda c: c.data == "back_main", state="*")
async def back_main(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    user_id = call.from_user.id
    await call.message.edit_text(
        "🏠 <b>Главное меню</b>\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=main_menu_kb(user_id)
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data == "create_deal")
async def create_deal_start(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    user_id = call.from_user.id
    await CreateDeal.role.set()
    await call.message.edit_text(
        "🆕 <b>Создание сделки</b>\n\nВыберите вашу роль:",
        parse_mode="HTML",
        reply_markup=role_kb(user_id)
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("role_"), state=CreateDeal.role)
async def process_role(call: types.CallbackQuery, state: FSMContext):
    role = "buyer" if call.data == "role_buyer" else "seller"
    await state.update_data(role=role)
    await CreateDeal.currency.set()
    await call.message.edit_text(
        "💱 Выберите валюту сделки:",
        parse_mode="HTML",
        reply_markup=currency_kb()
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("cur_"), state=CreateDeal.currency)
async def process_currency(call: types.CallbackQuery, state: FSMContext):
    currency = call.data[4:]
    await state.update_data(currency=currency)
    await CreateDeal.amount.set()
    await call.message.edit_text(
        f"💰 Введите сумму сделки в <b>{currency}</b>:\n(только число, например: 150.5)",
        parse_mode="HTML",
        reply_markup=back_main_kb()
    )
    await call.answer()


@dp.message_handler(state=CreateDeal.amount)
async def process_amount(message: types.Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    
    current_state = await state.get_state()
    if current_state != "CreateDeal:amount":
        await message.answer(
            "⏳ Пожалуйста, завершите текущее действие.",
            reply_markup=main_menu_kb(message.from_user.id)
        )
        return
    
    try:
        amount = float(message.text.replace(",", ".").strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное положительное число.")
        return
    
    await state.update_data(amount=amount)
    await CreateDeal.description.set()
    await message.answer(
        "📝 Введите описание / ссылку на NFT-подарок:",
        parse_mode="HTML",
        reply_markup=back_main_kb()
    )


@dp.message_handler(state=CreateDeal.description)
async def process_description(message: types.Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    
    current_state = await state.get_state()
    if current_state != "CreateDeal:description":
        await message.answer(
            "⏳ Пожалуйста, завершите текущее действие.",
            reply_markup=main_menu_kb(message.from_user.id)
        )
        return
    
    description = message.text.strip()[:500]
    data = await state.get_data()
    
    if not data.get("role") or not data.get("currency") or not data.get("amount"):
        await state.finish()
        await message.answer("❌ Данные потеряны. Начните создание сделки заново.", reply_markup=main_menu_kb(message.from_user.id))
        return
    
    deal_id = await generate_deal_id()
    short_code = deal_id[-6:]
    await create_deal(deal_id, message.from_user.id, data["role"], data["amount"], data["currency"], description)
    await log_action("DEAL", message.from_user.id, message.from_user.username, deal_id, "CREATE", f"{data['role']} | {data['amount']} {data['currency']}")
    link = f"https://t.me/{BOT_USERNAME}?start=deal_{short_code}"
    role_text = "Покупатель" if data["role"] == "buyer" else "Продавец"
    
    await message.answer(
        f"✅ <b>Сделка создана!</b>\n\n"
        f"🆔 ID: <code>{deal_id}</code>\n"
        f"👤 Ваша роль: <b>{role_text}</b>\n"
        f"💰 Сумма: <b>{data['amount']} {data['currency']}</b>\n"
        f"📝 Описание: {description}\n\n"
        f"🔗 Ссылка для второй стороны:\n<code>{link}</code>",
        parse_mode="HTML",
        reply_markup=main_menu_kb(message.from_user.id)
    )
    await state.finish()


@dp.callback_query_handler(lambda c: c.data.startswith("pay_"))
async def process_payment(call: types.CallbackQuery):
    deal_id = call.data.replace("pay_", "")
    deal = await get_deal(deal_id)
    
    if not deal:
        await call.message.edit_text("❌ Сделка не найдена.", reply_markup=back_main_kb())
        await call.answer()
        return
    
    buyer_id = None
    if deal["creator_role"] == "buyer":
        buyer_id = deal["creator_id"]
    elif deal.get("participant_role") == "buyer":
        buyer_id = deal.get("participant_id")
    
    if not buyer_id:
        await call.message.edit_text("❌ Покупец не найден.", reply_markup=back_main_kb())
        await call.answer()
        return
    
    if call.from_user.id != buyer_id:
        await call.answer("⛔ Только покупатель может оплатить!")
        return
    
    if deal["status"] != "active":
        await call.answer("❌ Сделка уже оплачена или завершена!")
        return
    
    user = await get_user(buyer_id)
    currency = deal["currency"]
    amount = float(deal["amount"])
    balance_field = f"balance_{currency.lower()}"
    current_balance = user.get(balance_field, 0) or 0
    
    if current_balance < amount:
        await call.message.edit_text(
            f"❌ Недостаточно средств!\n\n"
            f"💰 Ваш баланс: {current_balance:.4f} {currency}\n"
            f"💳 Сумма к оплате: {amount:.4f} {currency}\n\n"
            "Пополните баланс и попробуйте снова.",
            reply_markup=back_main_kb()
        )
        await call.answer()
        return
    
    await add_balance(buyer_id, currency, -amount)
    now = datetime.utcnow().isoformat()
    await update_deal(deal_id, status="paid", paid_at=now)
    
    await log_action("PAYMENT", buyer_id, call.from_user.username,
                     deal_id, "PAY", f"{amount} {currency} списано с баланса")
    
    deal = await get_deal(deal_id)
    
    await call.message.edit_text(
        f"✅ Оплата по сделке <code>{deal_id}</code> успешно проведена!\n\n"
        f"💰 Сумма: {amount} {currency}\n"
        f"📅 Дата: {now[:19]}\n\n"
        "Ожидайте передачи NFT от продавца.",
        reply_markup=back_main_kb()
    )
    
    seller_id = None
    if deal["creator_role"] == "seller":
        seller_id = deal["creator_id"]
    elif deal.get("participant_role") == "seller":
        seller_id = deal.get("participant_id")
    
    if seller_id:
        try:
            await bot.send_message(
                seller_id,
                f"💳 <b>Покупатель успешно оплатил сделку!</b>\n\n"
                f"📎 СДЕЛКА: <code>{deal_id}</code>\n"
                f"💰 СУММА: <b>{amount} {currency}</b>\n"
                f"👤 ПОКУПАТЕЛЬ: <code>{buyer_id}</code>\n\n"
                f"📤 <b>Передайте NFT-подарок строго на этот аккаунт:</b>\n"
                f"🔹 <code>@funpaybag</code>\n\n"
                f"⚠️ <b>После передачи нажмите кнопку «Подтвердить передачу» в админ-панели.</b>",
                parse_mode="HTML",
                reply_markup=main_menu_kb(seller_id)
            )
        except Exception as e:
            logger.error(f"Не вдалося повідомити продавця: {e}")
    
    await call.answer("✅ Оплата прошла успешно!")


@dp.callback_query_handler(lambda c: c.data.startswith("refresh_"))
async def refresh_deal(call: types.CallbackQuery):
    deal_id = call.data.replace("refresh_", "")
    deal = await get_deal(deal_id)
    
    if not deal:
        await call.message.edit_text("❌ Сделка не найдена.", reply_markup=back_main_kb())
        await call.answer()
        return
    
    user_role = None
    if deal["creator_id"] == call.from_user.id:
        user_role = deal["creator_role"]
    elif deal.get("participant_id") == call.from_user.id:
        user_role = deal.get("participant_role")
    
    text = deal_card(deal)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=deal_kb(deal, user_role))
    await call.answer("🔄 Статус обновлен!")


@dp.callback_query_handler(lambda c: c.data == "balance")
async def show_balance(call: types.CallbackQuery):
    user_id = call.from_user.id
    user = await get_user(user_id)
    text = get_text(user_id, "balance") + "\n━━━━━━━━━━━━━━━━━━━━\n"
    for cur in CURRENCIES:
        field = f"balance_{cur.lower()}"
        val = user.get(field, 0) or 0
        text += f"• {cur}: <b>{val:.4f}</b>\n"
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("➕ Пополнить баланс", callback_data="topup_info"),
        InlineKeyboardButton("➖ Вывести баланс", callback_data="withdraw_info"),
        InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_main")
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@dp.callback_query_handler(lambda c: c.data in ("topup_info", "withdraw_info"))
async def balance_info(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    if call.data == "topup_info":
        await call.message.edit_text(
            get_text(user_id, "topup_info"),
            parse_mode="HTML",
            reply_markup=back_main_kb()
        )
    else:
        await call.message.edit_text(
            get_text(user_id, "withdraw_info"),
            parse_mode="HTML",
            reply_markup=back_main_kb()
        )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data == "my_deals")
async def my_deals(call: types.CallbackQuery):
    user_id = call.from_user.id
    deals = await get_user_deals(user_id, 10)
    if not deals:
        text = get_text(user_id, "no_deals")
    else:
        text = get_text(user_id, "my_deals") + "\n━━━━━━━━━━━━━━━━━━━━\n"
        for d in deals:
            st = {"pending": "⏳", "active": "🟢", "paid": "💵", "completed": "✅", "cancelled": "❌"}.get(d["status"], "❓")
            text += f"{st} <code>{d['deal_id']}</code> — {d['amount']} {d['currency']} ({d['status']})\n"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=back_main_kb())
    await call.answer()


@dp.callback_query_handler(lambda c: c.data == "requisites")
async def requisites_menu(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    user = await get_user(user_id)
    current = user.get("requisites") or "не указаны"
    await AdminStates.set_requisites.set()
    await call.message.edit_text(
        f"💳 <b>Реквизиты</b>\n\nТекущие: <code>{current}</code>\n\nОтправьте новые реквизиты одним сообщением:",
        parse_mode="HTML",
        reply_markup=back_main_kb()
    )
    await call.answer()


@dp.message_handler(state=AdminStates.set_requisites)
async def save_requisites(message: types.Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    req = message.text.strip()[:500]
    await update_user(message.from_user.id, requisites=req)
    await log_action("USER", message.from_user.id, message.from_user.username, action="REQUISITES", details=req[:100])
    await state.finish()
    await message.answer("✅ Реквизиты сохранены.", reply_markup=main_menu_kb(message.from_user.id))


@dp.callback_query_handler(lambda c: c.data == "language")
async def language_menu(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=1)
    for code, name in {"en": "English", "ru": "Русский", "uk": "Українська", "zh": "中文", "kk": "Қазақша", "ko": "한국어", "ja": "日本語", "de": "Deutsch", "ar": "العربية"}.items():
        kb.add(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
    await call.message.edit_text("🌐 <b>Выберите язык</b>", parse_mode="HTML", reply_markup=kb)
    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def set_language(call: types.CallbackQuery):
    lang = call.data.replace("lang_", "")
    user_id = call.from_user.id
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE users SET language = ? WHERE user_id = ?', (lang, user_id))
    conn.commit()
    conn.close()
    
    await call.message.delete()
    await call.message.answer(
        get_text(user_id, "language_changed"),
        parse_mode="HTML",
        reply_markup=main_menu_kb(user_id)
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data == "safety")
async def safety(call: types.CallbackQuery):
    user_id = call.from_user.id
    await call.message.edit_text(
        get_text(user_id, "safety") + "\n━━━━━━━━━━━━━━━━━━━━\n"
        "1. 🔒 Все сделки проходят через гаранта.\n"
        "2. 💰 Средства удерживаются до подтверждения передачи.\n"
        "3. ✅ Администраторы проверяют каждую сделку.\n"
        "4. 📝 Ведётся полный лог действий.\n"
        "5. 🚫 Запрещены сделки вне бота.\n"
        "6. 👤 Рекомендуется верификация.\n"
        "7. 🆘 При споре обращайтесь в поддержку.\n\n"
        "Мы защищаем обе стороны сделки.",
        parse_mode="HTML",
        reply_markup=back_main_kb()
    )
    await call.answer()


@dp.callback_query_handler(lambda c: c.data == "support")
async def support(call: types.CallbackQuery):
    user_id = call.from_user.id
    await call.message.edit_text(
        get_text(user_id, "support"),
        parse_mode="HTML",
        reply_markup=back_main_kb()
    )
    await call.answer()


@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.finish()
    await message.answer("🔐 <b>Админ-панель</b>", parse_mode="HTML", reply_markup=admin_kb())


@dp.callback_query_handler(lambda c: c.data.startswith("adm_"))
async def admin_callback(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("⛔ Доступ запрещен.")
        return
    data = call.data
    if data == "adm_deals":
        deals = await get_all_deals(20)
        text = "📋 <b>Последние 20 сделок</b>\n\n" if deals else "Нет сделок."
        for d in deals or []:
            text += f"<code>{d['deal_id']}</code> | {d['amount']} {d['currency']} | {d['status']} | {d['created_at'][:10]}\n"
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_kb())
    elif data == "adm_stats":
        users, deals, turnover = await get_stats()
        text = f"📊 <b>Статистика</b>\n\n👥 Пользователей: <b>{users}</b>\n📄 Сделок: <b>{deals}</b>\n\n<b>Оборот (completed):</b>\n"
        for cur, val in turnover.items():
            if val:
                text += f"• {cur}: {val:.2f}\n"
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_kb())
    elif data == "adm_confirm_pay":
        await AdminStates.confirm_payment.set()
        await call.message.edit_text("Введите ID сделки для подтверждения оплаты:", reply_markup=back_main_kb())
    elif data == "adm_confirm_transfer":
        await AdminStates.confirm_transfer.set()
        await call.message.edit_text("Введите ID сделки для подтверждения передачи:", reply_markup=back_main_kb())
    elif data == "adm_topup":
        await AdminStates.topup_user.set()
        await call.message.edit_text("Введите user_id пользователя:", reply_markup=back_main_kb())
    elif data == "adm_broadcast":
        await AdminStates.broadcast.set()
        await call.message.edit_text("Введите текст рассылки:", reply_markup=back_main_kb())
    elif data == "adm_users":
        users = await get_recent_users(20)
        text = "👥 <b>Последние 20 пользователей</b>\n\n"
        for u in users:
            text += f"<code>{u['user_id']}</code> @{u['username'] or '—'} | {u['created_at'][:10]}\n"
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_kb())
    elif data == "adm_export":
        deals = await get_all_deals(1000)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["deal_id", "creator_id", "creator_role", "participant_id", "participant_role", "amount", "currency", "description", "status", "created_at", "completed_at"])
        for d in deals:
            writer.writerow([d["deal_id"], d["creator_id"], d["creator_role"], d.get("participant_id"), d.get("participant_role"), d["amount"], d["currency"], d["description"], d["status"], d["created_at"], d.get("completed_at")])
        output.seek(0)
        file = types.InputFile(io.BytesIO(output.getvalue().encode()), filename="deals_export.csv")
        await call.message.answer_document(file, caption="📤 Экспорт сделок")
    await call.answer()


@dp.message_handler(state=AdminStates.confirm_payment)
async def adm_confirm_pay(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    deal_id = message.text.strip()
    deal = await get_deal(deal_id)
    if not deal:
        await message.answer("❌ Сделка не найдена.")
        return
    if deal["status"] not in ("active", "pending"):
        await message.answer(f"❌ Статус уже: {deal['status']}")
        return
    await update_deal(deal_id, status="paid")
    await log_action("ADMIN", message.from_user.id, message.from_user.username, deal_id, "CONFIRM_PAY")
    for uid in (deal["creator_id"], deal.get("participant_id")):
        if uid:
            try:
                await bot.send_message(uid, f"💵 Оплата по сделке <code>{deal_id}</code> подтверждена!")
            except Exception:
                pass
    await state.finish()
    await message.answer("✅ Статус изменён на <b>paid</b>", reply_markup=admin_kb())


@dp.message_handler(state=AdminStates.confirm_transfer)
async def adm_confirm_transfer(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    deal_id = message.text.strip()
    deal = await get_deal(deal_id)
    if not deal:
        await message.answer("❌ Сделка не найдена.")
        return
    if deal["status"] not in ("paid", "active"):
        await message.answer(f"❌ Нельзя завершить. Статус: {deal['status']}")
        return
    seller_id = deal["creator_id"] if deal["creator_role"] == "seller" else deal.get("participant_id")
    if not seller_id:
        await message.answer("❌ Нет продавца в сделке.")
        return
    amount = float(deal["amount"])
    commission = amount * COMMISSION_PERCENT / 100
    seller_amount = amount - commission
    await add_balance(seller_id, deal["currency"], seller_amount)
    now = datetime.utcnow().isoformat()
    await update_deal(deal_id, status="completed", completed_at=now)
    await log_action("ADMIN", message.from_user.id, message.from_user.username, deal_id, "CONFIRM_TRANSFER", f"Seller +{seller_amount} {deal['currency']}, profit {commission}")
    await state.finish()
    await message.answer(
        f"✅ Сделка завершена.\n"
        f"Продавцу: {seller_amount:.4f} {deal['currency']}\n"
        f"Профит: {commission:.4f} {deal['currency']}",
        reply_markup=admin_kb()
    )


@dp.message_handler(state=AdminStates.topup_user)
async def adm_topup_user(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Нужен числовой user_id")
        return
    await state.update_data(topup_uid=uid)
    await AdminStates.topup_amount.set()
    await message.answer("Введите сумму:")


@dp.message_handler(state=AdminStates.topup_amount)
async def adm_topup_amount(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        amount = float(message.text.replace(",", ".").strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Некорректная сумма")
        return
    await state.update_data(topup_amount=amount)
    await AdminStates.topup_currency.set()
    kb = InlineKeyboardMarkup(row_width=1)
    for cur in CURRENCIES:
        kb.add(InlineKeyboardButton(cur, callback_data=f"admcur_{cur}"))
    await message.answer("Выберите валюту:", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith("admcur_"), state=AdminStates.topup_currency)
async def adm_topup_currency(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return
    currency = call.data[7:]
    data = await state.get_data()
    uid = data["topup_uid"]
    amount = data["topup_amount"]
    await get_user(uid)
    await add_balance(uid, currency, amount)
    await log_action("ADMIN", call.from_user.id, call.from_user.username, action="TOPUP", details=f"{uid} +{amount} {currency}")
    try:
        await bot.send_message(uid, f"💰 Вам пополнен баланс: +{amount} {currency}")
    except Exception:
        pass
    await state.finish()
    await call.message.edit_text(
        f"✅ Пополнено {amount} {currency} пользователю <code>{uid}</code>",
        parse_mode="HTML",
        reply_markup=admin_kb()
    )
    await call.answer()


@dp.message_handler(state=AdminStates.broadcast)
async def adm_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            users = [r[0] for r in await cur.fetchall()]
    success = 0
    for uid in users:
        try:
            await bot.send_message(uid, text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await state.finish()
    await message.answer(
        f"✅ Рассылка завершена. Доставлено: {success}/{len(users)}",
        reply_markup=admin_kb()
    )


@dp.message_handler(state="*")
async def unknown_message(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    user_id = message.from_user.id
    
    if not current_state:
        await message.answer(
            "🤔 Я не понимаю эту команду.\n\n"
            "Используйте кнопки меню или напишите /start",
            parse_mode="HTML",
            reply_markup=main_menu_kb(user_id)
        )
        return
    
    if current_state in ["CreateDeal:amount", "CreateDeal:description"]:
        await message.answer(
            "⏳ Пожалуйста, завершите создание сделки.\n"
            "Введите число или описание, или нажмите «Назад».",
            parse_mode="HTML",
            reply_markup=back_main_kb()
        )
    else:
        await message.answer(
            "🤔 Я не понимаю эту команду.\n\n"
            "Используйте кнопки меню или напишите /start",
            parse_mode="HTML",
            reply_markup=main_menu_kb(user_id)
        )


async def keep_alive():
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                await session.get("https://ваш-сервіс.onrender.com/health")
        except:
            pass
        await asyncio.sleep(300)


async def on_startup(dp):
    await init_db()
    logger.info("Бот запущено, БД ініціалізовано")


async def start_web():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    app.router.add_get("/health", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Web-сервер запущено на порту 8080")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_web())
    loop.create_task(keep_alive())
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
