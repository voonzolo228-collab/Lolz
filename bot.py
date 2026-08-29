import asyncio
import hashlib
import hmac
import json
import logging
import time
from urllib.parse import parse_qs
import aiohttp
import aiosqlite
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
import uvicorn

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ==================== НАЛАШТУВАННЯ ====================
BOT_TOKEN = "ТВІЙ_TELEGRAM_BOT_TOKEN"
LOLZ_API_TOKEN = "ТВІЙ_LOLZ_MARKET_API_TOKEN"
LOLZ_USER_ID = 1234567  # ТВІЙ USER ID НА LOLZTEAM
ADMIN_ID = 99999999     # TELEGRAM ID АДМІНІСТРАТОРА

FEE_PERCENT = 3.0       # Комісія сервісу (3%)
DEAL_TIMEOUT = 3600     # Таймаут на оплату в секундах (1 година)
MINI_APP_URL = "https://your-domain.com/app"  # Посилання HTTPS

DB_PATH = "escrow_production.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

# ==================== ВАЛІДАЦІЯ TELEGRAM WEBAPP ====================
def verify_webapp_data(init_data: str, bot_token: str) -> dict | None:
    """Перевіряє справжність даних із Telegram Mini App за допомогою HMAC-SHA256."""
    try:
        parsed_data = parse_qs(init_data)
        hash_hex = parsed_data.get('hash', [None])[0]
        if not hash_hex:
            return None

        data_check_string = "\n".join(
            f"{k}={v[0]}" for k, v in sorted(parsed_data.items()) if k != 'hash'
        )

        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if calculated_hash == hash_hex:
            user_json = parsed_data.get('user', [None])[0]
            return json.loads(user_json) if user_json else {}
        return None
    except Exception as e:
        logging.error(f"InitData verification error: {e}")
        return None

# ==================== БАЗА ДАНИХ (SQLite) ====================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблиця угод
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                id TEXT PRIMARY KEY,
                buyer_id INTEGER,
                seller_id INTEGER,
                amount REAL,
                fee REAL,
                status TEXT,
                created_at INTEGER
            )
        """)
        # Таблиця оброблених транзакцій (захист від double-spend)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS processed_payments (
                payment_id TEXT PRIMARY KEY,
                deal_id TEXT
            )
        """)
        # Профілі користувачів (статистика)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                successful_deals INTEGER DEFAULT 0,
                disputed_deals INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def update_user_stats(user_id: int, success: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        if success:
            await db.execute("UPDATE users SET successful_deals = successful_deals + 1 WHERE user_id = ?", (user_id,))
        else:
            await db.execute("UPDATE users SET disputed_deals = disputed_deals + 1 WHERE user_id = ?", (user_id,))
        await db.commit()

# ==================== LOLZTEAM API ====================
class LolzAPI:
    @staticmethod
    async def check_payment(comment: str, expected_amount: float) -> tuple[bool, str | None]:
        url = f"https://api.lzt.market/user/{LOLZ_USER_ID}/payments"
        headers = {"Authorization": f"Bearer {LOLZ_API_TOKEN}"}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        payments = data.get("payments", {})
                        for p_id, p in payments.items():
                            if p.get("type") == "transfer" and comment in str(p.get("data", {}).get("comment", "")):
                                if float(p.get("incoming_sum", 0)) >= expected_amount:
                                    return True, str(p_id)
            except Exception as e:
                logging.error(f"Lolz Check Error: {e}")
        return False, None

    @staticmethod
    async def transfer_money(receiver_id: int, amount: float, comment: str) -> bool:
        url = "https://api.lzt.market/user/transfer"
        headers = {"Authorization": f"Bearer {LOLZ_API_TOKEN}"}
        payload = {
            "user_id": receiver_id,
            "currency": "rub",
            "amount": amount,
            "comment": comment
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, data=payload) as resp:
                    res = await resp.json()
                    return "success" in res or resp.status == 200
            except Exception as e:
                logging.error(f"Lolz Transfer Error: {e}")
                return False

# ==================== ФОНОВІ ЗАДАЧІ (Таймаути) ====================
async def auto_cancel_expired_deals():
    """Скасовує угоди, якщо їх не оплатили за DEAL_TIMEOUT."""
    while True:
        try:
            now = int(time.time())
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT id, buyer_id FROM deals WHERE status = 'WAITING_PAYMENT' AND (? - created_at) > ?",
                    (now, DEAL_TIMEOUT)
                ) as cursor:
                    expired = await cursor.fetchall()

                for deal_id, buyer_id in expired:
                    await db.execute("UPDATE deals SET status = 'EXPIRED' WHERE id = ?", (deal_id,))
                    await db.commit()
                    try:
                        await bot.send_message(buyer_id, f"⏳ Угоду `{deal_id}` скасовано через закінчення часу на оплату.")
                    except Exception:
                        pass
        except Exception as e:
            logging.error(f"Auto Cancel Task Error: {e}")
        await asyncio.sleep(60)

