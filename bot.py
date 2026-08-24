import sqlite3
import random
import string
import re
import html
from datetime import datetime
from typing import Optional, Dict, Any
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import sys
import os
import asyncio
from aiohttp import web

print("=== БОТ НАЧИНАЕТ ЗАГРУЗКУ ===")
print(f"Python: {sys.version}")

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

# ============ КЛАВІАТУРИ (КНОПКИ ПІД ПОВІДОМЛЕННЯМ) ============
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("🆕 Создать сделку"),
        KeyboardButton("💰 Мой баланс"),
        KeyboardButton("📋 Мои сделки"),
        KeyboardButton("✅ Верификация"),
        KeyboardButton("💳 Мои реквизиты"),
        KeyboardButton("🌐 Сменить язык"),
        KeyboardButton("🛡 Безопасность сделок"),
        KeyboardButton("🆘 Поддержка")
    )
    return kb

def back_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔙 Вернуться в меню"))
    return kb

def role_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("👤 Я покупатель"), KeyboardButton("👤 Я продавец"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def currency_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    currencies = ["💎 TON", "₽ RUB", "$ USD", "₴ UAH", "⭐ Stars", "💵 USDT", "₸ KGS", "₸ UZS", "₽ BYN", "₸ KZT"]
    for cur in currencies:
        kb.add(KeyboardButton(cur))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def cancel_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("📋 Все сделки"),
        KeyboardButton("📊 Статистика"),
        KeyboardButton("✅ Подтвердить оплату"),
        KeyboardButton("✅ Подтвердить передачу"),
        KeyboardButton("💳 Пополнить баланс"),
        KeyboardButton("📩 Рассылка"),
        KeyboardButton("🔙 В главное меню")
    )
    return kb

print("✅ Клавиатуры загружены")

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
        conn.close()
        return {"total_deals": total_deals, "total_users": total_users, "completed_deals": completed_deals}
    except:
        return {"total_deals": 0, "total_users": 0, "completed_deals": 0}

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
        await message.answer(
            "🎉 <b>Добро пожаловать в FunPay!</b>\n\n"
            "💎 0% комиссии для всех сделок\n"
            "🔐 Безопасные P2P-сделки с NFT\n"
            "📱 Нажми кнопки ниже чтобы начать",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)[:100]}")

@dp.message_handler(lambda msg: msg.text == "💰 Мой баланс")
async def handle_balance(message: types.Message):
    try:
        balance = get_user_balance(message.from_user.id)
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
        await message.answer(text, parse_mode="HTML", reply_markup=back_menu())
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)[:100]}")

@dp.message_handler(lambda msg: msg.text == "📋 Мои сделки")
async def handle_my_deals(message: types.Message):
    try:
        user_id = message.from_user.id
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
            await message.answer("📭 У вас пока нет сделок.", reply_markup=back_menu())
            return
        text = "📋 <b>Ваши последние сделки</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        for deal in deals:
            status_emoji = "✅" if deal[3] == "completed" else "⏳"
            text += f"{status_emoji} {deal[0]} | {deal[1]} {deal[2]}\n"
        await message.answer(text, parse_mode="HTML", reply_markup=back_menu())
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)[:100]}")

@dp.message_handler(lambda msg: msg.text == "✅ Верификация")
async def handle_verification(message: types.Message):
    await message.answer(
        "🔐 <b>Верификация FunPay</b>\n\n"
        "Ваш статус: <b>не верифицирован</b>\n\n"
        "ℹ️ Этот бот показывает статус только внутри текущего гаранта.\n"
        "Официальной проверки сторонних площадок здесь нет.",
        parse_mode="HTML",
        reply_markup=back_menu()
    )

@dp.message_handler(lambda msg: msg.text == "💳 Мои реквизиты")
async def handle_requisites(message: types.Message):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT requisites FROM users WHERE user_id = ?', (message.from_user.id,))
        result = cur.fetchone()
        conn.close()
        if result and result[0]:
            await message.answer(
                f"💳 <b>Ваши реквизиты</b>\n\n{result[0]}",
                parse_mode="HTML",
                reply_markup=back_menu()
            )
        else:
            await message.answer(
                "💳 <b>Реквизиты не заполнены</b>\n\n"
                "Используйте команду:\n"
                "<code>/set_requisites Ваши реквизиты</code>",
                parse_mode="HTML",
                reply_markup=back_menu()
            )
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)[:100]}")

