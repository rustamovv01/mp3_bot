import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from dotenv import load_dotenv

import handlers


COMMANDS = {
    "uz": [("start", "Botni ishga tushirish"), ("language", "Tilni o'zgartirish"), ("cancel", "Bekor qilish")],
    "ru": [("start", "Запустить бота"), ("language", "Сменить язык"), ("cancel", "Отмена")],
    "en": [("start", "Start the bot"), ("language", "Change language"), ("cancel", "Cancel")],
}


async def set_commands(bot: Bot) -> None:
    """Telegram'dagi "/" menyusi: foydalanuvchi interfeys tiliga qarab ru/en, qolganiga uz."""
    def cmds(lang):
        return [BotCommand(command=c, description=d) for c, d in COMMANDS[lang]]

    await bot.set_my_commands(cmds("uz"))  # standart
    await bot.set_my_commands(cmds("ru"), language_code="ru")
    await bot.set_my_commands(cmds("en"), language_code="en")


async def main() -> None:
    load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN topilmadi. .env faylini tekshiring.")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(handlers.router)

    await set_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
