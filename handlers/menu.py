import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.commands import authorized
from config import Config

logger = logging.getLogger(__name__)


# ── Klavye Olusturucular ──

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Claude Code", callback_data="menu:claude")],
        [InlineKeyboardButton("📁 Projeler", callback_data="menu:projects")],
        [InlineKeyboardButton("🐳 Docker", callback_data="menu:docker")],
        [InlineKeyboardButton("⚙️ Sistem", callback_data="menu:system")],
        [InlineKeyboardButton("📶 Monitoring", callback_data="menu:monitor")],
        [InlineKeyboardButton("⚡ Kisayollar", callback_data="menu:shortcuts")],
    ])


def back_button(target: str = "menu:ana") -> InlineKeyboardButton:
    return InlineKeyboardButton("◀️ Geri", callback_data=target)


def claude_menu_keyboard() -> InlineKeyboardMarkup:
    from handlers.claude import runner
    status = "🔄 Calisiyor" if runner.is_running else "💤 Bosta"
    mode = Config.CLAUDE_PERMISSIONS

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Soru Sor", callback_data="claude:ask")],
        [InlineKeyboardButton("📝 Gorev Ver", callback_data="claude:task")],
        [InlineKeyboardButton(f"📊 Durum: {status}", callback_data="claude:status")],
        [InlineKeyboardButton("🛑 Gorevi Iptal Et", callback_data="claude:cancel")],
        [
            InlineKeyboardButton(f"🔐 Mod: {mode}", callback_data="claude:mode"),
        ],
        [InlineKeyboardButton("📜 Son Log", callback_data="claude:log")],
        [back_button()],
    ])


def claude_mode_keyboard() -> InlineKeyboardMarkup:
    current = Config.CLAUDE_PERMISSIONS
    modes = [
        ("skip", "⚡ Skip (tam yetki)"),
        ("auto", "🤖 Auto (otomatik)"),
        ("ask", "🙋 Ask (onay iste)"),
    ]
    buttons = []
    for mode_id, label in modes:
        marker = " ✅" if mode_id == current else ""
        buttons.append([InlineKeyboardButton(
            f"{label}{marker}", callback_data=f"claude:setmode:{mode_id}"
        )])
    buttons.append([back_button("menu:claude")])
    return InlineKeyboardMarkup(buttons)


def projects_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📥 Repo Klonla", callback_data="project:clone")],
    ]
    # Mevcut projeleri listele
    workspace = Config.WORKSPACE_DIR
    if os.path.isdir(workspace):
        projects = sorted([
            d for d in os.listdir(workspace)
            if os.path.isdir(os.path.join(workspace, d)) and not d.startswith(".")
        ])
        for p in projects:
            buttons.append([InlineKeyboardButton(
                f"📂 {p}", callback_data=f"project:select:{p}"
            )])
    buttons.append([back_button()])
    return InlineKeyboardMarkup(buttons)


def project_detail_keyboard(name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Claude Gorev Ver", callback_data=f"project:task:{name}")],
        [InlineKeyboardButton("📊 Git Durumu", callback_data=f"project:git:{name}")],
        [InlineKeyboardButton("🗑 Projeyi Sil", callback_data=f"project:delete:{name}")],
        [back_button("menu:projects")],
    ])


def monitoring_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 VPN Durumu", callback_data="monitor:vpn")],
        [InlineKeyboardButton("📶 WiFi Durumu", callback_data="monitor:wifi")],
        [InlineKeyboardButton("🌐 Internet Testi", callback_data="monitor:internet")],
        [back_button()],
    ])


# ── Komut Handler'lari ──

