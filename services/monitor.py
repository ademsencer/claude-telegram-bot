import asyncio
import logging
from services.notifier import Notifier
from config import Config

logger = logging.getLogger(__name__)


class SystemMonitor:
    """VPN ve WiFi durumunu izleyen arka plan servisi."""

    def __init__(self, notifier: Notifier):
        self.notifier = notifier
        self._vpn_was_up: bool | None = None
        self._wifi_was_up: bool | None = None
        self._internet_was_up: bool | None = None
        self._vpn_fail_count = 0
        self._wifi_fail_count = 0
        self._internet_fail_count = 0
        self.FAIL_THRESHOLD = 3

    async def start(self):
        logger.info("Sistem monitoring baslatildi")
        await asyncio.gather(
            self._vpn_monitor_loop(),
            self._wifi_monitor_loop(),
        )

    async def _vpn_monitor_loop(self):
        while True:
            try:
                is_up = await self._check_vpn()
                await self._handle_state_change(
                    "VPN", is_up, self._vpn_was_up, self._vpn_fail_count
                )
                self._vpn_fail_count = 0 if is_up else self._vpn_fail_count + 1
                self._vpn_was_up = is_up
            except Exception as e:
                logger.error(f"VPN monitor hatasi: {e}")
            await asyncio.sleep(Config.VPN_CHECK_INTERVAL)

    async def _wifi_monitor_loop(self):
        while True:
            try:
                wifi_up = await self._check_wifi()
                internet_up = await self._check_internet()

                await self._handle_state_change(
                    "WiFi", wifi_up, self._wifi_was_up, self._wifi_fail_count
                )
                await self._handle_state_change(
                    "Internet", internet_up, self._internet_was_up, self._internet_fail_count
                )

                self._wifi_fail_count = 0 if wifi_up else self._wifi_fail_count + 1
                self._internet_fail_count = 0 if internet_up else self._internet_fail_count + 1
                self._wifi_was_up = wifi_up
                self._internet_was_up = internet_up
            except Exception as e:
                logger.error(f"WiFi monitor hatasi: {e}")
            await asyncio.sleep(Config.WIFI_CHECK_INTERVAL)

    async def _handle_state_change(
        self, name: str, is_up: bool, was_up: bool | None, fail_count: int
    ):
        if was_up is None:
            return
        if was_up and not is_up and fail_count >= self.FAIL_THRESHOLD - 1:
            await self.notifier.send(f"🔴 <b>{name} koptu!</b>")
            logger.warning(f"{name} baglantisi kesildi")
        if not was_up and is_up:
            await self.notifier.send(f"🟢 <b>{name} geri geldi!</b>")
            logger.info(f"{name} baglantisi yeniden kuruldu")

    async def _check_vpn(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", "1", "-W", "3", Config.VPN_ENDPOINT,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except Exception:
            return False

    async def _check_wifi(self) -> bool:
        gateway = await self._get_gateway()
        if not gateway:
            return False
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", "1", "-W", "3", gateway,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except Exception:
            return False

    async def _check_internet(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", "1", "-W", "3", "8.8.8.8",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except Exception:
            return False

    async def _get_gateway(self) -> str | None:
        try:
            proc = await asyncio.create_subprocess_exec(
                "ip", "route", "show", "default",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode()
            if "via" in output:
                return output.split("via")[1].split()[0]
        except FileNotFoundError:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "route", "-n", "get", "default",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                stdout, _ = await proc.communicate()
                for line in stdout.decode().split("\n"):
                    if "gateway" in line:
                        return line.split(":")[-1].strip()
            except Exception:
                pass
        return None