# ==================== БОТ: ХЕНДЛЕРИ ====================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤝 Нова угода (Mini App)", web_app=WebAppInfo(url=MINI_APP_URL))],
        [InlineKeyboardButton(text="👤 Профіль", callback_data="my_profile")]
    ])
    await message.answer(
        "👋 **P2P Escrow Bot (Lolzteam)**\n\n"
        f"• Авто-перевірка платежів\n• Авто-виплати продавцю\n• Комісія сервісу: `{FEE_PERCENT}%`\n"
        "Оформіть угоду через Mini App нижче.",
        reply_markup=kb, parse_mode="Markdown"
    )

@dp.callback_query(F.data == "my_profile")
async def show_profile(call: types.CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT successful_deals, disputed_deals FROM users WHERE user_id = ?", (call.from_user.id,)) as cursor:
            row = await cursor.fetchone()
    
    succ = row[0] if row else 0
    disp = row[1] if row else 0
    await call.message.answer(
        f"👤 **Ваш профіль:**\n\n"
        f"✅ Успішних угод: `{succ}`\n"
        f"⚠️ Суперечок: `{disp}`",
        parse_mode="Markdown"
    )
    await call.answer()

@dp.callback_query(F.data.startswith("check_"))
async def check_payment_handler(call: types.CallbackQuery):
    deal_id = call.data.replace("check_", "")
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT buyer_id, seller_id, amount, status FROM deals WHERE id = ?", (deal_id,)) as cursor:
            deal = await cursor.fetchone()

    if not deal:
        await call.answer("Угоду не знайдено.", show_alert=True)
        return

    buyer_id, seller_id, amount, status = deal
    if status != "WAITING_PAYMENT":
        await call.answer("Угода в іншому статусі або вже оплачена.", show_alert=True)
        return

    is_paid, payment_id = await LolzAPI.check_payment(comment=deal_id, expected_amount=amount)
    
    if is_paid and payment_id:
        async with aiosqlite.connect(DB_PATH) as db:
            # Захист від повторної зарахованої транзакції
            async with db.execute("SELECT deal_id FROM processed_payments WHERE payment_id = ?", (payment_id,)) as cur:
                if await cur.fetchone():
                    await call.answer("Цей платіж вже зараховано в іншій угоді!", show_alert=True)
                    return
            
            await db.execute("INSERT INTO processed_payments (payment_id, deal_id) VALUES (?, ?)", (payment_id, deal_id))
            await db.execute("UPDATE deals SET status = 'PAID' WHERE id = ?", (deal_id,))
            await db.commit()

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Підтвердити виконання", callback_data=f"confirm_{deal_id}")],
            [InlineKeyboardButton(text="🚨 Відкрити спір (Арбітраж)", callback_data=f"dispute_{deal_id}")]
        ])

        await call.message.edit_text(
            f"🎉 **Оплата за угодою #{deal_id} підтверджена!**\n\n"
            f"Продавець передає товар/послугу.\n"
            f"Після перевірки Покупець підтверджує угоду або відкриває спір.",
            parse_mode="Markdown", reply_markup=kb
        )
        await bot.send_message(seller_id, f"💰 Покупець оплатив угоду `{deal_id}`. Можна передавати товар!")
    else:
        await call.answer("Оплату не знайдено. Перевірте коментар і спробуйте знову.", show_alert=True)

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_deal_handler(call: types.CallbackQuery):
    deal_id = call.data.replace("confirm_", "")

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT buyer_id, seller_id, amount, fee, status FROM deals WHERE id = ?", (deal_id,)) as cursor:
            deal = await cursor.fetchone()

    if not deal or call.from_user.id != deal[0]:
        await call.answer("Тільки покупець може підтвердити виконання!", show_alert=True)
        return

    buyer_id, seller_id, amount, fee, status = deal
    if status != "PAID":
        await call.answer("Угода не в статусі оплати.", show_alert=True)
        return

    payout_amount = amount - fee
    payout_success = await LolzAPI.transfer_money(receiver_id=seller_id, amount=payout_amount, comment=f"Payout for {deal_id}")

    async with aiosqlite.connect(DB_PATH) as db:
        new_status = "COMPLETED" if payout_success else "PAYOUT_FAILED"
        await db.execute("UPDATE deals SET status = ? WHERE id = ?", (new_status, deal_id))
        await db.commit()

    if payout_success:
        await update_user_stats(buyer_id, True)
        await update_user_stats(seller_id, True)
        await call.message.edit_text(f"🏁 **Угоду #{deal_id} успішно завершено!**\nПродавцю виплачено `{payout_amount}` ₽ (з урахуванням комісії).")
        await bot.send_message(seller_id, f"✅ Покупець підтвердив угоду `{deal_id}`. `{payout_amount}` ₽ зараховано на ваш Lolzteam!")
    else:
        await call.message.edit_text(f"⚠️ **Угоду підтверджено, але сталася помилка авто-виплати.**\nЗверніться до підтримки.")

