import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from handlers import lobby, gameplay, misc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Register routers
    dp.include_router(misc.router)    # /start, /quit, /cards, /status first
    dp.include_router(lobby.router)   # /newgame, join, start_game callbacks
    dp.include_router(gameplay.router)  # play, draw, color

    logger.info("UNO bot ishga tushdi...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
