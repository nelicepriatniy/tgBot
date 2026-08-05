from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

BACK_CB = "nav:back"
START_BTN = "Старт"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=START_BTN)]],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Нажми «Старт»",
    )


def back_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="← Назад", callback_data=BACK_CB)


def branch_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Сон", callback_data="branch:sleep")
    builder.button(text="Longevity", callback_data="branch:longevity")
    builder.button(text="Спорт", callback_data="branch:sport")
    builder.adjust(1)
    return builder.as_markup()


def gate_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Подписаться на канал", url=channel_url)
    builder.button(text="Я подписался", callback_data="gate:check")
    builder.button(text="← Назад", callback_data=BACK_CB)
    builder.adjust(1)
    return builder.as_markup()


def start_test_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Пройти тест", callback_data="test:start")
    builder.button(text="← Назад", callback_data=BACK_CB)
    builder.adjust(1)
    return builder.as_markup()


def options_keyboard(prefix: str, options: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, label in options:
        builder.button(text=label, callback_data=f"{prefix}:{key}")
    builder.button(text="← Назад", callback_data=BACK_CB)
    builder.adjust(1)
    return builder.as_markup()


def bolt_ready_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Готов — показать СТАРТ", callback_data="bolt:ready")
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


def offer_keyboard_tracked(purchase_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Забрать со скидкой", url=purchase_url))
    builder.row(
        InlineKeyboardButton(text="Перешёл по ссылке", callback_data="offer:clicked")
    )
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