# ==================== СИСТЕМА АРБІТРАЖУ ====================
@dp.callback_query(F.data.startswith("dispute_"))
async def open_dispute_handler(call: types.CallbackQuery):
    deal_id = call.data.replace("dispute_", "")
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT buyer_id, seller_id, amount, status FROM deals WHERE id = ?", (deal_id,)) as cursor:
            deal = await cursor.fetchone()

    if not deal or call.from_user.id not in (deal[0], deal[1]):
        await call.answer("Ви не є учасником цієї угоди.", show_alert=True)
        return

    buyer_id, seller_id, amount, status = deal
    if status != "PAID":
        await call.answer("Спір можна відкрити лише для оплачених угод.", show_alert=True)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE deals SET status = 'DISPUTE' WHERE id = ?", (deal_id,))
        await db.commit()

    await update_user_stats(buyer_id, False)
    await update_user_stats(seller_id, False)

    # Сповіщення адміну
    adm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Манібек покупцю", callback_data=f"adm_mb_{deal_id}")],
        [InlineKeyboardButton(text="💰 Виплата продавцю", callback_data=f"adm_pay_{deal_id}")]
    ])
    
    await bot.send_message(
        ADMIN_ID,
        f"🚨 **ОГОЛОШЕНО АРБІТРАЖ!**\nУгода: `{deal_id}`\nСума: `{amount}` ₽\n"
        f"Покупець: `{buyer_id}` | Продавець: `{seller_id}`",
        reply_markup=adm_kb, parse_mode="Markdown"
    )

    await call.message.edit_text(f"⚠️ **Угоду #{deal_id} переведено в арбітраж.**\nАдміністратор вивчить ситуацію та винесе рішення.")
    other_party = seller_id if call.from_user.id == buyer_id else buyer_id
    await bot.send_message(other_party, f"🚨 Інша сторона відкрила спір щодо угоди `{deal_id}`. Очікуйте рішення адміна.")

