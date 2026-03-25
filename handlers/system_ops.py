import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ContextTypes
from handlers.commands import authorized
from handlers.menu import back_button
from config import Config

logger = logging.getLogger(__name__)

# Tehlikeli komut kaliplari
DANGEROUS_PATTERNS = ["rm -rf", "mkfs", "dd if=", "reboot", "shutdown", "poweroff", "halt", "> /dev/"]
# Exec modu icin context key
EXEC_WAITING_KEY = "waiting_exec"


async def _run(cmd: str, timeout: int = 30) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode, stdout.decode("utf-8", errors="replace").strip()
    except asyncio.TimeoutError:
        proc.kill()
        return -1, f"Zaman asimi ({timeout}s)"


def system_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Sistem Durumu", callback_data="system:status")],
        [InlineKeyboardButton("🔧 Servisler", callback_data="system:services")],
        [InlineKeyboardButton("📋 Processler", callback_data="system:processes")],
        [InlineKeyboardButton("💻 Komut Calistir", callback_data="system:exec")],
        [back_button()],
    ])


async def handle_system_callback(query: CallbackQuery, data: str, context: ContextTypes.DEFAULT_TYPE):
    """Sistem callback'lerini isle."""

    if data == "system:status":
        lines = ["📊 <b>Sistem Durumu</b>\n"]

        code, output = await _run("uptime 2>/dev/null")
        if code == 0:
            lines.append(f"⏱ {output}")

        code, output = await _run("df -h / 2>/dev/null")
        if code == 0:
            disk_line = output.split("\n")[-1].split()
            if len(disk_line) >= 5:
                lines.append(f"💾 Disk: {disk_line[2]}/{disk_line[1]} ({disk_line[4]})")

        code, output = await _run("free -h 2>/dev/null")
        if code == 0:
            mem = output.split("\n")
            if len(mem) > 1:
                parts = mem[1].split()
                if len(parts) >= 3:
                    lines.append(f"🧠 RAM: {parts[2]}/{parts[1]}")

        code, output = await _run("nproc 2>/dev/null")
        if code == 0:
            lines.append(f"🔲 CPU cores: {output}")

        code, output = await _run("cat /proc/loadavg 2>/dev/null")
        if code == 0:
            lines.append(f"📈 Load: {output.split()[0:3]}")

        await query.edit_message_text(
            "\n".join(lines), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Yenile", callback_data="system:status")],
                [back_button("menu:system")],
            ]),
        )

    elif data == "system:services":
        code, output = await _run(
            "systemctl list-units --type=service --state=running --no-pager --no-legend 2>/dev/null | head -20"
        )
        if code != 0 or not output:
            # macOS icin
            code, output = await _run("launchctl list 2>/dev/null | head -20")

        buttons = []
        if code == 0 and output:
            services = []
            for line in output.split("\n")[:15]:
                parts = line.split()
                if parts:
                    svc = parts[0].replace(".service", "")
                    services.append(svc)
                    buttons.append([InlineKeyboardButton(
                        f"🔧 {svc}", callback_data=f"system:svc:{svc}"
                    )])

        text = f"🔧 <b>Calisan Servisler</b> ({len(buttons)})\nBirini sec:"
        buttons.append([back_button("menu:system")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("system:svc:"):
        svc = data.split(":", 2)[-1]
        code, output = await _run(f"systemctl status {svc} --no-pager 2>/dev/null | head -15")
        text = f"🔧 <b>{svc}</b>\n\n<pre>{output[:3000] if output else 'Bilgi yok'}</pre>"
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Restart", callback_data=f"system:svc_restart:{svc}"),
                    InlineKeyboardButton("⏹ Stop", callback_data=f"system:svc_stop:{svc}"),
                ],
                [back_button("system:services")],
            ]),
        )

    elif data.startswith("system:svc_restart:"):
        svc = data.split(":", 2)[-1]
        code, output = await _run(f"sudo systemctl restart {svc} 2>&1")
        icon = "✅" if code == 0 else "❌"
        await query.edit_message_text(
            f"{icon} <code>systemctl restart {svc}</code>\n{output}", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[back_button(f"system:svc:{svc}")]]),
        )

    elif data.startswith("system:svc_stop:"):
        svc = data.split(":", 2)[-1]
        code, output = await _run(f"sudo systemctl stop {svc} 2>&1")
        icon = "✅" if code == 0 else "❌"
        await query.edit_message_text(
            f"{icon} <code>systemctl stop {svc}</code>\n{output}", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[back_button("system:services")]]),
        )

    elif data == "system:processes":
        code, output = await _run("ps aux --sort=-%mem 2>/dev/null | head -15")
        if code != 0:
            code, output = await _run("ps aux | head -15")
        text = output[:4000] if output else "Bilgi yok"
        await query.edit_message_text(
            f"📋 <b>Processler (RAM sirali)</b>\n\n<pre>{text}</pre>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Yenile", callback_data="system:processes")],
                [back_button("menu:system")],
            ]),
        )

    elif data == "system:exec":
        context.user_data[EXEC_WAITING_KEY] = True
        await query.edit_message_text(
            "💻 <b>Komut Calistir</b>\n\n"
            "Calistirmak istedigin komutu yaz ve gonder.\n"
            "Veya: <code>/exec ls -la /workspace</code>\n\n"
            "Iptal icin /cancel yaz.",
            parse_mode="HTML",
        )

    elif data.startswith("system:confirm_exec:"):
        cmd = context.user_data.get("pending_exec", "")
        if cmd:
            await query.edit_message_text(f"⏳ Calistiriliyor: <code>{cmd}</code>", parse_mode="HTML")
            code, output = await _run(cmd, timeout=30)
            icon = "✅" if code == 0 else "❌"
            text = output[:4000] if output else "(Bos cikti)"
            await query.edit_message_text(
                f"{icon} <code>{cmd}</code>\n\n<pre>{text}</pre>", parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[back_button("menu:system")]]),
            )
            context.user_data.pop("pending_exec", None)

    elif data == "system:cancel_exec":
        context.user_data.pop("pending_exec", None)
        context.user_data.pop(EXEC_WAITING_KEY, None)
        await query.edit_message_text(
            "❌ Iptal edildi.", reply_markup=InlineKeyboardMarkup([[back_button("menu:system")]])
        )


