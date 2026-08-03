import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import get_settings
from bot.content import ensure_placeholder_files
from bot.db import Database
from bot.handlers import admin, start, test
from bot.middlewares import InjectMiddleware
from bot.services.drip import DripScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    ensure_placeholder_files()

    db = Database(settings.db_path)
    await db.connect()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(InjectMiddleware(db, settings))
    dp.include_router(start.router)
    dp.include_router(test.router)
    dp.include_router(admin.router)

    drip = DripScheduler(bot, db, settings)
    drip.start()

    logger.info("Bot starting…")
    try:
        await dp.start_polling(bot)
    finally:
        drip.shutdown()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
