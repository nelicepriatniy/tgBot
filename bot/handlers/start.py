from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.content import BRANCH_NAMES, CHOOSE_BRANCH, NEED_SUBSCRIBE, RESTART_HINT
from bot.db import BRANCHES, Database
from bot.keyboards import (
    START_BTN,
    branch_keyboard,
    main_reply_keyboard,
)
from bot.services.funnel import continue_after_branch, send_greeting, send_lead_magnet
from bot.services.subscription import is_subscribed
from bot.states import FunnelStates

router = Router(name="start")

_START_ALIASES = {START_BTN.lower(), "start", "старт", "/start"}


def _parse_branch(payload: str | None) -> str | None:
    if not payload:
        return None
    value = payload.strip().lower()
    return value if value in BRANCHES else None


async def run_start(
    message: Message,
    state: FSMContext,
    db: Database,
    settings: Settings,
    payload: str | None = None,
) -> None:
    await state.clear()
    branch = _parse_branch(payload)
    await db.upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        branch=branch,
    )

    await message.answer(RESTART_HINT, reply_markup=main_reply_keyboard())
    await send_greeting(message)

    if branch:
        await db.set_branch(message.from_user.id, branch)
        await continue_after_branch(
            message,
            user_id=message.from_user.id,
            branch=branch,
            state=state,
            db=db,
            settings=settings,
            confirm=True,
        )
        return

    await state.set_state(FunnelStates.choosing_branch)
    await message.answer(CHOOSE_BRANCH, reply_markup=branch_keyboard())


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    await run_start(message, state, db, settings, payload=command.args)


@router.message(F.text.func(lambda t: bool(t) and t.strip().lower() in _START_ALIASES))
async def btn_start(
    message: Message,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    await run_start(message, state, db, settings)


@router.callback_query(F.data == "nav:back")
async def nav_back(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    from bot.services.navigation import step_back

    await step_back(callback, state, db, settings)
    await callback.answer()


@router.callback_query(F.data == "menu:branches")
async def back_to_branches_legacy(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    from bot.services.navigation import step_back

    await step_back(callback, state, db, settings)
    await callback.answer()


@router.callback_query(F.data.startswith("branch:"))
async def choose_branch(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    branch = callback.data.split(":", 1)[1]
    if branch not in BRANCHES:
        await callback.answer("Неизвестная ветка", show_alert=True)
        return
    await callback.answer()
    await db.upsert_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        branch=branch,
    )
    await db.set_branch(callback.from_user.id, branch)
    try:
        await callback.message.edit_text(f"Выбрано: {BRANCH_NAMES[branch]}")
    except Exception:
        await callback.message.answer(f"Выбрано: {BRANCH_NAMES[branch]}")
    await continue_after_branch(
        callback.message,
        user_id=callback.from_user.id,
        branch=branch,
        state=state,
        db=db,
        settings=settings,
        confirm=False,
    )


@router.callback_query(F.data == "gate:check")
async def gate_check(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    if not settings.require_subscription:
        await callback.answer("Проверка подписки сейчас выключена", show_alert=True)
        return

    user = await db.get_user(callback.from_user.id)
    data = await state.get_data()
    branch = data.get("branch") or (user or {}).get("branch")
    if not branch:
        await callback.answer("Сначала нажми «Старт»", show_alert=True)
        return

    subscribed = await is_subscribed(
        callback.bot, settings.channel_id, callback.from_user.id
    )
    if not subscribed:
        await callback.answer(NEED_SUBSCRIBE, show_alert=True)
        return

    await db.mark_subscribed(callback.from_user.id, branch)
    await callback.answer("Подписка подтверждена")
    await send_lead_magnet(
        callback.message, branch, db, callback.from_user.id, announce=True
    )
    await state.set_state(FunnelStates.ready_for_test)
