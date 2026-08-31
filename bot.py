from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import json
import os
import random

# ========== НАЛАШТУВАННЯ ==========
BOT_TOKEN = "8819298037:AAEnCIZ5V4IdC3SjUf9j6MSvSwYRZ_Tlf94"  # ЗАМІНИТИ НА НОВИЙ ТОКЕН!
WEBAPP_URL = "https://lolz-6.onrender.com"

# ========== ДАНІ КОРИСТУВАЧІВ (зберігаються у файлі) ==========
DATA_FILE = "users.json"

def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=2)

users = load_users()

# ========== КЕЙСИ ==========
CASES = [
    {"id": 1, "name": "Стандартний", "price": 50, "items": [
        {"name": "🎁 Звичайний", "rarity": "common"},
        {"name": "🎀 Рідкісний", "rarity": "rare"},
        {"name": "💎 Епічний", "rarity": "epic"},
        {"name": "👑 Легендарний", "rarity": "legendary"}
    ]},
    {"id": 2, "name": "Преміум", "price": 150, "items": [
        {"name": "🏆 Золотий", "rarity": "epic"},
        {"name": "⭐ Платиновий", "rarity": "legendary"},
        {"name": "🔥 Міфічний", "rarity": "legendary"},
        {"name": "🌌 Космічний", "rarity": "legendary"}
    ]},
    {"id": 3, "name": "Безкоштовний", "price": 0, "items": [
        {"name": "🪙 Монетка", "rarity": "common"},
        {"name": "🔮 Наклейка", "rarity": "common"},
        {"name": "😎 Смайлик", "rarity": "rare"}
    ]}
]

PROMOCODES = {
    "GIFT2024": {"stars": 100, "uses": 10},
    "FREEBOX": {"case_id": 3, "uses": 5},
    "STAR500": {"stars": 500, "uses": 3}
}

# ========== КОМАНДИ БОТА ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Реєстрація нового користувача
    if user_id not in users:
        users[user_id] = {"stars": 300, "inventory": [], "promos_used": []}
        save_users(users)
    
    keyboard = [[InlineKeyboardButton("🎮 Відкрити Gifts Battle", web_app={"url": WEBAPP_URL})]]
    await update.message.reply_text(
        "🎁 Ласкаво просимо до Gifts Battle!\n\n"
        f"⭐️ Баланс: {users[user_id]['stars']} зірок\n"
        "🎒 Інвентар: " + (", ".join([i["name"] for i in users[user_id]["inventory"]]) if users[user_id]["inventory"] else "порожній") + "\n\n"
        "👇 Натисни кнопку, щоб відкрити гру:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in users:
        users[user_id] = {"stars": 300, "inventory": [], "promos_used": []}
        save_users(users)
    await update.message.reply_text(f"⭐️ Ваш баланс: {users[user_id]['stars']} зірок")

async def inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in users:
        users[user_id] = {"stars": 300, "inventory": [], "promos_used": []}
        save_users(users)
    
    inv = users[user_id]["inventory"]
    if inv:
        text = "🎒 Ваш інвентар:\n" + "\n".join([f"• {i['name']}" for i in inv])
    else:
        text = "🎒 Інвентар порожній"
    await update.message.reply_text(text)

async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in users:
        users[user_id] = {"stars": 300, "inventory": [], "promos_used": []}
        save_users(users)
    
    args = context.args
    if not args:
        await update.message.reply_text("❌ Введіть промокод: /promo КОД")
        return
    
    code = args[0].upper()
    if code not in PROMOCODES:
        await update.message.reply_text("❌ Невірний промокод")
        return
    
    promo_data = PROMOCODES[code]
    if promo_data["uses"] <= 0:
        await update.message.reply_text("❌ Промокод вже використано")
        return
    
    if code in users[user_id]["promos_used"]:
        await update.message.reply_text("❌ Ви вже використовували цей промокод")
        return
    
    # Активація промокоду
    promo_data["uses"] -= 1
    users[user_id]["promos_used"].append(code)
    
    if "stars" in promo_data:
        users[user_id]["stars"] += promo_data["stars"]
        await update.message.reply_text(f"✅ Отримано +{promo_data['stars']}⭐️!")
    elif "case_id" in promo_data:
        case = next(c for c in CASES if c["id"] == promo_data["case_id"])
        item = random.choice(case["items"])
        users[user_id]["inventory"].append(item)
        await update.message.reply_text(f"🎉 Ви відкрили кейс і отримали: {item['name']}!")
    
    save_users(users)
    await update.message.reply_text(f"⭐️ Новий баланс: {users[user_id]['stars']} зірок")

async def webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = json.loads(update.message.web_app_data.data)
    user_id = str(update.effective_user.id)
    
    if user_id not in users:
        users[user_id] = {"stars": 300, "inventory": [], "promos_used": []}
    
    action = data.get("action")
    
    if action == "open_case":
        case_id = data["case_id"]
        case = next(c for c in CASES if c["id"] == case_id)
        
        if case["price"] > 0 and users[user_id]["stars"] < case["price"]:
            await update.message.reply_text("❌ Недостатньо зірок!")
            return
        
        users[user_id]["stars"] -= case["price"]
        item = random.choice(case["items"])
        users[user_id]["inventory"].append(item)
        save_users(users)
        
        await update.message.reply_text(
            f"🎉 Ви відкрили {case['name']} кейс!\n"
            f"Отримали: {item['name']}\n"
            f"⭐️ Залишок: {users[user_id]['stars']}"
        )

# ========== ЗАПУСК БОТА ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("inventory", inventory))
    app.add_handler(CommandHandler("promo", promo))
    app.add_handler(CommandHandler("webapp_data", webapp_data))
    
    print("🤖 Бот запущено! Натисни /start")
    app.run_polling()

if __name__ == "__main__":
    main()
