from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.content import (
    AFTER_LEAD,
    BOLT_HOWTO,
    CHOOSE_BRANCH,
    TEST_Q1,
    TEST_Q2,
    TEST_Q3,
)
from bot.db import Database
from bot.keyboards import (
    bolt_ready_keyboard,
    bolt_start_keyboard,
    branch_keyboard,
    options_keyboard,
    start_test_keyboard,
)
from bot.services.funnel import send_gate
from bot.states import FunnelStates


async def show_branches(target: Message | CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    message = target.message if isinstance(target, CallbackQuery) else target
    await message.answer(CHOOSE_BRANCH, reply_markup=branch_keyboard())


async def show_gate(
    message: Message,
    state: FSMContext,
    branch: str,
    settings: Settings,
) -> None:
    await state.set_state(FunnelStates.waiting_subscription)
    await state.update_data(branch=branch)
    await send_gate(message, branch, settings)


async def show_ready_for_test(message: Message, state: FSMContext) -> None:
    await state.set_state(FunnelStates.ready_for_test)
    await message.answer(AFTER_LEAD, reply_markup=start_test_keyboard())


async def show_q1(message: Message, state: FSMContext) -> None:
    await state.set_state(FunnelStates.q1)
    await message.answer(
        TEST_Q1["text"],
        reply_markup=options_keyboard("q1", TEST_Q1["options"]),
    )


async def show_q2(message: Message, state: FSMContext) -> None:
    await state.set_state(FunnelStates.q2)
    await message.answer(
        TEST_Q2["text"],
        reply_markup=options_keyboard("q2", TEST_Q2["options"]),
    )


async def show_q3(message: Message, state: FSMContext) -> None:
    await state.set_state(FunnelStates.q3)
    await message.answer(
        TEST_Q3["text"],
        reply_markup=options_keyboard("q3", TEST_Q3["options"]),
    )


async def show_bolt_intro(message: Message, state: FSMContext) -> None:
    await state.set_state(FunnelStates.bolt_intro)
    await message.answer(BOLT_HOWTO, reply_markup=bolt_ready_keyboard())


async def show_bolt_start(message: Message, state: FSMContext) -> None:
    await state.set_state(FunnelStates.bolt_waiting_start)
    await state.update_data(bolt_started_at=None)
    await message.answer(
        "На выдохе зажми нос и нажми СТАРТ.",
        reply_markup=bolt_start_keyboard(),
    )


async def step_back(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    message = callback.message
    current = await state.get_state()
    data = await state.get_data()
    user = await db.get_user(callback.from_user.id)
    branch = data.get("branch") or (user or {}).get("branch")

    # Sport stub / no state → выбор ветки
    if current is None:
        await show_branches(callback, state)
        return

    if current == FunnelStates.waiting_subscription.state:
        await show_branches(callback, state)
        return

    if current == FunnelStates.ready_for_test.state:
        if settings.require_subscription and branch:
            await show_gate(message, state, branch, settings)
        else:
            await show_branches(callback, state)
        return

    if current == FunnelStates.q1.state:
        answers = data.get("answers", {})
        answers.pop("sleep_hours", None)
        await state.update_data(answers=answers)
        await show_ready_for_test(message, state)
        return

    if current == FunnelStates.q2.state:
        answers = data.get("answers", {})
        answers.pop("night_wakes", None)
        await state.update_data(answers=answers)
        await show_q1(message, state)
        return

    if current == FunnelStates.q3.state:
        answers = data.get("answers", {})
        answers.pop("mouth_breathing", None)
        await state.update_data(answers=answers)
        await show_q2(message, state)
        return

    if current == FunnelStates.bolt_intro.state:
        # Lifestyle-вопросы только у «Сон»
        if branch == "sleep":
            await show_q3(message, state)
        else:
            await show_ready_for_test(message, state)
        return

    if current == FunnelStates.bolt_waiting_start.state:
        await show_bolt_intro(message, state)
        return

    if current == FunnelStates.bolt_running.state:
        await show_bolt_start(message, state)
        return

    if current == FunnelStates.done.state:
        await show_ready_for_test(message, state)
        return

    # fallback
    await show_branches(callback, state)
