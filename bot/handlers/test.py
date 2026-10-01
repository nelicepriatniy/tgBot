import logging
import time

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile

from bot.config import Settings
from bot.content import (
    BOLT_HOWTO,
    BOLT_INTRO,
    BOLT_START_HINT,
    format_bolt_seconds,
    resolve_bolt_circle,
)
from bot.db import Database
from bot.keyboards import (
    bolt_ready_keyboard,
    bolt_start_keyboard,
    bolt_stop_keyboard,
)
from bot.services.funnel import send_result
from bot.states import FunnelStates

router = Router(name="test")
logger = logging.getLogger(__name__)


async def _user_branch(db: Database, user_id: int) -> str:
    user = await db.get_user(user_id)
    return (user or {}).get("branch") or "sleep"


async def _send_bolt_circle(callback: CallbackQuery) -> None:
    path = resolve_bolt_circle()
    if path is None:
        return
    try:
        await callback.message.answer_video_note(FSInputFile(path))
    except Exception:
        logger.exception("Failed to send BOLT video note %s", path)
        try:
            await callback.message.answer_video(
                FSInputFile(path),
                supports_streaming=True,
            )
        except Exception:
            logger.exception("Failed to send BOLT video fallback %s", path)


async def _start_bolt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FunnelStates.bolt_intro)
    await _send_bolt_circle(callback)
    await callback.message.answer(BOLT_INTRO)
    await callback.message.answer(
        BOLT_HOWTO,
        reply_markup=bolt_ready_keyboard(),
    )


@router.callback_query(F.data == "test:start")
async def test_start(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    branch = await _user_branch(db, callback.from_user.id)
    await callback.answer()
    await state.update_data(answers={}, branch=branch)
    await _start_bolt(callback, state)


@router.callback_query(FunnelStates.bolt_intro, F.data == "bolt:ready")
async def bolt_ready(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FunnelStates.bolt_waiting_start)
    await callback.message.edit_text(
        BOLT_START_HINT,
        reply_markup=bolt_start_keyboard(),
    )
    await callback.answer()


@router.callback_query(FunnelStates.bolt_waiting_start, F.data == "bolt:start")
async def bolt_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(bolt_started_at=time.monotonic())
    await state.set_state(FunnelStates.bolt_running)
    await callback.message.edit_text(
        "Идёт замер… При первом желании вдохнуть — СТОП.",
        reply_markup=bolt_stop_keyboard(),
    )
    await callback.answer()


@router.callback_query(FunnelStates.bolt_running, F.data == "bolt:stop")
async def bolt_stop(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    data = await state.get_data()
    started = data.get("bolt_started_at")
    if started is None:
        await callback.answer("Сначала нажми СТАРТ", show_alert=True)
        return

    seconds = float(round(max(0.0, time.monotonic() - float(started))))
    answers = data.get("answers", {})
    branch = data.get("branch") or await _user_branch(db, callback.from_user.id)

    level = await db.save_test_result(
        telegram_id=callback.from_user.id,
        answers=answers,
        bolt_seconds=seconds,
        branch=branch,
        promo_code="",
    )

    await callback.message.edit_text(format_bolt_seconds(seconds))
    await send_result(
        callback.message,
        branch=branch,
        bolt_seconds=seconds,
        level=level,
        settings=settings,
    )
    await state.set_state(FunnelStates.done)
    await callback.answer()


@router.callback_query(F.data == "offer:clicked")
async def offer_clicked(callback: CallbackQuery, db: Database) -> None:
    user = await db.get_user(callback.from_user.id)
    branch = (user or {}).get("branch")
    await db.mark_offer_click(callback.from_user.id, branch)
    await callback.answer("Отметили переход. Удачи!")


@router.callback_query(F.data == "drip:off")
async def drip_off(callback: CallbackQuery, db: Database) -> None:
    user = await db.get_user(callback.from_user.id)
    branch = (user or {}).get("branch")
    await db.unsubscribe(callback.from_user.id, branch)
    await callback.message.edit_text("Ты отписан от рассылки. Вернуться: /start")
    await callback.answer()
