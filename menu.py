from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards.main_menu import main_menu_keyboard
from database.db import Database

router = Router(name="menu")


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database) -> None:
    await db.get_or_create_user(message.chat.id)
    await message.answer(
        "Привіт! Це бот моніторингу NFT-подарунків на MRKT.\n\n"
        "Обери розділ у меню нижче.",
        reply_markup=main_menu_keyboard(),
    )
