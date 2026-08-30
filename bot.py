from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8819298037:AAH4UoKpbnESiRFNxBLT6w6aYEfC8moFeSo"  # ⚠️ ЗАМІНИТИ НА НОВИЙ ПІСЛЯ /revoke
WEBAPP_URL = "https://lolz-6.onrender.com"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎮 Відкрити Gifts Battle", web_app={"url": WEBAPP_URL})]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎁 Ласкаво просимо до Gifts Battle!\n\n"
        "Отримай 300⭐️ бонусом при старті!\n"
        "Відкривай кейси, збирай подарунки та вигравай!\n\n"
        "👇 Натисни кнопку нижче, щоб почати:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 Як грати:\n"
        "1. Відкрий Mini App\n"
        "2. Отримай 300⭐️ бонусом\n"
        "3. Обирай кейс і відкривай\n"
        "4. Використовуй промокоди: GIFT2024, FREEBOX, STAR500\n"
        "5. Збирай унікальні подарунки в інвентар!"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    print("🤖 Бот запущено! Натисни /start")
    app.run_polling()

if __name__ == "__main__":
    main()
