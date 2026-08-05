import logging

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberRestricted

logger = logging.getLogger(__name__)

MEMBER_OK = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}


def normalize_channel_id(channel_id: str) -> str:
    value = (channel_id or "").strip()
    if not value:
        return value
    # people sometimes paste URL into CHANNEL_ID
    for prefix in (
        "https://t.me/",
        "http://t.me/",
        "t.me/",
        "https://telegram.me/",
        "http://telegram.me/",
    ):
        if value.lower().startswith(prefix):
            value = value[len(prefix) :]
            break
    value = value.split("?")[0].strip("/")
    if value.startswith("+"):
        # invite links can't be used with getChatMember — need numeric -100…
        return value
    if value.lstrip("-").isdigit():
        return value
    if not value.startswith("@"):
        value = f"@{value}"
    return value


async def is_subscribed(bot: Bot, channel_id: str, user_id: int) -> bool:
    chat_id = normalize_channel_id(channel_id)
    if not chat_id or chat_id.startswith("+"):
        logger.error(
            "CHANNEL_ID invalid for getChatMember: %r "
            "(нужен @username или числовой id вида -100…)",
            channel_id,
        )
        return False
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    except Exception as exc:
        logger.warning(
            "getChatMember failed chat_id=%r user_id=%s: %s: %s",
            chat_id,
            user_id,
            type(exc).__name__,
            exc,
        )
        return False
    if member.status in MEMBER_OK:
        return True
    if isinstance(member, ChatMemberRestricted) and member.is_member:
        return True
    logger.info(
        "User %s not subscribed to %s (status=%s)",
        user_id,
        chat_id,
        member.status,
    )
    return False
