import asyncio
import logging
import uuid
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from config import BOT_TOKEN, ADMIN_ID, DATABASE_PATH
from database import Database

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database(DATABASE_PATH)


class CreateDealFSM(StatesGroup):
    waiting_role = State()
    waiting_partner_id = State()
    waiting_amount = State()
    waiting_description = State()


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🤝 Создать сделку")],
            [KeyboardButton(text="📜 Мои сделки"), KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
    )


def get_deal_keyboard(deal: dict, user_id: int) -> InlineKeyboardMarkup:
    buttons = []
    status = deal["status"]
    seller_id = deal["seller_id"]
    buyer_id = deal["buyer_id"]
    deal_id = deal["deal_id"]

    if status == "CREATED":
        if user_id in (seller_id, buyer_id):
            buttons.append([InlineKeyboardButton(text="❌ Отменить сделку", callback_data=f"cancel_{deal_id}")])
            if user_id == buyer_id:
                buttons.append([InlineKeyboardButton(text="💳 Я оплатил", callback_data=f"pay_{deal_id}")])

    elif status == "WAITING_PAYMENT":
        if user_id == buyer_id:
            buttons.append([InlineKeyboardButton(text="💳 Подтвердить оплату", callback_data=f"pay_{deal_id}")])
        if user_id in (seller_id, buyer_id):
            buttons.append([InlineKeyboardButton(text="❌ Отменить сделку", callback_data=f"cancel_{deal_id}")])

    elif status == "PAID":
        if user_id == seller_id:
            buttons.append([InlineKeyboardButton(text="✅ Подтвердить получение и завершить", callback_data=f"complete_{deal_id}")])
        if user_id in (seller_id, buyer_id):
            buttons.append([InlineKeyboardButton(text="⚠️ Открыть спор", callback_data=f"dispute_{deal_id}")])

    elif status == "DISPUTE":
        if user_id == ADMIN_ID:
            buttons.append([
                InlineKeyboardButton(text="⚙️ Завершить (в пользу продавца)", callback_data=f"adm_comp_{deal_id}"),
                InlineKeyboardButton(text="⚙️ Отменить (возврат покупателю)", callback_data=f"adm_canc_{deal_id}")
            ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    db.register_user(message.from_user.id, message.from_user.username)
    logging.info(f"Пользователь {message.from_user.id} запустил бота.")
    await message.answer(
        "👋 Добро пожаловать в P2P Гарант-бот!\n\n"
        "Здесь вы можете безопасно проводить сделки между покупателем и продавцом.",
        reply_markup=get_main_keyboard(),
    )


@dp.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    await message.answer(
        "💡 *Инструкция по использованию:*\n\n"
        "1. Нажмите *Создать сделку* и выберите вашу роль (Продавец/Покупатель).\n"
        "2. Укажите Telegram ID второго участника, сумму и условие сделки.\n"
        "3. Передайте ID сделки партнеру, если необходимо.\n"
        "4. Покупатель переводит средства и жмет кнопку *Оплачено*.\n"
        "5. Продавец передает товар/услугу и подтверждает получение средств.\n"
        "6. При возникновении разногласий любая сторона может *Открыть спор* для вызова администратора.",
        parse_mode="Markdown",
    )


@dp.message(F.text == "🤝 Создать сделку")
async def start_deal_creation(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛍 Я Продавец", callback_data="role_seller"),
                InlineKeyboardButton(text="💰 Я Покупатель", callback_data="role_buyer"),
            ]
        ]
    )
    await state.set_state(CreateDealFSM.waiting_role)
    await message.answer("Выберите вашу роль в сделке:", reply_markup=keyboard)