@dp.message_handler(commands=["set_requisites"])
async def set_requisites(message: types.Message):
    try:
        text = message.text.replace('/set_requisites', '').strip()
        if not text:
            await message.answer(
                "❌ <b>Использование:</b>\n"
                "<code>/set_requisites Ваши реквизиты</code>",
                parse_mode="HTML"
            )
            return
        conn = get_db()
        cur = conn.cursor()
        cur.execute('UPDATE users SET requisites = ? WHERE user_id = ?', (text, message.from_user.id))
        conn.commit()
        conn.close()
        await message.answer("✅ Реквизиты сохранены!", reply_markup=back_menu())
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)[:100]}")

@dp.message_handler(lambda msg: msg.text == "🌐 Сменить язык")
async def handle_language(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    for lang in ['🇬🇧 English', '🇷🇺 Русский', '🇺🇦 Українська', '🇨🇳 中文', '🇰🇿 Қазақша', '🇰🇷 한국어', '🇯🇵 日本語', '🇩🇪 Deutsch', '🇸🇦 العربية']:
        kb.add(KeyboardButton(lang))
    kb.add(KeyboardButton("🔙 Назад"))
    await message.answer("🌐 <b>Выберите язык</b>", parse_mode="HTML", reply_markup=kb)

@dp.message_handler(lambda msg: msg.text in ['🇬🇧 English', '🇷🇺 Русский', '🇺🇦 Українська', '🇨🇳 中文', '🇰🇿 Қазақша', '🇰🇷 한국어', '🇯🇵 日本語', '🇩🇪 Deutsch', '🇸🇦 العربية'])
async def set_language(message: types.Message):
    try:
        lang_map = {
            '🇬🇧 English': 'en', '🇷🇺 Русский': 'ru', '🇺🇦 Українська': 'uk',
            '🇨🇳 中文': 'zh', '🇰🇿 Қазақша': 'kz', '🇰🇷 한국어': 'ko',
            '🇯🇵 日本語': 'ja', '🇩🇪 Deutsch': 'de', '🇸🇦 العربية': 'ar'
        }
        conn = get_db()
        cur = conn.cursor()
        cur.execute('UPDATE users SET language = ? WHERE user_id = ?', (lang_map[message.text], message.from_user.id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Язык изменен на {message.text}", reply_markup=back_menu())
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)[:100]}")

@dp.message_handler(lambda msg: msg.text == "🛡 Безопасность сделок")
async def handle_safety(message: types.Message):
    text = (
        "🛡 <b>Безопасность сделок FunPay</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "1️⃣ Сделка фиксируется внутри бота\n"
        "2️⃣ Вторая сторона подключается только к конкретной сделке\n"
        "3️⃣ Деньги и товар не смешиваются в одном шаге\n"
        "4️⃣ Участники видят свои роли\n"
        "5️⃣ Статус сделки отслеживается\n"
        "6️⃣ Доступ к информации ограничен участниками\n"
        "7️⃣ Всегда сверяйте номер сделки, сумму, валюту, описание и username\n\n"
        "⚠️ <b>Главное правило:</b>\n"
        "Безопасной считается только та сделка, условия которой совпадают в карточке бота и у обеих сторон."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=back_menu())

@dp.message_handler(lambda msg: msg.text == "🆘 Поддержка")
async def handle_support(message: types.Message):
    await message.answer(
        "🆘 <b>Поддержка FunPay</b>\n\n"
        "👨‍💻 Свяжитесь с нами: @FunPaySupport\n\n"
        "⏱ Мы отвечаем в течение 15 минут.",
        parse_mode="HTML",
        reply_markup=back_menu()
    )

@dp.message_handler(lambda msg: msg.text == "🔙 Вернуться в меню" or msg.text == "🔙 Назад" or msg.text == "❌ Отмена")
async def back_to_menu(message: types.Message):
    await message.answer("🏠 <b>Главное меню</b>", parse_mode="HTML", reply_markup=main_menu())

# ============ ІНШІ ХЕНДЛЕРИ ============
# Тут йдуть всі інші хендлери для створення сделки, адмін-панелі тощо...
# Вони такі ж, як у попередніх версіях

# ============ ЗАПУСК ============
print("=== БОТ ГОТОВ К ЗАПУСКУ ===")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_web())
    print("🚀 БОТ ЗАПУЩЕН!")
    executor.start_polling(dp, skip_updates=True)
