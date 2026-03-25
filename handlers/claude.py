import os
import shutil
import asyncio
import logging
import subprocess
from telegram import Update
from telegram.ext import ContextTypes
from handlers.commands import authorized
from services.claude_runner import ClaudeRunner
from config import Config

logger = logging.getLogger(__name__)

# Tek bir global runner instance (ayni anda tek gorev)
runner = ClaudeRunner()


@authorized
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Claude'a direkt soru sor."""
    if not context.args:
        await update.message.reply_text(
            "Kullanim: /ask &lt;soru&gt;\nOrnek: /ask Python'da list comprehension nedir?",
            parse_mode="HTML",
        )
        return

    prompt = " ".join(context.args)
    await update.message.reply_text(f"🤖 Claude'a soruluyor...\n\n<i>{prompt[:200]}</i>", parse_mode="HTML")

    async def stream_cb(msg: str):
        await update.message.reply_text(msg, parse_mode="HTML")

    try:
        result = await runner.run(prompt, stream_callback=stream_cb)
        # Sonucu gonder (uzunsa parcala)
        if result:
            for i in range(0, len(result), 4000):
                chunk = result[i:i + 4000]
                await update.message.reply_text(chunk)
    except RuntimeError as e:
        await update.message.reply_text(f"⚠️ {e}")
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")


@authorized
async def task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bir projede Claude'a gorev ver."""
    if not context.args:
        await update.message.reply_text(
            "Kullanim:\n"
            "/task &lt;proje&gt; &lt;gorev&gt; - Gorev ver\n"
            "/task status - Aktif gorev durumu\n"
            "/task cancel - Gorevi iptal et\n\n"
            "Ornek: /task isp auth modulune unit test yaz",
            parse_mode="HTML",
        )
        return

    subcmd = context.args[0].lower()

    # /task status
    if subcmd == "status":
        if runner.is_running:
            await update.message.reply_text("🔄 Claude calisiyor...")
        else:
            last = runner.last_output
            if last:
                text = f"✅ Son gorev tamamlandi.\n\nSon cikti:\n{last[:500]}"
            else:
                text = "💤 Aktif gorev yok."
            await update.message.reply_text(text)
        return

    # /task cancel
    if subcmd == "cancel":
        if await runner.cancel():
            await update.message.reply_text("🛑 Gorev iptal edildi.")
        else:
            await update.message.reply_text("💤 Aktif gorev yok.")
        return

    # /task <proje> <gorev...>
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Proje adi ve gorev belirtmelisin.\nOrnek: /task isp bug fix yap")
        return

    project_name = context.args[0]
    task_prompt = " ".join(context.args[1:])
    project_dir = os.path.join(Config.WORKSPACE_DIR, project_name)

    if not os.path.isdir(project_dir):
        projects = _list_projects()
        text = f"❌ Proje bulunamadi: {project_name}"
        if projects:
            text += f"\n\nMevcut projeler: {', '.join(projects)}"
        text += "\n\n/project clone ile yeni proje ekleyebilirsin."
        await update.message.reply_text(text)
        return

    await update.message.reply_text(
        f"🚀 Claude baslatiliyor...\n"
        f"📁 Proje: <code>{project_name}</code>\n"
        f"📝 Gorev: <i>{task_prompt[:200]}</i>",
        parse_mode="HTML",
    )

    async def stream_cb(msg: str):
        await update.message.reply_text(msg, parse_mode="HTML")

    try:
        result = await runner.run(task_prompt, project_dir=project_dir, stream_callback=stream_cb)
        if result:
            for i in range(0, len(result), 4000):
                await update.message.reply_text(result[i:i + 4000])
    except RuntimeError as e:
        await update.message.reply_text(f"⚠️ {e}")
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")


