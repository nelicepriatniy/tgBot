from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from bot.config import Settings
from bot.content import (
    AFTER_LEAD,
    ALREADY_SUBSCRIBED,
    BRANCH_DESC,
    BRANCH_NAMES,
    CTA_GOOD_BTN,
    CTA_WEAK_BTN,
    DISCLAIMER,
    GATE_TEXT,
    GREETING,
    INTERPRETATION,
    LEAD_MAGNET,
    PREPARING_FILE,
    RESULT_CTA_GOOD,
    RESULT_CTA_WEAK,
    ensure_placeholder_files,
    resolve_lead_pdf,
    resolve_video,
)
from bot.db import Database
from bot.keyboards import channel_post_keyboard, gate_keyboard, start_test_keyboard
from bot.services.media import has_cached, send_cached_document, send_cached_video
from bot.services.subscription import is_subscribed
from bot.states import FunnelStates

logger = logging.getLogger(__name__)


async def _send_video_or_text(
    message: Message,
    *,
    key: str,
    path: Path | None,
    caption: str | None,
) -> None:
    if path is not None:
        try:
            await send_cached_video(
                message,
                key=key,
                path=path,
                caption=caption,
            )
            return
        except Exception:
            logger.exception("Failed to send video %s", path)
    if caption:
        await message.answer(caption)


async def send_greeting(message: Message) -> None:
    await _send_video_or_text(
        message,
        key="video:greeting",
        path=resolve_video("greeting"),
        caption=GREETING,
    )


async def send_branch_intro(message: Message, branch: str) -> None:
    caption = BRANCH_DESC.get(branch, "")
    await _send_video_or_text(
        message,
        key=f"video:{branch}",
        path=resolve_video(branch),
        caption=caption,
    )


async def send_gate(message: Message, branch: str, settings: Settings) -> None:
    text = GATE_TEXT.get(branch, GATE_TEXT["sleep"])
    await message.answer(text, reply_markup=gate_keyboard(settings.channel_url))


async def continue_after_branch(
    message: Message,
    *,
    user_id: int,
    branch: str,
    state: FSMContext,
    db: Database,
    settings: Settings,
    confirm: bool = True,
) -> None:
    if confirm:
        await message.answer(f"Выбрано: {BRANCH_NAMES[branch]}")
    await send_branch_intro(message, branch)

    if settings.require_subscription:
        subscribed = await is_subscribed(message.bot, settings.channel_id, user_id)
        if not subscribed:
            await state.set_state(FunnelStates.waiting_subscription)
            await state.update_data(branch=branch)
            await send_gate(message, branch, settings)
            return
        await db.mark_subscribed(user_id, branch)

    await send_lead_magnet(message, branch, db, user_id)
    await state.set_state(FunnelStates.ready_for_test)


async def send_lead_magnet(
    message: Message,
    branch: str,
    db: Database,
    user_id: int,
    *,
    announce: bool = False,
) -> None:
    ensure_placeholder_files()
    meta = LEAD_MAGNET[branch]
    if announce:
        await message.answer(ALREADY_SUBSCRIBED)

    pdf_path = resolve_lead_pdf(branch)
    sent = False
    if pdf_path is not None:
        if not has_cached(f"pdf:{branch}", pdf_path):
            await message.answer(PREPARING_FILE)
        try:
            await send_cached_document(
                message,
                key=f"pdf:{branch}",
                path=pdf_path,
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
    interp = INTERPRETATION[branch][level]
    await message.answer(f"{interp}\n\n{DISCLAIMER}")

    if level in ("good", "excellent"):
        await message.answer(
            RESULT_CTA_GOOD,
            reply_markup=channel_post_keyboard(
                settings.channel_post_tests_url,
                CTA_GOOD_BTN,
            ),
        )
    else:
        await message.answer(
            RESULT_CTA_WEAK,
            reply_markup=channel_post_keyboard(
                settings.channel_post_breathe_url,
                CTA_WEAK_BTN,
            ),
        )


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
