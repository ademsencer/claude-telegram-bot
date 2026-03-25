import asyncio
import subprocess
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ContextTypes
from handlers.commands import authorized
from handlers.menu import back_button
from config import Config

logger = logging.getLogger(__name__)


@authorized
async def vpn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    interface = Config.VPN_INTERFACE
    endpoint = Config.VPN_ENDPOINT
    lines = [f"🔐 <b>VPN Durumu</b> ({interface})\n"]

    # WireGuard
    try:
        result = subprocess.run(
            ["wg", "show", interface], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines.append("✅ WireGuard aktif")
            for line in result.stdout.split("\n"):
                line = line.strip()
                if "latest handshake" in line:
                    lines.append(f"🤝 {line}")
                elif "transfer" in line:
                    lines.append(f"📊 {line}")
        else:
            lines.append("❌ WireGuard aktif degil")
    except FileNotFoundError:
        try:
            result = subprocess.run(
                ["ip", "link", "show", interface], capture_output=True, text=True, timeout=5
            )
            lines.append(f"{'✅' if result.returncode == 0 else '❌'} {interface} interface")
        except Exception:
            lines.append("⚠️ Interface kontrol edilemedi")

    # Ping
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "3", endpoint], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "time=" in line:
                    lines.append(f"📡 Ping: {line.split('time=')[-1].strip()}")
                    break
        else:
            lines.append(f"❌ Endpoint ({endpoint}) ulasilamiyor")
    except Exception:
        lines.append("⚠️ Ping calistirilamadi")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


@authorized
async def wifi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = _wifi_status_text()
    await update.message.reply_text(text, parse_mode="HTML")


def _vpn_status_text() -> str:
    interface = Config.VPN_INTERFACE
    endpoint = Config.VPN_ENDPOINT
    lines = [f"🔐 <b>VPN Durumu</b> ({interface})\n"]
    try:
        result = subprocess.run(["wg", "show", interface], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines.append("✅ WireGuard aktif")
        else:
            lines.append("❌ WireGuard aktif degil")
    except FileNotFoundError:
        lines.append("⚠️ WireGuard bulunamadi")
    try:
        result = subprocess.run(["ping", "-c", "1", "-W", "3", endpoint], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "time=" in line:
                    lines.append(f"📡 Ping: {line.split('time=')[-1].strip()}")
                    break
        else:
            lines.append(f"❌ Endpoint ({endpoint}) ulasilamiyor")
    except Exception:
        pass
    return "\n".join(lines)


def _wifi_status_text() -> str:
    lines = ["📶 <b>WiFi Durumu</b>\n"]
    try:
        result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines.append(f"📡 SSID: <code>{result.stdout.strip()}</code>")
        else:
            lines.append("❌ WiFi bagli degil")
    except FileNotFoundError:
        lines.append("⚠️ iwgetid bulunamadi")
    try:
        result = subprocess.run(["ping", "-c", "1", "-W", "3", "8.8.8.8"], capture_output=True, text=True, timeout=5)
        lines.append(f"🌐 Internet: {'✅ Erisim var' if result.returncode == 0 else '❌ Erisim yok'}")
    except Exception:
        lines.append("⚠️ Internet kontrol edilemedi")
    return "\n".join(lines)


async def handle_monitor_callback(query: CallbackQuery, data: str):
    """Monitoring callback'lerini isle."""
    if data == "monitor:vpn":
        text = _vpn_status_text()
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Yenile", callback_data="monitor:vpn")],
                [back_button("menu:monitor")],
            ]),
        )
    elif data == "monitor:wifi":
        text = _wifi_status_text()
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Yenile", callback_data="monitor:wifi")],
                [back_button("menu:monitor")],
            ]),
        )
    elif data == "monitor:internet":
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", "3", "-W", "3", "8.8.8.8",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode()
            icon = "✅" if proc.returncode == 0 else "❌"
            # Son satirdaki ozet
            summary = output.strip().split("\n")[-1] if output else ""
            text = f"🌐 <b>Internet Testi</b>\n\n{icon} {summary}"
        except Exception as e:
            text = f"❌ Test basarisiz: {e}"
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Tekrar Test", callback_data="monitor:internet")],
                [back_button("menu:monitor")],
            ]),
        )