@dp.callback_query(F.data.startswith("adm_"))
async def admin_resolve_dispute(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Недостатньо прав!", show_alert=True)
        return

    action, deal_id = call.data.replace("adm_", "").split("_", 1)
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT buyer_id, seller_id, amount, fee, status FROM deals WHERE id = ?", (deal_id,)) as cursor:
            deal = await cursor.fetchone()

    if not deal or deal[4] != "DISPUTE":
        await call.answer("Угоду не знайдено або спір уже вирішено.", show_alert=True)
        return

    buyer_id, seller_id, amount, fee, _ = deal
    
    if action == "mb":  # Манібек покупцю
        success = await LolzAPI.transfer_money(buyer_id, amount, f"Refund for {deal_id}")
        target_name, target_id = "Покупцю", buyer_id
    else:  # Виплата продавцю
        payout = amount - fee
        success = await LolzAPI.transfer_money(seller_id, payout, f"Dispute payout for {deal_id}")
        target_name, target_id = "Продавцю", seller_id

    if success:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE deals SET status = 'RESOLVED' WHERE id = ?", (deal_id,))
            await db.commit()

        await call.message.edit_text(f"⚖️ **Арбітраж розпущено!**\nКошти переведено: {target_name} (`{target_id}`).")
        await bot.send_message(buyer_id, f"⚖️ Арбітраж за угодою `{deal_id}` вирішено на користь {target_name}.")
        await bot.send_message(seller_id, f"⚖️ Арбітраж за угодою `{deal_id}` вирішено на користь {target_name}.")
    else:
        await call.answer("Помилка виконання виплати через Lolz API!", show_alert=True)

# ==================== FASTAPI (MINI APP API) ====================
@app.post("/api/create_deal")
async def api_create_deal(request: Request):
    body = await request.json()
    init_data = body.get("initData")
    user = verify_webapp_data(init_data, BOT_TOKEN)
    
    if not user:
        raise HTTPException(status_code=403, detail="Invalid Telegram InitData signature")

    buyer_id = user["id"]
    seller_id = int(body["seller_id"])
    amount = float(body["amount"])
    
    if amount <= 0 or buyer_id == seller_id:
        raise HTTPException(status_code=400, detail="Invalid deal parameters")

    fee = round(amount * (FEE_PERCENT / 100.0), 2)
    deal_id = f"DEAL-{buyer_id}-{seller_id}-{int(time.time())}"
    created_at = int(time.time())

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO deals (id, buyer_id, seller_id, amount, fee, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (deal_id, buyer_id, seller_id, amount, fee, "WAITING_PAYMENT", created_at)
        )
        await db.commit()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Перевірити оплату", callback_data=f"check_{deal_id}")]
    ])

    pay_text = (
        f"✅ **Угоду #{deal_id} створено!**\n\n"
        f"💰 Сума: `{amount}` ₽ (Комісія: `{fee}` ₽)\n"
        f"👤 Продавець ID: `{seller_id}`\n\n"
        f"📌 **Реквізити для оплати:**\n"
        f"1. Перерахуйте `{amount}` ₽ на Lolzteam (ID: `{LOLZ_USER_ID}`)\n"
        f"2. Коментар до переказу: `{deal_id}`\n"
        f"3. Натисніть «Перевірити оплату» нижче."
    )
    
    await bot.send_message(buyer_id, pay_text, parse_mode="Markdown", reply_markup=kb)
    try:
        await bot.send_message(seller_id, f"🔔 Вас додано як Продавця в угоду `{deal_id}` на суму `{amount}` ₽.")
    except Exception:
        pass

    return {"status": "ok", "deal_id": deal_id}

@app.get("/app", response_class=HTMLResponse)
async def serve_miniapp():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>P2P Escrow</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { font-family: -apple-system, sans-serif; background: var(--tg-theme-bg-color, #17212b); color: var(--tg-theme-text-color, #fff); padding: 20px; }
            .form-group { margin-bottom: 16px; }
            label { display: block; margin-bottom: 6px; font-size: 14px; opacity: 0.8; }
            input { width: 100%; padding: 12px; box-sizing: border-box; border-radius: 10px; border: 1px solid #444; background: var(--tg-theme-secondary-bg-color, #232e3c); color: #fff; font-size: 16px; }
            button { width: 100%; padding: 14px; background: var(--tg-theme-button-color, #2481cc); color: #fff; border: none; border-radius: 10px; font-weight: bold; font-size: 16px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h2>🤝 Нова P2P Угода</h2>
        <div class="form-group">
            <label>Сума угоди (₽):</label>
            <input type="number" id="amount" placeholder="1000">
        </div>
        <div class="form-group">
            <label>Telegram ID продавця:</label>
            <input type="number" id="seller_id" placeholder="123456789">
        </div>
        <button onclick="submitDeal()">Створити угоду</button>

        <script>
            const tg = window.Telegram.WebApp;
            tg.expand();

            async function submitDeal() {
                const amount = document.getElementById('amount').value;
                const sellerId = document.getElementById('seller_id').value;

                if (!amount || !sellerId || amount <= 0) {
                    tg.showAlert("Вкажіть коректні дані!");
                    return;
                }

                const response = await fetch('/api/create_deal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        initData: tg.initData,
                        amount: parseFloat(amount),
                        seller_id: parseInt(sellerId)
                    })
                });

                if (response.ok) {
                    tg.close();
                } else {
                    const err = await response.json();
                    tg.showAlert("Помилка: " + (err.detail || "Невідома помилка"));
                }
            }
        </script>
    </body>
    </html>
    """)

# ==================== ЗАПУСК ====================
async def main():
    await init_db()
    asyncio.create_task(dp.start_polling(bot))
    asyncio.create_task(auto_cancel_expired_deals())
    
    config = uvicorn.Config(app=app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
