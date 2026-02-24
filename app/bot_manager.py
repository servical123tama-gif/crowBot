"""
BotManager — singleton yang mengelola lifecycle BarbershopBot.

Bot berjalan di background thread dengan asyncio event loop sendiri.
Stop dilakukan via asyncio.Event (thread-safe, tidak paksa-kill thread).

Cara pakai:
    mgr = BotManager()
    mgr.start()   # nyalakan
    mgr.stop()    # matikan (graceful)
    mgr.status    # 'stopped' | 'starting' | 'running' | 'stopping'
"""
import threading
import asyncio
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class BotManager:
    """Thread-safe singleton untuk start/stop BarbershopBot."""

    _instance: Optional['BotManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._status = 'stopped'   # 'stopped' | 'starting' | 'running' | 'stopping'
        self._lock = threading.Lock()
        self.started_at: Optional[datetime] = None
        self.error_msg: Optional[str] = None

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def status(self) -> str:
        """Baca status bot; auto-koreksi jika thread mati tiba-tiba."""
        with self._lock:
            if self._status in ('running', 'starting', 'stopping'):
                if self._thread is None or not self._thread.is_alive():
                    self._status = 'stopped'
                    self._loop = None
                    self._stop_event = None
                    self.started_at = None
            return self._status

    @property
    def is_running(self) -> bool:
        return self.status == 'running'

    def start(self):
        """Nyalakan bot. Return (ok: bool, pesan: str)."""
        with self._lock:
            current = self._status
        if current in ('running', 'starting'):
            return False, 'Bot sudah berjalan.'

        with self._lock:
            self._status = 'starting'
            self.error_msg = None

        self._thread = threading.Thread(
            target=self._run_bot, name='BotThread', daemon=True
        )
        self._thread.start()
        return True, 'Bot sedang dinyalakan...'

    def stop(self):
        """Matikan bot secara graceful. Return (ok: bool, pesan: str)."""
        with self._lock:
            current = self._status
        if current != 'running':
            return False, 'Bot tidak sedang berjalan.'

        with self._lock:
            self._status = 'stopping'

        # Kirim sinyal stop ke asyncio event loop bot
        if self._loop and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)

        return True, 'Bot sedang dimatikan...'

    # ── Internal ──────────────────────────────────────────────────────────

    def _run_bot(self):
        """Entry point thread bot — buat event loop sendiri lalu jalankan."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._bot_async_main())
        except Exception as e:
            logger.error(f"Bot thread error: {e}", exc_info=True)
            with self._lock:
                self.error_msg = str(e)
        finally:
            with self._lock:
                self._status = 'stopped'
            self._loop = None
            self._stop_event = None
            self.started_at = None
            logger.info("Bot thread selesai.")

    async def _bot_async_main(self):
        """Logika async bot: init → polling → tunggu stop → shutdown."""
        # asyncio.Event harus dibuat di dalam event loop yang sama
        self._stop_event = asyncio.Event()

        logger.info("Bot thread: mengimpor dan menginisialisasi bot...")
        from app.bot import BarbershopBot
        bot_instance = BarbershopBot()
        ptb_app = bot_instance.app   # telegram.ext.Application

        # Jalankan bot secara manual (tidak pakai run_polling yang block sinyal OS)
        async with ptb_app:
            await ptb_app.start()
            await ptb_app.updater.start_polling(drop_pending_updates=True)

            with self._lock:
                self._status = 'running'
                self.started_at = datetime.now()
            logger.info("Bot berjalan (managed mode). Menunggu sinyal stop...")

            # Tunggu sampai stop() dipanggil dari Flask thread
            await self._stop_event.wait()

            logger.info("Sinyal stop diterima, mematikan bot...")
            await ptb_app.updater.stop()
            await ptb_app.stop()

        logger.info("Bot shutdown selesai.")
