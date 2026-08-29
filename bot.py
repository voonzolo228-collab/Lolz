import asyncio
import logging
import os
import uuid
from aiohttp import web

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

import database as db_module

# ==================== ВАШІ ДАНІ ====================
TOKEN = "8804498885:AAETe-rVJMfs4eL3dlqrArTLPrJ-cpNXfJ8"
BOT_USERNAME = "LolzDealsBot"
ADMIN_IDS = [8557408726]
RENDER_URL = "https://lolz-4.onrender.com"
# ===================================================

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# --- СТАНИ FSM ---
class DealForm(StatesGroup):
    category = State()
    warning_confirmed = State()
    gift_link = State()
    requisites = State()
    amount_stars = State()
    description = State()

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

def get_categories_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Telegram Gifts", callback_data="cat_Telegram Gifts")],
        [InlineKeyboardButton(text="2️⃣ Юзернейм", callback_data="cat_Юзернейм")],
        [InlineKeyboardButton(text="3️⃣ Канал", callback_data="cat_Канал")],
        [InlineKeyboardButton(text="4️⃣ Услуга", callback_data="cat_Услуга")],
        [InlineKeyboardButton(text="5️⃣ Аккаунт", callback_data="cat_Аккаунт")],
        [InlineKeyboardButton(text="🅿️ Назад", callback_data="to_main_menu")],
    ])

def get_warning_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☑️ Я ознакомился", callback_data="confirm_warning")]
    ])

def get_requisites_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Telegram", callback_data="req_Telegram")],
        [InlineKeyboardButton(text="➕ Добавить другие реквизиты", callback_data="req_Другие реквизиты")],
        [InlineKeyboardButton(text="🅿️ Назад", callback_data="to_main_menu")],
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