@authorized
async def exec_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/exec <komut> - Serbest komut calistir."""
    if not context.args:
        await update.message.reply_text(
            "Kullanim: <code>/exec komut</code>\nOrnek: <code>/exec docker ps</code>",
            parse_mode="HTML",
        )
        return

    cmd = " ".join(context.args)

    # Tehlikeli komut kontrolu
    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd.lower():
            await update.message.reply_text(
                f"⚠️ Tehlikeli komut tespit edildi!\n<code>{cmd}</code>\n\nEmin misin?",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Evet, calistir", callback_data="system:confirm_exec:1")],
                    [InlineKeyboardButton("❌ Iptal", callback_data="system:cancel_exec")],
                ]),
            )
            context.user_data["pending_exec"] = cmd
            return

    await update.message.reply_text(f"⏳ <code>{cmd}</code>", parse_mode="HTML")
    code, output = await _run(cmd, timeout=30)
    icon = "✅" if code == 0 else "❌"
    text = output[:4000] if output else "(Bos cikti)"
    await update.message.reply_text(f"{icon}\n<pre>{text}</pre>", parse_mode="HTML")


async def handle_exec_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Exec modu aktifken gelen text mesajlarini isle. True donerse islendi demek."""
    if not context.user_data.get(EXEC_WAITING_KEY):
        return False

    if not Config.is_authorized(update.effective_chat.id):
        return False

    cmd = update.message.text.strip()
    context.user_data.pop(EXEC_WAITING_KEY, None)

    if cmd.lower() in ("/cancel", "iptal"):
        await update.message.reply_text("❌ Iptal edildi.")
        return True

    # Tehlikeli komut kontrolu
    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd.lower():
            context.user_data["pending_exec"] = cmd
            await update.message.reply_text(
                f"⚠️ Tehlikeli komut!\n<code>{cmd}</code>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Calistir", callback_data="system:confirm_exec:1")],
                    [InlineKeyboardButton("❌ Iptal", callback_data="system:cancel_exec")],
                ]),
            )
            return True

    await update.message.reply_text(f"⏳ <code>{cmd}</code>", parse_mode="HTML")
    code, output = await _run(cmd, timeout=30)
    icon = "✅" if code == 0 else "❌"
    text = output[:4000] if output else "(Bos cikti)"
    await update.message.reply_text(f"{icon}\n<pre>{text}</pre>", parse_mode="HTML")
    return True
