import sqlite3
import random
import string
import asyncio
import aiohttp
import re
import csv
import io
import traceback
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import os

# ============ НАЛАШТУВАННЯ ============
API_TOKEN = '8698578814:AAEavw5BZ7nj6czWH5Dq6g22r4WGfvzRHHo'
LOG_CHAT_ID = -1004451013532
PROFIT_CHAT_ID = -1004451013532
LOG_THREAD_ID = 2986
PROFIT_THREAD_ID = 159
ADMIN_IDS = [8323946313]

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)

# ============ БАЗА ДАНИХ ============
def init_db():
    conn = sqlite3.connect('funpay.db')
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
            requisites TEXT DEFAULT ''
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS deals (
            deal_id TEXT PRIMARY KEY,
            creator_id INTEGER,
            creator_role TEXT,
            participant_id INTEGER,
            participant_role TEXT,
            amount REAL,
            currency TEXT,
            description TEXT,
            status TEXT DEFAULT 'created',
            created_at TEXT,
            completed_at TEXT
        )
    ''')
    cur.execute('''
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
    ''')
    conn.commit()
    conn.close()

init_db()

# ============ СТАНИ ============
class DealStates(StatesGroup):
    choose_role = State()
    choose_currency = State()
    enter_amount = State()
    enter_description = State()

# ============ КЛАВІАТУРИ ============
main_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
main_menu.add(
    KeyboardButton('Сохранить сделки'),
    KeyboardButton('Баланс'),
    KeyboardButton('Мои сделки'),
    KeyboardButton('Верификация'),
    KeyboardButton('Реквизиты'),
    KeyboardButton('Язык'),
    KeyboardButton('Безопасно ли это?'),
    KeyboardButton('Поддержка')
)

back_menu = ReplyKeyboardMarkup(resize_keyboard=True)
back_menu.add(KeyboardButton('Вернуться в меню'))

currency_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
currency_menu.add(
    KeyboardButton('На TON-кошелек'),
    KeyboardButton('Карта (RUB)'),
    KeyboardButton('Карта (USD)'),
    KeyboardButton('Карта (UAH)'),
    KeyboardButton('Звезды'),
    KeyboardButton('USDT-кошелек'),
    KeyboardButton('Карта (KGS)'),
    KeyboardButton('Карта (UZS)'),
    KeyboardButton('Карта (BYN)'),
    KeyboardButton('Карта (KZT)'),
    KeyboardButton('Отмена')
)

role_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
role_menu.add(
    KeyboardButton('Покупатель'),
    KeyboardButton('Продавец'),
    KeyboardButton('Отмена')
)

admin_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
admin_menu.add(
    KeyboardButton('📋 Все сделки'),
    KeyboardButton('📊 Статистика'),
    KeyboardButton('✅ Подтвердить оплату'),
    KeyboardButton('✅ Подтвердить передачу'),
    KeyboardButton('💳 Пополнить баланс'),
    KeyboardButton('📩 Рассылка'),
    KeyboardButton('📋 Логи'),
    KeyboardButton('📊 Профиты'),
    KeyboardButton('📤 Скачать логи'),
    KeyboardButton('🔙 В главное меню')
)

# ============ ДОПОМІЖНІ ФУНКЦІЇ ============
def generate_deal_id():
    return '#716MZK' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def get_user_balance(user_id):
    conn = sqlite3.connect('funpay.db')
    cur = conn.cursor()
    cur.execute('SELECT balance_ton, balance_rub, balance_usd, balance_uah, balance_stars, balance_usdt, balance_kgs, balance_uzs, balance_byn, balance_kzt FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    return result if result else (0,0,0,0,0,0,0,0,0,0)

def update_balance(user_id, currency, amount):
    if amount <= 0:
        return
    conn = sqlite3.connect('funpay.db')
    cur = conn.cursor()
    cur.execute(f'UPDATE users SET balance_{currency} = balance_{currency} + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ============ ЛОГИ ============
async def send_log_to_group(log_type, username=None, user_id=None, deal_id=None, action=None, details=None):
    emoji_map = {
        'deal_created': '🟢', 'deal_joined': '🔵', 'deal_paid': '💰',
        'deal_completed': '✅', 'deal_disputed': '🔴', 'deal_resolved': '⚖️',
        'admin_action': '🛠️', 'user_activity': '👤', 'nft_transfer': '🎁',
        'payment': '💳', 'error': '⚠️'
    }
    emoji = emoji_map.get(log_type, '📌')
    time = datetime.now().strftime('%d.%m.%Y %H:%M')
    text = f'{emoji} <b>Лог | {time}</b>\n📌 Тип: {log_type}\n'
    if username:
        text += f'👤 @{username}'
    elif user_id:
        text += f'👤 ID: {user_id}'
    if deal_id:
        text += f' | 📎 <code>{deal_id}</code>'
    if action:
        text += f'\n📝 {action}'
    if details:
        text += f'\n📄 {details}'
    try:
        if LOG_THREAD_ID and LOG_THREAD_ID != 0:
            await bot.send_message(LOG_CHAT_ID, text, parse_mode='HTML', message_thread_id=LOG_THREAD_ID)
        else:
            await bot.send_message(LOG_CHAT_ID, text, parse_mode='HTML')
    except Exception as e:
        print(f'Ошибка отправки лога: {e}')

async def add_log_and_send(log_type, user_id=None, username=None, deal_id=None, action=None, details=None):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect('funpay.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO logs (log_type, user_id, username, deal_id, action, details, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (log_type, user_id, username, deal_id, action, details, timestamp))
    conn.commit()
    conn.close()
    await send_log_to_group(log_type, username, user_id, deal_id, action, details)

# ============ ПРОФІТИ ============
async def send_profit_to_group(deal_id, nft_link, amount, worker_name, worker_share):
    text = f"""
НОВЫЙ ПРОФИТ

- ПРОФИТ · ОТС
- СДЕЛКА: {deal_id}
- СУММА ПРОФИТА: {amount}

- {nft_link}

- ВОРКЕР: {worker_name}
- ДОЛЯ ВОРКЕРА: {worker_share} (70%)
"""
    try:
        if PROFIT_THREAD_ID and PROFIT_THREAD_ID != 0:
            await bot.send_message(PROFIT_CHAT_ID, text, parse_mode='HTML', message_thread_id=PROFIT_THREAD_ID)
        else:
            await bot.send_message(PROFIT_CHAT_ID, text, parse_mode='HTML')
    except Exception as e:
        print(f'Ошибка отправки профита: {e}')

# ============ ЦІНА NFT ============
async def get_nft_price(nft_link):
    try:
        if not nft_link:
            return None
        if 't.me/nft/' in nft_link:
            async with aiohttp.ClientSession() as session:
                async with session.get(nft_link) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        price_match = re.search(r'"price":\s*([\d.]+)', html)
                        if price_match:
                            return float(price_match.group(1))
                        price_match = re.search(r'([\d.]+)\s*(TON|Stars|RUB|USD)', html)
                        if price_match:
                            return float(price_match.group(1))
        return None
    except Exception as e:
        print(f'Помилка отримання ціни: {e}')
        return None

async def calculate_profit(nft_link):
    if not nft_link:
        return {'price': None, 'commission': None, 'profit': None, 'currency': 'Stars', 'error': 'Посилання на NFT відсутнє'}
    
    price = await get_nft_price(nft_link)
    if not price:
        return {'price': None, 'commission': None, 'profit': None, 'currency': 'Stars', 'error': 'Не удалось определить цену'}
    
    currency = 'Stars'
    if 'TON' in nft_link.upper():
        currency = 'TON'
    elif 'RUB' in nft_link.upper():
        currency = 'RUB'
    elif 'USD' in nft_link.upper():
        currency = 'USD'
    
    commission = price * 0.30
    profit = price - commission
    return {
        'price': price,
        'commission': commission,
        'profit': profit,
        'currency': currency,
        'commission_percent': 30,
        'error': None
    }

# ============ ХЕНДЛЕРИ ============
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    user_id = msg.from_user.id
    username = msg.from_user.username
    conn = sqlite3.connect('funpay.db')
    cur = conn.cursor()
    cur.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()
    await msg.answer('Добро пожаловать в FunPay.\n\n0% комиссии, нажми кнопки ниже чтобы открыть маркет', reply_markup=main_menu)

@dp.message_handler(lambda msg: msg.text == 'Баланс')
async def show_balance(msg: types.Message):
    balance = get_user_balance(msg.from_user.id)
    text = f"""
Ваш баланс FunPay:

TON: {balance[0]:.3f}
RUB: {balance[1]:.2f}
USD: {balance[2]:.2f}
UAH: {balance[3]:.2f}
Stars: {balance[4]:.0f}
USDT: {balance[5]:.2f}
KGS: {balance[6]:.2f}
UZS: {balance[7]:.2f}
BYN: {balance[8]:.2f}
KZT: {balance[9]:.2f}
"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(KeyboardButton('Пополнить баланс'), KeyboardButton('Вывести баланс'), KeyboardButton('Вернуться в меню'))
    await msg.answer(text, reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == 'Пополнить баланс')
async def deposit(msg: types.Message):
    await msg.answer('🚧 Функция пополнения в разработке. Свяжитесь с поддержкой: @FunPaySupport', reply_markup=back_menu)

@dp.message_handler(lambda msg: msg.text == 'Вывести баланс')
async def withdraw(msg: types.Message):
    await msg.answer('🚧 Функция вывода в разработке. Свяжитесь с поддержкой: @FunPaySupport', reply_markup=back_menu)

@dp.message_handler(lambda msg: msg.text == 'Верификация')
async def verify(msg: types.Message):
    await msg.answer('Ваш статус: не верифицирован.\n\nЭтот бот показывает статус только внутри текущего гаранта.', reply_markup=back_menu)

@dp.message_handler(lambda msg: msg.text == 'Мои сделки')
async def my_deals(msg: types.Message):
    user_id = msg.from_user.id
    conn = sqlite3.connect('funpay.db')
    cur = conn.cursor()
    cur.execute('SELECT deal_id, amount, currency, status FROM deals WHERE creator_id = ? OR participant_id = ? ORDER BY created_at DESC LIMIT 10', (user_id, user_id))
    deals = cur.fetchall()
    conn.close()
    if not deals:
        await msg.answer('У вас пока нет сделок.', reply_markup=back_menu)
        return
    text = 'Ваши последние сделки:\n\n'
    for deal in deals:
        text += f'{deal[0]} | {deal[1]} {deal[2]} | {"✅" if deal[3] == "completed" else "⏳"}\n'
    await msg.answer(text, reply_markup=back_menu)

@dp.message_handler(lambda msg: msg.text == 'Реквизиты')
async def show_requisites(msg: types.Message):
    conn = sqlite3.connect('funpay.db')
    cur = conn.cursor()
    cur.execute('SELECT requisites FROM users WHERE user_id = ?', (msg.from_user.id,))
    result = cur.fetchone()
    conn.close()
    if result and result[0]:
        await msg.answer(f'Ваши реквизиты:\n\n{result[0]}', reply_markup=back_menu)
    else:
        await msg.answer('Реквизиты не заполнены. Используйте /set_requisites', reply_markup=back_menu)

@dp.message_handler(commands=['set_requisites'])
async def set_requisites(msg: types.Message):
    text = msg.text.replace('/set_requisites', '').strip()
    if not text:
        await msg.answer('Использование: /set_requisites Ваши реквизиты')
        return
    conn = sqlite3.connect('funpay.db')
    cur = conn.cursor()
    cur.execute('UPDATE users SET requisites = ? WHERE user_id = ?', (text, msg.from_user.id))
    conn.commit()
    conn.close()
    await msg.answer('Реквизиты сохранены!', reply_markup=back_menu)

@dp.message_handler(lambda msg: msg.text == 'Язык')
async def language(msg: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    for lang in ['English', 'Русский', 'Українська', '中文', 'Қазақша', '한국어', '日本語', 'Deutsch', 'العربية']:
        keyboard.add(KeyboardButton(lang))
    keyboard.add(KeyboardButton('Назад'))
    await msg.answer('Выберите язык:', reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text in ['English', 'Русский', 'Українська', '中文', 'Қазақша', '한국어', '日本語', 'Deutsch', 'العربية'])
async def set_language(msg: types.Message):
    conn = sqlite3.connect('funpay.db')
    cur = conn.cursor()
    lang_map = {'English': 'en', 'Русский': 'ru', 'Українська': 'uk', '中文': 'zh', 'Қазақша': 'kz', '한국어': 'ko', '日本語': 'ja', 'Deutsch': 'de', 'العربية': 'ar'}
    cur.execute('UPDATE users SET language = ? WHERE user_id = ?', (lang_map[msg.text], msg.from_user.id))
    conn.commit()
    conn.close()
    await msg.answer(f'Язык изменен на {msg.text}', reply_markup=back_menu)

@dp.message_handler(lambda msg: msg.text == 'Безопасно ли это?')
async def security(msg: types.Message):
    text = """
1️⃣ Сделка фиксируется внутри бота
2️⃣ Вторая сторона подключается только к конкретной сделке
3️⃣ Деньги и товар не смешиваются в одном шаге
4️⃣ Участники видят свои роли
5️⃣ Статус сделки отслеживается
6️⃣ Доступ к информации ограничен участниками
7️⃣ Всегда сверяйте номер сделки, сумму, валюту, описание и username

Главное правило: безопасной считается только та сделка, условия которой совпадают в карточке бота и у обеих сторон.
"""
    await msg.answer(text, reply_markup=back_menu)

@dp.message_handler(lambda msg: msg.text == 'Поддержка')
async def support(msg: types.Message):
    await msg.answer('👨‍💻 Свяжитесь с нами: @FunPaySupport\n\nМы отвечаем в течение 15 минут.', reply_markup=back_menu)

# ============ СОЗДАНИЕ СДЕЛКИ ============
@dp.message_handler(lambda msg: msg.text == 'Сохранить сделки')
async def create_deal_start(msg: types.Message, state: FSMContext):
    await msg.answer('Создание сделки\n\nВыберите вашу роль в этой сделке:', reply_markup=role_menu)
    await DealStates.choose_role.set()

@dp.message_handler(state=DealStates.choose_role)
async def choose_role(msg: types.Message, state: FSMContext):
    if msg.text == 'Отмена':
        await state.finish()
        await msg.answer('Создание сделки отменено.', reply_markup=main_menu)
        return
    if msg.text not in ['Покупатель', 'Продавец']:
        await msg.answer('Выберите роль: Покупатель или Продавец')
        return
    await state.update_data(role=msg.text)
    await msg.answer('Выберите метод оплаты:', reply_markup=currency_menu)
    await DealStates.choose_currency.set()

@dp.message_handler(state=DealStates.choose_currency)
async def choose_currency(msg: types.Message, state: FSMContext):
    if msg.text == 'Отмена':
        await state.finish()
        await msg.answer('Создание сделки отменено.', reply_markup=main_menu)
        return
    currency_map = {
        'На TON-кошелек': 'TON', 'Карта (RUB)': 'RUB', 'Карта (USD)': 'USD',
        'Карта (UAH)': 'UAH', 'Звезды': 'Stars', 'USDT-кошелек': 'USDT',
        'Карта (KGS)': 'KGS', 'Карта (UZS)': 'UZS', 'Карта (BYN)': 'BYN', 'Карта (KZT)': 'KZT'
    }
    if msg.text not in currency_map:
        await msg.answer('Выберите метод оплаты из меню')
        return
    await state.update_data(currency=currency_map[msg.text])
    await msg.answer(f'Ваша роль: {await state.get_data()["role"]}\nМетод оплаты: {msg.text}\n\nВведите сумму в формате: 100', reply_markup=back_menu)
    await DealStates.enter_amount.set()

@dp.message_handler(state=DealStates.enter_amount)
async def enter_amount(msg: types.Message, state: FSMContext):
    try:
        amount = float(msg.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError
    except:
        await msg.answer('Введите корректную сумму (например: 100 или 50.5)')
        return
    await state.update_data(amount=amount)
    await msg.answer('Укажите ссылку на NFT-подарок или опишите, на что создается сделка.\n\nПример: https://t.me/nft/PlushPepe-1', reply_markup=back_menu)
    await DealStates.enter_description.set()

@dp.message_handler(state=DealStates.enter_description)
async def enter_description(msg: types.Message, state: FSMContext):
    if len(msg.text) < 5:
        await msg.answer('Описание слишком короткое (минимум 5 символов)')
        return
    await state.update_data(description=msg.text)
    data = await state.get_data()
    deal_id = generate_deal_id()
    user_id = msg.from_user.id
    created_at = datetime.now().isoformat()
    
    conn = sqlite3.connect('funpay.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO deals (deal_id, creator_id, creator_role, amount, currency, description, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (deal_id, user_id, data['role'], data['amount'], data['currency'], data['description'], 'created', created_at))
    conn.commit()
    conn.close()
    
    deal_link = f'https://t.me/FunOTC_Bot?start={deal_id.replace("#", "deal")}'
    text = f"""
✅ Сделка успешно создана!

ID сделки: {deal_id}
Ваша роль: {data['role']}
Сумма: {data['amount']} {data['currency']}
Товар: {data['description']}

📎 Ссылка для второй стороны:
{deal_link}
"""
    await msg.answer(text, reply_markup=main_menu)
    await state.finish()
    await add_log_and_send('deal_created', user_id=user_id, username=msg.from_user.username, deal_id=deal_id, 
                           action=f'Создана сделка на {data["amount"]} {data["currency"]}', details=data['description'][:50])

# ============ ПОДКЛЮЧЕНИЕ К СДЕЛКЕ ============
@dp.message_handler(lambda msg: msg.text and msg.text.startswith('/deal'))
async def join_deal(msg: types.Message):
    deal_id = '#716MZK' + msg.text.replace('/deal', '').strip()
    conn = sqlite3.connect('funpay.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM deals WHERE deal_id = ?', (deal_id,))
    deal = cur.fetchone()
    if not deal:
        await msg.answer('❌ Сделка не найдена.', reply_markup=main_menu)
        conn.close()
        return
    if deal[4] is not None:
        await msg.answer('❌ К этой сделке уже подключились.', reply_markup=main_menu)
        conn.close()
        return
    user_id = msg.from_user.id
    if user_id == deal[2]:
        await msg.answer('❌ Вы создали эту сделку. Ожидайте подключения второй стороны.', reply_markup=main_menu)
        conn.close()
        return
    participant_role = 'Продавец' if deal[3] == 'Покупатель' else 'Покупатель'
    cur.execute('UPDATE deals SET participant_id = ?, participant_role = ?, status = "active" WHERE deal_id = ?', (user_id, participant_role, deal_id))
    conn.commit()
    conn.close()
    
    text = f"""
✅ Вы подключились к сделке!

ID сделки: {deal_id}
Ваша роль: {participant_role}
Сумма: {deal[5]} {deal[6]}
Товар: {deal[7]}

⏳ Ожидайте подтверждения от второй стороны.
"""
    await msg.answer(text, reply_markup=main_menu)
    await add_log_and_send('deal_joined', user_id=user_id, username=msg.from_user.username, deal_id=deal_id,
                           action=f'Участник вступил в сделку', details=f'Сумма: {deal[5]} {deal[6]} | Роль: {participant_role}')

# ============ АДМИН-ПАНЕЛЬ ============
@dp.message_handler(commands=['admin'])
async def admin_panel(msg: types.Message):
    if not is_admin(msg.from_user.id):
        await msg.answer('⛔ Доступ запрещен.')
        return
    await msg.answer('🔐 Админ-панель FunPay\n\nВыберите действие:', reply_markup=admin_menu)

@dp.message_handler(lambda msg: msg.text == '📋 Все сделки' and is_admin(msg.from_user.id))
async def all_deals(msg: types.Message):
    conn = sqlite3.connect('funpay.db')
    cur = conn.cursor()
    cur.execute('SELECT deal_id, creator_id, participant_id, amount, currency, status, created_at FROM deals ORDER BY created_at DESC LIMIT 20')
    deals = cur.fetchall()
    conn.close()
    if not deals:
        await msg.answer('📭 Сделок нет.')
        return
    text = '📋 <b>Последние 20 сделок:</b>\n\n'
    for deal in deals:
        status_emoji = {'created': '🟡', 'active': '🟢', 'completed': '✅', 'disputed': '🔴'}.get(deal[5], '⚪')
        text += f'{status_emoji} {deal[0]} | {deal[3]} {deal[4]} | {deal[5]}\n   Создатель: {deal[1]} | Участник: {deal[2] or "❌"}\n   📅 {deal[6][:16]}\n\n'
    await msg.answer(text, parse_mode='HTML', reply_markup=admin_menu)

@dp.message_handler(lambda msg: msg.text == '📊 Статистика' and is_admin(msg.from_user.id))
async def stats(msg: types.Message):
    conn = sqlite3.connect('funpay.db')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM deals'); total_deals = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM deals WHERE status = "completed"'); completed_deals = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM deals WHERE status = "active"'); active_deals = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM users'); total_users = cur.fetchone()[0]
    cur.execute('SELECT SUM(amount) FROM deals WHERE currency = "Stars" AND status = "completed"'); total_stars = cur.fetchone()[0] or 0
    cur.execute('SELECT SUM(amount) FROM deals WHERE currency = "RUB" AND status = "completed"'); total_rub = cur.fetchone()[0] or 0
    conn.close()
    text = f"""
📊 <b>СТАТИСТИКА FUNPAY</b>

👥 Пользователей: {total_users}
📋 Всего сделок: {total_deals}
🟢 Активных: {active_deals}
✅ Завершено: {completed_deals}

💰 Оборот:
   ⭐ Stars: {total_stars:.0f}
   ₽ RUB: {total_rub:.2f}
"""
    await msg.answer(text, parse_mode='HTML', reply_markup=admin_menu)

@dp.message_handler(lambda msg: msg.text == '✅ Подтвердить оплату' and is_admin(msg.from_user.id))
async def confirm_payment_start(msg: types.Message):
    await msg.answer('Введите ID сделки для подтверждения оплаты:\n\nПример: #716MZK100', reply_markup=admin_menu)

@dp.message_handler(lambda msg: msg.text and msg.text.startswith('#') and is_admin(msg.from_user.id))
async def confirm_payment(msg: types.Message):
    deal_id = msg.text.strip()
    conn = sqlite3.connect('funpay.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM deals WHERE deal_id = ?', (deal_id,))
    deal = cur.fetchone()
    if not deal:
        await msg.answer('❌ Сделка не найдена.', reply_markup=admin_menu)
        conn.close()
        return
    if deal[8] != 'active':
        await msg.answer(f'⚠️ Сделка в статусе: {deal[8]}. Подтверждение оплаты невозможно.', reply_markup=admin_menu)
        conn.close()
        return
    cur.execute('UPDATE deals SET status = "paid" WHERE deal_id = ?', (deal_id,))
    conn.commit()
    conn.close()
    
    await bot.send_message(deal[2], f'✅ Оплата по сделке {deal_id} подтверждена!\n\nОжидайте передачи NFT от продавца.')
    if deal[4]:
        await bot.send_message(deal[4], f'✅ Покупатель успешно оплатил сделку {deal_id}.\n\n💳 Ваш баланс FunPay пополнен на: {deal[5]} {deal[6]}\nСредства зафиксированы системой.\n\n📤 Передайте NFT-подарок на @funpaybag и подтвердите передачу.')
    await msg.answer(f'✅ Оплата по сделке {deal_id} подтверждена.', reply_markup=admin_menu)

# ============ ПОДТВЕРЖДЕНИЕ ПЕРЕДАЧИ (ИСПРАВЛЕНО) ============
@dp.message_handler(lambda msg: msg.text == '✅ Подтвердить передачу' and is_admin(msg.from_user.id))
async def confirm_transfer_start(msg: types.Message):
    await msg.answer('Введите ID сделки для подтверждения передачи NFT:', reply_markup=admin_menu)

@dp.message_handler(lambda msg: msg.text and msg.text.startswith('#') and is_admin(msg.from_user.id))
async def confirm_transfer(msg: types.Message):
    deal_id = msg.text.strip()
    conn = sqlite3.connect('funpay.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM deals WHERE deal_id = ?', (deal_id,))
    deal = cur.fetchone()
    if not deal:
        await msg.answer('❌ Сделка не найдена.', reply_markup=admin_menu)
        conn.close()
        return
    if deal[8] != 'paid':
        await msg.answer(f'⚠️ Сделка в статусе: {deal[8]}. Подтверждение передачи невозможно.', reply_markup=admin_menu)
        conn.close()
        return
    
    cur.execute('UPDATE deals SET status = "completed", completed_at = ? WHERE deal_id = ?', (datetime.now().isoformat(), deal_id))
    conn.commit()
    conn.close()
    
    # Безопасно обновляем баланс
    if deal[4] and deal[5] and deal[6]:
        try:
            seller_id = deal[4]
            currency = deal[6].lower()
            amount = float(deal[5])
            update_balance(seller_id, currency, amount)
        except Exception as e:
            print(f'Ошибка обновления баланса: {e}')
    
    await bot.send_message(deal[2], f'✅ NFT-подарок по сделке {deal_id} передан на ваш кошелек!\n\nСпасибо за использование FunPay!')
    if deal[4]:
        await bot.send_message(deal[4], f'✅ Средства по сделке {deal_id} зачислены на ваш баланс!\nСумма: {deal[5]} {deal[6]}')
    
    await msg.answer(f'✅ Сделка {deal_id} завершена!', reply_markup=admin_menu)

# ============ НАЗАД ============
@dp.message_handler(lambda msg: msg.text == 'Вернуться в меню' or msg.text == 'Назад')
async def back_to_menu(msg: types.Message):
    await msg.answer('Главное меню:', reply_markup=main_menu)

@dp.message_handler(lambda msg: msg.text == '🔙 В главное меню' and is_admin(msg.from_user.id))
async def admin_back(msg: types.Message):
    await msg.answer('Главное меню:', reply_markup=main_menu)

# ============ ЗАПУСК ============
if __name__ == '__main__':
    print('🚀 Бот FunPay запущен...')
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
