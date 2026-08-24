from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import FSInputFile, Message

from bot.config import Settings
from bot.content import (
    AFTER_LEAD,
    ALREADY_SUBSCRIBED,
    DISCLAIMER,
    GATE_TEXT,
    INTERPRETATION,
    LEAD_MAGNET,
    ensure_placeholder_files,
    resolve_lead_pdf,
)
from bot.db import Database
from bot.keyboards import gate_keyboard, start_test_keyboard

logger = logging.getLogger(__name__)


async def send_gate(message: Message, branch: str, settings: Settings) -> None:
    text = GATE_TEXT.get(branch, GATE_TEXT["sleep"])
    await message.answer(text, reply_markup=gate_keyboard(settings.channel_url))


async def send_lead_magnet(
    message: Message,
    branch: str,
    db: Database,
    user_id: int,
) -> None:
    ensure_placeholder_files()
    meta = LEAD_MAGNET[branch]
    await message.answer(ALREADY_SUBSCRIBED)

    pdf_path = resolve_lead_pdf(branch)
    sent = False
    if pdf_path is not None:
        try:
            await message.answer_document(
                FSInputFile(pdf_path),
                caption=meta["caption"],
            )
            sent = True
        except Exception:
            logger.exception("Failed to send lead magnet %s for user %s", pdf_path, user_id)
            await message.answer(
                "Не удалось отправить файл. Напиши в поддержку или нажми «Старт» ещё раз."
            )
    else:
        logger.error(
            "Lead magnet PDF missing for branch=%s (expected %s)",
            branch,
            meta["pdf"],
        )
        await message.answer(
            "Файл материалов пока не найден на сервере. "
            "Загрузи PDF в content/%s/ и перезапусти бота." % branch
        )

    audio_path = meta.get("audio")
    if audio_path and audio_path.exists():
        await message.answer_audio(FSInputFile(audio_path))

    if sent:
        await db.mark_lead_magnet(user_id, branch)

    await message.answer(AFTER_LEAD, reply_markup=start_test_keyboard())


def promo_until(issued_at: str | None = None) -> str:
    # промокод пока отключён — функция оставлена на будущее
    if issued_at:
        start = datetime.fromisoformat(issued_at)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
    else:
        start = datetime.now(timezone.utc)
    until = start + timedelta(hours=48)
    return until.astimezone().strftime("%d.%m.%Y %H:%M")


async def send_result(
    message: Message,
    *,
    branch: str,
    bolt_seconds: float,
    level: str,
    settings: Settings,
) -> None:
    interp = INTERPRETATION[branch][level].format(seconds=bolt_seconds)
    await message.answer(f"{interp}\n\n{DISCLAIMER}")
    # Промокод пока отключён
    # promo = PROMO_TEXT.format(
    #     code=settings.promo_code,
    #     until=promo_until(),
    # )
    # await message.answer(
    #     promo,
    #     reply_markup=offer_keyboard_tracked(settings.purchase_url(branch)),
    # )


async def broadcast(
    bot: Bot,
    db: Database,
    text: str,
    branch: str | None,
) -> tuple[int, int]:
    users = await db.users_by_branch(branch)
    ok = 0
    fail = 0
    for user in users:
        try:
            await bot.send_message(user["telegram_id"], text)
            ok += 1
        except Exception:
            fail += 1
    return ok, fail