# --- АДМІН-ПАНЕЛЬ (/eter) ---
@router.message(Command("eter"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("⚡️ **Панель администратора**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "admin_add_balance")
async def admin_add_balance_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AdminStates.waiting_for_user_id_balance)
    await callback.message.edit_text("👤 Введите **ID пользователя**:")

@router.message(AdminStates.waiting_for_user_id_balance)
async def process_admin_user_balance(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Введите числовой ID.")
        return
    await state.update_data(target_user_id=int(message.text))
    await state.set_state(AdminStates.waiting_for_amount_balance)
    await message.answer("💰 Введите **количество STARS**:")

@router.message(AdminStates.waiting_for_amount_balance)
async def process_admin_amount_balance(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Введите число.")
        return
    data = await state.get_data()
    user_id = data['target_user_id']
    amount = int(message.text)
    await state.clear()

    async with db_module.aiosqlite.connect(db_module.DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

    await message.answer(f"✅ Пользователю `{user_id}` начислено **{amount} STARS**.", parse_mode="Markdown")

@router.callback_query(F.data == "admin_add_deals")
async def admin_add_deals_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AdminStates.waiting_for_user_id_deals)
    await callback.message.edit_text("👤 Введите **ID пользователя**:")

@router.message(AdminStates.waiting_for_user_id_deals)
async def process_admin_user_deals(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Введите числовой ID.")
        return
    await state.update_data(target_user_id=int(message.text))
    await state.set_state(AdminStates.waiting_for_amount_deals)
    await message.answer("📈 Введите **количество сделок**:")

@router.message(AdminStates.waiting_for_amount_deals)
async def process_admin_amount_deals(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Введите число.")
        return
    data = await state.get_data()
    user_id = data['target_user_id']
    amount = int(message.text)
    await state.clear()

    async with db_module.aiosqlite.connect(db_module.DB_NAME) as db:
        await db.execute("UPDATE users SET deals_count = deals_count + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

    await message.answer(f"✅ Пользователю `{user_id}` добавлено **{amount} сделок**.", parse_mode="Markdown")

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
                f"💸 **Оплата сделки #{deal_id}**\n\n"
                f"Вы перешли в защищённый чат сделки. Пожалуйста, проверьте данные перед проведением платежа:\n\n"
                f"┌ **Категория:** {deal['category']}\n"
                f"├ **Товар:** {deal['gift_link']}\n"
                f"├ **Описание:** {deal['description']}\n"
                f"└ **Продавец:** @{deal['seller_username']}\n\n"
                f"Метод оплаты: 💳 {deal['requisites']}\n"
                f"**Сумма к оплате:** **{deal['amount_stars']} STARS**"
            )
            pay_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay_{deal_id}")],
                [InlineKeyboardButton(text="🅿️ Отмена", callback_data="to_main_menu")]
            ])
            await message.answer(buyer_text, reply_markup=pay_kb, parse_mode="Markdown", disable_web_page_preview=True)
            return

    if args and args.startswith("ref_"):
        ref_id = args.replace("ref_", "")
        if ref_id.isdigit() and int(ref_id) != message.from_user.id:
            await db_module.add_referral(int(ref_id))

    text = (
        "Официальный Telegram-сервис автоматической безопасности сделок.\n"
        "Торгуйте игровыми ценностями напрямую и без риска.\n\n"
        "⚡️ **Автопилот** — автоматическое исполнение и холдирование средств\n"
        "⚡️ **Комиссия** — фиксированные 5%\n\n"
        "Выберите нужный раздел ниже:"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "to_main_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = "Официальный Telegram-сервис автоматической безопасности сделок."
    await callback.message.edit_text(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = await db_module.get_or_create_user(callback.from_user.id, callback.from_user.username)
    text = (
        f"💼 **Ваш профиль**\n\n"
        f"🆔 **ID:** `{user['user_id']}`\n"
        f"👤 **Пользователь:** @{user['username'] or 'не указан'}\n"
        f"⭐ **Рейтинг:** 5.0 / 5.0\n\n"
        f"📊 **Успешных сделок:** {user['deals_count']}\n"
        f"💰 **Баланс:** {user['balance']} STARS\n"
        f"🌐 **Язык интерфейса:** {user['lang']}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🅿️ Назад", callback_data="to_main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "referrals")
async def show_referrals(callback: CallbackQuery):
    user = await db_module.get_or_create_user(callback.from_user.id, callback.from_user.username)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{callback.from_user.id}"
    text = (
        f"🤝 **Партнёрская программа**\n\n"
        f"Приглашайте друзей и получайте 1% от суммы каждой их успешной сделки!\n\n"
        f"📊 **Приглашено пользователей:** {user['referrals']}\n"
        f"🔗 **Ваша реферальная ссылка:**\n`{ref_link}`"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📲 Поделиться ссылкой", switch_inline_query=ref_link)],
        [InlineKeyboardButton(text="🅿️ Назад", callback_data="to_main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "create_deal")
async def start_create_deal(callback: CallbackQuery, state: FSMContext):
    text = "Выберите тип товара для сделки:\n\n❗️ **Сделку создаёт продавец** ❗️"
    await callback.message.edit_text(text, reply_markup=get_categories_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("cat_"))
async def process_category(callback: CallbackQuery, state: FSMContext):
    selected_cat = callback.data.replace("cat_", "")
    await state.update_data(category=selected_cat)
    await state.set_state(DealForm.warning_confirmed)
    text = (
        "Внимание⚠️\n"
        "Если покупатель просит вас передать товар ему лично, это может быть признаком мошенничества. "
        "В случае передачи актива напрямую покупателю, а не через нашу систему безопасности сделок, "
        "вы рискуете потерять свой актив."
    )
    await callback.message.edit_text(text, reply_markup=get_warning_keyboard())

@router.callback_query(F.data == "confirm_warning", DealForm.warning_confirmed)
async def process_warning(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DealForm.gift_link)
    text = "🎯 **Ссылка на товар / подарок**\n\nУкажите ссылку на объект сделки:"
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")

@router.message(DealForm.gift_link)
async def process_gift_link(message: Message, state: FSMContext):
    await state.update_data(gift_link=message.text)
    await state.set_state(DealForm.requisites)
    text = "💳 **Реквизиты сделки**\n\nВыберите реквизиты для получения денег:"
    await message.answer(text, reply_markup=get_requisites_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("req_"), DealForm.requisites)
async def process_requisites(callback: CallbackQuery, state: FSMContext):
    req_type = callback.data.replace("req_", "")
    await state.update_data(requisites=req_type)
    await state.set_state(DealForm.amount_stars)
    text = "⭐️ **Сумма сделки**\n\nВведите сумму в звездах (STARS):"
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")

@router.message(DealForm.amount_stars)
async def process_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Введите корректное число.")
        return
    await state.update_data(amount_stars=int(message.text))
    await state.set_state(DealForm.description)
    text = "📝 **Описание сделки**\n\nНапишите описание:"
    await message.answer(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")

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
        f"🎉 **Сделка #{deal_uuid} успешно создана**\n\n"
        f"**Категория:** {data['category']}\n"
        f"**Товар:** {data['gift_link']}\n"
        f"**Описание:** {data['description']}\n"
        f"**Метод оплаты:** 💳 {data['requisites']}\n"
        f"**Итого к оплате:** {data['amount_stars']} STARS\n\n"
        f"🎯 **Ссылка для покупателя**\n`{deal_link}`"
    )
    final_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📲 Поделиться с покупателем", switch_inline_query=deal_link)],
        [InlineKeyboardButton(text="🅿️ Вернуться в меню", callback_data="to_main_menu")],
    ])
    await message.answer(summary_text, reply_markup=final_kb, parse_mode="Markdown", disable_web_page_preview=True)

@router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery):
    deal_id = callback.data.replace("pay_", "")
    deal = await db_module.get_deal(deal_id)

    if not deal:
        await callback.answer("⚠️ Сделка не найдена.", show_alert=True)
        return

    buyer = callback.from_user
    buyer_username = f"@{buyer.username}" if buyer.username else buyer.first_name

    await callback.message.edit_text(
        f"✅ **Оплата сделки #{deal_id} успешно проведена!**\n\n"
        f"Средства в размере **{deal['amount_stars']} STARS** заморожены системой гаранта.\n"
        f"Продавец уведомлён и обязался передать актив.",
        parse_mode="Markdown"
    )

    seller_text = (
        f"🔔 **Покупатель оплатил сделку #{deal_id}!**\n\n"
        f"💰 Средства (**{deal['amount_stars']} STARS**) зарезервированы.\n\n"
        f"📦 **Инструкция по передаче товара:**\n"
        f"Передайте актив (**{deal['gift_link']}**) строго на аккаунт покупателя: **{buyer_username}**"
    )
    seller_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Передал актив", callback_data=f"sent_{deal_id}")],
        [InlineKeyboardButton(text="🚨 Проблема со сделкой", url="https://t.me/telegram")]
    ])

    try:
        await bot.send_message(chat_id=deal['seller_id'], text=seller_text, reply_markup=seller_kb, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        logging.error(f"Ошибка отсылки продавцу: {e}")

# --- WEBHOOK ТА ПОРТ ---
async def on_startup(bot: Bot):
    await db_module.init_db()
    await bot.set_webhook(WEBHOOK_URL)

def main():
    logging.basicConfig(level=logging.INFO)
    dp.startup.register(on_startup)
    app = web.Application()
    
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    
    port = int(os.getenv("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
