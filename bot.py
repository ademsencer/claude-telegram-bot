#!/usr/bin/env python3
"""
Claude Telegram Bot
Telegram uzerinden Claude Code'a komut gonder, sonuclari al.
Menu sistemi, Docker/sistem yonetimi, kisayollar ve monitoring.
"""
import asyncio
import logging
from telegram import BotCommand, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
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
from handlers.menu import menu_command, menu_callback_handler
from handlers.monitoring import vpn_command, wifi_command
from handlers.system_ops import exec_command, handle_exec_text
from services.notifier import Notifier
from services.monitor import SystemMonitor
from services.shortcuts import ShortcutManager

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    bot = application.bot

    # BotCommand menu (/ tiklayinca cikan liste)
    await bot.set_my_commands([
        BotCommand("menu", "Ana menuyu ac"),
        BotCommand("ask", "Claude'a soru sor"),
        BotCommand("task", "Projede gorev ver"),
        BotCommand("exec", "Komut calistir"),
        BotCommand("project", "Proje yonetimi"),
        BotCommand("status", "Sistem durumu"),
        BotCommand("help", "Tum komutlar"),
    ])

    notifier = Notifier(bot)
    await notifier.send(
        "🟢 <b>Bot baslatildi!</b>\n"
        f"🤖 Model: <code>{Config.CLAUDE_MODEL}</code>\n"
        f"🔐 Mod: <code>{Config.CLAUDE_PERMISSIONS}</code>\n\n"
        "/menu ile menuyu ac"
    )

    monitor = SystemMonitor(notifier)
    asyncio.create_task(monitor.start())
    logger.info("Sistem monitoring baslatildi")


async def text_message_handler(update: Update, context):
    """Komut olmayan text mesajlarini isle (exec modu, kisayol ekleme vs.)."""
    if not update.message or not update.message.text:
        return

    # Exec modu aktifse
    if await handle_exec_text(update, context):
        return

    # Kisayol ekleme akisi aktifse
    sm = ShortcutManager()
    if await sm.handle_text(update, context):
        return


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
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("status", status_command))

    # Claude komutlari
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("task", task_command))
    app.add_handler(CommandHandler("project", project_command))
    app.add_handler(CommandHandler("mode", mode_command))
    app.add_handler(CommandHandler("log", log_command))

    # Sistem
    app.add_handler(CommandHandler("exec", exec_command))

    # Monitoring
    app.add_handler(CommandHandler("vpn", vpn_command))
    app.add_handler(CommandHandler("wifi", wifi_command))

    # Inline buton callback'leri (tek handler, menu.py icinde route edilir)
    app.add_handler(CallbackQueryHandler(menu_callback_handler))

    # Serbest text mesajlari (exec modu, kisayol ekleme vs.)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    logger.info("Bot baslatiliyor...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
