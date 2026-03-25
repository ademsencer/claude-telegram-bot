#!/usr/bin/env python3
"""
Claude Telegram Bot
Telegram uzerinden Claude Code'a komut gonder, sonuclari al.
Sistem monitoring, proje yonetimi ve bildirim sistemi.
"""
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler
from config import Config
from handlers.commands import (
    start_command,
    help_command,
    ping_command,
    status_command,
)
from handlers.claude import (
    ask_command,
    task_command,
    project_command,
    mode_command,
    log_command,
)
from handlers.monitoring import vpn_command, wifi_command
from services.notifier import Notifier
from services.monitor import SystemMonitor

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    bot = application.bot
    notifier = Notifier(bot)

    await notifier.send(
        "🟢 <b>Bot baslatildi!</b>\n"
        f"🤖 Model: <code>{Config.CLAUDE_MODEL}</code>\n"
        f"🔐 Mod: <code>{Config.CLAUDE_PERMISSIONS}</code>"
    )

    monitor = SystemMonitor(notifier)
    asyncio.create_task(monitor.start())
    logger.info("Sistem monitoring baslatildi")


def main():
    if not Config.BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN ayarlanmamis!")
        return

    if not Config.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY ayarlanmamis! Claude komutlari calismayacak.")

    app = Application.builder().token(Config.BOT_TOKEN).post_init(post_init).build()

    # Genel komutlar
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("status", status_command))

    # Claude komutlari
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("task", task_command))
    app.add_handler(CommandHandler("project", project_command))
    app.add_handler(CommandHandler("mode", mode_command))
    app.add_handler(CommandHandler("log", log_command))

    # Monitoring
    app.add_handler(CommandHandler("vpn", vpn_command))
    app.add_handler(CommandHandler("wifi", wifi_command))

    logger.info("Bot baslatiliyor...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
