from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.content import BRANCH_BUTTONS

BACK_CB = "nav:back"
START_BTN = "Старт"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=START_BTN)]],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Нажми «Старт», чтобы начать заново",
    )


def back_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="← Назад", callback_data=BACK_CB)


def branch_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, label in BRANCH_BUTTONS:
        builder.button(text=label, callback_data=f"branch:{key}")
    builder.adjust(2, 1)
    return builder.as_markup()


def gate_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Подписаться на канал", url=channel_url)
    builder.button(text="✅ Я подписался, проверить", callback_data="gate:check")
    builder.button(text="← Назад", callback_data=BACK_CB)
    builder.adjust(1)
    return builder.as_markup()


def start_test_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Пройти тест", callback_data="test:start")
    builder.button(text="← Назад", callback_data=BACK_CB)
    builder.adjust(1)
    return builder.as_markup()


def bolt_ready_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Готов, показать «Старт»", callback_data="bolt:ready")
    builder.button(text="← Назад", callback_data=BACK_CB)
    builder.adjust(1)
    return builder.as_markup()


def bolt_start_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="▶ СТАРТ", callback_data="bolt:start")
    builder.button(text="← Назад", callback_data=BACK_CB)
    builder.adjust(1)
    return builder.as_markup()


def bolt_stop_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⏹ СТОП", callback_data="bolt:stop")
    builder.button(text="← Назад", callback_data=BACK_CB)
    builder.adjust(1)
    return builder.as_markup()


def channel_post_keyboard(url: str, button_text: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=button_text, url=url)
    builder.button(text="← Назад", callback_data=BACK_CB)
    builder.adjust(1)
    return builder.as_markup()


def offer_keyboard_tracked(purchase_url: str) -> InlineKeyboardMarkup:
    # Промокод / оффер со скидкой пока отключён — клавиатура оставлена на будущее
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Перейти", url=purchase_url))
    builder.row(back_button())
    return builder.as_markup()


def unsubscribe_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Отписаться от рассылки", callback_data="drip:off")
    builder.button(text="← Назад", callback_data=BACK_CB)
    builder.adjust(1)
    return builder.as_markup()


def back_only_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="← Назад", callback_data=BACK_CB)
    return builder.as_markup()
