import subprocess
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.commands import authorized
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
    lines = ["📶 <b>WiFi Durumu</b>\n"]

    # SSID
    try:
        result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines.append(f"📡 SSID: <code>{result.stdout.strip()}</code>")
        else:
            lines.append("❌ WiFi bagli degil")
    except FileNotFoundError:
        lines.append("⚠️ WiFi bilgisi alinamadi (iwgetid yok)")

    # Internet
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "3", "8.8.8.8"], capture_output=True, text=True, timeout=5
        )
        lines.append(f"🌐 Internet: {'✅ Erisim var' if result.returncode == 0 else '❌ Erisim yok'}")
    except Exception:
        lines.append("⚠️ Internet kontrol edilemedi")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