@dp.callback_query(CreateDealFSM.waiting_role, F.data.startswith("role_"))
async def process_role(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split("_")[1]
    await state.update_data(role=role)
    await state.set_state(CreateDealFSM.waiting_partner_id)
    await callback.message.edit_text(
        "Введите numeric Telegram ID второго участника:\n"
        "_(Пользователь должен хотя бы раз запустить бота)_",
        parse_mode="Markdown",
    )
    await callback.answer()


@dp.message(CreateDealFSM.waiting_partner_id)
async def process_partner_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите корректный числовой Telegram ID.")
        return

    partner_id = int(message.text)
    if partner_id == message.from_user.id:
        await message.answer("Вы не можете указать свой собственный ID.")
        return

    await state.update_data(partner_id=partner_id)
    await state.set_state(CreateDealFSM.waiting_amount)
    await message.answer("Введите сумму сделки (число, например: 1500 или 50.5):")


@dp.message(CreateDealFSM.waiting_amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("Введите корректную положительную сумму.")
        return

    await state.update_data(amount=amount)
    await state.set_state(CreateDealFSM.waiting_description)
    await message.answer("Введите описание сделки (условия, товар или услуга):")


@dp.message(CreateDealFSM.waiting_description)
async def process_description(message: Message, state: FSMContext):
    description = message.text.strip()
    data = await state.get_data()
    state_role = data["role"]
    partner_id = data["partner_id"]
    amount = data["amount"]

    creator_id = message.from_user.id
    if state_role == "seller":
        seller_id = creator_id
        buyer_id = partner_id
    else:
        seller_id = partner_id
        buyer_id = creator_id

    deal_id = str(uuid.uuid4())[:8]
    db.create_deal(deal_id, creator_id, seller_id, buyer_id, amount, description)
    await state.clear()

    logging.info(f"Сделка {deal_id} создана пользователем {creator_id}.")

    text = (
        f"🤝 *Сделка #{deal_id} успешно создана!*\n\n"
        f"💰 *Сумма:* {amount}\n"
        f"📝 *Описание:* {description}\n"
        f"👤 *Продавец:* `{seller_id}`\n"
        f"👤 *Покупатель:* `{buyer_id}`\n"
        f"📌 *Статус:* CREATED (Ожидает действий)"
    )

    deal_data = db.get_deal(deal_id)
    await message.answer(text, parse_mode="Markdown", reply_markup=get_deal_keyboard(deal_data, creator_id))

    try:
        await bot.send_message(
            partner_id,
            f"🔔 Вы были указаны участником в новой сделке #{deal_id}!\n\n" + text,
            parse_mode="Markdown",
            reply_markup=get_deal_keyboard(deal_data, partner_id),
        )
    except Exception as e:
        logging.warning(f"Не удалось отправить уведомление партеру {partner_id}: {e}")


@dp.callback_query(F.data.startswith("pay_"))
async def process_pay(callback: CallbackQuery):
    deal_id = callback.data.split("_")[1]
    deal = db.get_deal(deal_id)
    user_id = callback.from_user.id

    if not deal:
        await callback.answer("Сделка не найдена.", show_alert=True)
        return

    if user_id != deal["buyer_id"]:
        await callback.answer("Только покупатель может подтвердить оплату.", show_alert=True)
        return

    if deal["status"] in ("PAID", "COMPLETED", "CANCELLED", "DISPUTE"):
        await callback.answer("Действие недоступно для текущего статуса.", show_alert=True)
        return

    db.update_deal_status(deal_id, "PAID")
    logging.info(f"Сделка {deal_id}: покупатель подтвердил оплату.")
    deal = db.get_deal(deal_id)

    text = (
        f"💳 *Покупатель подтвердил оплату по сделке #{deal_id}!*\n\n"
        f"💰 *Сумма:* {deal['amount']}\n"
        f"📝 *Описание:* {deal['description']}\n"
        f"📌 *Статус:* PAID (Оплачено, ожидается передача товара)"
    )

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_deal_keyboard(deal, user_id))
    await callback.answer("Оплата подтверждена!")

    try:
        await bot.send_message(
            deal["seller_id"],
            f"🔔 Покупатель оплатил сделку #{deal_id}. Проверьте получение средств и завершите сделку.",
            reply_markup=get_deal_keyboard(deal, deal["seller_id"]),
        )
    except Exception as e:
        logging.warning(f"Ошибка уведомления продавца: {e}")


@dp.callback_query(F.data.startswith("complete_"))
async def process_complete(callback: CallbackQuery):
    deal_id = callback.data.split("_")[1]
    deal = db.get_deal(deal_id)
    user_id = callback.from_user.id

    if not deal:
        await callback.answer("Сделка не найдена.", show_alert=True)
        return

    if user_id != deal["seller_id"]:
        await callback.answer("Только продавец может завершить сделку.", show_alert=True)
        return

    if deal["status"] != "PAID":
        await callback.answer("Завершить можно только оплаченную сделку.", show_alert=True)
        return

    db.update_deal_status(deal_id, "COMPLETED")
    logging.info(f"Сделка {deal_id} завершена.")
    deal = db.get_deal(deal_id)

    text = f"✅ *Сделка #{deal_id} успешно завершена!*\nСтатус: COMPLETED"
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer("Сделка completed!")

    try:
        await bot.send_message(deal["buyer_id"], f"✅ Продавец подтвердил выполнение условий. Сделка #{deal_id} закрыта!")
    except Exception as e:
        logging.warning(f"Ошибка уведомления покупателя: {e}")


@dp.callback_query(F.data.startswith("cancel_"))
async def process_cancel(callback: CallbackQuery):
    deal_id = callback.data.split("_")[1]
    deal = db.get_deal(deal_id)
    user_id = callback.from_user.id

    if not deal:
        await callback.answer("Сделка не найдена.", show_alert=True)
        return

    if user_id not in (deal["seller_id"], deal["buyer_id"]):
        await callback.answer("У вас нет прав на отмену этой сделки.", show_alert=True)
        return

    if deal["status"] in ("COMPLETED", "CANCELLED", "DISPUTE"):
        await callback.answer("Сделку нельзя отменить в текущем статусе.", show_alert=True)
        return

    db.update_deal_status(deal_id, "CANCELLED")
    logging.info(f"Сделка {deal_id} отменена пользователем {user_id}.")

    text = f"❌ *Сделка #{deal_id} отменена.*\nСтатус: CANCELLED"
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer("Сделка отменена.")

    other_id = deal["buyer_id"] if user_id == deal["seller_id"] else deal["seller_id"]
    try:
        await bot.send_message(other_id, f"❌ Вторая сторона отменила сделку #{deal_id}.")
    except Exception as e:
        logging.warning(f"Ошибка уведомления партнера: {e}")


@dp.callback_query(F.data.startswith("dispute_"))
async def process_dispute(callback: CallbackQuery):
    deal_id = callback.data.split("_")[1]
    deal = db.get_deal(deal_id)
    user_id = callback.from_user.id

    if not deal:
        await callback.answer("Сделка не найдена.", show_alert=True)
        return

    if user_id not in (deal["seller_id"], deal["buyer_id"]):
        await callback.answer("Вы не являетесь участником сделки.", show_alert=True)
        return

    if deal["status"] in ("COMPLETED", "CANCELLED", "DISPUTE"):
        await callback.answer("Спор невозможно открыть для этой сделки.", show_alert=True)
        return

    db.update_deal_status(deal_id, "DISPUTE")
    logging.info(f"Открыт спор по сделке {deal_id} пользователем {user_id}.")
    deal = db.get_deal(deal_id)

    text = f"⚠️ *По сделке #{deal_id} открыт спор!*\nОжидайте ответа администратора.\nСтатус: DISPUTE"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_deal_keyboard(deal, user_id))
    await callback.answer("Спор открыт. Уведомление отправлено администратору.")

    if ADMIN_ID != 0:
        admin_text = (
            f"🚨 *ОТКРЫТ СПОР!*\n\n"
            f"ID сделки: `{deal_id}`\n"
            f"Продавец: `{deal['seller_id']}`\n"
            f"Покупатель: `{deal['buyer_id']}`\n"
            f"Сумма: {deal['amount']}\n"
            f"Описание: {deal['description']}"
        )
        try:
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=get_deal_keyboard(deal, ADMIN_ID))
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение админу: {e}")