@authorized
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ana menuyu goster."""
    await update.message.reply_text(
        "📋 <b>Ana Menu</b>", parse_mode="HTML", reply_markup=main_menu_keyboard()
    )


# ── Callback Router ──

async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tum inline buton tiklamalarini yonlendir."""
    query = update.callback_query
    chat_id = query.from_user.id

    if not Config.is_authorized(chat_id):
        await query.answer("⛔ Yetkisiz", show_alert=True)
        return

    await query.answer()
    data = query.data

    # ── Ana Menu ──
    if data == "menu:ana":
        await query.edit_message_text(
            "📋 <b>Ana Menu</b>", parse_mode="HTML", reply_markup=main_menu_keyboard()
        )

    # ── Claude Menu ──
    elif data == "menu:claude":
        await query.edit_message_text(
            "🤖 <b>Claude Code</b>", parse_mode="HTML", reply_markup=claude_menu_keyboard()
        )
    elif data == "claude:ask":
        await query.edit_message_text(
            "💬 Sorunuzu yazip gonderin.\n\nOrnek:\n<code>/ask Python'da async nedir?</code>",
            parse_mode="HTML",
        )
    elif data == "claude:task":
        await query.edit_message_text(
            "📝 Gorev vermek icin:\n<code>/task proje-adi gorev aciklamasi</code>\n\n"
            "Ornek:\n<code>/task isp auth modulune test yaz</code>",
            parse_mode="HTML",
        )
    elif data == "claude:status":
        from handlers.claude import runner
        if runner.is_running:
            text = "🔄 Claude calisiyor..."
        elif runner.last_output:
            text = f"✅ Son gorev tamamlandi.\n\n{runner.last_output[:500]}"
        else:
            text = "💤 Aktif gorev yok."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[back_button("menu:claude")]]))
    elif data == "claude:cancel":
        from handlers.claude import runner
        if await runner.cancel():
            await query.edit_message_text("🛑 Gorev iptal edildi.", reply_markup=InlineKeyboardMarkup([[back_button("menu:claude")]]))
        else:
            await query.edit_message_text("💤 Aktif gorev yok.", reply_markup=InlineKeyboardMarkup([[back_button("menu:claude")]]))
    elif data == "claude:mode":
        await query.edit_message_text(
            "🔐 <b>Claude Izin Modu</b>", parse_mode="HTML", reply_markup=claude_mode_keyboard()
        )
    elif data.startswith("claude:setmode:"):
        mode = data.split(":")[-1]
        Config.CLAUDE_PERMISSIONS = mode
        await query.edit_message_text(
            f"✅ Mod degistirildi: <code>{mode}</code>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[back_button("menu:claude")]]),
        )
    elif data == "claude:log":
        from handlers.claude import runner
        last = runner.last_output
        text = last[:4000] if last else "📭 Henuz cikti yok."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[back_button("menu:claude")]]))

    # ── Projeler Menu ──
    elif data == "menu:projects":
        await query.edit_message_text(
            "📁 <b>Projeler</b>", parse_mode="HTML", reply_markup=projects_menu_keyboard()
        )
    elif data == "project:clone":
        await query.edit_message_text(
            "📥 Repo klonlamak icin:\n<code>/project clone https://github.com/user/repo</code>",
            parse_mode="HTML",
        )
    elif data.startswith("project:select:"):
        name = data.split(":", 2)[-1]
        await query.edit_message_text(
            f"📂 <b>{name}</b>", parse_mode="HTML", reply_markup=project_detail_keyboard(name)
        )
    elif data.startswith("project:task:"):
        name = data.split(":", 2)[-1]
        await query.edit_message_text(
            f"📝 <code>/task {name} gorev aciklamasi yazin</code>", parse_mode="HTML",
        )
    elif data.startswith("project:git:"):
        name = data.split(":", 2)[-1]
        import subprocess
        pdir = os.path.join(Config.WORKSPACE_DIR, name)
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-5"], cwd=pdir,
                capture_output=True, text=True, timeout=5,
            )
            branch = subprocess.run(
                ["git", "branch", "--show-current"], cwd=pdir,
                capture_output=True, text=True, timeout=5,
            )
            text = f"📂 <b>{name}</b>\n🌿 Branch: <code>{branch.stdout.strip()}</code>\n\n<pre>{result.stdout.strip()}</pre>"
        except Exception as e:
            text = f"❌ Git bilgisi alinamadi: {e}"
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[back_button(f"project:select:{name}")]]),
        )
    elif data.startswith("project:delete:"):
        name = data.split(":", 2)[-1]
        await query.edit_message_text(
            f"⚠️ <b>{name}</b> silinsin mi?", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Evet, sil", callback_data=f"project:confirm_delete:{name}")],
                [back_button(f"project:select:{name}")],
            ]),
        )
    elif data.startswith("project:confirm_delete:"):
        import shutil
        name = data.split(":", 2)[-1]
        target = os.path.join(Config.WORKSPACE_DIR, name)
        if os.path.isdir(target):
            shutil.rmtree(target)
            await query.edit_message_text(
                f"🗑 <code>{name}</code> silindi.", parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[back_button("menu:projects")]]),
            )
        else:
            await query.edit_message_text(f"❌ Bulunamadi: {name}")

    # ── Docker Menu ──
    elif data == "menu:docker":
        from handlers.docker_ops import docker_menu_keyboard, docker_status_text
        text = await docker_status_text()
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=docker_menu_keyboard())
    elif data.startswith("docker:"):
        from handlers.docker_ops import handle_docker_callback
        await handle_docker_callback(query, data)

    # ── Sistem Menu ──
    elif data == "menu:system":
        from handlers.system_ops import system_menu_keyboard
        await query.edit_message_text(
            "⚙️ <b>Sistem</b>", parse_mode="HTML", reply_markup=system_menu_keyboard()
        )
    elif data.startswith("system:"):
        from handlers.system_ops import handle_system_callback
        await handle_system_callback(query, data, context)

    # ── Monitoring Menu ──
    elif data == "menu:monitor":
        await query.edit_message_text(
            "📶 <b>Monitoring</b>", parse_mode="HTML", reply_markup=monitoring_menu_keyboard()
        )
    elif data.startswith("monitor:"):
        from handlers.monitoring import handle_monitor_callback
        await handle_monitor_callback(query, data)

    # ── Kisayollar Menu ──
    elif data == "menu:shortcuts":
        from services.shortcuts import ShortcutManager
        sm = ShortcutManager()
        await query.edit_message_text(
            "⚡ <b>Kisayollar</b>", parse_mode="HTML", reply_markup=sm.menu_keyboard()
        )
    elif data.startswith("shortcut:"):
        from services.shortcuts import ShortcutManager
        sm = ShortcutManager()
        await sm.handle_callback(query, data, context)
