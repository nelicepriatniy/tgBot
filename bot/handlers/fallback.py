from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards import main_reply_keyboard

router = Router(name="fallback")


@router.message(F.text)
async def any_text(message: Message, state: FSMContext) -> None:
    """Если человек пишет что угодно вместо кнопок — подсказываем Старт."""
    current = await state.get_state()
    if current is not None:
        await message.answer(
            "Используй кнопки под сообщением или нажми «Старт», чтобы начать сначала.",
            reply_markup=main_reply_keyboard(),
        )
        return

    await message.answer(
        "Нажми кнопку «Старт» ниже, чтобы начать 👇",
        reply_markup=main_reply_keyboard(),
    )
