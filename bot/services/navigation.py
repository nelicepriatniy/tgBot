from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.content import AFTER_LEAD, BOLT_HOWTO, BOLT_INTRO, BOLT_START_HINT, CHOOSE_BRANCH
from bot.db import Database
from bot.keyboards import (
    bolt_ready_keyboard,
    bolt_start_keyboard,
    branch_keyboard,
    start_test_keyboard,
)
from bot.services.funnel import send_gate
from bot.states import FunnelStates


async def show_branches(target: Message | CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FunnelStates.choosing_branch)
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


async def show_bolt_intro(message: Message, state: FSMContext) -> None:
    await state.set_state(FunnelStates.bolt_intro)
    await message.answer(BOLT_INTRO)
    await message.answer(BOLT_HOWTO, reply_markup=bolt_ready_keyboard())


async def show_bolt_start(message: Message, state: FSMContext) -> None:
    await state.set_state(FunnelStates.bolt_waiting_start)
    await state.update_data(bolt_started_at=None)
    await message.answer(
        BOLT_START_HINT,
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

    if current is None or current == FunnelStates.choosing_branch.state:
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

    if current == FunnelStates.bolt_intro.state:
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

    await show_branches(callback, state)
