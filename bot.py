from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = '8698578814:AAEavw5BZ7nj6czWH5Dq6g22r4WGfvzRHHo'
bot = Bot(token=API_TOKEN)

@bot.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer('✅ Бот работает!')

print('🚀 Бот запущен...')
bot.polling()
