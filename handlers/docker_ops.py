import asyncio
import json
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from handlers.menu import back_button

logger = logging.getLogger(__name__)


async def _run(cmd: str, timeout: int = 15) -> tuple[int, str]:
    """Shell komutu calistir, (returncode, output) dondur."""
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode, stdout.decode("utf-8", errors="replace").strip()
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "Zaman asimi"


async def docker_status_text() -> str:
    """Docker ozet durumu."""
    code, output = await _run("docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null")
    if code != 0:
        return "🐳 <b>Docker</b>\n\n❌ Docker erisilemedi"

    lines = ["🐳 <b>Docker Container'lar</b>\n"]
    if not output:
        lines.append("📭 Calisan container yok")
    else:
        for row in output.split("\n"):
            parts = row.split("\t")
            if len(parts) >= 2:
                name, status = parts[0], parts[1]
                icon = "🟢" if "Up" in status else "🔴"
                lines.append(f"{icon} <code>{name}</code> - {status}")
    return "\n".join(lines)


def docker_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📋 Container Listesi", callback_data="docker:list")],
        [
            InlineKeyboardButton("▶️ Compose Up", callback_data="docker:compose:up"),
            InlineKeyboardButton("⏹ Compose Down", callback_data="docker:compose:down"),
        ],
        [InlineKeyboardButton("📊 Kaynak Kullanimi", callback_data="docker:stats")],
        [back_button()],
    ]
    return InlineKeyboardMarkup(buttons)


async def _container_list_keyboard() -> InlineKeyboardMarkup:
    """Calisan container'lari buton olarak listele."""
    code, output = await _run("docker ps -a --format '{{.Names}}\t{{.State}}' 2>/dev/null")
    buttons = []
    if code == 0 and output:
        for row in output.split("\n"):
            parts = row.split("\t")
            if len(parts) >= 2:
                name, state = parts[0], parts[1]
                icon = "🟢" if state == "running" else "🔴"
                buttons.append([InlineKeyboardButton(
                    f"{icon} {name}", callback_data=f"docker:detail:{name}"
                )])
    buttons.append([back_button("menu:docker")])
    return InlineKeyboardMarkup(buttons)


def _container_detail_keyboard(name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("▶️ Start", callback_data=f"docker:start:{name}"),
            InlineKeyboardButton("⏹ Stop", callback_data=f"docker:stop:{name}"),
        ],
        [
            InlineKeyboardButton("🔄 Restart", callback_data=f"docker:restart:{name}"),
            InlineKeyboardButton("📜 Logs", callback_data=f"docker:logs:{name}"),
        ],
        [InlineKeyboardButton("🔍 Inspect", callback_data=f"docker:inspect:{name}")],
        [back_button("docker:list")],
    ])


async def handle_docker_callback(query: CallbackQuery, data: str):
    """Docker callback'lerini isle."""

    if data == "docker:list":
        kb = await _container_list_keyboard()
        await query.edit_message_text(
            "🐳 <b>Container'lar</b>\nBirini sec:", parse_mode="HTML", reply_markup=kb
        )

    elif data.startswith("docker:detail:"):
        name = data.split(":", 2)[-1]
        code, output = await _run(f"docker inspect --format '{{{{.State.Status}}}} | {{{{.Config.Image}}}} | {{{{.State.StartedAt}}}}' {name}")
        text = f"🐳 <b>{name}</b>\n\n"
        if code == 0:
            text += f"<pre>{output}</pre>"
        else:
            text += "Bilgi alinamadi"
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=_container_detail_keyboard(name))

    elif data.startswith("docker:start:"):
        name = data.split(":", 2)[-1]
        code, output = await _run(f"docker start {name}")
        icon = "✅" if code == 0 else "❌"
        await query.edit_message_text(
            f"{icon} <code>docker start {name}</code>\n{output}", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[back_button(f"docker:detail:{name}")]]),
        )

    elif data.startswith("docker:stop:"):
        name = data.split(":", 2)[-1]
        code, output = await _run(f"docker stop {name}", timeout=30)
        icon = "✅" if code == 0 else "❌"
        await query.edit_message_text(
            f"{icon} <code>docker stop {name}</code>\n{output}", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[back_button(f"docker:detail:{name}")]]),
        )

    elif data.startswith("docker:restart:"):
        name = data.split(":", 2)[-1]
        code, output = await _run(f"docker restart {name}", timeout=30)
        icon = "✅" if code == 0 else "❌"
        await query.edit_message_text(
            f"{icon} <code>docker restart {name}</code>\n{output}", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[back_button(f"docker:detail:{name}")]]),
        )

    elif data.startswith("docker:logs:"):
        name = data.split(":", 2)[-1]
        code, output = await _run(f"docker logs --tail 30 {name} 2>&1")
        text = output[:4000] if output else "(Bos log)"
        await query.edit_message_text(
            f"📜 <b>{name} logs</b>\n\n<pre>{text}</pre>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Yenile", callback_data=f"docker:logs:{name}")],
                [back_button(f"docker:detail:{name}")],
            ]),
        )

    elif data.startswith("docker:inspect:"):
        name = data.split(":", 2)[-1]
        code, output = await _run(
            f"docker inspect --format 'Image: {{{{.Config.Image}}}}\nStatus: {{{{.State.Status}}}}\nPorts: {{{{.NetworkSettings.Ports}}}}\nCreated: {{{{.Created}}}}' {name}"
        )
        text = output[:4000] if output else "Bilgi yok"
        await query.edit_message_text(
            f"🔍 <b>{name}</b>\n\n<pre>{text}</pre>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[back_button(f"docker:detail:{name}")]]),
        )

    elif data == "docker:compose:up":
        await query.edit_message_text("⏳ <code>docker compose up -d</code> calistiriliyor...", parse_mode="HTML")
        code, output = await _run("docker compose up -d 2>&1", timeout=120)
        icon = "✅" if code == 0 else "❌"
        text = output[:4000] if output else "Cikti yok"
        await query.edit_message_text(
            f"{icon} <b>Compose Up</b>\n\n<pre>{text}</pre>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[back_button("menu:docker")]]),
        )

    elif data == "docker:compose:down":
        await query.edit_message_text("⏳ <code>docker compose down</code> calistiriliyor...", parse_mode="HTML")
        code, output = await _run("docker compose down 2>&1", timeout=60)
        icon = "✅" if code == 0 else "❌"
        text = output[:4000] if output else "Cikti yok"
        await query.edit_message_text(
            f"{icon} <b>Compose Down</b>\n\n<pre>{text}</pre>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[back_button("menu:docker")]]),
        )

    elif data == "docker:stats":
        code, output = await _run("docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' 2>/dev/null")
        text = output[:4000] if output else "Bilgi yok"
        await query.edit_message_text(
            f"📊 <b>Kaynak Kullanimi</b>\n\n<pre>{text}</pre>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Yenile", callback_data="docker:stats")],
                [back_button("menu:docker")],
            ]),
        )
