from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberRestricted

MEMBER_OK = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}


async def is_subscribed(bot: Bot, channel_id: str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
    except Exception:
        return False
    if member.status in MEMBER_OK:
        return True
    if isinstance(member, ChatMemberRestricted) and member.is_member:
        return True
    return False
