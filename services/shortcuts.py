import asyncio
import json
import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ContextTypes
from handlers.menu import back_button

logger = logging.getLogger(__name__)

from config import Config
SHORTCUTS_FILE = Config.SHORTCUTS_FILE

# Conversation state key
SHORTCUT_ADD_STATE = "shortcut_add_state"


class ShortcutManager:
    """Kullanici tanimli kisayol yonetimi."""

    def _load(self) -> dict:
        if os.path.isfile(SHORTCUTS_FILE):
            try:
                with open(SHORTCUTS_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save(self, data: dict):
        with open(SHORTCUTS_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def menu_keyboard(self) -> InlineKeyboardMarkup:
        shortcuts = self._load()
        buttons = []

        for key, sc in shortcuts.items():
            name = sc.get("name", key)
            buttons.append([InlineKeyboardButton(
                f"⚡ {name}", callback_data=f"shortcut:run:{key}"
            )])

        buttons.append([InlineKeyboardButton("➕ Kisayol Ekle", callback_data="shortcut:add")])
        if shortcuts:
            buttons.append([InlineKeyboardButton("🗑 Kisayol Sil", callback_data="shortcut:delete_menu")])
        buttons.append([back_button()])
        return InlineKeyboardMarkup(buttons)

    async def handle_callback(self, query: CallbackQuery, data: str, context: ContextTypes.DEFAULT_TYPE):
        """Kisayol callback'lerini isle."""

        if data.startswith("shortcut:run:"):
            key = data.split(":", 2)[-1]
            shortcuts = self._load()
            sc = shortcuts.get(key)
            if not sc:
                await query.edit_message_text("❌ Kisayol bulunamadi.")
                return

            cmd = sc.get("command", "")
            name = sc.get("name", key)
            await query.edit_message_text(f"⏳ <b>{name}</b> calistiriliyor...\n<code>{cmd}</code>", parse_mode="HTML")

            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
                output = stdout.decode("utf-8", errors="replace").strip()
                code = proc.returncode
            except asyncio.TimeoutError:
                proc.kill()
                output = "Zaman asimi (60s)"
                code = -1

            icon = "✅" if code == 0 else "❌"
            text = output[:4000] if output else "(Bos cikti)"
            await query.edit_message_text(
                f"{icon} <b>{name}</b>\n\n<pre>{text}</pre>", parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Tekrar Calistir", callback_data=f"shortcut:run:{key}")],
                    [back_button("menu:shortcuts")],
                ]),
            )

        elif data == "shortcut:add":
            context.user_data[SHORTCUT_ADD_STATE] = "name"
            await query.edit_message_text(
                "➕ <b>Yeni Kisayol</b>\n\n"
                "1️⃣ Kisayol adini yazin (ornek: deploy-isp)\n\n"
                "Iptal icin /cancel",
                parse_mode="HTML",
            )

        elif data == "shortcut:delete_menu":
            shortcuts = self._load()
            buttons = []
            for key, sc in shortcuts.items():
                name = sc.get("name", key)
                buttons.append([InlineKeyboardButton(
                    f"🗑 {name}", callback_data=f"shortcut:delete:{key}"
                )])
            buttons.append([back_button("menu:shortcuts")])
            await query.edit_message_text(
                "🗑 <b>Silinecek kisayolu sec:</b>", parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )

        elif data.startswith("shortcut:delete:"):
            key = data.split(":", 2)[-1]
            shortcuts = self._load()
            name = shortcuts.get(key, {}).get("name", key)
            if key in shortcuts:
                del shortcuts[key]
                self._save(shortcuts)
                await query.edit_message_text(
                    f"🗑 <b>{name}</b> silindi.", parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[back_button("menu:shortcuts")]]),
                )
            else:
                await query.edit_message_text("❌ Kisayol bulunamadi.")

    async def handle_text(self, update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Kisayol ekleme akisindaki text mesajlarini isle."""
        state = context.user_data.get(SHORTCUT_ADD_STATE)
        if not state:
            return False

        text = update.message.text.strip()

        if text.lower() in ("/cancel", "iptal"):
            context.user_data.pop(SHORTCUT_ADD_STATE, None)
            context.user_data.pop("shortcut_new", None)
            await update.message.reply_text("❌ Kisayol ekleme iptal edildi.")
            return True

        if state == "name":
            # Slug olustur
            slug = text.lower().replace(" ", "-")
            context.user_data["shortcut_new"] = {"name": text, "slug": slug}
            context.user_data[SHORTCUT_ADD_STATE] = "command"
            await update.message.reply_text(
                f"✅ Ad: <b>{text}</b>\n\n"
                "2️⃣ Simdi komutu yazin:\n"
                "Ornek: <code>docker compose -f /workspace/isp/docker-compose.yml up -d</code>",
                parse_mode="HTML",
            )
            return True

        elif state == "command":
            context.user_data["shortcut_new"]["command"] = text
            context.user_data[SHORTCUT_ADD_STATE] = "description"
            await update.message.reply_text(
                f"✅ Komut: <code>{text}</code>\n\n"
                "3️⃣ Kisa bir aciklama yazin:\n"
                "Ornek: ISP projesini deploy et",
                parse_mode="HTML",
            )
            return True

        elif state == "description":
            new_sc = context.user_data.get("shortcut_new", {})
            new_sc["description"] = text

            shortcuts = self._load()
            slug = new_sc.get("slug", "shortcut")
            shortcuts[slug] = {
                "name": new_sc.get("name", slug),
                "command": new_sc.get("command", ""),
                "description": text,
            }
            self._save(shortcuts)

            context.user_data.pop(SHORTCUT_ADD_STATE, None)
            context.user_data.pop("shortcut_new", None)

            await update.message.reply_text(
                f"✅ Kisayol eklendi!\n\n"
                f"📌 <b>{new_sc.get('name')}</b>\n"
                f"💻 <code>{new_sc.get('command')}</code>\n"
                f"📝 {text}\n\n"
                "/menu ile menuye donebilirsin.",
                parse_mode="HTML",
            )
            return True

        return False
