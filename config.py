import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram
    BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    ALLOWED_CHAT_IDS: list[str] = [
        cid.strip()
        for cid in os.getenv("ALLOWED_CHAT_IDS", "").split(",")
        if cid.strip()
    ]

    # Claude Code
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    CLAUDE_MAX_TURNS: int = int(os.getenv("CLAUDE_MAX_TURNS", "50"))
    CLAUDE_PERMISSIONS: str = os.getenv("CLAUDE_PERMISSIONS", "skip")  # skip|auto|ask

    # Workspace
    WORKSPACE_DIR: str = os.getenv("WORKSPACE_DIR", "/workspace")

    # Monitoring
    VPN_CHECK_INTERVAL: int = int(os.getenv("VPN_CHECK_INTERVAL", "30"))
    WIFI_CHECK_INTERVAL: int = int(os.getenv("WIFI_CHECK_INTERVAL", "60"))
    VPN_INTERFACE: str = os.getenv("VPN_INTERFACE", "wg0")
    VPN_ENDPOINT: str = os.getenv("VPN_ENDPOINT", "10.0.0.1")

    @classmethod
    def is_authorized(cls, chat_id: int | str) -> bool:
        return str(chat_id) in cls.ALLOWED_CHAT_IDS