@authorized
async def project_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proje yonetimi: clone, list, delete."""
    if not context.args:
        await update.message.reply_text(
            "Kullanim:\n"
            "/project clone &lt;git-url&gt; - Repo klonla\n"
            "/project list - Projeleri listele\n"
            "/project delete &lt;ad&gt; - Projeyi sil",
            parse_mode="HTML",
        )
        return

    subcmd = context.args[0].lower()

    if subcmd == "clone":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ Git URL belirt.\nOrnek: /project clone https://github.com/user/repo")
            return

        url = context.args[1]
        # Repo adini URL'den cikar
        repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
        target = os.path.join(Config.WORKSPACE_DIR, repo_name)

        if os.path.isdir(target):
            await update.message.reply_text(f"⚠️ <code>{repo_name}</code> zaten mevcut.", parse_mode="HTML")
            return

        await update.message.reply_text(f"📥 Klonlaniyor: <code>{repo_name}</code>...", parse_mode="HTML")

        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "clone", "--depth", "1", url, target,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

            if proc.returncode == 0:
                await update.message.reply_text(
                    f"✅ <code>{repo_name}</code> klonlandi!\n\n"
                    f"Kullanim: /task {repo_name} &lt;gorev&gt;",
                    parse_mode="HTML",
                )
            else:
                err = stderr.decode()[:200] if stderr else "Bilinmeyen hata"
                await update.message.reply_text(f"❌ Clone basarisiz: {err}")
        except asyncio.TimeoutError:
            await update.message.reply_text("❌ Clone zaman asimina ugradi (120s)")
        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {e}")

    elif subcmd == "list":
        projects = _list_projects()
        if projects:
            lines = [f"📁 <b>Projeler</b> ({len(projects)})\n"]
            for p in projects:
                pdir = os.path.join(Config.WORKSPACE_DIR, p)
                # Git bilgisi
                branch = _get_git_branch(pdir)
                info = f"  <code>{p}</code>"
                if branch:
                    info += f" ({branch})"
                lines.append(info)
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        else:
            await update.message.reply_text("📁 Henuz proje yok.\n/project clone ile ekle.")

    elif subcmd == "delete":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ Proje adi belirt.")
            return
        name = context.args[1]
        target = os.path.join(Config.WORKSPACE_DIR, name)
        if os.path.isdir(target):
            shutil.rmtree(target)
            await update.message.reply_text(f"🗑 <code>{name}</code> silindi.", parse_mode="HTML")
        else:
            await update.message.reply_text(f"❌ Proje bulunamadi: {name}")

    else:
        await update.message.reply_text("⚠️ Bilinmeyen alt komut. /project yaz.")


@authorized
async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Claude izin modunu degistir."""
    valid_modes = ["skip", "auto", "ask"]
    if not context.args or context.args[0].lower() not in valid_modes:
        current = Config.CLAUDE_PERMISSIONS
        await update.message.reply_text(
            f"Mevcut mod: <code>{current}</code>\n\n"
            f"Kullanim: /mode &lt;{'|'.join(valid_modes)}&gt;\n\n"
            "<b>skip</b> - Tum izinleri atla (Docker icin guvenli)\n"
            "<b>auto</b> - Otomatik kabul (guvenli islemler)\n"
            "<b>ask</b> - Her islem icin sor",
            parse_mode="HTML",
        )
        return

    new_mode = context.args[0].lower()
    Config.CLAUDE_PERMISSIONS = new_mode
    await update.message.reply_text(f"✅ Claude modu: <code>{new_mode}</code>", parse_mode="HTML")


@authorized
async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Son Claude ciktisini goster."""
    last = runner.last_output
    if last:
        for i in range(0, len(last), 4000):
            await update.message.reply_text(last[i:i + 4000])
    else:
        await update.message.reply_text("📭 Henuz Claude ciktisi yok.")


def _list_projects() -> list[str]:
    workspace = Config.WORKSPACE_DIR
    if not os.path.isdir(workspace):
        return []
    return sorted([
        d for d in os.listdir(workspace)
        if os.path.isdir(os.path.join(workspace, d)) and not d.startswith(".")
    ])


def _get_git_branch(path: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=path, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None
