from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    manager_username: str
    channel_invite: str
    chat_invite: str


def get_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")
    return Settings(
        bot_token=token,
        manager_username=os.getenv("MANAGER_USERNAME", "rezar_auto1").lstrip("@"),
        channel_invite=os.getenv("CHANNEL_INVITE", "https://t.me/+Lr5L8xRGZa9kZGRi"),
        chat_invite=os.getenv("CHAT_INVITE", "https://t.me/+YuRmEjW__dplMTZi"),
    )
