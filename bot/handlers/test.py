import time

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.config import Settings
from bot.content import (
    BOLT_HOWTO,
    SPORT_COMING_SOON,
    TEST_DESC,
    TEST_Q1,
    TEST_Q2,
    TEST_Q3,
    TEST_START,
)
from bot.db import Database
from bot.keyboards import (
    back_only_keyboard,
    bolt_ready_keyboard,
    bolt_start_keyboard,
    bolt_stop_keyboard,
    options_keyboard,
)
from bot.services.funnel import send_result
from bot.states import FunnelStates

router = Router(name="test")


async def _user_branch(db: Database, user_id: int) -> str:
    user = await db.get_user(user_id)
    return (user or {}).get("branch") or "sleep"


@router.callback_query(F.data == "test:start")
async def test_start(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    branch = await _user_branch(db, callback.from_user.id)
    if branch == "sport":
        await callback.message.answer(
            SPORT_COMING_SOON,
            reply_markup=back_only_keyboard(),
        )
        await callback.answer()
        return

    await state.set_state(FunnelStates.q1)
    await state.update_data(answers={}, branch=branch)

    desc = TEST_DESC.get(branch)
    if desc:
        await callback.message.answer(desc)

    await callback.message.answer(TEST_START)
    await callback.message.answer(
        TEST_Q1["text"],
        reply_markup=options_keyboard("q1", TEST_Q1["options"]),
    )
    await callback.answer()


@router.callback_query(FunnelStates.q1, F.data.startswith("q1:"))
async def on_q1(callback: CallbackQuery, state: FSMContext) -> None:
    answer = callback.data.split(":", 1)[1]
    data = await state.get_data()
    answers = data.get("answers", {})
    answers["sleep_hours"] = answer
    await state.update_data(answers=answers)
    await state.set_state(FunnelStates.q2)
    await callback.message.edit_text(f"{TEST_Q1['text']}\n\n✓")
    await callback.message.answer(
        TEST_Q2["text"],
        reply_markup=options_keyboard("q2", TEST_Q2["options"]),
    )
    await callback.answer()


@router.callback_query(FunnelStates.q2, F.data.startswith("q2:"))
async def on_q2(callback: CallbackQuery, state: FSMContext) -> None:
    answer = callback.data.split(":", 1)[1]
    data = await state.get_data()
    answers = data.get("answers", {})
    answers["night_wakes"] = answer
    await state.update_data(answers=answers)
    await state.set_state(FunnelStates.q3)
    await callback.message.edit_text(f"{TEST_Q2['text']}\n\n✓")
    await callback.message.answer(
        TEST_Q3["text"],
        reply_markup=options_keyboard("q3", TEST_Q3["options"]),
    )
    await callback.answer()


@router.callback_query(FunnelStates.q3, F.data.startswith("q3:"))
async def on_q3(callback: CallbackQuery, state: FSMContext) -> None:
    answer = callback.data.split(":", 1)[1]
    data = await state.get_data()
    answers = data.get("answers", {})
    answers["mouth_breathing"] = answer
    await state.update_data(answers=answers)
    await state.set_state(FunnelStates.bolt_intro)
    await callback.message.edit_text(f"{TEST_Q3['text']}\n\n✓")
    await callback.message.answer(
        BOLT_HOWTO,
        reply_markup=bolt_ready_keyboard(),
    )
    await callback.answer()


@router.callback_query(FunnelStates.bolt_intro, F.data == "bolt:ready")
async def bolt_ready(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FunnelStates.bolt_waiting_start)
    await callback.message.edit_text(
        "На выдохе зажми нос и нажми СТАРТ.",
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

    seconds = max(0.0, time.monotonic() - float(started))
    answers = data.get("answers", {})
    branch = data.get("branch") or await _user_branch(db, callback.from_user.id)

    level = await db.save_test_result(
        telegram_id=callback.from_user.id,
        answers=answers,
        bolt_seconds=seconds,
        branch=branch,
        promo_code=settings.promo_code,
    )

    await callback.message.edit_text(f"BOLT: {seconds:.1f} сек")
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
