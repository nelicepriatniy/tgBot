from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import Settings
from bot.content import BRANCH_NAMES
from bot.db import BRANCHES, Database
from bot.services.funnel import broadcast
from bot.states import AdminStates

router = Router(name="admin")


def _is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_id_list


@router.message(Command("stats"))
async def cmd_stats(message: Message, db: Database, settings: Settings) -> None:
    if not _is_admin(message.from_user.id, settings):
        return
    stats = await db.funnel_stats()
    lines = ["📊 Воронка (уникальные пользователи)\n"]
    labels = {
        "start": "1. Переходы в бота",
        "subscribed": "2. Подписались на канал",
        "test_completed": "3. Прошли тест",
        "offer_click": "4. Кликнули оффер",
        "unsubscribed": "5. Отписались",
    }
    for key, title in labels.items():
        total = stats["total"].get(key, 0)
        by = stats["by_branch"].get(key, {})
        parts = ", ".join(
            f"{BRANCH_NAMES.get(b, b)}: {by.get(b, 0)}" for b in BRANCHES
        )
        lines.append(f"{title}: {total}\n   ({parts})")
    await message.answer("\n".join(lines))


@router.message(Command("broadcast"))
async def cmd_broadcast(
    message: Message,
    state: FSMContext,
    settings: Settings,
) -> None:
    if not _is_admin(message.from_user.id, settings):
        return
    await state.set_state(AdminStates.broadcast_text)
    await message.answer("Пришли текст рассылки одним сообщением.")


@router.message(AdminStates.broadcast_text)
async def broadcast_text(
    message: Message,
    state: FSMContext,
    settings: Settings,
) -> None:
    if not _is_admin(message.from_user.id, settings):
        return
    await state.update_data(broadcast_text=message.text or message.html_text)
    await state.set_state(AdminStates.broadcast_branch)
    builder = InlineKeyboardBuilder()
    builder.button(text="Вся база", callback_data="bcast:all")
    for b in BRANCHES:
        builder.button(text=BRANCH_NAMES[b], callback_data=f"bcast:{b}")
    builder.adjust(1)
    await message.answer("Кому отправить?", reply_markup=builder.as_markup())


@router.callback_query(AdminStates.broadcast_branch, F.data.startswith("bcast:"))
async def broadcast_send(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer()
        return
    data = await state.get_data()
    text = data.get("broadcast_text")
    if not text:
        await callback.answer("Текст потерян, начни с /broadcast", show_alert=True)
        await state.clear()
        return
    target = callback.data.split(":", 1)[1]
    branch = None if target == "all" else target
    await callback.message.edit_text("Отправляю…")
    ok, fail = await broadcast(callback.bot, db, text, branch)
    await callback.message.answer(f"Готово. Успешно: {ok}, ошибок: {fail}")
    await state.clear()
    await callback.answer()
