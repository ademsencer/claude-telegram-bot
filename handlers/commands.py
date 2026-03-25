import os
import logging
import subprocess
from telegram import Update
from telegram.ext import ContextTypes
from config import Config

logger = logging.getLogger(__name__)


def authorized(func):
    """Yetkilendirme decorator'u."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        if not Config.is_authorized(chat_id):
            await update.message.reply_text(
                f"⛔ Yetkisiz erisim.\nChat ID'n: <code>{chat_id}</code>",
                parse_mode="HTML",
            )
            logger.warning(f"Yetkisiz erisim denemesi: {chat_id}")
            return
        return await func(update, context)
    return wrapper


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    name = update.effective_user.first_name or "Kullanici"
    text = (
        f"Merhaba {name}! 👋\n\n"
        f"Chat ID'n: <code>{chat_id}</code>\n\n"
        "Komutlar icin /help yaz."
    )
    await update.message.reply_text(text, parse_mode="HTML")


@authorized
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 <b>Komutlar</b>\n\n"
        "<b>Genel:</b>\n"
        "/start - Bot'u baslat\n"
        "/help - Bu mesaj\n"
        "/ping - Bot canli mi?\n\n"
        "<b>Claude Code:</b>\n"
        "/ask &lt;soru&gt; - Claude'a soru sor\n"
        "/task &lt;proje&gt; &lt;gorev&gt; - Projede gorev ver\n"
        "/task status - Aktif gorev durumu\n"
        "/task cancel - Gorevi iptal et\n"
        "/mode &lt;skip|auto|ask&gt; - Izin modu\n"
        "/log - Son Claude ciktisi\n\n"
        "<b>Projeler:</b>\n"
        "/project clone &lt;url&gt; - Repo klonla\n"
        "/project list - Projeleri listele\n"
        "/project delete &lt;ad&gt; - Projeyi sil\n\n"
        "<b>Sistem:</b>\n"
        "/status - Sistem durumu\n"
        "/vpn - VPN durumu\n"
        "/wifi - WiFi durumu\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")


@authorized
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! Bot calisiyor.")


@authorized
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["📊 <b>Sistem Durumu</b>\n"]

    # Uptime
    try:
        result = subprocess.run(["uptime"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines.append(f"⏱ {result.stdout.strip()}")
    except Exception:
        pass

    # Disk
    try:
        result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            disk_line = result.stdout.strip().split("\n")[-1].split()
            lines.append(f"💾 Disk: {disk_line[2]}/{disk_line[1]} ({disk_line[4]})")
    except Exception:
        pass

    # Bellek
    try:
        result = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            mem = result.stdout.strip().split("\n")[1].split()
            lines.append(f"🧠 RAM: {mem[2]}/{mem[1]}")
    except Exception:
        pass

    # Workspace projeleri
    workspace = Config.WORKSPACE_DIR
    if os.path.isdir(workspace):
        projects = [d for d in os.listdir(workspace) if os.path.isdir(os.path.join(workspace, d))]
        lines.append(f"\n📁 Projeler ({len(projects)}): {', '.join(projects) if projects else 'yok'}")

    # Claude durumu
    lines.append(f"\n🤖 Claude modu: <code>{Config.CLAUDE_PERMISSIONS}</code>")
    lines.append(f"🧠 Model: <code>{Config.CLAUDE_MODEL}</code>")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
