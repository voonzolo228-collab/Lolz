import sys
import os

print("=" * 50)
print("🔍 ДИАГНОСТИКА ЗАПУСКА")
print("=" * 50)
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Files in directory: {os.listdir('.')}")
print("=" * 50)

# ============ ПЕРЕВІРКА ІМПОРТІВ ============
print("📦 ШАГ 1: Проверка импортов...")

try:
    import sqlite3
    print("✅ sqlite3 - OK")
except Exception as e:
    print(f"❌ sqlite3 - ERROR: {e}")

try:
    import random
    import string
    print("✅ random, string - OK")
except Exception as e:
    print(f"❌ random/string - ERROR: {e}")

try:
    import re
    import html
    print("✅ re, html - OK")
except Exception as e:
    print(f"❌ re/html - ERROR: {e}")

try:
    from datetime import datetime
    from typing import Optional, Dict, Any
    print("✅ datetime, typing - OK")
except Exception as e:
    print(f"❌ datetime/typing - ERROR: {e}")

try:
    from aiogram import Bot, Dispatcher, types
    from aiogram.contrib.fsm_storage.memory import MemoryStorage
    from aiogram.dispatcher import FSMContext
    from aiogram.dispatcher.filters.state import State, StatesGroup
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    from aiogram.utils import executor
    print("✅ aiogram - OK")
except Exception as e:
    print(f"❌ aiogram - ERROR: {e}")
    sys.exit(1)

try:
    import asyncio
    print("✅ asyncio - OK")
except Exception as e:
    print(f"❌ asyncio - ERROR: {e}")

try:
    from aiohttp import web
    print("✅ aiohttp.web - OK")
except Exception as e:
    print(f"❌ aiohttp.web - ERROR: {e}")

print("=" * 50)
print("🚀 ШАГ 2: Инициализация бота...")
print("=" * 50)

# ============ НАЛАШТУВАННЯ ============
API_TOKEN = '8698578814:AAEavw5BZ7nj6czWH5Dq6g22r4WGfvzRHHo'
LOG_CHAT_ID = -1004451013532
PROFIT_CHAT_ID = -1004451013532
LOG_THREAD_ID = 2986
PROFIT_THREAD_ID = 159
ADMIN_IDS = [8323946313]
DB_PATH = "funpay.db"
BOT_USERNAME = "IoIzDeaIs_bot"

print(f"✅ API_TOKEN: {API_TOKEN[:10]}...")
print(f"✅ LOG_CHAT_ID: {LOG_CHAT_ID}")
print(f"✅ ADMIN_IDS: {ADMIN_IDS}")

# ============ СТВОРЕННЯ БОТА ============
print("🤖 ШАГ 3: Создание бота...")

try:
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(bot, storage=MemoryStorage())
    print("✅ Бот создан успешно!")
except Exception as e:
    print(f"❌ Ошибка создания бота: {e}")
    sys.exit(1)

print("=" * 50)
print("📊 ШАГ 4: Инициализация базы данных...")
print("=" * 50)

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
        return True
    except Exception as e:
        print(f"❌ Ошибка создания БД: {e}")
        return False

if init_db():
    print("✅ База данных инициализирована")
else:
    print("❌ Ошибка инициализации БД")
    sys.exit(1)

print("=" * 50)
print("🌐 ШАГ 5: Запуск WEB-сервера...")
print("=" * 50)

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

print("=" * 50)
print("🎯 ШАГ 6: Загрузка клавиатур...")
print("=" * 50)

# ============ КРАСИВІ КЛАВІАТУРИ ============
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

print("=" * 50)
print("🎯 ШАГ 7: Загрузка состояний...")
print("=" * 50)

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

print("✅ Состояния загружены")

print("=" * 50)
print("🎯 ШАГ 8: Загрузка функций...")
print("=" * 50)

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

print("✅ Вспомогательные функции загружены")

print("=" * 50)
print("🚀 БОТ ГОТОВ К ЗАПУСКУ!")
print("=" * 50)

# ============ ХЕНДЛЕРИ КОРИСТУВАЧА ============
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

# ============ ЗАПУСК ============
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_web())
    print("🚀 ЗАПУСК БОТА...")
    executor.start_polling(dp, skip_updates=True)
