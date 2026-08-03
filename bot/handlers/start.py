from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.content import BRANCH_NAMES, CHOOSE_BRANCH, NEED_SUBSCRIBE
from bot.db import BRANCHES, Database
from bot.keyboards import branch_keyboard, start_test_keyboard
from bot.services.funnel import send_gate, send_lead_magnet
from bot.services.subscription import is_subscribed
from bot.states import FunnelStates

router = Router(name="start")


def _parse_branch(payload: str | None) -> str | None:
    if not payload:
        return None
    value = payload.strip().lower()
    return value if value in BRANCHES else None


async def _continue_after_branch(
    message: Message,
    *,
    user_id: int,
    branch: str,
    user: dict,
    state: FSMContext,
    db: Database,
    settings: Settings,
    returning: bool = False,
) -> None:
    if settings.require_subscription:
        subscribed = await is_subscribed(message.bot, settings.channel_id, user_id)
        if not subscribed:
            await state.set_state(FunnelStates.waiting_subscription)
            await state.update_data(branch=branch)
            await send_gate(message, branch, settings)
            return
        await db.mark_subscribed(user_id, branch)

    if returning and user.get("lead_magnet_sent"):
        await message.answer(
            f"Снова на связи. Ветка: {BRANCH_NAMES.get(branch, branch)}.\n"
            "Можешь пройти тест заново или дождаться писем рассылки.",
        )
        await message.answer("Пройти тест ещё раз?", reply_markup=start_test_keyboard())
        await state.set_state(FunnelStates.ready_for_test)
        return

    if user.get("lead_magnet_sent"):
        await message.answer(
            "Материалы уже отправлялись. Пройти тест ещё раз?",
            reply_markup=start_test_keyboard(),
        )
        await state.set_state(FunnelStates.ready_for_test)
        return

    await send_lead_magnet(message, branch, db, user_id)
    await state.set_state(FunnelStates.ready_for_test)


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    await state.clear()
    branch = _parse_branch(command.args)
    user = await db.upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        branch=branch,
    )
    if not branch and not user.get("branch"):
        await message.answer(CHOOSE_BRANCH, reply_markup=branch_keyboard())
        return

    branch = branch or user["branch"]
    if not user.get("branch"):
        await db.set_branch(message.from_user.id, branch)
        user = await db.get_user(message.from_user.id) or user

    await _continue_after_branch(
        message,
        user_id=message.from_user.id,
        branch=branch,
        user=user,
        state=state,
        db=db,
        settings=settings,
        returning=True,
    )


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
    await db.upsert_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        branch=branch,
    )
    await db.set_branch(callback.from_user.id, branch)
    user = await db.get_user(callback.from_user.id) or {}
    await callback.message.edit_text(f"Выбрано: {BRANCH_NAMES[branch]}")
    await _continue_after_branch(
        callback.message,
        user_id=callback.from_user.id,
        branch=branch,
        user=user,
        state=state,
        db=db,
        settings=settings,
    )
    await callback.answer()


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
        await callback.answer("Сначала выбери ветку через /start", show_alert=True)
        return

    subscribed = await is_subscribed(
        callback.bot, settings.channel_id, callback.from_user.id
    )
    if not subscribed:
        await callback.answer(NEED_SUBSCRIBE, show_alert=True)
        return

    await db.mark_subscribed(callback.from_user.id, branch)
    await callback.answer("Подписка подтверждена")
    await send_lead_magnet(callback.message, branch, db, callback.from_user.id)
    await state.set_state(FunnelStates.ready_for_test)
