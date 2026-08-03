from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import Settings
from bot.content import DRIP
from bot.db import Database
from bot.keyboards import offer_keyboard_tracked, unsubscribe_keyboard

logger = logging.getLogger(__name__)

DRIP_DAYS = (1, 2, 3, 5, 7)


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class DripScheduler:
    def __init__(self, bot: Bot, db: Database, settings: Settings) -> None:
        self.bot = bot
        self.db = db
        self.settings = settings
        self.scheduler = AsyncIOScheduler(timezone="UTC")

    def start(self) -> None:
        self.scheduler.add_job(
            self.tick,
            "interval",
            minutes=15,
            id="drip_tick",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info("Drip scheduler started")

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def tick(self) -> None:
        now = datetime.now(timezone.utc)
        for day in DRIP_DAYS:
            users = await self.db.users_for_drip(day)
            for user in users:
                started = _parse_iso(user["drip_started_at"])
                due_at = started + timedelta(days=day)
                if now < due_at:
                    continue
                if user["drip_day"] >= day:
                    continue
                await self._send_letter(user, day)
                await asyncio.sleep(0.05)  # soft rate-limit

    async def _send_letter(self, user: dict, day: int) -> None:
        branch = user.get("branch") or "sleep"
        templates = DRIP.get(branch, DRIP["sleep"])
        text_tpl = templates.get(day)
        if not text_tpl:
            return
        seconds = float(user.get("bolt_seconds") or 0)
        text = text_tpl.format(seconds=seconds, code=self.settings.promo_code)
        markup = None
        if day in (3, 7):
            markup = offer_keyboard_tracked(self.settings.purchase_url(branch))
        else:
            markup = unsubscribe_keyboard()
        try:
            await self.bot.send_message(
                user["telegram_id"],
                text,
                reply_markup=markup,
            )
            await self.db.set_drip_day(user["telegram_id"], day)
        except TelegramRetryAfter as e:
            logger.warning("Rate limited, sleep %s", e.retry_after)
            await asyncio.sleep(e.retry_after)
        except TelegramForbiddenError:
            await self.db.unsubscribe(user["telegram_id"], branch)
        except Exception:
            logger.exception("Failed drip to %s day %s", user["telegram_id"], day)