@dp.callback_query(F.data.startswith("adm_comp_"))
async def admin_complete(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    deal_id = callback.data.split("_")[2]
    db.update_deal_status(deal_id, "COMPLETED")
    logging.info(f"Администратор закрыл спор #{deal_id} в пользу продавца.")

    await callback.message.edit_text(f"⚙️ Администратор завершил сделку #{deal_id} (COMPLETED).")
    await callback.answer("Сделка завершена.")


@dp.callback_query(F.data.startswith("adm_canc_"))
async def admin_cancel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    deal_id = callback.data.split("_")[2]
    db.update_deal_status(deal_id, "CANCELLED")
    logging.info(f"Администратор отменил сделку #{deal_id}.")

    await callback.message.edit_text(f"⚙️ Администратор отменил сделку #{deal_id} (CANCELLED).")
    await callback.answer("Сделка отменена.")


@dp.message(F.text == "📜 Мои сделки")
async def show_my_deals(message: Message):
    user_deals = db.get_user_deals(message.from_user.id)
    if not user_deals:
        await message.answer("У вас пока нет активных или завершенных сделок.")
        return

    response = "*История ваших сделок:*\n\n"
    for deal in user_deals[:10]:
        role = "Продавец" if deal["seller_id"] == message.from_user.id else "Покупатель"
        response += (
            f"🔹 *ID:* `{deal['deal_id']}` | Роль: {role}\n"
            f"💰 Сумма: {deal['amount']} | Статус: `{deal['status']}`\n"
            f"📝 {deal['description']}\n\n"
        )
    await message.answer(response, parse_mode="Markdown")


@dp.message(Command("admin_deals"))
async def admin_deals(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    deals = db.get_all_deals()
    if not deals:
        await message.answer("Сделок в системе не найдено.")
        return

    response = "🛠 *Последние сделки в системе:*\n\n"
    for deal in deals[:15]:
        response += (
            f"ID: `{deal['deal_id']}` | Статус: `{deal['status']}`\n"
            f"Сумма: {deal['amount']} | Продавец: `{deal['seller_id']}` | Покупатель: `{deal['buyer_id']}`\n\n"
        )
    await message.answer(response, parse_mode="Markdown")


async def main():
    if not BOT_TOKEN:
        logging.error("Не задан BOT_TOKEN!")
        return
    logging.info("Запуск бота P2P Гаранта...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
