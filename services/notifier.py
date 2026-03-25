import logging
from telegram import Bot
from config import Config

logger = logging.getLogger(__name__)


class Notifier:
    """Telegram bildirim gonderme servisi."""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def send(self, text: str, parse_mode: str = "HTML") -> bool:
        if not Config.CHAT_ID:
            logger.warning("TELEGRAM_CHAT_ID ayarlanmamis")
            return False
        try:
            await self.bot.send_message(
                chat_id=Config.CHAT_ID,
                text=text,
                parse_mode=parse_mode,
            )
            return True
        except Exception as e:
            logger.error(f"Bildirim gonderilemedi: {e}")
            return False

    async def send_to(self, chat_id: int | str, text: str, parse_mode: str = "HTML") -> bool:
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
            )
            return True
        except Exception as e:
            logger.error(f"Bildirim gonderilemedi ({chat_id}): {e}")
            return False
