import asyncio
import json
import logging
import time
from typing import Callable, Awaitable

from config import Config

logger = logging.getLogger(__name__)

# Tool isimlerini Turkceye cevir
TOOL_NAMES_TR = {
    "Write": "📝 Dosya yaziliyor",
    "Edit": "✏️ Dosya duzenleniyor",
    "Read": "📖 Dosya okunuyor",
    "Bash": "⚡ Komut calistiriliyor",
    "Glob": "🔍 Dosya araniyor",
    "Grep": "🔎 Icerik araniyor",
    "Agent": "🤖 Alt agent baslatiliyor",
    "TodoWrite": "📋 Gorev listesi",
    "WebSearch": "🌐 Web araniyor",
    "WebFetch": "🌐 Web okunuyor",
}


class ClaudeRunner:
    """Claude Code CLI'yi subprocess olarak calistirir ve ciktiyi stream eder."""

    def __init__(self):
        self._active_process: asyncio.subprocess.Process | None = None
        self._is_running = False
        self._last_output: str = ""
        self._cancel_requested = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def last_output(self) -> str:
        return self._last_output

    async def run(
        self,
        prompt: str,
        project_dir: str | None = None,
        stream_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """Claude Code'u calistir, sonucu dondur.

        Args:
            prompt: Claude'a gonderilecek komut
            project_dir: Calisma dizini (None ise workspace root)
            stream_callback: Her anlamli event icin cagirilacak async fonksiyon
        """
        if self._is_running:
            raise RuntimeError("Zaten bir Claude gorevi calisiyor. /task cancel ile iptal et.")

        self._is_running = True
        self._cancel_requested = False
        self._last_output = ""
        cwd = project_dir or Config.WORKSPACE_DIR

        # Komut olustur
        cmd = ["claude", "-p", prompt, "--output-format", "stream-json"]

        if Config.CLAUDE_PERMISSIONS == "skip":
            cmd.append("--dangerously-skip-permissions")

        if Config.CLAUDE_MODEL:
            cmd.extend(["--model", Config.CLAUDE_MODEL])

        cmd.extend(["--max-turns", str(Config.CLAUDE_MAX_TURNS)])

        env = {
            "ANTHROPIC_API_KEY": Config.ANTHROPIC_API_KEY,
            "HOME": "/root",
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        }

        logger.info(f"Claude baslatiliyor: cwd={cwd}, prompt={prompt[:80]}...")

        try:
            self._active_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            final_result = ""
            last_stream_time = 0
            min_stream_interval = 2.0  # Telegram rate limit korunmasi

            async for line in self._active_process.stdout:
                if self._cancel_requested:
                    self._active_process.terminate()
                    break

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                try:
                    event = json.loads(line_str)
                except json.JSONDecodeError:
                    continue

                msg = self._parse_event(event)

                # Son sonucu kaydet
                if event.get("type") == "result":
                    result_text = ""
                    for block in event.get("result", {}).get("content", []):
                        if block.get("type") == "text":
                            result_text += block.get("text", "")
                    final_result = result_text

                # Stream callback
                if msg and stream_callback:
                    now = time.time()
                    if now - last_stream_time >= min_stream_interval:
                        try:
                            await stream_callback(msg)
                            last_stream_time = now
                        except Exception as e:
                            logger.error(f"Stream callback hatasi: {e}")

            await self._active_process.wait()

            # Stderr kontrol
            stderr = await self._active_process.stderr.read()
            if stderr and self._active_process.returncode != 0:
                err_msg = stderr.decode("utf-8").strip()
                logger.error(f"Claude stderr: {err_msg}")
                if stream_callback:
                    await stream_callback(f"❌ Hata: {err_msg[:200]}")

            self._last_output = final_result or "(Sonuc alinamadi)"
            return self._last_output

        except Exception as e:
            logger.error(f"Claude calistirma hatasi: {e}")
            self._last_output = f"Hata: {e}"
            raise
        finally:
            self._is_running = False
            self._active_process = None

    async def cancel(self) -> bool:
        """Calisan gorevi iptal et."""
        if not self._is_running or not self._active_process:
            return False
        self._cancel_requested = True
        try:
            self._active_process.terminate()
            await asyncio.wait_for(self._active_process.wait(), timeout=5)
        except asyncio.TimeoutError:
            self._active_process.kill()
        return True

    def _parse_event(self, event: dict) -> str | None:
        """Claude stream event'ini Turkce mesaja cevir."""
        event_type = event.get("type", "")

        if event_type == "assistant":
            # Claude'un text mesaji
            content = event.get("message", {}).get("content", [])
            for block in content:
                if block.get("type") == "text":
                    text = block.get("text", "").strip()
                    if text and len(text) > 10:
                        # Uzun mesajlari kisalt
                        return f"💬 {text[:300]}{'...' if len(text) > 300 else ''}"

        elif event_type == "content_block_start":
            block = event.get("content_block", {})
            if block.get("type") == "tool_use":
                tool_name = block.get("name", "?")
                tr_name = TOOL_NAMES_TR.get(tool_name, f"🔧 {tool_name}")
                return tr_name

        elif event_type == "result":
            cost = event.get("cost_usd")
            duration = event.get("duration_ms")
            turns = event.get("num_turns")
            parts = ["✅ <b>Tamamlandi</b>"]
            if turns:
                parts.append(f"({turns} adim)")
            if duration:
                secs = duration / 1000
                parts.append(f"{secs:.1f}s")
            if cost:
                parts.append(f"${cost:.4f}")
            return " | ".join(parts)

        elif event_type == "error":
            error = event.get("error", {})
            msg = error.get("message", str(error))
            return f"❌ {msg[:200]}"

        return None
